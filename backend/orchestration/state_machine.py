"""Invoice state machine (spec §16). Invalid transitions raise; nothing else moves state."""

from backend.models import InvoiceStatus as S

TRANSITIONS: dict[S, frozenset[S]] = {
    S.RECEIVED: frozenset({S.EXTRACTED, S.FAILED}),
    S.EXTRACTED: frozenset({S.VERIFYING, S.FAILED}),
    S.VERIFYING: frozenset({S.VERIFIED, S.RISK_REVIEW, S.FAILED}),
    S.VERIFIED: frozenset({S.RISK_REVIEW, S.FAILED}),
    S.RISK_REVIEW: frozenset({S.APPROVED, S.PENDING_APPROVAL, S.REJECTED, S.BLOCKED, S.FAILED}),
    S.PENDING_APPROVAL: frozenset({S.APPROVED, S.REJECTED, S.FAILED}),
    S.BLOCKED: frozenset({S.APPROVED, S.REJECTED, S.FAILED}),  # only via a recorded human decision
    S.APPROVED: frozenset({S.COMPLETED, S.FAILED}),
    S.REJECTED: frozenset(),
    S.COMPLETED: frozenset(),
    S.FAILED: frozenset(),
}

TERMINAL: frozenset[S] = frozenset({S.COMPLETED, S.REJECTED, S.FAILED})
AWAITING_HUMAN: frozenset[S] = frozenset({S.PENDING_APPROVAL, S.BLOCKED})


class InvalidTransition(ValueError):
    def __init__(self, current: S, target: S):
        self.current, self.target = current, target
        super().__init__(f"cannot move from {current.value} to {target.value}")


def can_transition(current: S, target: S) -> bool:
    return target in TRANSITIONS.get(S(current), frozenset())


def transition(current: S, target: S) -> S:
    """Return `target` if the move is legal; raise InvalidTransition otherwise."""
    current, target = S(current), S(target)
    if not can_transition(current, target):
        raise InvalidTransition(current, target)
    return target


def is_terminal(status: S) -> bool:
    return S(status) in TERMINAL
