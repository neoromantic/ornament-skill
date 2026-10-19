# ornament-skill

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
