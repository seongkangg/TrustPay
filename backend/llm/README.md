# backend/llm/

Everything that touches the language model. The model is used only for extraction,
summarization, and recommendations — never for authorization or policy decisions.

| File | What it does |
|------|--------------|
| `granite_client.py` | Client for watsonx.ai / Granite. Reads API key, project ID, and model ID from env. Includes a `MockLLM` mode that returns canned responses for the three demo invoices so the demo never depends on live model behavior. |
| `prompts.py` | Prompt templates per agent (extraction, verification summary, risk reasoning, recommendation). All prompts demand structured JSON output and evidence IDs. Sensitive fields are passed in already masked. |
| `output_parser.py` | Parses model responses into the Pydantic models in `models/` and validates against the schema. Malformed or unsupported output is rejected and surfaced as a `LOW_CONFIDENCE` / parse-failure escalation, never silently accepted. |

## Guardrails

- Structured JSON only; every response schema-validated.
- Model cannot call tools — it returns a *request* that the agent routes through governance.
- Confidence is advisory.
- Model cannot override governance policy; payment limits and authorization are deterministic.
