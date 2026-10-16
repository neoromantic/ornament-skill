---
name: ornament
description: Read Ornament Health patient profiles, lab biomarkers, measurement history, abnormal results, and health-condition scores. Use when the user wants data from their Ornament account.
license: MIT
metadata: {"openclaw": {"requires": {"env": ["ORNAMENT_API_KEY"]}, "primaryEnv": "ORNAMENT_API_KEY"}}
---

# Ornament Health

The skill ships a single Python 3 CLI — `scripts/ornament.py` — that wraps the Ornament Health REST API (`https://api.ornament.health`). No third-party deps; stdlib only.

## Prerequisites

The API is only accessible to **Ornament Pro** accounts. Before this skill is useful:

1. **Create a Pro account** at https://pro.ornament.health/ (free tier exists; sign up with email or SSO).
2. **Link a patient** — either yourself or someone who's granted access:
   - In Ornament Pro → "Patients" → "Invite patient", copy the invite link, send it to the patient (or open it yourself in another browser if it's your own profile).
   - The patient signs in / signs up via that link and authorises read access to their lab data.
   - Each linked patient becomes a PID (UUID) visible to your API key.
3. **Get the API key** at Pro → Account → "Developer tools" → "Get API Key". It's a long-lived JWE token (starts with `eyJhbGciOiJBMjU2S1ciLCJlbmMiOiJBMjU2Q0JDLUhTNTEyIn0.…`).
4. **Save the key** to either `ORNAMENT_API_KEY` env var or `~/.config/ornament/api_key`:

```bash
~/.claude/skills/ornament/scripts/ornament.py auth set     # prompts for hidden input
~/.claude/skills/ornament/scripts/ornament.py auth status  # verify
```

5. **Verify** the key sees your patients:

```bash
~/.claude/skills/ornament/scripts/ornament.py profiles
```

The list always includes one auto-generated "Daniel Smith" demo patient (`isDemoPatient: true`) — that's normal. Your real linked profile(s) appear alongside it.

### Don't have a Pro account yet?

Run `ornament.py onboard` to see the step-by-step checklist, then either complete it manually or **ask Claude to drive a browser through it** — Claude can use the `agent-browser` skill to open https://pro.ornament.health, register, copy the API key, and run `auth set` for you. Just say "use agent-browser to onboard me to Ornament" once `agent-browser` is available.

Detailed setup: [references/setup.md](references/setup.md).

## Most-common tasks (do these first)

The `--profile` argument accepts a PID (UUID), a name substring (e.g. `"Jane"`), or the literal `me` (the first non-demo profile). Default is `me`.

### 1. Who's in my account?

```bash
ornament.py profiles
```

### 2. What's abnormal in the latest tests?

```bash
ornament.py biomarkers --abnormal-only
ornament.py biomarkers --abnormal-only --since 2024-01-01
ornament.py biomarkers --abnormal-only --by-category
```

`status` column: `N` = within reference, `A` = abnormal. Reference ranges are auto-converted into the lab's original units, so the displayed `[lo–hi]` is directly comparable to the displayed `Value`. The trailing `N` column is how many historical measurements exist for that biomarker.

### 3. Dynamics of a specific biomarker

```bash
ornament.py history --name "холестерин"           # name substring
ornament.py history --name "глюкоза натощак"
ornament.py history --id 38                         # exact biomarker id
```

To find IDs: `ornament.py thesaurus biomarkers --search глюкоза`.

### 4. All biomarkers (latest value each)

```bash
ornament.py biomarkers                              # full latest snapshot
ornament.py biomarkers --name "ферритин"            # filter by name
ornament.py biomarkers --by-category                # group by display category
```

## Secondary tasks

### Health conditions / risk scores

Two sources of conditions. Health Advisor access depends on the API key; `advisor states` can return HTTP 403 even when the Medical Data commands work.

```bash
# Medical Data API — quick scores for current PID
ornament.py conditions              # interpreted (diseases + probabilities)
ornament.py conditions --raw        # raw scores per partId

# Health Advisor API — full "interpretation engine" (richer, separate subapi)
ornament.py advisor states          # GET /v1.0/actual-states  (interpreted)
ornament.py advisor raw             # GET /v1.0/profile-health-conditions-raw (full detail)
```

### Submissions (uploaded reports)

```bash
ornament.py submissions                       # all (no server-side paging — see note)
ornament.py submissions --limit 3             # client-side cap (last 3)
ornament.py submissions --since 2024-01-01
ornament.py submissions --json
```

> Note: the `submissions` endpoint returns HTTP 500 when the server's `limit`/`skip` params are sent. The CLI omits them and slices client-side, so `--limit`/`--skip` still work as expected.

### Reference data (thesaurus)

```bash
ornament.py thesaurus biomarkers --search глюкоза
ornament.py thesaurus units
ornament.py thesaurus categories
ornament.py thesaurus biomarkers --refresh         # force refetch
```

Thesaurus is cached in `~/.cache/ornament/` for 30 days.

### Raw API escape hatch

Anything the CLI doesn't expose. Ornament has six sub-APIs — see the prefix in each path:

```bash
# Medical Data API
ornament.py raw GET '/medical-data-api/public/v1.0/profile/health-conditions?pid=<uuid>'

# Health Advisor API
ornament.py raw GET '/public/health-advisor-api/v1.0/profile-health-conditions-raw?pid=<uuid>'
ornament.py raw GET '/public/health-advisor-api/v1.0/actual-states?pid=<uuid>'

# Thesaurus
ornament.py raw POST '/thesaurus-api/public/v1.0/diseases' --body '{"lang":"RU"}'
ornament.py raw POST '/thesaurus-api/public/v1.0/medical-medicine' --body '{"ids":[1,2,3]}'

# Accounting (create a new linked profile)
ornament.py raw POST '/accounting-api/public/v1.0/user/linked-profiles/<email_or_pid>' \
  --body '{"sex":"M","connectType":"HEALER","birthday":605863553,"name":"John"}'
```

Full list of endpoints, schemas, and quirks: [references/api.md](references/api.md).

## Common flags (cheat sheet)

| Flag | Where | What |
|---|---|---|
| `--profile <pid\|name\|me>` | most commands | Default `me` = first non-demo profile. |
| `--lang RU\|EN\|EN+RU\|…` | biomarkers, history, thesaurus | Thesaurus localisation (default `RU`); units and categories use the first language. |
| `--since YYYY-MM-DD` | biomarkers, submissions | Date filter. |
| `--limit N`, `--skip N` | biomarkers, submissions | Server-side for biomarkers (before local filters); client-side for submissions. |
| `--abnormal-only` | biomarkers | Only `status: A`. |
| `--by-category` | biomarkers | Group by display category. |
| `--name <substr>` | biomarkers, history | Filter by biomarker name (matches synonyms too). |
| `--id <int>` | history | Filter by biomarker ID. |
| `--refresh` | thesaurus | Force redownload of cached dictionary. |
| `--json` | most commands | JSON output (dates duplicated as ISO; units resolved). |

## JSON output

`profiles`, `biomarkers`, `history`, and `submissions` support `--json`; `conditions`, `advisor`, and `raw` always return JSON. Biomarker entries include ISO dates and resolved unit names. The `biomarkers` filters apply to both table and JSON output:

```bash
ornament.py biomarkers --json | jq '.biomarkers | length'
ornament.py history --name "холестерин" --json
```

## Data-model gotchas (read once before debugging)

- `entry.originalValue` + `measurement-units[originalUnitId]` = what the lab wrote. `entry.value` is canonical (internal) — don't display it directly.
- `refs.<id>.common/optimal/paidOptimal` ranges are also canonical. Convert via `biomarker.unitsFactors` before comparing to `originalValue`. The CLI handles this for you; if you go raw, see [references/data-model.md](references/data-model.md).
- `biomarker.status` reflects only the *latest* entry. Use `history` to see whether older entries were abnormal.
- `pid` ≠ `ssoId`: one account (ssoId) can own several profiles (pids).

## Recipes / patterns

[references/cookbook.md](references/cookbook.md) — common asks and how to answer them, plus anti-patterns.
