# Cookbook

Common asks and how to answer them.

> All commands assume `~/.claude/skills/ornament/scripts/ornament.py` is on hand. From the skill dir you can shorten to `./scripts/ornament.py`.

## "Show me my profiles"

```bash
ornament.py profiles
```

Tiny table. `Demo` column flags Ornament Pro's auto-generated demo patient — usually skip it.

## "What's flagged abnormal in my latest tests?"

```bash
ornament.py biomarkers --profile me --abnormal-only
```

Defaults to the first non-demo profile. To target someone else: `--profile "Jane"` (name substring) or pass a PID.

Add `--since 2025-01-01` to ignore old measurements. Add `--by-category` to group results by display category (липиды, гормоны, кровь, etc.).

## "How has my cholesterol moved over the years?"

```bash
ornament.py history --profile me --name "холестерин"
```

Returns every measurement of every matching biomarker, oldest → newest, with the ref range converted into the lab's original unit. Add `--id <int>` to nail it down to one specific biomarker (use `thesaurus biomarkers --search …` to discover IDs).

## "Find the biomarker IDs for X"

```bash
ornament.py thesaurus biomarkers --search "гликирован"
```

Russian or English (load with `--lang EN` if you prefer). Matches against title and synonyms.

## "Refresh the cached dictionaries"

The cache is 30-day TTL. Force refresh:

```bash
ornament.py thesaurus biomarkers --lang RU --refresh
ornament.py thesaurus units --lang RU --refresh
ornament.py thesaurus categories --lang RU --refresh
```

## "Pull everything as JSON for further analysis"

Every command supports `--json` where it makes sense:

```bash
ornament.py biomarkers --profile me --json > /tmp/bm.json
ornament.py history    --profile me --name "глюкоза" --json
```

Then chew through it with `jq`, pandas, etc.

## "I need an endpoint that the CLI doesn't have"

Use `raw`:

```bash
ornament.py raw GET '/medical-data-api/public/v1.0/profile/health-conditions?pid=…'
ornament.py raw POST '/thesaurus-api/public/v1.0/diseases' --body '{"lang":"RU"}'
```

See `references/api.md` for the full surface.

## "Health conditions"

```bash
ornament.py conditions --profile me           # interpreted
ornament.py conditions --profile me --raw     # raw scores per partId
```

The `--raw` flavour returns numeric scores for each `partId` (body part / system). Each score has a `rawScore`, plus low/high boundaries. The interpreted flavour groups by disease with probabilities.

## Anti-patterns

- **Don't** display `entry.value` directly without unit context — it's canonical, not what the patient saw. Use `originalValue + measurement-units[originalUnitId]`.
- **Don't** trust `refs[id].common` raw — it's also canonical. Convert via `unitsFactors`. (The `biomarkers` command does this for you.)
- **Don't** refetch the thesaurus on every call. Use the cached copy; only force `--refresh` if a brand-new biomarker is missing.
- **Don't** treat `status: "N"` on the biomarker block as historical — it reflects only the most recent entry.
