"""RoomLab: submit, validate, save, reconnect, and render one consistent revision."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Item:
    name: str
    x: float
    width: float


@dataclass(frozen=True)
class Snapshot:
    run: str
    seq: int
    state: str
    revision: int

    @property
    def finished(self):
        return self.state in {"done", "failed"}


@dataclass
class RoomStore:
    revision: int = 2
    items: tuple[Item, ...] = ()
    commits: dict[str, tuple[int, tuple[Item, ...]]] = field(default_factory=dict)

    def save(self, run, expected_revision, draft):
        if run in self.commits:
            original_revision, original_draft = self.commits[run]
            if original_draft != draft:
                raise ValueError("idempotency_conflict")
            return original_revision
        if expected_revision != self.revision:
            raise ValueError("stale_base_revision")
        self.revision += 1
        self.items = draft
        self.commits[run] = self.revision, draft
        return self.revision


def validate(draft, room_width=4.0):
    if not draft or any(not (0 <= i.x < i.x + i.width <= room_width) for i in draft):
        raise ValueError("invalid_geometry")


def complete(run, base_revision, draft, store):
    try:
        validate(draft)
        new_revision = store.save(run, base_revision, draft)
    except ValueError:
        return Snapshot(run, 2, "failed", store.revision)
    return Snapshot(run, 2, "done", new_revision)


def reduce_view(current, event, read_snapshot):
    if event.run != current.run or event.seq <= current.seq or current.finished:
        return current
    if event.seq == current.seq + 1:
        return event
    latest = read_snapshot(current.run)
    if latest.run == current.run and latest.seq > current.seq:
        return latest
    return current


def verify():
    store = RoomStore()
    run = "sample-layout"
    accepted = Snapshot(run, 0, "accepted", 2)
    valid = (Item("chair-a", 0.5, 0.6),)
    result = complete(run, 2, valid, store)

    # The client missed sequence 1 while offline. Fetch the canonical snapshot.
    view = reduce_view(accepted, result, lambda run_id: result)
    assert (view.state, view.revision) == ("done", 3)
    assert reduce_view(view, result, lambda _: result) == view

    # A stale completion from a different request cannot overwrite this view.
    old = Snapshot("other-layout", 9, "done", 99)
    assert reduce_view(view, old, lambda _: old) == view

    # The first write succeeded but the worker lost the response.
    assert store.save(run, 2, valid) == 3
    assert len(store.commits) == 1

    # A malformed draft must keep the existing revision visible.
    invalid = complete("bad-layout", 3, (Item("oversize", 3.9, 1.0),), store)
    assert (invalid.state, store.revision, store.items) == ("failed", 3, valid)

    # Two drafts against revision 2 must not silently overwrite one another.
    conflict = complete("late-layout", 2, valid, store)
    assert conflict.state == "failed"
    assert store.revision == 3
    print("RoomLab: all regression checks passed.")


if __name__ == "__main__":
    verify()
