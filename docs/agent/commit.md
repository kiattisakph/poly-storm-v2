# Commit And Branch Workflow

Follow this workflow when the user asks to create a branch or commit code.

## Allowed Types

- `feat`: new behavior or capability.
- `fix`: bug fix.
- `refactor`: internal restructuring without intended behavior change.
- `chore`: tooling, docs, config, maintenance, or non-product changes.

## Branch Naming

- Prefer branch names that start with one allowed type.
- Use short kebab-case names.

Examples:

```text
feat/scheduler-dry-run
fix/db-port-5433
refactor/scheduler-cli
chore/agent-docs
```

## Commit Message

Format:

```text
type(branchname): description
```

Rules:

- `type` must be `feat`, `fix`, `refactor`, or `chore`.
- `branchname` should be the current branch name without the leading type
  prefix when practical.
- The full first line must be 72 characters or fewer.
- Use lowercase type.
- Keep the description imperative and concise.
- Do not include secrets or local machine details.

Examples:

```text
feat(scheduler-dry-run): add safe order dry-run mode
fix(db-port-5433): avoid local postgres port conflict
refactor(scheduler-cli): split scheduler setup from entrypoint
chore(agent-docs): document codex project workflow
```

## Commit Request Handling

When the user says phrases like "commit code", "commit ให้หน่อย",
"เก็บ commit", or "ช่วย commit":

- Inspect `git status --short`.
- Review the relevant diff before committing.
- Do not commit `.env`, secrets, local logs, caches, or unrelated files.
- If unrelated user changes exist, do not include them unless explicitly asked.
- Run relevant verification commands before committing when practical.
- Use the commit message format above.
- After committing, report the commit hash and short summary.
