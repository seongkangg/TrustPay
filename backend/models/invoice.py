"""Invoice data contract.

`Invoice` is the stored/served representation: sensitive fields are already masked.
`InvoiceUpload` is what arrives at `POST /invoices` before the intake agent runs.
`ExtractedField` carries the per-field extraction confidence from the intake agent.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .enums import Currency, InvoiceStatus, RiskLevel, Recommendation

ID_PATTERN = r"^INV-\d{4,}$"
VENDOR_ID_PATTERN = r"^V-\d{3,}$"
PO_ID_PATTERN = r"^PO-\d{4,}$"


class InvoiceUpload(BaseModel):
    """Raw invoice submission. May contain unmasked sensitive data — it is masked
    by the intake step before anything is stored or shown."""

    vendor_invoice_number: str = Field(..., description="The vendor's own invoice number")
    vendor_name: Optional[str] = None
    vendor_id: Optional[str] = Field(None, pattern=VENDOR_ID_PATTERN)
    amount: Optional[float] = Field(None, gt=0, le=10_000_000)
    currency: Optional[Currency] = Currency.USD
    due_date: Optional[date] = None
    purchase_order_id: Optional[str] = Field(None, pattern=PO_ID_PATTERN)
    bank_account: Optional[str] = None
    routing_number: Optional[str] = None
    tax_id: Optional[str] = None
    source_document: Optional[str] = Field(None, description="File name of the uploaded invoice")
    raw_text: Optional[str] = Field(None, description="OCR / parsed text, if any")


class ExtractedField(BaseModel):
    field: str
    value: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    missing: bool = False
    malformed: bool = False


class Invoice(BaseModel):
    """Stored invoice. `bank_account`, `routing_number`, `tax_id` are ALWAYS masked
    (last four digits only) in this model."""

    invoice_id: str = Field(..., pattern=ID_PATTERN, examples=["INV-1001"])
    vendor_invoice_number: str
    vendor_id: Optional[str] = Field(None, pattern=VENDOR_ID_PATTERN, examples=["V-101"])
    vendor_name: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    currency: Currency = Currency.USD
    due_date: Optional[date] = None
    purchase_order_id: Optional[str] = Field(None, pattern=PO_ID_PATTERN)
    bank_account: Optional[str] = Field(None, description="Masked, e.g. ****6789")
    routing_number: Optional[str] = Field(None, description="Masked")
    tax_id: Optional[str] = Field(None, description="Masked, e.g. ****4321")
    source_document: Optional[str] = None

    status: InvoiceStatus = InvoiceStatus.RECEIVED
    risk_level: Optional[RiskLevel] = None
    recommendation: Optional[Recommendation] = None
    recommendation_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    sensitive_data_detected: bool = False
    correlation_id: str = Field(..., description="Shared by every event for this invoice")
    extraction: list[ExtractedField] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime

    @field_validator("bank_account", "routing_number", "tax_id")
    @classmethod
    def must_be_masked(cls, v: Optional[str]) -> Optional[str]:
        """Defense in depth: a stored invoice may never carry a raw identifier."""
        if v is None:
            return v
        if not v.startswith("****") or len(v) != 8:
            raise ValueError("sensitive field must be masked as ****NNNN")
        return v


class InvoiceSummary(BaseModel):
    """Compact row for list views and the dashboard."""

    invoice_id: str
    vendor_name: Optional[str]
    amount: Optional[float]
    currency: Currency
    status: InvoiceStatus
    risk_level: Optional[RiskLevel]
    recommendation: Optional[Recommendation]
    sensitive_data_detected: bool
    updated_at: datetime
