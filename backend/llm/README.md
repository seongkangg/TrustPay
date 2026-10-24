# backend/llm/

Everything that touches the language model. The model is used only for extraction,
summarization, and recommendations — never for authorization or policy decisions.

| File | What it does |
|------|--------------|
| `granite_client.py` | Model clients, chosen by `LLM_MODE`: `MockLLM` (default, deterministic canned responses so the demo never depends on live model behavior), `WatsonxLLM` (Granite on watsonx.ai; needs `WATSONX_API_KEY` + `WATSONX_PROJECT_ID`), and `OllamaLLM` (a model served locally by Ollama at `OLLAMA_URL`, default `granite3.3:8b`; no key needed). Any provider error becomes `LLMError`, which the agent treats as a failed model call. |
| `prompts.py` | Prompt templates per agent (extraction, verification summary, risk reasoning, recommendation), plus `invoice_fields_prompt` for reading free-form emailed invoices (verbatim copies only; checked against the document in `backend/inbox/llm_extraction.py`). All prompts demand structured JSON output and evidence IDs. Sensitive fields are passed in already masked. |
| `output_parser.py` | Parses model responses into the Pydantic models in `models/` and validates against the schema. Malformed or unsupported output is rejected and surfaced as a `LOW_CONFIDENCE` / parse-failure escalation, never silently accepted. |

## Guardrails

- Structured JSON only; every response schema-validated.
- Model cannot call tools — it returns a *request* that the agent routes through governance.
- Confidence is advisory.
- Model cannot override governance policy; payment limits and authorization are deterministic.

## Running Granite locally with Ollama

```bash
ollama pull granite3.3:8b
```

Then set `LLM_MODE=ollama` in `.env` and restart the backend; `/health` reports `"llm_mode": "ollama"`.
Expect roughly 15–20 s per invoice with the 8B model on a laptop (four model calls per invoice).
Real models return numbers for numeric fields (`"value": 4250.0`); `ExtractedField` coerces scalars
to text so that parses, while lists/objects are still rejected. Granite also answers
`"confidence": null` for absent fields; every schema reads that as 0.0, which escalates.
The first call loads the model into memory and can take about a minute, so send one warm-up
prompt before a live demo (or run `ollama run granite3.3:8b --keepalive -1 ""`). If Ollama is
not running, model calls fail and agents fall back exactly as they do for any `LLMError`.
