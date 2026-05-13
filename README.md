# Ornament Health — Claude Code skill

A [Claude Code](https://docs.claude.com/en/docs/agents-and-tools/claude-code/overview) skill for reading patient data from the [Ornament Health API](https://ornament.readme.io/reference) — profiles, lab biomarkers with full history, abnormal-result filtering, health-condition risk scores.

- Ships a single-file Python 3 CLI (`scripts/ornament.py`) — stdlib only, no dependencies.
- Resolves biomarker names + reference ranges via Ornament's thesaurus, then converts ranges into the lab's original units so the displayed `Reference` column is directly comparable to the displayed `Value`.
- Full progressive-disclosure layout: most-common tasks in `SKILL.md`, full API map in `references/api.md`, gotchas in `references/data-model.md`, recipes in `references/cookbook.md`.

## Install

### Via `skills` CLI ([skills.sh](https://www.skills.sh))

```bash
npx skills add neoromantic/ornament-skill
```

That drops the skill into `~/.claude/skills/ornament/` and Claude Code will discover it automatically on next session.

### Manually

```bash
git clone https://github.com/neoromantic/ornament-skill.git ~/.claude/skills/ornament
```

Or place the contents of this repo anywhere Claude Code scans for skills (project-level `.claude/skills/<name>/`, user-level `~/.claude/skills/<name>/`).

## Configure your API key

Get a JWE token from Ornament Pro → Account → Developer tools → "Get API Key" (instructions: https://ornament.readme.io/reference/obtaining-api-key).

Then save it once:

```bash
# Interactive (input hidden):
~/.claude/skills/ornament/scripts/ornament.py auth set

# Or set the env var:
export ORNAMENT_API_KEY='eyJ…'
```

The CLI looks at `ORNAMENT_API_KEY` first, then falls back to `~/.config/ornament/api_key` (chmod 600). Verify:

```bash
~/.claude/skills/ornament/scripts/ornament.py auth status
```

## Use

Once the skill is installed and the key is set, you can just ask Claude things like:

- "Show my Ornament profiles"
- "What's abnormal in my latest tests since the start of 2024?"
- "Show me the dynamics of my cholesterol"
- "Что у меня с ферритином?"
- "Get the Health Advisor raw scores"

Or run the CLI directly:

```bash
ornament.py profiles
ornament.py biomarkers --abnormal-only --since 2024-01-01
ornament.py biomarkers --by-category
ornament.py history --name "холестерин"
ornament.py history --id 38
ornament.py submissions --limit 5
ornament.py conditions --raw
ornament.py advisor states
ornament.py thesaurus biomarkers --search ферритин
ornament.py raw GET '/medical-data-api/public/v1.0/profile/health-conditions?pid=<uuid>'
```

The `--profile` flag everywhere accepts a PID (UUID), a name substring, or the literal `me` (default — the first non-demo profile in the account). See [`SKILL.md`](SKILL.md) for the full flag cheat sheet.

## What's in here

```
SKILL.md                  Skill entry-point: quick start + common tasks + flag cheat sheet
references/
  setup.md                API key + cache locations + sanity check
  data-model.md           Biomarker entries, refs hierarchy, unit conversion, status codes
  api.md                  Full endpoint reference (six sub-APIs, ~60 endpoints, schemas, known bugs)
  cookbook.md             Recipes for common asks + anti-patterns to avoid
scripts/
  ornament.py             CLI entry-point (9 subcommands)
  _lib.py                 Shared library: auth, HTTP, thesaurus cache, unit conversion
```

The CLI has no runtime dependencies — just Python 3.10+.

## License

[MIT](LICENSE).
