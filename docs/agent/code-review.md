# Code Review Workflow

Follow this workflow when the user asks for "review", "code review",
"ช่วย review", or asks whether changes are ready.

## Review Style

- Use a code-review mindset.
- Findings come first.
- Order findings by severity.
- Include file and line references.
- Prioritize correctness, behavior regressions, safety risks, data issues,
  trading risks, and missing tests.
- Do not focus on style unless it affects correctness, safety,
  maintainability, or runtime behavior.
- If no findings are found, say so clearly.
- Mention residual risks and tests not run.
- Keep summaries brief and after findings.

## Scheduler Review Checklist

Always check scheduler changes for these risks:

- Could this place a real Polymarket order unexpectedly?
- Is `POLY_DRY_RUN=true` preserved for development and smoke tests?
- Does the change affect DB writes to `trades` or `run_logs`?
- Does the change break local venv execution?
- Does the change confuse host DB port `5433` with container DB port `5432`?
- Does it change entry/risk gate behavior for Seoul, Singapore, or Hong Kong?
- Does resolver behavior update production-like trades unintentionally?

## Output Shape

Use this order:

1. Findings.
2. Open questions or assumptions.
3. Brief summary or verification notes.

If there are no findings:

```text
No findings found.
Residual risk: ...
Tests reviewed/run: ...
```
