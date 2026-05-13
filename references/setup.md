# Setup

## API key

Ornament issues a long JWE token (starts with `eyJhbGciOiJBMjU2S1ciLCJlbmMiOiJBMjU2Q0JDLUhTNTEyIn0.…`).
You can get yours at https://ornament.readme.io/reference/obtaining-api-key.

The skill resolves the key in this order:

1. Environment variable `ORNAMENT_API_KEY`.
2. File `~/.config/ornament/api_key` (chmod 600).

### One-time setup

```bash
# Interactive: hidden input from terminal
~/.claude/skills/ornament/scripts/ornament.py auth set

# Or pass directly (mind your shell history!)
~/.claude/skills/ornament/scripts/ornament.py auth set 'eyJhbGc…'

# Verify
~/.claude/skills/ornament/scripts/ornament.py auth status
```

### Rotating / clearing

The key is just a single line in `~/.config/ornament/api_key`. Run `auth set` again to overwrite, or `rm` the file to clear. To temporarily override without touching the file, set `ORNAMENT_API_KEY` for the current shell.

## Cache location

Thesaurus and unit dictionaries cache to `~/.cache/ornament/`. They're large-ish (~2 MB) and refreshed every 30 days, or sooner with `thesaurus … --refresh`.

## Sanity check

```bash
~/.claude/skills/ornament/scripts/ornament.py profiles
```

A configured key with no patients returns an empty list; a malformed key returns HTTP 401.
