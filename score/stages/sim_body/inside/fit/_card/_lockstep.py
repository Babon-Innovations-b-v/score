"""Level 2 across sets in lockstep (#70): every nudged set of one body runs its own scipy `least_squares` (same
cold start, same tolerances as alone), each in its own thread, and every round of exact Jacobians is ONE
`CardKinematics.frames` call over all still-running sets' frames (worlds = sets x frames, each world its own
`body_pos` and `site_pos` row) instead of one per set; a set that finishes drops out. Each world's kinematics are
its own (per-world kernels, `motions` fixed order), so each set sees what it would alone, bit for bit.
Each set needs its own `Fitting` (the solve lays constants on it); they share one model structure."""

import threading

import numpy as np

from . import _level2, _level2_card


class Lockstep:
    """One card model of `sets` x `frames` worlds, gathering every running set's frames into one call a round."""

    def __init__(self, fitting, frames, sets):
        self.frames_each, self.sets = frames, sets
        self.card = _level2_card.CardKinematics(fitting, frames * sets)
        model = fitting.model
        self.qpos = np.tile(model.qpos0, (frames * sets, 1))
        self.body_pos = np.tile(model.body_pos, (frames * sets, 1, 1))
        self.site_pos = np.tile(model.site_pos, (frames * sets, 1, 1))
        self.lock = threading.Condition()
        self.live, self.pending, self.answers = sets, set(), {}

    def jacobian_for(self, index):
        """`staged`'s `jacobian` for set `index`: `_level2.jacobian` with its frames from the shared round."""
        return lambda problem, unknowns: _level2.jacobian(problem, unknowns, _SetCard(self, index, problem.fitting))

    def submit(self, index, qpos, model):
        """Set `index`'s frames at `qpos` on `model`'s constants, once every running set has asked."""
        rows = slice(index * self.frames_each, (index + 1) * self.frames_each)
        with self.lock:
            self.qpos[rows], self.body_pos[rows], self.site_pos[rows] = qpos, model.body_pos, model.site_pos
            self.pending.add(index)
            self._round_if_all_asked()
            while index not in self.answers:
                self.lock.wait()
            return self.answers.pop(index)

    def finish(self):
        """A set's solve ended: it no longer holds a round back."""
        with self.lock:
            self.live -= 1
            self._round_if_all_asked()

    def _round_if_all_asked(self):
        """Run the one card call when every running set has asked (lock held)."""
        if not self.pending or len(self.pending) < self.live:
            return
        seen = self.card.frames(self.qpos, self.body_pos, self.site_pos)
        for index in self.pending:
            self.answers[index] = seen[index * self.frames_each:(index + 1) * self.frames_each]
        self.pending.clear()
        self.lock.notify_all()


class _SetCard:
    """One set's face of the shared card: what `_level2.jacobian` calls as `card.frames`."""

    def __init__(self, lockstep, index, fitting):
        self.lockstep, self.index, self.fitting = lockstep, index, fitting

    def frames(self, qpos):
        """This set's frames from the round (its fitting's constants laid by `jacobian` just before)."""
        return self.lockstep.submit(self.index, qpos, self.fitting.model)


def run(lockstep, solves):
    """Each set's solve (`solves[index](jacobian)` -> its answer, `jacobian` for `staged`) side by side, their answers
    in order; a failed solve's error is raised after all end."""
    answers, errors = [None] * len(solves), []

    def one(index):
        """Set `index`'s solve, dropping out of the rounds when it ends."""
        try:
            answers[index] = solves[index](lockstep.jacobian_for(index))
        except BaseException as error:  # raised below, after the other sets end
            errors.append(error)
        finally:
            lockstep.finish()

    threads = [threading.Thread(target=one, args=(index,)) for index in range(len(solves))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if errors:
        raise errors[0]
    return answers
