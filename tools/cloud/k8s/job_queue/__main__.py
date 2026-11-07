"""The box's job queue process: one a box, started on demand by a client (`job_queue.start`), it runs every run handed
to it on warm workers of the run's chain (image kind, image, commit), so a pull, a node's set-up and an environment's
set-up are paid once a chain, not once a job.

    python3 tools/cloud/k8s/job_queue/__main__.py [--root <queue folder>]

One tick every QUEUE_TICK seconds:
1. three looks at the cluster: the box's Jobs and pods (by `score.dev/box`), the nodes, and the quota's room;
2. the inbox (new runs) and each worker's beat in the job store;
3. finished jobs noted (a worker gone without its job's done.json gives the job back, one generation on), then
   assign (admission.py: priority, places round robin, a worker of the job's chain and band, the same place's worker
   first), tell idle workers to go, and grow workers while the quota's room and this box's share allow (one apply);
4. money: each node any of the box's pods ran on is counted once, its minutes at its price; a node gone is booked as
   one ledger row. At the lowest stop line of the open runs nothing more is assigned or made and only this box's Jobs
   are deleted.

Every control file is small and lives under the queue folder; the jobs' bytes are in the job store. A restarted queue
reads its runs from `state/`, every assignment back from the job store, and the workers from their labels and beats,
so a job is assigned once unless its worker is gone without its done.json.
"""
import argparse
import fcntl
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import admission  # noqa: E402
import job_queue as client  # noqa: E402
import ledger  # noqa: E402
import manifests  # noqa: E402
import submitter  # noqa: E402
import workers  # noqa: E402

QUEUE_TICK = 10
QUEUE_IDLE_EXIT_SECONDS = 600  # the process ends once it has had no open run and no worker this long
OVER = ("done", "failed", "stopped", client.ELSEWHERE)


def say(line):
    print(time.strftime("%H:%M:%S ") + line, flush=True)


class Queue:
    """The box's queue: its open runs, the assignments, the workers it made and the nodes it pays for."""

    def __init__(self, kubectl, store, cluster, root=None, box=None, clock=time.time):
        self.kubectl, self.store, self.cluster, self.clock = kubectl, store, cluster, clock
        self.root = client.root_of(root)
        self.box = manifests.label_value(box or manifests.box())
        self.tolerations = getattr(cluster, "TOLERATIONS", ())
        self.started = clock()
        self.runs = {path.stem: json.loads(path.read_text()) for path in sorted((self.root / "state").glob("*.json"))}
        self.runs = {run: state for run, state in self.runs.items() if not state.get("over")}
        self.seqs, self.last_place, self.told_go, self.idle_since = {}, {}, set(), {}
        self.after, self.widening, self.made = {}, {}, 0
        money = client.read_json(self.root / "money.json") or {}
        self.nodes, self.booked = money.get("nodes", {}), money.get("booked", 0.0)
        self.read_assignments()

    # The job store.

    def done(self, run, job_id):
        return self.store.exists(f"runs/{run}/{job_id}/done.json")

    def read_assignments(self):
        """Every assignment back from the job store: each worker's last seq and place, the workers told to go, and each
        job's newest assignment taken as its state (an assignment written just before a crash, its state not)."""
        for key in self.store.keys(f"{workers.store_prefix(self.box)}/assign/"):
            worker, name = key.split("/")[-2:]
            seq = int(name.split(".")[0])
            given = json.loads(self.store.read_bytes(key))
            if seq >= self.seqs.get(worker, -1):
                self.seqs[worker] = seq
                self.last_place[worker] = given.get("place")
            if given.get("go"):
                self.told_go.add(worker)
                continue
            record = self.runs.get(given["run"], {}).get("jobs", {}).get(given["job"])
            if record and record["state"] in ("queued", "assigned") and given["generation"] >= record["generation"]:
                record.update(state="assigned", worker=worker, seq=seq, generation=given["generation"])

    def read_beats(self):
        beats = {}
        for key in self.store.keys(f"{workers.store_prefix(self.box)}/beat/"):
            beats[key.split("/")[-1].removesuffix(".json")] = json.loads(self.store.read_bytes(key))
        return beats

    def assign(self, worker, value):
        """Write the worker's next assignment; its seq."""
        seq = self.seqs.get(worker, -1) + 1
        self.store.write_bytes(workers.assignment_key(self.box, worker, seq), json.dumps(value).encode())
        self.seqs[worker] = seq
        return seq

    # The runs.

    def take_inbox(self):
        """New runs from the inbox, their state written before the inbox file goes, after the runs their clients took
        back (`take_cancels`). A job whose done.json is already in the job store (a resumed run) is done at once."""
        self.take_cancels()
        for path in sorted((self.root / "inbox").glob("*.json")):
            entry = client.read_json(path)
            if entry is None:
                continue
            try:
                if entry["run"] not in self.runs:
                    self.runs[entry["run"]] = self.intake(entry)
                    self.write_state(entry["run"])
            except (Exception, SystemExit) as error:  # noqa: BLE001  one bad entry refused, not the queue
                self.refuse_entry(path, entry, error)
            path.unlink(missing_ok=True)

    def refuse_entry(self, path, entry, error):
        """A run the queue cannot take (its inbox entry raised: card and processor classes mixed, tube rehearsal
        2026-11-07, when the process exited and the box's queue with it): its state written over, each job failed and
        why, so its client's wait returns and its runner makes or blocks those nodes; the queue goes on."""
        why = f"refused by the queue: {type(error).__name__}: {error}"
        say(f"{path.name}: {why}")
        run = str(entry.get("run") or path.stem) if isinstance(entry, dict) else path.stem
        specs = entry.get("specs") if isinstance(entry, dict) and isinstance(entry.get("specs"), dict) else {}
        client.write_whole(self.root / "state" / f"{run}.json", {
            "run": run, "over": True, "refused": why, "jobs": {job_id: {"state": "failed"} for job_id in specs}})

    def take_cancels(self):
        """Each run its client took back (`cancel/<run>`, job_queue.cancel): its inbox file dropped and, when it is
        open here, its jobs not over stopped and the run over, so none of its jobs is assigned again."""
        for path in sorted((self.root / "cancel").glob("*")):
            run = path.name
            (self.root / "inbox" / f"{run}.json").unlink(missing_ok=True)
            if run in self.runs:
                for record in self.runs[run]["jobs"].values():
                    if record["state"] not in OVER:
                        record["state"] = "stopped"
                self.runs[run].update(over=True, stopped="taken back by its client")
                self.write_state(run)
            path.unlink()

    def intake(self, entry):
        jobs = {}
        for job_id, spec in entry["specs"].items():
            cards = submitter.job_cards(spec, entry["classes"])
            jobs[job_id] = {"state": "done" if self.done(entry["run"], job_id) else "queued", "cards": cards,
                            "band": admission.band_of(spec, cards), "generation": 0, "worker": None, "seq": None,
                            "node": None}
        return {"run": entry["run"], "chain": [entry["kind"], entry["image"], entry.get("code") or ""],
                "classes": entry["classes"], "priority": entry["priority"], "place": entry["place"],
                "stop_line": entry.get("stop_line"), "who": entry.get("who"), "jobs": jobs, "over": False}

    def queued(self):
        """The queued jobs as admission sees them."""
        return [{"key": f"{run}/{job_id}", "run": run, "job": job_id, "chain": tuple(state["chain"]),
                 "band": record["band"], "cards": record["cards"], "priority": state["priority"],
                 "place": state["place"]}
                for run, state in self.runs.items() for job_id, record in state["jobs"].items()
                if record["state"] == "queued"]

    def note_finished(self, listed, beats):
        """A job its worker has moved past is done (its done.json) or failed; a job whose worker is gone without its
        done.json goes back on the queue one generation on. A run whose jobs are all over is over."""
        for run, state in self.runs.items():
            for job_id, record in state["jobs"].items():
                if record["state"] != "assigned":
                    continue
                beat, worker = beats.get(record["worker"]), listed.get(record["worker"])
                if worker and worker["node"]:
                    record["node"] = worker["node"]
                if beat and beat["seq"] >= record["seq"] and beat.get("job") != f"{run}/{job_id}":
                    record["state"] = "done" if self.done(run, job_id) else "failed"
                elif workers.gone(worker):
                    if self.done(run, job_id):
                        record["state"] = "done"
                    else:
                        say(f"{run}/{job_id}: worker {record['worker']} gone; queued again")
                        record.update(state="queued", worker=None, seq=None, generation=record["generation"] + 1)
                if record["state"] in OVER and record["node"] in self.nodes:  # it ended this tick
                    self.nodes[record["node"]]["jobs"].append(f"{run}/{job_id}")
            state["over"] = all(record["state"] in OVER for record in state["jobs"].values())

    # The workers.

    def idle(self, listed, beats, now):
        """The running workers with nothing to do: their beat at their last assignment and no job on."""
        found = []
        for worker_id, worker in listed.items():
            beat = beats.get(worker_id)
            if worker["phase"] != "Running" or worker_id in self.told_go or not beat or beat.get("job"):
                continue
            if beat["seq"] < self.seqs.get(worker_id, -1):
                continue
            self.idle_since.setdefault(worker_id, now)
            found.append({"id": worker_id, "chain": worker["chain"], "band": worker["band"],
                          "cards": worker["cards"], "last_place": self.last_place.get(worker_id)})
        return found

    def give_out(self, idle, now):
        """Assign queued jobs to idle workers (admission's order and choice); the workers still idle."""
        pairs = admission.assignments(admission.ordered(self.queued(), self.after), idle)
        for job, worker in pairs:
            record = self.runs[job["run"]]["jobs"][job["job"]]
            seq = self.assign(worker["id"], {"run": job["run"], "job": job["job"], "generation": record["generation"],
                                             "place": job["place"], "at": now})
            record.update(state="assigned", worker=worker["id"], seq=seq)
            self.last_place[worker["id"]] = job["place"]
            self.after[job["priority"]] = job["place"]
            self.idle_since.pop(worker["id"], None)
        taken = {worker["id"] for _job, worker in pairs}
        return [worker for worker in idle if worker["id"] not in taken]

    def send_home(self, idle, now):
        """Tell an idle worker to go once nothing it serves is queued and: a job of another chain waits for the room it
        holds (cards for cards), or nothing of its image is expected and it has idled WORKER_IDLE_SECONDS, or it has
        idled WORKER_EXPECTED_SECONDS."""
        queued = self.queued()
        expected = workers.expected(self.root)
        for worker in idle:
            if any(job["chain"] == worker["chain"] and admission.serves(worker["band"], job["band"]) for job in queued):
                continue
            others_wait = any(job["chain"] != worker["chain"] and bool(job["cards"]) == bool(worker["cards"])
                              for job in queued)
            idle_for = now - self.idle_since[worker["id"]]
            if (others_wait or (not expected.get(worker["chain"][0]) and idle_for >= workers.WORKER_IDLE_SECONDS)
                    or idle_for >= workers.WORKER_EXPECTED_SECONDS):
                self.assign(worker["id"], {"go": True, "at": now})
                self.told_go.add(worker["id"])
                self.idle_since.pop(worker["id"], None)

    def classes_of(self, chain, listed, now):
        """The classes a new worker of the chain may take: its runs' classes one at a time, one more each time its
        waiting workers show the ones it has cannot be had (submitter's widening rules); the waiting workers of a
        widened chain are deleted, so they are made again on the wider classes."""
        order = next(state["classes"] for state in self.runs.values() if tuple(state["chain"]) == chain)
        kind = chain[0]
        widening = self.widening.setdefault(chain, {"step": 1, "since": now, "first": now})
        late = set(submitter.capacity.late_for(kind)) & set(order)
        waiting = [(submitter.unscheduled_since(worker["pod"]), None) for worker in listed.values()
                   if worker["chain"] == chain and worker["pod"] and worker["phase"] == "Pending"
                   and submitter.unscheduled_since(worker["pod"]) is not None]
        if submitter.may_widen(widening, order, late, now) and submitter.wants_widening(widening, waiting, now):
            widening.update(step=widening["step"] + 1, since=now)
            for worker in listed.values():
                if worker["chain"] == chain and worker["phase"] == "Pending":
                    self.kubectl.delete_job(worker["job"])
                    worker["phase"] = "Failed"
        return order[:widening["step"]]

    def widen_pending(self, listed, now):
        """Each open chain with a worker pending asks its widening every tick (classes_of), not only when a new worker
        is made: a pending worker is its jobs' spare, so no new worker came and a worker on a class out of stock
        waited for good (tube rehearsal 2026-11-07, 17 min on cpu-64c-128gb)."""
        open_chains = {tuple(state["chain"]) for state in self.runs.values()}
        pending = {worker["chain"] for worker in listed.values()
                   if worker["phase"] == "Pending" and worker["id"] not in self.told_go}
        for chain in sorted(pending & open_chains):
            self.classes_of(chain, listed, now)

    def send_elsewhere(self, listed, now):
        """A chain of processor classes alone, widened to its last class, whose pending workers still got no node in
        a further NODE_MINUTES (its start window): its classes noted as not to be had (`unhad.json`, job_queue.unhad),
        its pending workers deleted and its queued jobs given back as `elsewhere`, so their runners send that
        processor work to rented machines instead of waiting (owner's coordinator, 2026-11-07: the big CPU classes in
        shortage in every Paris zone, in stock in nl-ams-2, pl-waw-1 and pl-waw-3). Card work stays here."""
        for chain, widening in list(self.widening.items()):
            runs = [state for state in self.runs.values() if tuple(state["chain"]) == chain]
            order = runs[0]["classes"] if runs else []
            if not order or any(submitter.provider.cards(name) for name in order) or widening["step"] < len(order):
                continue
            pending = [worker for worker in listed.values() if worker["chain"] == chain
                       and worker["phase"] == "Pending" and worker["pod"]]
            waiting = [(submitter.unscheduled_since(worker["pod"]), None) for worker in pending
                       if submitter.unscheduled_since(worker["pod"]) is not None]
            if not submitter.wants_widening(widening, waiting, now):
                continue
            say(f"{', '.join(order)}: no node in {submitter.NODE_MINUTES} min; the chain's work goes to rented machines")
            client.write_whole(self.root / client.UNHAD, {**(client.read_json(self.root / client.UNHAD) or {}),
                                                          **dict.fromkeys(order, now)})
            for worker in pending:
                self.kubectl.delete_job(worker["job"])
                worker["phase"] = "Failed"
            for state in runs:
                for record in state["jobs"].values():
                    if record["state"] == "queued":
                        record["state"] = client.ELSEWHERE
                state["over"] = all(record["state"] in OVER for record in state["jobs"].values())
            del self.widening[chain]

    def grow(self, listed, beats, room, now):
        """Make workers for the queued jobs no idle or starting worker will take, in admission's order, while a new
        worker's pod fits the quota's room (less this tick's own) and this box's share: one apply. A chain whose
        pending workers show its classes cannot be had is widened first (widen_pending)."""
        self.widen_pending(listed, now)
        self.send_elsewhere(listed, now)
        live = [worker for worker in listed.values() if not workers.gone(worker) and worker["id"] not in self.told_go]
        use = {}
        for worker in live:
            for name, value in submitter.quota_demand(workers.requests_of(worker["band"]), worker["cards"]).items():
                use[name] = use.get(name, 0) + value
        room = admission.room_left(room, admission.shares(), use)
        starting = [worker for worker in live if worker["phase"] != "Running" or worker["id"] not in beats]
        made = []
        for job in admission.ordered(self.queued(), self.after):
            spare = next((worker for worker in starting if worker["chain"] == job["chain"]
                          and admission.serves(worker["band"], job["band"])), None)
            if spare:
                starting.remove(spare)
                continue
            demand = submitter.quota_demand(workers.requests_of(job["band"]), job["cards"])
            if not submitter.fits(demand, room):
                continue
            self.made += 1
            worker_id = f"{manifests.name_part(job['chain'][0])}-{job['band'].lower()}-{int(now)}-{self.made}"
            made.append(workers.manifest(self.box, worker_id, job["chain"], job["band"],
                                         self.classes_of(job["chain"], listed, now), job["cards"], self.tolerations))
            room = admission.less(room, demand)
        if made:
            self.kubectl.apply([workers.configmap(), *made])  # the loop they mount comes in the same apply
        return made

    # Money.

    def count_money(self, items, nodes, now):
        """The box's euros: each node a pod of the box is or was on, counted once, from its creation (or from when the
        box first saw it, for a node up before the queue) to now, or once no live pod of the box is on it (a finished
        worker's pod is kept with its Job for KEEP_SECONDS, never hosting) to its removal (at most the autoscaler's
        idle tail); a node gone, or past that tail, is booked."""
        hosting = {item["spec"].get("nodeName") for item in items if item.get("kind") == "Pod"
                   and item.get("status", {}).get("phase") not in ("Succeeded", "Failed")}  # a finished pod holds no node
        listed = {node["metadata"]["name"]: node for node in nodes}
        for name in hosting & set(listed):
            meta = listed[name]["metadata"]
            if name not in self.nodes:
                created = submitter.parse_time(meta.get("creationTimestamp")) or now
                labels = meta.get("labels", {})
                self.nodes[name] = {"created": created if created >= self.started else now,
                                    "type": (labels.get(submitter.INSTANCE_LABEL) or "?").upper(),
                                    "zone": labels.get(submitter.ZONE_LABEL) or "?",
                                    "class": submitter.provider.capability_class(labels.get(manifests.CLASS_LABEL)),
                                    "jobs": []}
        tail = submitter.IDLE_ESTIMATE_MINUTES * 60  # an empty node's last minutes before the autoscaler takes it
        for name, seen in list(self.nodes.items()):
            if name in hosting:
                seen.update(last=now, left=None)
                continue
            if name not in listed:  # gone: its minutes end at its last sight
                self.book(name, seen)
                continue
            seen["left"] = seen.get("left") or now
            seen["last"] = min(now, seen["left"] + tail)
            if now >= seen["left"] + tail:
                self.book(name, seen)
        return self.booked + sum(self.node_euros(seen) for seen in self.nodes.values())

    def node_euros(self, seen):
        per_minute, unit = self.cluster.price(seen["type"], seen["zone"])
        return ledger.cost(max(0.0, seen["last"] - seen["created"]) / 60, per_minute, unit)

    def book(self, name, seen):
        """One ledger row for a node the box's pods ran on, now gone: its minutes, euros and the jobs it ran."""
        per_minute, unit = self.cluster.price(seen["type"], seen["zone"])
        cards = submitter.provider.cards(seen["class"]) if seen["class"] else None  # a node not of a class pool
        machine = {"type": seen["type"], "zone": seen["zone"], "cards": cards,
                   "created": seen["created"], "ready": None, "deleted": seen["last"], "price": per_minute,
                   "unit_minutes": unit, "class": seen["class"], "node": name}
        record = ledger.machines_record([machine], [], seen["created"])
        ledger.record({"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(seen["created"])),
                       "batch": f"queue-{self.box}", "kind": "queue-node", "path": "k8s-queue", "node": name,
                       **record, "jobs": seen["jobs"]})
        self.booked += record["euros"]
        del self.nodes[name]

    def stop_line(self):
        lines = [state["stop_line"] for state in self.runs.values() if state.get("stop_line") is not None]
        return min(lines) if lines else None

    def stop(self, euros, line):
        """At the stop line: only this box's Jobs deleted, every open run's unfinished jobs stopped."""
        say(f"EUR {euros:.2f} reached the stop line EUR {line:.2f}: this box's Jobs deleted")
        self.kubectl.run("delete", "jobs", "-n", manifests.NAMESPACE, "-l", f"{manifests.BOX_LABEL}={self.box}",
                         "--ignore-not-found", "--wait=false")
        for state in self.runs.values():
            for record in state["jobs"].values():
                if record["state"] not in OVER:
                    record["state"] = "stopped"
            state.update(over=True, stopped=f"stop line EUR {line:.2f} reached at EUR {euros:.2f}")

    # The tick.

    def look(self):
        """The tick's three looks at the cluster."""
        items = self.kubectl.json("get", "jobs,pods", "-n", manifests.NAMESPACE, "-l",
                                  f"{manifests.BOX_LABEL}={self.box}")["items"]
        nodes = self.kubectl.json("get", "nodes")["items"]
        return items, nodes, submitter.quota_room(self.kubectl)

    def tick(self, now=None):
        now = self.clock() if now is None else now
        items, nodes, room = self.look()
        self.take_inbox()
        listed, beats = workers.listed(items), self.read_beats()
        self.note_finished(listed, beats)
        euros = self.count_money(items, nodes, now)
        line = self.stop_line()
        if line is not None and euros >= line:
            self.stop(euros, line)
        else:
            idle = self.give_out(self.idle(listed, beats, now), now)
            self.send_home(idle, now)
            self.grow(listed, beats, room, now)
        self.save(euros, now)
        return listed

    def write_state(self, run):
        client.write_whole(self.root / "state" / f"{run}.json", self.runs[run])

    def save(self, euros, now):
        """Every open run's state (a run just over written once more, then dropped), the money and the beat."""
        for run in list(self.runs):
            self.write_state(run)
            if self.runs[run]["over"]:
                del self.runs[run]
        client.write_whole(self.root / "money.json", {"euros": euros, "booked": self.booked, "nodes": self.nodes,
                                                      "at": now})
        (self.root / "beat").touch()


def serve(queue, idle_exit=QUEUE_IDLE_EXIT_SECONDS):
    """Tick until the queue has had no open run, no worker and no node left to book (its idle tail counted to the
    ledger; tube rehearsal 2026-11-07: the queue ended first and an L4 node's EUR 0.21 never reached it) for
    `idle_exit` seconds."""
    quiet_since = None
    while True:
        listed = queue.tick()
        active = queue.runs or queue.nodes or any(not workers.gone(worker) for worker in listed.values())
        quiet_since = None if active else (quiet_since or time.time())
        if quiet_since and time.time() - quiet_since >= idle_exit:
            say("no run and no worker; the queue ends")
            return
        time.sleep(QUEUE_TICK)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default=str(client.QUEUE))
    options = parser.parse_args()
    root = pathlib.Path(options.root)
    root.mkdir(parents=True, exist_ok=True)
    with (root / "lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            say("another queue holds this box's lock")
            return
        cluster = submitter.cluster_module()
        queue = Queue(submitter.cluster_kubectl(cluster), submitter.runtime().cloud_store(), cluster, root)
        serve(queue)


if __name__ == "__main__":
    main()
