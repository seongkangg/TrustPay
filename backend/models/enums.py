"""Enumerations shared across the whole system.

Nothing in the codebase should use free-text strings for these concepts.
If a value is not listed here, the system does not support it.
"""

from enum import Enum


class InvoiceStatus(str, Enum):
    RECEIVED = "RECEIVED"
    EXTRACTED = "EXTRACTED"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    RISK_REVIEW = "RISK_REVIEW"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AgentName(str, Enum):
    """Every actor that can appear on a decision, tool call, or audit event."""

    INTAKE = "intake_agent"
    VERIFICATION = "verification_agent"
    POLICY_RISK = "policy_risk_agent"
    APPROVAL = "approval_agent"
    GOVERNANCE = "governance_layer"
    HUMAN_REVIEWER = "human_reviewer"
    SYSTEM = "system"


class ToolName(str, Enum):
    DOCUMENT_PARSER = "document_parser"
    VENDOR_LOOKUP = "vendor_lookup"
    PO_LOOKUP = "po_lookup"
    APPROVAL_LIMIT_LOOKUP = "approval_limit_lookup"
    RISK_RULES = "risk_rules"
    APPROVAL_REQUEST_CREATE = "approval_request_create"
    PAYMENT_AUTHORIZE = "payment_authorize"
    AUDIT_LOG_WRITE = "audit_log_write"


class Authorization(str, Enum):
    """Outcome of a governance check on a tool call or action."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    ESCALATED = "escalated"


class Recommendation(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"


class HumanDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PENDING = "pending"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class EventType(str, Enum):
    INVOICE_RECEIVED = "invoice_received"
    INVOICE_EXTRACTED = "invoice_extracted"
    VENDOR_LOOKUP_REQUESTED = "vendor_lookup_requested"
    VENDOR_VERIFIED = "vendor_verified"
    VENDOR_UNVERIFIED = "vendor_unverified"
    PURCHASE_ORDER_CHECKED = "purchase_order_checked"
    DUPLICATE_DETECTED = "duplicate_detected"
    SENSITIVE_DATA_MASKED = "sensitive_data_masked"
    RISK_ASSIGNED = "risk_assigned"
    RECOMMENDATION_GENERATED = "recommendation_generated"
    APPROVAL_REQUESTED = "approval_requested"
    PAYMENT_AUTHORIZED = "payment_authorized"
    PAYMENT_BLOCKED = "payment_blocked"
    TOOL_CALL_DENIED = "tool_call_denied"
    HUMAN_DECISION_RECORDED = "human_decision_recorded"
    AGENT_FAILED = "agent_failed"
    AUDIT_RECORD_CREATED = "audit_record_created"


class ReasonCode(str, Enum):
    """Explicit, deterministic reasons attached to governance decisions.

    The language model is never allowed to invent new ones.
    """

    AMOUNT_ABOVE_LIMIT = "AMOUNT_ABOVE_LIMIT"
    UNKNOWN_VENDOR = "UNKNOWN_VENDOR"
    VENDOR_UNVERIFIED = "VENDOR_UNVERIFIED"
    DUPLICATE_INVOICE = "DUPLICATE_INVOICE"
    PO_AMOUNT_MISMATCH = "PO_AMOUNT_MISMATCH"
    INVALID_PURCHASE_ORDER = "INVALID_PURCHASE_ORDER"
    SENSITIVE_DATA_DETECTED = "SENSITIVE_DATA_DETECTED"
    UNAUTHORIZED_TOOL_CALL = "UNAUTHORIZED_TOOL_CALL"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    MALFORMED_FIELD = "MALFORMED_FIELD"
    AGENT_FAILURE = "AGENT_FAILURE"
    MOCK_SYSTEM_UNAVAILABLE = "MOCK_SYSTEM_UNAVAILABLE"
    POLICY_PASSED = "POLICY_PASSED"


class SensitiveFieldType(str, Enum):
    BANK_ACCOUNT = "bank_account"
    ROUTING_NUMBER = "routing_number"
    TAX_ID = "tax_id"
    PERSONAL_NAME = "personal_name"
    ADDRESS = "address"
    PAYMENT_CREDENTIAL = "payment_credential"
    API_KEY = "api_key"


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
