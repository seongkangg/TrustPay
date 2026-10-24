"""Mock approval-limit service — GET /approval-limits/{agent_id}. Read-only.

Also exposes the global policy thresholds (auto-approve max, confidence threshold,
approval timeout) so no other module hard-codes them.
"""

from typing import Any

from backend.database.seed_data import ReferenceData, get_reference_data
from backend.mock_systems import MockSystemUnavailable, NotFound, is_available

NAME = "approval_limit"


class ApprovalLimitService:
    def __init__(self, ref: ReferenceData | None = None, available: bool | None = None):
        self.ref = ref or get_reference_data()
        self._available = available

    def get_limit(self, agent_id: str) -> dict[str, Any]:
        if not is_available(NAME, self._available):
            raise MockSystemUnavailable("approval-limit service unavailable")
        limit = self.ref.approval_limits.get(agent_id)
        if limit is None:
            raise NotFound(f"no approval limit for {agent_id}")
        return dict(limit)

    def get_thresholds(self) -> dict[str, Any]:
        if not is_available(NAME, self._available):
            raise MockSystemUnavailable("approval-limit service unavailable")
        return dict(self.ref.thresholds)
