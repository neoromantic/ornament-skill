#!/usr/bin/env python3
"""Ornament Health API command-line interface.

Run `ornament.py --help` for the list of subcommands.
Auth: ORNAMENT_API_KEY env var or ~/.config/ornament/api_key.
"""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
import _lib as L  # noqa: E402


# ---------- helpers ----------

def _fmt_date(ts: int | float) -> str:
    return dt.date.fromtimestamp(int(ts)).isoformat()


def _print_json(obj: Any) -> None:
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def _resolve_profile(pid_or_name: str) -> tuple[str, dict[str, Any]]:
    """Resolve a user-provided identifier to a (pid, profile) pair.

    Accepts a UUID, a substring of the profile name, or the literal 'me' which
    picks the first non-demo profile.
    """
    profiles = L.request("GET", "/accounting-api/public/v1.0/healer/linked-profiles")
    if not isinstance(profiles, list):
        sys.exit("Unexpected linked-profiles response")
    needle = pid_or_name.lower().strip()
    if needle == "me":
        for p in profiles:
            if not p.get("isDemoPatient"):
                return p["pid"], p
        sys.exit("No non-demo profile found")
    for p in profiles:
        if p.get("pid", "").lower() == needle:
            return p["pid"], p
    matches = [p for p in profiles if needle in (p.get("name") or "").lower()]
    if len(matches) == 1:
        return matches[0]["pid"], matches[0]
    if len(matches) == 0:
        sys.exit(f"No profile matches '{pid_or_name}'. Run: ornament.py profiles")
    names = ", ".join(f"{p['name']} ({p['pid'][:8]})" for p in matches)
    sys.exit(f"Multiple profiles match '{pid_or_name}': {names}")


# ---------- onboard ----------

ONBOARD_STEPS = """\
Ornament Pro onboarding — required before this skill is useful

The API only answers calls for accounts registered at Ornament Pro. Follow
these steps, then run `ornament.py auth set` to save the key.

  1. Sign up at https://pro.ornament.health/ (email or SSO; free tier OK).
  2. In Pro → "Patients" → "Invite patient": Ornament generates a unique
     invite link. Send it to the patient, or open it yourself in another
     browser to onboard your own profile. The patient confirms access.
  3. In Pro → Account → "Developer tools" → "Get API Key": copy the long
     JWE token (it starts with `eyJhbGciOiJBMjU2S1ciLCJlbmMi...`).
  4. Save it locally:

         ornament.py auth set            # prompts for hidden input
         ornament.py auth status         # verify

  5. Confirm the linked profile shows up:

         ornament.py profiles

Don't want to click through it yourself?
  Ask Claude to drive the steps above via the `agent-browser` skill — it
  can open the Pro dashboard, register/sign in, copy the API key, and
  hand it to `auth set`. Phrase it like:
      "Use agent-browser to onboard me to Ornament Pro."
"""


def cmd_onboard(args: argparse.Namespace) -> None:  # noqa: ARG001
    sys.stdout.write(ONBOARD_STEPS)


# ---------- auth ----------

def cmd_auth(args: argparse.Namespace) -> None:
    if args.auth_cmd == "status":
        st = L.auth_status()
        if not st["ready"]:
            print("API key: NOT configured")
            print("Set via: ORNAMENT_API_KEY env var, or run: ornament.py auth set")
            sys.exit(1)
        src = "env var ORNAMENT_API_KEY" if st["env"] else st["file"]
        print(f"API key: configured ({src})")
        return
    if args.auth_cmd == "set":
        key = args.key
        if not key:
            print("Paste your Ornament API key (input hidden):", file=sys.stderr)
            key = getpass.getpass("")
        if not key.strip():
            sys.exit("Empty key, aborting.")
        path = L.save_api_key(key)
        print(f"Saved to {path} (chmod 600)")
        return
    if args.auth_cmd == "show-file":
        if L.KEY_FILE.is_file():
            print(L.KEY_FILE)
        else:
            sys.exit("No key file (using env or unconfigured)")
        return


# ---------- profiles ----------

def cmd_profiles(args: argparse.Namespace) -> None:
    profiles = L.request("GET", "/accounting-api/public/v1.0/healer/linked-profiles")
    if args.json:
        _print_json(profiles)
        return
    if not isinstance(profiles, list) or not profiles:
        print("No profiles found.")
        return
    print(f"{'PID':<38} {'Name':<28} {'Sex':<4} {'Birthday':<11} Demo  LastUpdate")
    print("-" * 100)
    for p in profiles:
        ts = p.get("lastSubmissionsUpdate")
        last = _fmt_date(ts) if ts else "-"
        print(
            f"{p.get('pid',''):<38} "
            f"{(p.get('name') or '')[:28]:<28} "
            f"{(p.get('sex') or ''):<4} "
            f"{(p.get('birthday') or ''):<11} "
            f"{'yes' if p.get('isDemoPatient') else 'no ':<4} "
            f"{last}"
        )


# ---------- biomarkers ----------

def _load_entries(pid: str, since: int | None, limit: int, skip: int) -> dict[str, Any]:
    params = {"pid": pid}
    if limit:
        params["limit"] = limit
    if skip:
        params["skip"] = skip
    if since:
        params["dateFrom"] = dt.date.fromtimestamp(since).isoformat()
    return L.request("GET", "/medical-data-api/public/v1.0/profile/biomarkers", params=params)


def cmd_biomarkers(args: argparse.Namespace) -> None:
    pid, profile = _resolve_profile(args.profile)
    since_ts = None
    if args.since:
        since_ts = int(dt.datetime.fromisoformat(args.since).timestamp())
    data = _load_entries(pid, since_ts, args.limit or 0, args.skip or 0)
    thes = L.load_biomarker_thesaurus(args.lang)
    units = L.load_units(args.lang)
    cats = L.load_biomarker_categories(args.lang) if args.by_category else {}

    biomarkers = data.get("biomarkers", [])
    refs = data.get("refs", {})

    rows: list[dict[str, Any]] = []
    name_filter = (args.name or "").lower().strip()
    for b in biomarkers:
        if args.abnormal_only and b.get("status") == "N":
            continue
        entries = b.get("entries") or []
        if not entries:
            continue
        latest = max(entries, key=lambda e: e["date"])
        if since_ts and latest["date"] < since_ts:
            continue
        name = L.biomarker_name(b["id"], thes)
        if name_filter and name_filter not in name.lower():
            syn = (thes.get(b["id"]) or {}).get("synonyms") or []
            if not any(name_filter in (s.get("title", "") or "").lower() for s in syn):
                continue
        if args.json:
            for e in entries:
                e["dateISO"] = _fmt_date(e["date"])
                e["unit"] = units.get(e.get("originalUnitId"), "")
            rows.append({**b, "name": name})
            continue
        val, unit = L.display_value(latest, b["id"], thes, units)
        ref = L.reference_in_original_unit(b["id"], refs, latest, thes)
        rows.append({
            "date": latest["date"],
            "bm_id": b["id"],
            "category_id": b.get("categoryId"),
            "name": name,
            "value": val,
            "unit": unit,
            "ref": ref,
            "status": b.get("status"),
            "count": len(entries),
        })

    if args.json:
        out = {**data, "biomarkers": rows, "profile": {"pid": pid, "name": profile.get("name")}}
        _print_json(out)
        return

    rows.sort(key=lambda r: (-r["date"], r["name"]))

    print(f"Profile: {profile.get('name')}  PID {pid}")
    print(f"Biomarkers shown: {len(rows)} (of {data.get('total', '?')} total recorded)")
    print()
    if args.by_category:
        rows_by_cat: dict[int, list[dict[str, Any]]] = {}
        for r in rows:
            rows_by_cat.setdefault(r["category_id"] or 0, []).append(r)
        for cat_id in sorted(rows_by_cat):
            cat = cats.get(cat_id, {})
            print(f"## {cat.get('title') or f'Category {cat_id}'}")
            _print_rows(rows_by_cat[cat_id])
            print()
    else:
        _print_rows(rows)


def _print_rows(rows: list[dict[str, Any]]) -> None:
    print(f"{'Date':<11} {'S':<2} {'Name':<48} {'Value':<14} {'Unit':<14} {'Reference':<18} N")
    print("-" * 115)
    for r in rows:
        ref = L.format_ref(r["ref"])
        print(
            f"{_fmt_date(r['date']):<11} "
            f"{r['status'] or '?':<2} "
            f"{(r['name'])[:48]:<48} "
            f"{r['value'][:14]:<14} "
            f"{(r['unit'] or '')[:14]:<14} "
            f"{ref:<18} "
            f"{r['count']}"
        )


# ---------- history ----------

def cmd_history(args: argparse.Namespace) -> None:
    pid, profile = _resolve_profile(args.profile)
    data = _load_entries(pid, None, 0, 0)
    biomarkers = data.get("biomarkers", [])
    thes = L.load_biomarker_thesaurus(args.lang)
    units = L.load_units(args.lang)
    refs = data.get("refs", {})

    target: list[dict[str, Any]] = []
    if args.id is not None:
        target = [b for b in biomarkers if b["id"] == args.id]
    else:
        needle = (args.name or "").lower().strip()
        if not needle:
            sys.exit("Provide --id <int> or --name <substring>")
        for b in biomarkers:
            name = L.biomarker_name(b["id"], thes)
            if needle in name.lower():
                target.append(b)
            else:
                syn = (thes.get(b["id"]) or {}).get("synonyms") or []
                if any(needle in (s.get("title", "") or "").lower() for s in syn):
                    target.append(b)
    if not target:
        sys.exit("No biomarker matched. Try --json on the biomarkers command to discover IDs.")

    if args.json:
        out = []
        for b in target:
            entries = []
            for e in (b.get("entries") or []):
                ee = dict(e)
                ee["dateISO"] = _fmt_date(e["date"])
                ee["unit"] = units.get(e.get("originalUnitId"), "")
                entries.append(ee)
            out.append({
                "id": b["id"],
                "name": L.biomarker_name(b["id"], thes),
                "status": b.get("status"),
                "entries": entries,
            })
        _print_json(out)
        return

    print(f"Profile: {profile.get('name')}  PID {pid}")
    for b in target:
        name = L.biomarker_name(b["id"], thes)
        entries = sorted(b.get("entries") or [], key=lambda e: e["date"])
        print(f"\n=== [{b['id']}] {name}  (last status: {b.get('status')}, {len(entries)} measurement(s)) ===")
        if entries:
            # Show ref range in the unit of the most recent entry
            ref_block = refs.get(str(b["id"]), {})
            for kind in ("common", "optimal", "paidOptimal"):
                if ref_block.get(kind):
                    rng = L.reference_in_original_unit(b["id"], refs, entries[-1], thes, prefer=kind)
                    unit_disp = units.get(entries[-1].get("originalUnitId"), "")
                    print(f"  {kind:<11} range: {L.format_ref(rng)} {unit_disp}")
        print(f"  {'Date':<11} {'Value':<14} {'Unit':<14} {'Reference (orig)':<20}")
        for e in entries:
            unit = units.get(e.get("originalUnitId"), "")
            ref = L.reference_in_original_unit(b["id"], refs, e, thes)
            val_str = L._fmt_value(e.get("originalValue"))
            print(f"  {_fmt_date(e['date']):<11} {val_str[:14]:<14} {unit[:14]:<14} {L.format_ref(ref):<20}")


# ---------- submissions ----------

def cmd_submissions(args: argparse.Namespace) -> None:
    pid, profile = _resolve_profile(args.profile)
    # NOTE: server returns 500 when `limit`/`skip` are sent. Filter on the client.
    params: dict[str, Any] = {"pid": pid}
    if args.since:
        params["dateFrom"] = args.since
    data = L.request("GET", "/medical-data-api/public/v1.0/profile/submissions", params=params)
    subs = data.get("submissions") if isinstance(data, dict) else data
    if args.skip:
        subs = subs[args.skip:]
    if args.limit:
        subs = subs[:args.limit]
    if args.json:
        if isinstance(data, dict):
            data = {**data, "submissions": subs}
        _print_json(data)
        return
    if not subs:
        print("No submissions found.")
        return
    has_lab = any(((s.get("laboratory") or {}).get("title") or "") for s in subs)
    print(f"Profile: {profile.get('name')}  PID {pid}  ({data.get('total', '?')} total)")
    if has_lab:
        print(f"{'Date':<11} {'SID':<38} {'Lab':<22} Entries  Deleted")
        print("-" * 95)
    else:
        print(f"{'Date':<11} {'SID':<38} Entries  Deleted")
        print("-" * 75)
    for s in subs:
        d = _fmt_date(s.get("date")) if s.get("date") else "-"
        entries = len(s.get("entries") or []) if isinstance(s, dict) else "?"
        del_flag = "yes" if s.get("isDeleted") else ""
        if has_lab:
            lab = (s.get("laboratory") or {}).get("title") or "—"
            print(f"{d:<11} {s.get('sid',''):<38} {lab[:22]:<22} {entries:<8} {del_flag}")
        else:
            print(f"{d:<11} {s.get('sid',''):<38} {entries:<8} {del_flag}")


# ---------- health conditions ----------

def cmd_conditions(args: argparse.Namespace) -> None:
    pid, profile = _resolve_profile(args.profile)
    endpoint = "/medical-data-api/public/v1.0/profile/health-conditions-raw" if args.raw else \
               "/medical-data-api/public/v1.0/profile/health-conditions"
    data = L.request("GET", endpoint, params={"pid": pid})
    _print_json(data)


# ---------- health advisor ----------

def cmd_advisor(args: argparse.Namespace) -> None:
    pid, profile = _resolve_profile(args.profile)
    if args.advisor_cmd == "raw":
        data = L.request("GET", "/public/health-advisor-api/v1.0/profile-health-conditions-raw", params={"pid": pid})
    else:
        data = L.request("GET", "/public/health-advisor-api/v1.0/actual-states", params={"pid": pid})
    _print_json(data)


# ---------- thesaurus ----------

def cmd_thesaurus(args: argparse.Namespace) -> None:
    if args.target == "biomarkers":
        thes = L.load_biomarker_thesaurus(args.lang, refresh=args.refresh)
        if args.search:
            needle = args.search.lower()
            hits = [b for b in thes.values() if needle in b.get("title", "").lower()
                    or any(needle in (s.get("title", "") or "").lower() for s in (b.get("synonyms") or []))]
            for b in sorted(hits, key=lambda x: x["title"])[:50]:
                print(f"  [{b['id']:>5}] {b['title']}")
        else:
            print(f"Loaded {len(thes)} biomarkers in '{args.lang}' (cached).")
    elif args.target == "units":
        units = L.load_units(args.lang, refresh=args.refresh)
        for uid in sorted(units):
            print(f"  [{uid:>4}] {units[uid]}")
    elif args.target == "categories":
        cats = L.load_biomarker_categories(args.lang, refresh=args.refresh)
        for cid in sorted(cats):
            c = cats[cid]
            print(f"  [{cid:>4}] {c.get('title')}  parent={c.get('parentId')}")
    else:
        sys.exit(f"Unknown thesaurus target: {args.target}")


# ---------- raw escape hatch ----------

def cmd_raw(args: argparse.Namespace) -> None:
    body = None
    if args.body:
        body = json.loads(args.body)
    data = L.request(args.method.upper(), args.path, body=body)
    _print_json(data)


# ---------- argparse ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ornament", description="Ornament Health API CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    ob = sub.add_parser("onboard", help="Print the Ornament Pro onboarding checklist")
    ob.set_defaults(func=cmd_onboard)

    a = sub.add_parser("auth", help="Manage API key")
    a_sub = a.add_subparsers(dest="auth_cmd", required=True)
    a_set = a_sub.add_parser("set", help="Save API key to ~/.config/ornament/api_key")
    a_set.add_argument("key", nargs="?", help="If omitted, read from stdin (hidden)")
    a_sub.add_parser("status", help="Show whether a key is configured")
    a_sub.add_parser("show-file", help="Print the key file path if it exists")
    a.set_defaults(func=cmd_auth)

    pf = sub.add_parser("profiles", help="List linked profiles (patients)")
    pf.add_argument("--json", action="store_true")
    pf.set_defaults(func=cmd_profiles)

    bm = sub.add_parser("biomarkers", help="Show biomarkers for a profile")
    bm.add_argument("--profile", default="me", help="PID, name substring, or 'me' (default)")
    bm.add_argument("--abnormal-only", action="store_true")
    bm.add_argument("--name", help="Filter by biomarker name substring")
    bm.add_argument("--since", help="YYYY-MM-DD — only latest values from this date")
    bm.add_argument("--by-category", action="store_true", help="Group by display category")
    bm.add_argument("--limit", type=int, default=0)
    bm.add_argument("--skip", type=int, default=0)
    bm.add_argument("--lang", default="RU")
    bm.add_argument("--json", action="store_true")
    bm.set_defaults(func=cmd_biomarkers)

    hi = sub.add_parser("history", help="Show full history of one biomarker")
    hi.add_argument("--profile", default="me")
    hi.add_argument("--id", type=int, help="Biomarker ID")
    hi.add_argument("--name", help="Biomarker name substring")
    hi.add_argument("--lang", default="RU")
    hi.add_argument("--json", action="store_true")
    hi.set_defaults(func=cmd_history)

    sb = sub.add_parser("submissions", help="List the profile's submissions (uploaded reports)")
    sb.add_argument("--profile", default="me")
    sb.add_argument("--since", help="YYYY-MM-DD")
    sb.add_argument("--limit", type=int, default=0, help="Client-side cap (server's limit param is broken)")
    sb.add_argument("--skip", type=int, default=0, help="Client-side offset")
    sb.add_argument("--json", action="store_true")
    sb.set_defaults(func=cmd_submissions)

    co = sub.add_parser("conditions", help="Show profile health-conditions (medical-data API)")
    co.add_argument("--profile", default="me")
    co.add_argument("--raw", action="store_true", help="Use the *-raw endpoint")
    co.set_defaults(func=cmd_conditions)

    ad = sub.add_parser("advisor", help="Health Advisor API: interpreted risk scores / diseases")
    ad_sub = ad.add_subparsers(dest="advisor_cmd", required=True)
    for name, help_ in [("states", "GET /v1.0/actual-states (interpreted)"),
                        ("raw", "GET /v1.0/profile-health-conditions-raw (detailed)")]:
        p_ = ad_sub.add_parser(name, help=help_)
        p_.add_argument("--profile", default="me")
        p_.add_argument("--json", action="store_true", help="(default — kept for consistency)")
        p_.set_defaults(func=cmd_advisor)

    th = sub.add_parser("thesaurus", help="Inspect/refresh reference data (biomarker names, units, categories)")
    th.add_argument("target", choices=["biomarkers", "units", "categories"])
    th.add_argument("--lang", default="RU")
    th.add_argument("--search", help="(biomarkers only) substring search")
    th.add_argument("--refresh", action="store_true", help="Bypass cache and refetch")
    th.set_defaults(func=cmd_thesaurus)

    rw = sub.add_parser("raw", help="Send a raw request (escape hatch)")
    rw.add_argument("method", help="GET, POST, ...")
    rw.add_argument("path", help="/medical-data-api/public/v1.0/...")
    rw.add_argument("--body", help="JSON string for request body")
    rw.set_defaults(func=cmd_raw)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except L.OrnamentError as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
