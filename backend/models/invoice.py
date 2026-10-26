"""Invoice data contract.

`Invoice` is the stored/served representation: sensitive fields are already masked.
`InvoiceUpload` is what arrives at `POST /invoices` before the intake agent runs.
`ExtractedField` carries the per-field extraction confidence from the intake agent.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from .enums import Currency, InvoiceStatus, Recommendation, RiskLevel

ID_PATTERN = r"^INV-\d{4,}$"
VENDOR_ID_PATTERN = r"^V-\d{3,}$"
PO_ID_PATTERN = r"^PO-\d{4,}$"


class InvoiceUpload(BaseModel):
    """Raw invoice submission. May contain unmasked sensitive data — it is masked
    by the intake step before anything is stored or shown."""

    vendor_invoice_number: str = Field(..., description="The vendor's own invoice number")
    vendor_name: str | None = None
    vendor_id: str | None = Field(None, pattern=VENDOR_ID_PATTERN)
    amount: float | None = Field(None, gt=0, le=10_000_000)
    currency: Currency | None = Currency.USD
    due_date: date | None = None
    purchase_order_id: str | None = Field(None, pattern=PO_ID_PATTERN)
    bank_account: str | None = None
    routing_number: str | None = None
    tax_id: str | None = None
    source_document: str | None = Field(None, description="File name of the uploaded invoice")
    raw_text: str | None = Field(None, description="OCR / parsed text, if any")


class ExtractedField(BaseModel):
    field: str
    value: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    missing: bool = False
    malformed: bool = False

    @field_validator("value", mode="before")
    @classmethod
    def scalar_to_text(cls, v):
        """Real models return numbers for numeric fields (`4250.0`); store them as text.
        Anything structured (list/dict) is still rejected."""
        if isinstance(v, bool | int | float):
            return str(v)
        return v

    @field_validator("confidence", mode="before")
    @classmethod
    def null_confidence_is_zero(cls, v):
        """Real models answer `"confidence": null` for absent fields. No stated confidence is
        treated as zero confidence — the safe reading, since low confidence escalates."""
        return 0.0 if v is None else v


class Invoice(BaseModel):
    """Stored invoice. `bank_account`, `routing_number`, `tax_id` are ALWAYS masked
    (last four digits only) in this model."""

    invoice_id: str = Field(..., pattern=ID_PATTERN, examples=["INV-1001"])
    vendor_invoice_number: str
    vendor_id: str | None = Field(None, pattern=VENDOR_ID_PATTERN, examples=["V-101"])
    vendor_name: str | None = None
    amount: float | None = Field(None, gt=0)
    currency: Currency = Currency.USD
    due_date: date | None = None
    purchase_order_id: str | None = Field(None, pattern=PO_ID_PATTERN)
    bank_account: str | None = Field(None, description="Masked, e.g. ****6789")
    routing_number: str | None = Field(None, description="Masked")
    tax_id: str | None = Field(None, description="Masked, e.g. ****4321")
    source_document: str | None = None
    source_text: str | None = Field(
        None, description="Text read from the source document; sensitive values masked"
    )
    has_source_pdf: bool = Field(
        False, description="A redacted copy of the emailed PDF is available for download"
    )

    status: InvoiceStatus = InvoiceStatus.RECEIVED
    risk_level: RiskLevel | None = None
    recommendation: Recommendation | None = None
    recommendation_confidence: float | None = Field(None, ge=0.0, le=1.0)
    sensitive_data_detected: bool = False
    correlation_id: str = Field(..., description="Shared by every event for this invoice")
    extraction: list[ExtractedField] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime

    @field_validator("bank_account", "routing_number", "tax_id")
    @classmethod
    def must_be_masked(cls, v: str | None) -> str | None:
        """Defense in depth: a stored invoice may never carry a raw identifier."""
        if v is None:
            return v
        if not v.startswith("****") or len(v) != 8:
            raise ValueError("sensitive field must be masked as ****NNNN")
        return v


class InvoiceSummary(BaseModel):
    """Compact row for list views and the dashboard."""

    invoice_id: str
    vendor_name: str | None
    amount: float | None
    currency: Currency
    status: InvoiceStatus
    risk_level: RiskLevel | None
    recommendation: Recommendation | None
    sensitive_data_detected: bool
    updated_at: datetime
