"""Shared library for the Ornament Health skill.

Handles:
- API key resolution (env var > config file).
- HTTP requests (stdlib only, no dependencies).
- Thesaurus caching for biomarker names and units.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE = "https://api.ornament.health"
CONFIG_DIR = Path(os.path.expanduser("~/.config/ornament"))
CACHE_DIR = Path(os.path.expanduser("~/.cache/ornament"))
KEY_FILE = CONFIG_DIR / "api_key"
DEFAULT_TIMEOUT = 30
CACHE_TTL_SECONDS = 30 * 24 * 3600  # 30 days for thesaurus


# ---------- API key ----------

def load_api_key() -> str:
    key = os.environ.get("ORNAMENT_API_KEY", "").strip()
    if key:
        return key
    if KEY_FILE.is_file():
        return KEY_FILE.read_text().strip()
    sys.stderr.write(
        "ERROR: Ornament API key not found.\n"
        "Set ORNAMENT_API_KEY env var or run:  ornament.py auth set\n"
    )
    sys.exit(2)


def save_api_key(key: str) -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_text(key.strip() + "\n")
    KEY_FILE.chmod(0o600)
    return KEY_FILE


def auth_status() -> dict[str, Any]:
    env_set = bool(os.environ.get("ORNAMENT_API_KEY", "").strip())
    file_set = KEY_FILE.is_file()
    return {
        "env": env_set,
        "file": str(KEY_FILE) if file_set else None,
        "ready": env_set or file_set,
    }


# ---------- HTTP ----------

class OrnamentError(Exception):
    def __init__(self, status: int, body: str, url: str):
        self.status = status
        self.body = body
        self.url = url
        super().__init__(f"HTTP {status} from {url}: {body[:300]}")


def request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    url = path if path.startswith("http") else BASE + path
    if params:
        q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{url}?{q}" if q else url

    data = None
    headers = {
        "Authorization": f"Bearer {load_api_key()}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return None
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
    except urllib.error.HTTPError as e:
        raise OrnamentError(e.code, e.read().decode("utf-8", "replace"), url) from e


# ---------- Thesaurus cache ----------

def _cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / name


def _fresh(p: Path) -> bool:
    if not p.is_file():
        return False
    return (time.time() - p.stat().st_mtime) < CACHE_TTL_SECONDS


def load_biomarker_thesaurus(lang: str = "RU", refresh: bool = False) -> dict[int, dict[str, Any]]:
    """Return {biomarker_id: thesaurus_entry}. Cached locally."""
    p = _cache_path(f"biomarkers_{lang}.json")
    if refresh or not _fresh(p):
        data = request("POST", "/thesaurus-api/public/v1.1/biomarkers", body={"lang": lang})
        p.write_text(json.dumps(data, ensure_ascii=False))
    data = json.loads(p.read_text())
    return {b["id"]: b for b in data.get("biomarkers", [])}


def load_units(lang: str = "RU", refresh: bool = False) -> dict[int, str]:
    """Return {unit_id: title}."""
    lang = lang.split("+")[0]
    p = _cache_path(f"units_{lang}.json")
    if refresh or not _fresh(p):
        data = request("GET", "/thesaurus-api/public/v1.1/measurement-units", params={"lang": lang})
        p.write_text(json.dumps(data, ensure_ascii=False))
    data = json.loads(p.read_text())
    return {u["id"]: u["title"] for u in data}


def load_biomarker_categories(lang: str = "RU", refresh: bool = False) -> dict[int, dict[str, Any]]:
    lang = lang.split("+")[0]
    p = _cache_path(f"categories_{lang}.json")
    if refresh or not _fresh(p):
        data = request("GET", "/thesaurus-api/public/v1.0/biomarker-categories", params={"lang": lang})
        p.write_text(json.dumps(data, ensure_ascii=False))
    data = json.loads(p.read_text())
    # API returns a list of category objects
    return {c["id"]: c for c in (data if isinstance(data, list) else data.get("categories", []))}


# ---------- Value normalization ----------

def biomarker_name(bm_id: int, thes: dict[int, dict[str, Any]]) -> str:
    entry = thes.get(bm_id)
    return (entry["title"].strip() if entry else f"ID {bm_id}")


def display_value(entry: dict[str, Any], bm_id: int, thes: dict[int, dict[str, Any]], units: dict[int, str]) -> tuple[str, str]:
    """Return (value_string, unit_string) suitable for display.

    `entry.originalValue` and `entry.originalUnitId` are what the lab reported.
    `entry.value` is the canonical (internal) value.
    """
    raw = entry.get("originalValue")
    if raw is None:
        raw = entry.get("value")
    val_str = _fmt_value(raw)
    unit = units.get(entry.get("originalUnitId"), "")
    return val_str, unit


def _fmt_value(raw: Any) -> str:
    if raw is None:
        return ""
    try:
        x = float(raw)
    except (TypeError, ValueError):
        return str(raw)
    if x == int(x) and abs(x) < 1e9:
        return str(int(x))
    ax = abs(x)
    if ax >= 1000:
        return f"{x:,.1f}".replace(",", " ").rstrip("0").rstrip(".")
    if ax >= 10:
        return f"{x:.2f}".rstrip("0").rstrip(".")
    if ax >= 1:
        return f"{x:.3f}".rstrip("0").rstrip(".")
    if ax >= 0.01:
        return f"{x:.4f}".rstrip("0").rstrip(".")
    return f"{x:.3g}"


def reference_in_original_unit(
    bm_id: int,
    refs: dict[str, Any],
    entry: dict[str, Any],
    thes: dict[int, dict[str, Any]],
    prefer: str = "common",
) -> tuple[float, float] | None:
    """Convert refs.common (canonical) into the entry's original unit using unitsFactors.

    biomarker.unitsFactors is a list like [[unitId, factor], ...]. The canonical value
    equals originalValue * factor.  So a ref range [lo, hi] in canonical units becomes
    [lo/factor, hi/factor] in the original unit.
    """
    ref_block = refs.get(str(bm_id)) or {}
    ref = ref_block.get(prefer) or ref_block.get("common") or []
    if not ref or len(ref) < 2:
        return None
    lo, hi = float(ref[0]), float(ref[1])
    orig_unit = entry.get("originalUnitId")
    bm = thes.get(bm_id) or {}
    factors = {u: f for u, f in (bm.get("unitsFactors") or [])}
    factor = factors.get(orig_unit)
    if factor and factor != 0:
        return (lo / factor, hi / factor)
    return (lo, hi)


def format_ref(rng: tuple[float, float] | None) -> str:
    if rng is None:
        return ""
    lo, hi = rng

    def fmt(x: float) -> str:
        if x == 0:
            return "0"
        ax = abs(x)
        if ax >= 1000:
            return f"{x:,.0f}".replace(",", " ")  # 1 800, 2 900
        if ax >= 100:
            return f"{x:.0f}"
        if ax >= 10:
            return f"{x:.1f}".rstrip("0").rstrip(".")
        if ax >= 1:
            return f"{x:.2f}".rstrip("0").rstrip(".")
        if ax >= 0.1:
            return f"{x:.3f}".rstrip("0").rstrip(".")
        if ax >= 0.01:
            return f"{x:.4f}".rstrip("0").rstrip(".")
        return f"{x:.3g}"

    return f"[{fmt(lo)}–{fmt(hi)}]"
