"""Detects and masks sensitive data, producing SCAN-NNN evidence and audit events.

Runs at ingestion (before persistence and before any model call) and on any free text
an agent produces. The raw input is handled in memory only and never returned.
Pattern logic lives in services/masking_service.py; this module adds evidence IDs and
the `sensitive_data_masked` audit event.
"""

from dataclasses import dataclass, field

from backend.models import AgentName, EventType, ReasonCode, SensitiveFieldType, Severity
from backend.services.audit_service import AuditService
from backend.services.masking_service import Detection, contains_unmasked, mask_text, mask_upload


@dataclass
class ScanResult:
    masked: dict
    detections: list[Detection] = field(default_factory=list)
    evidence_id: str | None = None  # SCAN-NNN, only when something was found

    @property
    def found(self) -> bool:
        return bool(self.detections)

    @property
    def field_types(self) -> set[SensitiveFieldType]:
        return {d.field_type for d in self.detections}


class SensitiveDataScanner:
    def __init__(self, audit: AuditService):
        self.audit = audit

    def scan_upload(self, data: dict, *, invoice_id: str, correlation_id: str) -> ScanResult:
        masked, detections = mask_upload(data)
        if not detections:
            return ScanResult(masked=masked)

        evidence_id = f"SCAN-{self.audit.count() + 1:03d}"
        self.audit.append(
            invoice_id=invoice_id,
            correlation_id=correlation_id,
            event_type=EventType.SENSITIVE_DATA_MASKED,
            severity=Severity.MEDIUM,
            actor=AgentName.GOVERNANCE,
            reason_codes=[ReasonCode.SENSITIVE_DATA_DETECTED],
            input_summary="sensitive fields detected on upload: "
            + ", ".join(sorted({d.field_type.value for d in detections})),
            output_summary="values masked to last four digits before storage",
            evidence_refs=[evidence_id],
        )
        return ScanResult(masked=masked, detections=detections, evidence_id=evidence_id)

    @staticmethod
    def scan_text(text: str | None) -> tuple[str | None, list[Detection]]:
        return mask_text(text)

    @staticmethod
    def has_unmasked(text: str | None) -> bool:
        return contains_unmasked(text)
