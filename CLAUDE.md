# CLAUDE.md — AI Assistant Reference for MyShit

This file provides guidance for AI assistants (Claude and others) working in this repository. It describes the project state, conventions, and rules to follow.

---

## Project Overview

| Field | Value |
|-------|-------|
| Repository | MyShit |
| Owner | Crosalo (crosalcarlos@hotmail.de) |
| Remote | `http://local_proxy@127.0.0.1:29719/git/Crosalo/MyShit` |
| Status | Bootstrapping — no source code yet |
| Default branch | `main` |

This repository is in its earliest stage. Currently it contains only a `README.md` and this `CLAUDE.md`. All conventions here are intentionally forward-looking so that as the project grows, AI assistants have a stable reference to follow.

---

## Repository Structure

```
MyShit/
├── CLAUDE.md       # This file — AI assistant reference
└── README.md       # Project overview (minimal for now)
```

As the project grows, update this section to reflect the actual layout (e.g. `src/`, `tests/`, `docs/`, etc.).

---

## Git Conventions

### Branches

- **`main`** — production-ready, protected. Never push directly.
- **`claude/<description>-<SESSION_ID>`** — branches used by AI assistants. Always match this pattern exactly; pushes to other patterns may be rejected (HTTP 403).

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short imperative summary>

[optional body]
```

Common types:

| Type | When to use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes only |
| `refactor` | Code restructuring, no behavior change |
| `test` | Adding or fixing tests |
| `chore` | Tooling, dependencies, CI changes |
| `style` | Formatting, whitespace |

Keep the subject line under 72 characters. Use the body for the *why*, not the *what*.

### Pull Requests

- Branch off `main` for all work.
- PRs should be small and focused on one concern.
- PR titles should follow the same Conventional Commits format as commit messages.
- All work by AI assistants must be committed and pushed on the designated feature branch before a PR is opened.

---

## AI Assistant Rules

These rules apply specifically to Claude Code and any other AI-driven agents working in this repo.

### Branch Rules

- **Always** develop on the branch specified in the task description or system prompt.
- **Never** push to `main` or any branch not explicitly authorized.
- If no branch is specified, ask the user before creating or pushing.

### Push Rules

```bash
# Always use -u to set tracking:
git push -u origin <branch-name>

# Branch must follow pattern: claude/<description>-<SESSION_ID>
# Example: claude/add-claude-documentation-RYGF4
```

Retry push on network failure only (not on 403/404). Backoff: 2s → 4s → 8s → 16s, max 4 retries.

### What to Do When Adding New Code

When the project gains a language or framework, update the following sections of this file:

- **Build commands** — how to compile or bundle the project
- **Test commands** — how to run the test suite
- **Lint/format commands** — how to check and auto-fix style
- **Environment variables** — required secrets and config keys
- **Repository structure** — updated directory tree

Do not leave these sections stale. Keep CLAUDE.md in sync with the actual project state.

### General Guidelines

- Read files before editing them.
- Prefer editing existing files over creating new ones.
- Do not add unnecessary abstractions, helpers, or comments.
- Do not handle hypothetical edge cases — solve only what is needed.
- Avoid over-engineering. Minimum complexity for the current task.
- Do not commit secrets, credentials, or `.env` files.
- Confirm with the user before destructive or irreversible actions (force push, branch delete, file deletion, etc.).

---

## Build (Not yet configured)

_Update this section when a build system is added._

```bash
# Example placeholder — replace with real commands:
# npm run build
# cargo build --release
# make build
```

---

## Tests (Not yet configured)

_Update this section when a test framework is added._

```bash
# Example placeholder — replace with real commands:
# npm test
# pytest
# cargo test
# go test ./...
```

---

## Linting & Formatting (Not yet configured)

_Update this section when linters/formatters are configured._

```bash
# Example placeholder — replace with real commands:
# npm run lint
# ruff check .
# cargo clippy
```

---

## Environment Variables (Not yet configured)

_List required environment variables here as they are introduced. Use `.env.example` as the source of truth._

```
# Example:
# DATABASE_URL=
# API_KEY=
```

---

## Updating This File

Whenever the project structure, tooling, or conventions change, update CLAUDE.md in the same commit. This file is the single source of truth for AI assistants; stale documentation causes mistakes.
