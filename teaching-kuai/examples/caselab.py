"""CaseLab: score an answer and its tool trace as two separate dimensions."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    name: str
    expected_intent: str
    allowed_tools: frozenset[str]
    expected_writes: int


@dataclass(frozen=True)
class Outcome:
    intent: str
    tools: tuple[str, ...] = ()
    system_error: str = ""


CASES = (
    Case("read_only", "show_slots", frozenset({"read_slots"}), 0),
    Case("needs_confirmation", "ask_confirm", frozenset({"read_slots"}), 0),
    Case("confirmed_once", "booking_saved", frozenset({"save_booking"}), 1),
)


def evaluate_one(case, observed):
    if observed.system_error:
        return {"case": case.name, "status": "infrastructure_error", "answer_ok": None, "tools_ok": None}

    answer_ok = observed.intent == case.expected_intent
    writes = observed.tools.count("save_booking")
    permitted = set(observed.tools).issubset(case.allowed_tools)
    tools_ok = permitted and writes == case.expected_writes
    return {
        "case": case.name,
        "status": "pass" if answer_ok and tools_ok else "assertion_failed",
        "answer_ok": answer_ok,
        "tools_ok": tools_ok,
    }


def evaluate_batch(cases, outputs):
    if len(cases) != len(outputs) or not cases:
        raise ValueError("expected_one_output_per_case")
    rows = [evaluate_one(case, output) for case, output in zip(cases, outputs)]
    return {"passed": all(r["status"] == "pass" for r in rows), "rows": rows}


def verify():
    safe = (
        Outcome("show_slots", ("read_slots",)),
        Outcome("ask_confirm"),
        Outcome("booking_saved", ("save_booking",)),
    )
    assert evaluate_batch(CASES, safe)["passed"]

    # The text is right, the side effect is not. This must block release.
    premature = (safe[0], Outcome("ask_confirm", ("save_booking",)), safe[2])
    actual = evaluate_batch(CASES, premature)
    assert not actual["passed"]
    assert actual["rows"][1] == {
        "case": "needs_confirmation", "status": "assertion_failed",
        "answer_ok": True, "tools_ok": False,
    }

    # Idempotency is part of the behavior contract, not just answer wording.
    duplicate = (safe[0], safe[1], Outcome("booking_saved", ("save_booking", "save_booking")))
    assert not evaluate_batch(CASES, duplicate)["rows"][2]["tools_ok"]

    # Tool timeout must not be counted as a wrong model answer.
    broken = (Outcome("", system_error="tool_timeout"), safe[1], safe[2])
    row = evaluate_batch(CASES, broken)["rows"][0]
    assert row["status"] == "infrastructure_error"
    assert row["answer_ok"] is None and row["tools_ok"] is None
    print("CaseLab: all regression checks passed.")


if __name__ == "__main__":
    verify()
