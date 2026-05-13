# Setup

## 1. Create an Ornament Pro account

The API is gated behind Pro. Sign up at https://pro.ornament.health/. The free tier is enough for read access to your own labs.

## 2. Link at least one patient

A fresh Pro account has only the demo patient (`Daniel Smith`). To see real data:

1. In Ornament Pro open **Patients → Invite patient**.
2. Ornament generates a unique invite link.
3. Send that link to the patient (or open it yourself in another browser to invite your own profile).
4. The patient signs in / signs up and grants you read access.
5. Once they accept, their PID (UUID) appears in `GET /healer/linked-profiles` and `ornament.py profiles`.

The API also exposes `POST /accounting-api/public/v1.0/user/linked-profiles/{pid_or_email}` for programmatic creation, but the invite-link flow is what the UI uses and is normally easier.

## 3. Get the API key

Pro → Account → **Developer tools → Get API Key**. Ornament issues a long JWE token (starts with `eyJhbGciOiJBMjU2S1ciLCJlbmMiOiJBMjU2Q0JDLUhTNTEyIn0.…`).

If you'd rather not click through the dashboard, ask Claude to run the onboarding via the `agent-browser` skill — see `ornament.py onboard` for the step list it'll follow.

## 4. Save the key

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
