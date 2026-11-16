"""The store's upkeep, one pass (`python -m score.dashboard sync`, the conductor's score-sync every 5 minutes): the
disk sweep, the library handover and sweep, the free design steps, the gaps, prepare's figure, the runner's price, the
basket a Buy buys from, the checkouts tidied and the USD check, each in words on the pass's one line. The hosted
cockpit it once fed went (owner, 2026-11-16: "cockpit can also go"); the owner's decisions and Buys come through the
agents' door only (sync/chat_decisions.py, checkout/chat_yes.py).

A pass runs only from a checkout whose tracked files are committed and whose commit origin's main holds
(tree_refusal), and makes the basket only once the runner has priced the gaps and the remake on it (`score price
<environment> --gaps`, after the gaps check): when either fails the pass stops there and says why."""
import json
import os
import signal
import subprocess
import sys

from django.conf import settings

from score.dashboard.launch import guard































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






















def checkouts_tidied(chosen):
    """The checkouts cared for (checkout/flow.tidied: one left launching by a process now gone failed, an ended
    batch's stop line taken back); its words, or why it could not be done (the pass goes on)."""
    from score.dashboard.checkout import flow
    try:
        return flow.tidied(chosen)
    except Exception as error:  # reported in the pass's line, never swallowed
        return f"checkouts not tidied: {type(error).__name__}: {error}"[:400]




def library_handing(world):
    """What accepted outputs have not reached the library, and their handover started when any have (python -m
    score.stages.library.handed --start: a failed one tried again, an accept no run or click handed taken up; the
    handover runs detached, minutes); its line, or why it failed. Before the sweep, which compares what was handed."""
    return step_line("score.stages.library.handed", "library handing failed", "--world", world, "--start")


def library_sweep():
    """The environment compared with its library (score.stages.library.sweep, free, seconds), its findings written where
    the place pages read their problems; its words. A sweep that fails is said in the pass's words, and the pass goes
    on: the export still goes out."""
    from score.stages.library import sweep
    try:
        return sweep.run()
    except Exception as error:  # reported in the pass's line, never swallowed
        return f"library sweep failed: {type(error).__name__}: {error}"


def readings_fixed(store_root):
    """Every locked place's reading fixed where it holds a part of another row's thing read as a thing of its own
    (score/review/reading_fixes.py: free, from its own rows and boxes), so the parts, light and plans after it in
    the pass are of the right rows; its words. One that fails is said, and the pass goes on."""
    from score.review import concepts, reading_fixes
    from score.store import Store
    store = Store.in_folder(store_root)
    try:
        return reading_fixes.said(reading_fixes.fix(store, concepts.placed(store), "the sync pass"))
    except Exception as error:  # reported in the pass's line, never swallowed
        return f"reading fixes failed: {type(error).__name__}: {error}"[:400]


def parts_read(store_root, ask=None):
    """The parts asked of every locked place whose reading's rows have none (score/review/reading.py parted), so the
    gaps, plans, prepare and price after it in the pass route those rows; its words (`asked_of_readings`)."""
    from score.review import reading
    return asked_of_readings(store_root, "parts", reading.unparted, reading.parted, ask)


def light_read(store_root, ask=None):
    """The concept's light (which rows glow, their colour and brightness, whether daylight lights the place) asked of
    every locked place whose reading has none (score/review/reading.py lit), so the plans kept after it in the pass
    carry it to the scene record's lamps, the light layer's fill and the environment plan's scene time; its words
    (`asked_of_readings`)."""
    from score.review import reading
    return asked_of_readings(store_root, "light", reading.unlit, reading.lit, ask)


def asked_of_readings(store_root, noun, missing_of, asked, ask=None):
    """One reading question asked of every locked place `missing_of` names (one model call a place under the
    reading's clearance, the owner's standing allowance of 2026-10-21, its cost kept where the cockpit's running total
    reads it); its words. The store at `store_root` (the pass's source's). Refused while Stop everything holds; one
    that fails is said, and the pass goes on."""
    from score.review import concepts
    from score.store import Store
    store = Store.in_folder(store_root)
    missing = missing_of(store, concepts.placed(store))
    if not missing:
        return f"{noun}: none missing"
    if free_only_followed():
        return f"{noun} not read for {len(missing)} places: refused, Stop everything holds (free only)"
    try:
        found = asked(store, missing, "the sync pass (the owner's standing allowance)", **({"ask": ask} if ask else {}))
    except Exception as error:  # reported in the pass's line, never swallowed
        return f"{noun} failed: {type(error).__name__}: {error}"[:400]
    return f"{noun} read: {len(found)} places, EUR {sum(record['euros']['total'] for record in found):.2f}"


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


USD_LIMIT = 900  # seconds: about a second a place measured; a stage of millions of faces must not hold the pass


def copies_swept():
    """The data disk's sweep (`python -m score.conductor sweep`, score/conductor/disk.py): every pass the frozen copies
    no run needs (2026-10-26: the conductor's disk filled with the copies of ended runs), the makes left in the store
    cache's making/ and the kept jobs no current key asks for; on a conductor under the warning line every step
    (2026-10-30, the owner: "this should be routine"); its summary line. A failure is said in the pass's words, and the
    pass goes on. Run first in the pass: a pass refused later must not leave the disk full."""
    done = step_run([sys.executable, "-m", "score.conductor", "sweep"])
    return (done.stdout.strip().splitlines() or [f"sweep wrote nothing, exit {done.returncode}"])[-1]


def usd_sweep(limit=USD_LIMIT):
    """Every place's composed stage judged by SCORE's USD rule set and its findings written where the place pages
    read their problems (score.stages.complete.usd, free, in a process of its own: it reads OpenUSD), ended after
    `limit` seconds; its summary line. Run after the pricing lock: nothing priced reads its findings, and a long
    check must not keep a Buy judged by its basket's commit alone. One that fails or runs out of time is said in the
    pass's words, and the pass goes on."""
    done = step_run([sys.executable, "-m", "score.stages.complete.usd"], limit=limit)
    if done.returncode != 0:
        return f"usd check failed: exit {done.returncode}: {(done.stderr.strip().splitlines() or ['no output'])[-1]}"
    return (done.stdout.strip().splitlines() or ["usd check wrote nothing"])[-1]


def step_run(command, grace=10, limit=None):
    """A pass step's command run to its end, or for at most `limit` seconds, in a process group of its own, its output
    kept; whatever it left running (a film preview's Chromium) ended with it, and the whole group ended when the pass
    is stopped (2026-10-25: a shrink left the preview's chrome-headless running after the unit stopped). A step out of
    time ends with a nonzero exit and says so as its last error line. A `score run --detach` it starts has a session
    of its own and is never ended here."""
    process = subprocess.Popen(command, cwd=settings.SCORE_REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    try:
        out, err = process.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        group_ended(process, grace)
        out, err = process.communicate()
        return subprocess.CompletedProcess(command, process.returncode or -1, out,
                                           f"{err}\nout of time after {limit} s")
    finally:
        group_ended(process, grace)
    return subprocess.CompletedProcess(command, process.returncode, out, err)


def group_ended(process, grace):
    """End a step's process group: SIGTERM, then SIGKILL to what is left after `grace` seconds."""
    for number in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, number)
        except ProcessLookupError:
            break
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            continue
        if not group_alive(process.pid):
            break
    process.wait()


def group_alive(group):
    """Whether any process is still in a process group."""
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return False
    return True


def step_line(module, failed, *args):
    """A free store-side step (`python -m <module> [args]`, in a process of its own) run once; its last line, or
    `failed` with its exit code and last error line. One that fails is said in the pass's words, and the pass goes
    on."""
    done = step_run([sys.executable, "-m", module, *args])
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
    local, its run detached; score.review.plans_pass: the same in seconds), so the batch is made from the plan his
    cockpit shows; its line."""
    return step_line("score.review.plans_pass", "plans failed")




def basket_benchmarks():
    """Prepare's benchmarks as the basket's one Benchmarks item (proposals/benchmarks.py), so the export carries this
    pass's estimate; its line."""
    from score.dashboard.proposals import benchmarks
    return benchmarks.put(settings.SCORE_HOME / "proposals", settings.SCORE_PROPS_HOME)


def basket_made(chosen):
    """The basket made again from the runner's plan on this checkout (proposals/make.py, free), so what Buy buys is what a run here buys now and the checkout reads a basket made after the design
    last changed; its line. One that fails is said in the pass's words, and the pass goes on (the checkout refuses
    the older basket)."""
    from score.dashboard.proposals import make
    try:
        made = make.make(settings.SCORE_HOME, settings.SCORE_PROPS_HOME / "store", chosen=chosen)
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
    """Why the pass may not run from the checkout, or None: a tracked file changed and not committed, origin's main
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


def sync_pass(source, chosen=None):
    """One pass of the store's upkeep; what it did, in words. Nothing runs from a checkout not clean and pushed, and a
    pass whose runner price fails stops there."""
    free_only_followed()
    copies = copies_swept()
    chosen = chosen or guard.backend()
    refused = tree_refusal(settings.SCORE_REPO)
    if refused:
        return f"REFUSED: nothing done: {refused}; {copies}"
    handing = library_handing(source.world.name)  # every accept to the library, a failed handover again (#40)
    swept = library_sweep()
    readings = readings_fixed(source.store_root)  # before the parts, light and plans: each reads its rows
    parts = parts_read(source.store_root)  # before the gaps, plans, prepare and price: each routes rows by part
    lights = light_read(source.store_root)  # before the plans kept: they carry it to the lamps and scene times
    gaps = gaps_sweep()
    planned = plans_kept()  # before prepare and the price: both read the plans the plan stage reads
    prepared, benched, pictured = remake_prepared(), basket_benchmarks(), library_pictures()
    demos = library_demos()
    priced, failed = runner_price(settings.SCORE_REPO, source.world.name)
    if failed:
        return (f"REFUSED: {failed}; {copies}; {handing}; {swept}; {readings}; {parts}; {lights}; {gaps}; {planned}; "
                f"{prepared}; {benched}; {pictured}; {demos}")
    basket = basket_made(chosen)  # after prepare (its benchmarks) and the price
    tidy = checkouts_tidied(chosen)
    usd = usd_sweep()
    return (f"{tidy}; {copies}; {swept}; {handing}; {readings}; {parts}; {lights}; {gaps}; {usd}; {priced}; {planned}; "
            f"{prepared}; {benched}; {basket}; {pictured}; {demos}")

