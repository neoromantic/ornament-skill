# ornament-skill

<!-- devkit:agents v1 -->
<!-- managed by devkit v1: edit in https://github.com/neoromantic/devkit/blob/main/agents/AGENTS.shared.md -->
## Shared rules (devkit)

These rules apply to people and coding agents in every repo that uses
[devkit](https://github.com/neoromantic/devkit). Project rules follow in `## Project` below.
Where they conflict, the project section wins.

### Data

- Use only made-up data in tests, fixtures, examples, docs and screenshots. No real people, chats,
  phone numbers, tokens, session files or local paths such as home directories.
- Never commit `.env` files or credentials. Tests run offline by default; live API tests are
  opt-in and read their credentials from the environment.

### Commands

Use the project section's native commands for checks, offline tests and builds:

- Bun: `bun run <script>` (`check`, or `lint` and `typecheck`; `test`, `test:e2e`, `build`).
- Python: the documented `uv run` / `uvx` commands, such as pytest, unittest and ruff.
- Go: the documented `go` commands from `go.mod`. Do not add Bun wrappers for Python or Go.
- Use Bun, uv or Go modules for installs. Use npm only for `npm publish` and `npm view`.

### Definition of done

- The change works end to end and the project's applicable checks and tests pass locally.
- README, docs and affected demos change with the behaviour they describe; follow the
  [product content standard](https://github.com/neoromantic/devkit/blob/main/docs/standards/product-content.md).
- No new warnings, no commented-out code, no stray debug output.

### Commits and releases

- Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `ci:`.
  A breaking change adds `!` (`feat!:`) and a `BREAKING CHANGE:` footer.
- One logical change per commit. Never rewrite published history or force-push `main`.
- Follow the project's documented release procedure, including any owner-only steps. It defines
  versioning, tags, changelog and delivery (release, skill revision or production deployment).

### Files

- Don't add planning or progress files (`progress.md`, `docs/plans/`). Plans live in issues.
  `ROADMAP.md`, if present, is a short "Known gaps" list that links issues.
- Don't add agent hooks that rewrite tracked files.
- `AGENTS.md` is the canonical instruction file. `CLAUDE.md` contains only `@AGENTS.md`.
- Files marked "managed by devkit" (this block, `SECURITY.md`, `CONTRIBUTING.md`, the PR
  template, `.gitleaks.toml`, `.github/zizmor.yml`, `renovate.json`, `lefthook.yml` and the
  CI stub) are synced from devkit. Change them there, not here.
<!-- /devkit:agents -->

## Project

An Agent Skill for the Ornament Health API. `SKILL.md` is the entry point that agents load;
`scripts/ornament.py` is a stdlib-only Python CLI (Python 3.10+, no dependencies) and
`scripts/_lib.py` holds its shared helpers. `references/` holds the longer docs the skill links.

### Commands

| What | Command |
|---|---|
| Tests (offline, includes the SKILL.md frontmatter check) | `uv run --no-project python -m unittest discover -s tests` |
| Lint | `uvx ruff check .` |

CI runs both on Python 3.10 and 3.14 through devkit's `ci-python.yml`, plus devkit's hygiene checks.

### Rules

- Keep the CLI stdlib-only. Users run it straight from the skill folder with any Python 3.10+.
- Tests never call the Ornament API. Use made-up biomarkers, units and profiles only.
- Keep the `description` in `SKILL.md` under 1024 characters, with English and Russian triggers.
  `tests/test_frontmatter.py` enforces it.
- Personal defaults (language, preferred profile, output style) don't belong here. Users keep
  them in their own agent instructions or a private overlay skill.
- There are no releases: skills.sh installs the latest `main`, so `main` must always work.
- Update `README.md`, `SKILL.md` and `references/` in the same commit as the behaviour they
  describe.
