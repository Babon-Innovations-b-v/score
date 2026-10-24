"""The store side of hosted mode, one pass (`python -m score.dashboard sync`, the owner's timer every 5 minutes):
build the export and send what the hosted side lacks, pull the waiting requests, mark each picked up, apply it,
report its state; then poll the launches earlier passes started and report how they ended. Every call goes out from
the store's machine; a pass that fails leaves each request in its last reported state and the next pass goes on from
there.

The export is sent content-addressed (sync/endpoints.py): only the files the hosted side lacks, in the builder's
priority order, CHUNK bytes of a file per request, so no request nears TIMEOUT on a slow link; files not started within
PASS_SECONDS of upload (counted from the end of the build) wait for the next pass and the export committed meanwhile
names them "still uploading"; while one of its records (a .json) waits, nothing is committed. An export the
hosted side refuses (a format it cannot read) is said in the pass's words, and the requests are still applied.

A pass feeds the cockpit only from a checkout whose tracked files are committed and whose commit origin's main holds
(tree_refusal), and only once the runner has priced the gaps and the remake on it (`score price <environment>
--gaps`, after the gaps check): when either fails the pass syncs nothing and says why, so no stale record is ever
sent."""
import contextlib
import datetime
import fcntl
import gzip
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from django.conf import settings

from score.dashboard.launch import guard
from score.dashboard.pages.models import Launch
from score.dashboard.state import machine
from score.dashboard.sync import applying, building

TIMEOUT = 120
MACHINE_HEADER = "X-Score-Machine"  # this machine's name on every sync call (sync/endpoints.MACHINE_HEADER)
CHUNK = 2 * 1024 * 1024
PASS_SECONDS = 200.0
STILL = "still uploading"


class Refused(Exception):
    """The hosted side refused to swap in the export; its words."""


class Remote:
    """The hosted dashboard's sync endpoints, called with the token and this machine's name (the hosted side applies
    requests for the store's machine only, sync/one_store.py)."""

    def __init__(self, url, token, opener=urllib.request.urlopen, machine_name=None):
        self.url = url.rstrip("/")
        self.token = token
        self.opener = opener
        self.machine_name = machine_name or machine.identity(settings.SCORE_PROPS_HOME)["name"]
        self.not_the_store = None  # the hosted side's words when it refused a claim: not the store's machine

    def call(self, method, path, body=None, kind="application/json"):
        request = urllib.request.Request(f"{self.url}/api/sync{path}", data=body, method=method, headers={
            "Authorization": f"Bearer {self.token}", "Content-Type": kind, MACHINE_HEADER: self.machine_name})
        with self.opener(request, timeout=TIMEOUT) as answer:
            return json.loads(answer.read() or b"null")

    def lacking(self, sizes):
        """The shas of {sha: size} the hosted side does not hold."""
        return self.call("POST", "/lacking", json.dumps({"files": sizes}).encode())["missing"]

    def put_chunk(self, sha, offset, size, data):
        """Send `data` (raw bytes of the file at `offset`) gzipped; {"have", "done"}, or {"have"} when the hosted
        side holds a different length (409), to go on from."""
        try:
            return self.call("PUT", f"/blobs/{sha}?offset={offset}&size={size}", gzip.compress(data, 6),
                             "application/gzip")
        except urllib.error.HTTPError as answer:
            if answer.code != 409:
                raise
            return {**json.loads(answer.read()), "done": False, "conflict": True}

    def commit(self, name, files):
        """Swap the export in; Refused with the hosted side's words when it will not (409, an unreadable format)."""
        try:
            return self.call("POST", "/commit", json.dumps({"name": name, "files": files}).encode())
        except urllib.error.HTTPError as answer:
            if answer.code != 409:
                raise
            raise Refused(json.loads(answer.read() or b"{}").get("detail", f"refused ({answer.code})")) from answer

    def waiting(self, kinds=(), wait=0, skip=()):
        """The waiting requests (of `kinds` when given, less the ids `skip`); with `wait` the hosted side holds the
        call open up to that many seconds until one is there."""
        query = "".join([f"&kind={','.join(kinds)}" if kinds else "", f"&wait={wait}" if wait else "",
                         f"&skip={','.join(map(str, skip))}" if skip else ""])
        return self.call("GET", f"/requests?state=waiting{query}")

    def claim(self, request_id):
        """True when this caller took the waiting request, False when another took it first or this machine is not
        the store's (423: its words kept in `not_the_store`); a hosted side from before the claim (404) is told
        picked_up instead."""
        try:
            self.call("POST", f"/requests/{request_id}/claim")
        except urllib.error.HTTPError as answer:
            if answer.code == 409:
                return False
            if answer.code == 423:
                self.not_the_store = json.loads(answer.read() or b"{}").get("detail", "not the store's machine")
                return False
            if answer.code != 404:
                raise
            self.report(request_id, "picked_up")
        self.not_the_store = None  # the owner made this the store's machine since: no longer said
        return True

    def put_request_file(self, name, data):
        """One picture a request brought back, `<sha>-<side>.jpg`."""
        return self.call("PUT", f"/request-files/{name}", data, "image/jpeg")

    def report(self, request_id, state, detail="", log_tail=""):
        return self.call("POST", f"/requests/{request_id}", json.dumps(
            {"state": state, "detail": detail, "log_tail": log_tail}).encode())

    def note(self, request_id, detail):
        """Words on a request left waiting (why it waits); False from a hosted side before notes (404)."""
        try:
            self.call("POST", f"/requests/{request_id}/note", json.dumps({"detail": detail}).encode())
        except urllib.error.HTTPError as answer:
            if answer.code != 404:
                raise
            return False
        return True

    def put_batch_run(self, run):
        """The run monitor's record of the batch now (state/batch_run.py), between the passes' exports."""
        return self.call("PUT", "/batch-run", json.dumps(run, sort_keys=True).encode())


def folder_name(made_at):
    """The export's folder name on the hosted side: its made_at with no colons."""
    return made_at.replace(":", "")


def made_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def sha_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as read:
        for block in iter(lambda: read.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def listing(folder, written):
    """{path: (sha, size)} of the export's files in upload order: the builder's `written`."""
    return {path: (sha_of(folder / path), (folder / path).stat().st_size) for path in written}


def sent_file(remote, path, sha, size):
    """Send one file in CHUNK pieces, going on from what the hosted side already holds; the bytes sent."""
    offset, sent = 0, 0
    with open(path, "rb") as read:
        while True:
            read.seek(offset)
            data = read.read(CHUNK)
            answer = remote.put_chunk(sha, offset, size, data)
            sent += 0 if answer.get("conflict") else len(data)
            if answer["done"]:
                return sent
            if answer["have"] == offset and data:
                raise RuntimeError(f"{path.name}: the hosted side took none of the chunk at {offset}")
            offset = answer["have"]


def uploaded(remote, folder, files, missing, deadline):
    """Send the missing files in order until `deadline` (time.monotonic) passes; (shas now held, bytes sent)."""
    held, sent = set(), 0
    for path, (sha, size) in files.items():
        if sha not in missing or sha in held:
            continue
        if time.monotonic() > deadline:
            break
        sent += sent_file(remote, folder / path, sha, size)
        held.add(sha)
    return held, sent


def with_still_uploading(manifest, files, waiting):
    """The manifest with each file still to come named in left_out and bytes counting what is in."""
    later = [path for path, (sha, _) in files.items() if sha in waiting]
    return {**manifest, "bytes": sum(size for path, (_, size) in files.items() if path not in later),
            "left_out": [*manifest["left_out"], *({"what": path, "why": STILL} for path in later)]}


def committed(remote, folder, manifest, present):
    """Write and send the final manifest, then commit it with the files the hosted side holds; the bytes sent."""
    path = folder / "manifest.json"
    path.write_text(json.dumps(manifest, indent=1))
    own, size = sha_of(path), path.stat().st_size
    sent = sent_file(remote, path, own, size) if remote.lacking({own: size}) else 0
    remote.commit(folder_name(manifest["made_at"]), {**present, "manifest.json": own})
    return sent


def push_export(remote, source, chosen):
    """Build the export in a temporary folder and send what the hosted side lacks, then commit it unless one of its
    records (a .json) is still to come: the hosted side then keeps its last whole export; what was sent."""
    with tempfile.TemporaryDirectory(dir=settings.SCORE_HOME) as made:
        folder = pathlib.Path(made)
        manifest = building.build(source, folder, made_now(), settings.SCORE_EXPORT_MAX_MB, chosen.spend(),
                                  settings.SCORE_REPO)
        deadline = time.monotonic() + PASS_SECONDS  # the upload's time: a build past it sent nothing (2026-10-21)
        files = listing(folder, manifest["written"])
        missing = set(remote.lacking({sha: size for sha, size in files.values()}))
        held, sent = uploaded(remote, folder, files, missing, deadline)
        waiting = missing - held
        manifest = with_still_uploading(manifest, files, waiting)
        whole = not any(path.endswith(".json") for path, (sha, _) in files.items() if sha in waiting)
        if whole:
            sent += committed(remote, folder, manifest, {path: sha for path, (sha, _) in files.items()
                                                           if sha not in waiting})
    return {"made_at": manifest["made_at"], "files": len([path for path, (sha, _) in files.items() if sha in held]),
            "bytes": sent, "committed": whole,
            "to_come": len({path for path, (sha, _) in files.items() if sha in waiting}),
            "left_out": manifest["left_out"]}


def tracked_path():
    return settings.SCORE_HOME / "sync" / "launches.json"


def tracked():
    """{hosted request id: local launch id} of launches still being reported."""
    path = tracked_path()
    return json.loads(path.read_text()) if path.is_file() else {}


def tracked_changed(change):
    """`change(found)` of the followed launches, read and written under a lock: the listener and a pass both add."""
    path = tracked_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        found = tracked()
        change(found)
        path.write_text(json.dumps(found, indent=1))


LATCHED = {"set": False}  # whether free_only_followed set SCORE_FREE_ONLY here (only then does it take it off)


def free_only_followed():
    """Mirror the owner's kill switch latch (score.conductor's free-only file) into this process's environment, so
    the sync pass, the listener and every process they start spend nothing while it holds, and again once he
    allows paid work; whether it holds. Off a conductor's code nothing changes."""
    try:
        from score import conductor
    except ModuleNotFoundError:
        return False
    if conductor.free_only():
        if os.environ.get(conductor.FREE_ONLY) != "1":
            os.environ[conductor.FREE_ONLY] = "1"
            LATCHED["set"] = True
        return True
    if LATCHED["set"]:
        os.environ.pop(conductor.FREE_ONLY, None)
        LATCHED["set"] = False
    return False


def answered(remote, item, source, chosen=None):
    """Claim one waiting request, apply it, send back the pictures it brought and report it, its launch followed
    (report_launches); the Applied, or None when another caller (the listener, sync/listen.py, or a pass) took it
    first, or when it is a Buy that waits for the next pass (buy_waits: said on the request, left waiting)."""
    waits = buy_waits(source) if item["kind"] == "checkout" else None
    if waits:
        remote.note(item["id"], f"waits for the next sync pass: {waits}")
        return None
    if not remote.claim(item["id"]):
        return None
    free_only_followed()
    applied = applying.apply(item, source, chosen)
    for name, path in applied.files.items():
        remote.put_request_file(name, pathlib.Path(path).read_bytes())
    remote.report(item["id"], applied.state, applied.detail, applied.log_tail)
    if applied.launch_id:
        tracked_changed(lambda found: found.update({str(item["id"]): applied.launch_id}))
    return applied


def apply_waiting(remote, source, chosen):
    """Pick up, apply and report each waiting request; [(id, state)]."""
    done = []
    for item in remote.waiting():
        applied = answered(remote, item, source, chosen)
        if applied is not None:
            done.append((item["id"], applied.state))
    return done


def report_launches(remote, chosen):
    """Report each followed launch that ended (done, else refused: the hosted side's states have no failed, so the
    run's own state leads its words); [(id, state)]."""
    reported = []
    for request_id, launch_id in tracked().items():
        record = guard.polled(Launch.objects.get(pk=launch_id), chosen)
        if record.state in ("running", "starting"):
            continue
        tail = "\n".join(item.get("log_tail", "") for item in record.handles)[-4000:]
        said = record.result if record.state == "done" else f"{record.state}: {record.result}"
        remote.report(int(request_id), "done" if record.state == "done" else "refused", said, tail)
        reported.append((int(request_id), record.state))
        tracked_changed(lambda found, ended=request_id: found.pop(ended, None))
    return reported


def pass_lock():
    return settings.SCORE_HOME / "sync" / "pass.lock"


@contextlib.contextmanager
def pricing_now():
    """Held while a pass prices and makes its export (sync_pass), so the listener leaves a Buy to the pass then."""
    pass_lock().parent.mkdir(parents=True, exist_ok=True)
    with pass_lock().open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def pass_pricing():
    """Whether a sync pass holds pricing_now."""
    if not pass_lock().is_file():
        return False
    with pass_lock().open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False


def record_of(path):
    return json.loads(path.read_text()) if path.is_file() else None


def figures_moved(source, now):
    """Why the pass's figures do not price the code at commit `now`, in words: the runner's price or prepare's figure
    made on other code (or not made), the basket made on another commit or before prepare's figure; [] when they
    stand."""
    from score.dashboard.proposals import records
    from score.dashboard.state import local
    checks = source.props_home / "work" / local.CHECKS
    figures = (("the runner's price", record_of(checks / local.GAPS_PRICE / f"{source.world.name}.json")),
               ("prepare's figure", record_of(checks / local.REMAKE)))
    found = []
    for name, written in figures:
        moved = "it is not made yet" if written is None else local.code_moved(written.get("priced_on"))
        if moved:
            found.append(f"{name}: {moved}")
    index = records.index(settings.SCORE_HOME / "proposals")
    if index.get("commit") != now:
        found.append(f"the basket was made on commit {str(index.get('commit'))[:8]}, the code is at {str(now)[:8]}")
    remake = figures[1][1]
    made = datetime.datetime.fromisoformat(index["made_at"]) if index.get("made_at") else None
    if remake and made and datetime.datetime.fromisoformat(remake["made_at"]).replace(microsecond=0) > made:
        found.append(f"the basket was made at {index['made_at']}, before prepare's figure ({remake['made_at']})")
    return found


def buy_waits(source):
    """Why a hosted Buy is left for the next sync pass rather than applied now, in words, or None: a pass pricing
    now, the checkout not clean and pushed (tree_refusal), or figures_moved. The pass makes them again, then applies
    it; every other refusal is the checkout's own (checkout/flow.py)."""
    if pass_pricing():
        return "a sync pass is pricing now; it applies this Buy once its price stands"
    refused = tree_refusal(settings.SCORE_REPO)
    if refused:
        return refused
    return "; ".join(figures_moved(source, head(settings.SCORE_REPO))) or None


def checkouts_tidied(chosen):
    """The checkouts cared for (checkout/flow.tidied: one left launching by a process now gone failed, an ended
    batch's stop line taken back); its words, or why it could not be done (the pass goes on)."""
    from score.dashboard.checkout import flow
    try:
        return flow.tidied(chosen)
    except Exception as error:  # reported in the pass's line, never swallowed
        return f"checkouts not tidied: {type(error).__name__}: {error}"[:400]


def pushed_words(remote, source, chosen):
    """Push the export; what was sent in words, or the hosted side's refusal."""
    try:
        pushed = push_export(remote, source, chosen)
    except Refused as refused:
        return f"REFUSED: the hosted side did not take the export: {refused}"
    return (f"pushed the export of {pushed['made_at']}: {pushed['files']} files sent ({pushed['bytes'] / 1e6:.1f} MB), "
            f"{pushed['to_come']} still to come" + ("" if pushed["committed"] else ", records among them: not swapped in"))


def library_sweep():
    """The environment compared with its library (score.stages.library.sweep, free, seconds), its findings written where
    the place pages read their problems; its words. A sweep that fails is said in the pass's words, and the pass goes
    on: the export still goes out."""
    from score.stages.library import sweep
    try:
        return sweep.run()
    except Exception as error:  # reported in the pass's line, never swallowed
        return f"library sweep failed: {type(error).__name__}: {error}"


def gaps_sweep():
    """Every place's gaps written where the place pages read them (score.stages.complete.gaps, free, seconds, in a
    process of its own: it reads OpenUSD); its summary line. One that fails is said in the pass's words, and the pass
    goes on."""
    done = subprocess.run([sys.executable, "-m", "score.stages.complete.gaps"], cwd=settings.SCORE_REPO,
                          capture_output=True, text=True)
    if done.returncode != 0:
        said = (done.stderr.strip().splitlines() or ["no output"])[-1]
        return f"gaps failed: exit {done.returncode}: {said}"
    return (done.stdout.strip().splitlines() or ["gaps wrote nothing"])[-1]


def step_line(module, failed, *args):
    """A free store-side step (`python -m <module> [args]`, in a process of its own) run once; its last line, or
    `failed` with its exit code and last error line. One that fails is said in the pass's words, and the pass goes
    on."""
    done = subprocess.run([sys.executable, "-m", module, *args], cwd=settings.SCORE_REPO, capture_output=True,
                          text=True)
    if done.returncode != 0:
        return f"{failed}: exit {done.returncode}: {(done.stderr.strip().splitlines() or ['no output'])[-1]}"
    return (done.stdout.strip().splitlines() or [f"{module} wrote nothing"])[0]


def remake_prepared():
    """Prepare's one-shot figure of the remake written where the pages read it (score.stages.complete.prepare,
    free, local, seconds), so the cockpit's remake price is this checkout's; its line."""
    return step_line("score.stages.complete.prepare", "prepare failed")


def plans_kept():
    """Every place's plan (made from its picked concept and its inventory, or his edit) where the plan stage reads
    it, and the plan row made again for those that changed or are not made yet (score.review.plans keep, free,
    local, its run detached), so the batch is made from the plan his cockpit shows; its line."""
    return step_line("score.review.plans", "plans failed", "keep")


def basket_benchmarks():
    """Prepare's benchmarks as the basket's one Benchmarks item (proposals/benchmarks.py), so the export carries this
    pass's estimate; its line."""
    from score.dashboard.proposals import benchmarks
    return benchmarks.put(settings.SCORE_HOME / "proposals", settings.SCORE_PROPS_HOME)


def basket_made(chosen):
    """The basket made again from the runner's plan on this checkout (proposals/make.py, plan only: free, no place
    assembled), so what Buy buys is what a run here buys now and the checkout reads a basket made after the design
    last changed; its line. One that fails is said in the pass's words, and the pass goes on (the checkout refuses
    the older basket)."""
    from score.dashboard.proposals import make
    try:
        made = make.make(settings.SCORE_HOME, settings.SCORE_PROPS_HOME / "store", chosen=chosen, plan_only=True)
    except Exception as error:  # reported in the pass's line, never swallowed
        return f"basket failed: {type(error).__name__}: {error}"[:400]
    return f"basket made: {len(made['items'])} items, {sum(len(item['nodes']) for item in made['items'])} paid steps"


def library_pictures():
    """The library's pictures and its item pages' viewer files fetched into the library cache
    (score.stages.library.pictures: one object read each the first time, then a hash check), so the tiles, the item
    pages and the export have their bytes; its line."""
    return step_line("score.stages.library.pictures", "library pictures failed")


def library_demos():
    """Each library algorithm's demo, made from real data into the library cache (score.stages.library.demos: free,
    local, its files fetched once), so its item page shows its work and the export carries it; its line."""
    return step_line("score.stages.library.demos", "library demos failed")


def git(repo, *args):
    """A git command's run in `repo` (its exit code and output kept, never raised)."""
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def tree_refusal(repo):
    """Why the checkout may not feed the cockpit, or None: a tracked file changed and not committed, origin's main
    not read, or a commit origin's main does not hold (not pushed)."""
    changed = git(repo, "status", "--porcelain", "--untracked-files=no")
    if changed.returncode != 0 or changed.stdout.strip():
        return f"{repo} has changes not committed: commit and push them first"
    fetched = git(repo, "fetch", "-q", "origin", "main")
    if fetched.returncode != 0:
        return f"origin's main could not be read ({(fetched.stderr.strip().splitlines() or ['no output'])[-1]})"
    head = git(repo, "rev-parse", "--short=8", "HEAD").stdout.strip()
    if git(repo, "merge-base", "--is-ancestor", "HEAD", "FETCH_HEAD").returncode != 0:
        return f"commit {head} is not on origin's main: push it first"
    return None


def head(repo):
    """The checkout's commit, or None when git cannot say."""
    return git(repo, "rev-parse", "HEAD").stdout.strip() or None


def runner_price(repo, world):
    """(its words, why it failed or None) of the runner's price of the environment's gaps and remake (`score price
    <world> --gaps --json`, free and local, in a process of its own), written where the pages read it."""
    done = subprocess.run([sys.executable, "-m", "score", "price", world, "--gaps", "--json"], cwd=repo,
                          capture_output=True, text=True)
    if done.returncode != 0:
        return None, f"the runner's price failed: exit {done.returncode}: " + (
            (done.stderr.strip().splitlines() or ["no output"])[-1])
    try:
        totals = json.loads(done.stdout)["totals"]
    except (ValueError, KeyError, TypeError) as unread:
        return None, f"the runner's price wrote no totals ({type(unread).__name__}: {unread})"
    return (f"priced by the runner: EUR {totals['likely_euros']:.2f} to {totals['high_euros']:.2f} measured, "
            f"{len(totals['unpriced'])} paid steps with no measured price"), None


def refused_words(why):
    """A pass that synced nothing, in words."""
    return f"REFUSED: nothing synced: {why}"


def sync_pass(remote, source, chosen=None):
    """One pass; what it did, in words. Nothing is synced from a checkout not clean and pushed, when the runner's
    price fails; the export is pushed even when the checkout moved to another commit during the pass, so his locks and
    designs reach the cockpit while agents push (owner 2026-10-21, "my concepts still not back"): prepare's and the
    price's records name the commit they were made on, so the cockpit shows those figures stale and Buy waits."""
    free_only_followed()
    chosen = chosen or guard.backend()
    with pricing_now():  # the listener leaves a Buy to this pass meanwhile (buy_waits)
        refused = tree_refusal(settings.SCORE_REPO)
        if refused:
            return refused_words(refused)
        started = head(settings.SCORE_REPO)
        swept = library_sweep()
        gaps = gaps_sweep()
        planned = plans_kept()  # before prepare and the price: both read the plans the plan stage reads
        prepared, benched, pictured = remake_prepared(), basket_benchmarks(), library_pictures()
        demos = library_demos()
        priced, failed = runner_price(settings.SCORE_REPO, source.world.name)
        if failed:
            return refused_words(f"{failed}; {swept}; {gaps}; {planned}; {prepared}; {benched}; {pictured}; {demos}")
        basket = basket_made(chosen)  # after prepare (its benchmarks) and the price, before the export carries it
        now = head(settings.SCORE_REPO)
        pushed = pushed_words(remote, source, chosen) + ("" if now == started else (
            f" (the checkout moved from {str(started)[:8]} to {str(now)[:8]} during the pass: its remake and price "
            "show as stale, Buy waits for the next pass)"))
    tidy = checkouts_tidied(chosen)
    applied = apply_waiting(remote, source, chosen)
    ended = report_launches(remote, chosen)
    refused = f" (none applied here: {remote.not_the_store})" if remote.not_the_store else ""
    return (f"{pushed}; applied {len(applied)} requests{refused}; {len(ended)} launches ended; {tidy}; {swept}; "
            f"{gaps}; {priced}; {planned}; {prepared}; {benched}; {basket}; {pictured}; {demos}")
