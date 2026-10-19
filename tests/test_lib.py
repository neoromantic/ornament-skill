"""Offline tests for the pure helpers in scripts/_lib.py. No network, no real data."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import _lib as L

# A made-up thesaurus: one biomarker with a unit factor, one without.
THES = {
    10: {"id": 10, "title": "  Glucose ", "unitsFactors": [[1, 1.0], [2, 0.0555]]},
    20: {"id": 20, "title": "Ferritin"},
}
UNITS = {1: "mmol/L", 2: "mg/dL"}
REFS = {"10": {"common": [3.9, 5.6], "optimal": [4.0, 5.0]}, "20": {"common": [30, 400]}}


class BiomarkerNameTest(unittest.TestCase):
    def test_strips_title(self):
        self.assertEqual(L.biomarker_name(10, THES), "Glucose")

    def test_unknown_id(self):
        self.assertEqual(L.biomarker_name(99, THES), "ID 99")


class FmtValueTest(unittest.TestCase):
    def test_none(self):
        self.assertEqual(L._fmt_value(None), "")

    def test_integer_like(self):
        self.assertEqual(L._fmt_value(5.0), "5")
        self.assertEqual(L._fmt_value("12"), "12")

    def test_ranges(self):
        self.assertEqual(L._fmt_value(1234.5), "1 234.5")
        self.assertEqual(L._fmt_value(12.345), "12.35")
        self.assertEqual(L._fmt_value(5.5), "5.5")
        self.assertEqual(L._fmt_value(0.0512), "0.0512")
        self.assertEqual(L._fmt_value(0.001234), "0.00123")

    def test_non_numeric(self):
        self.assertEqual(L._fmt_value("negative"), "negative")


class DisplayValueTest(unittest.TestCase):
    def test_prefers_original_value_and_unit(self):
        entry = {"value": 5.5, "originalValue": 99.1, "originalUnitId": 2}
        self.assertEqual(L.display_value(entry, 10, THES, UNITS), ("99.1", "mg/dL"))

    def test_falls_back_to_canonical_value(self):
        entry = {"value": 5.5, "originalUnitId": 7}
        self.assertEqual(L.display_value(entry, 10, THES, UNITS), ("5.5", ""))


class ReferenceTest(unittest.TestCase):
    def test_converts_to_original_unit(self):
        entry = {"originalUnitId": 2}
        lo, hi = L.reference_in_original_unit(10, REFS, entry, THES)
        self.assertAlmostEqual(lo, 3.9 / 0.0555)
        self.assertAlmostEqual(hi, 5.6 / 0.0555)

    def test_prefer_block(self):
        entry = {"originalUnitId": 1}
        self.assertEqual(L.reference_in_original_unit(10, REFS, entry, THES, prefer="optimal"), (4.0, 5.0))

    def test_no_factor_keeps_canonical(self):
        self.assertEqual(L.reference_in_original_unit(20, REFS, {"originalUnitId": 3}, THES), (30.0, 400.0))

    def test_missing_ref(self):
        self.assertIsNone(L.reference_in_original_unit(30, REFS, {}, THES))
        self.assertIsNone(L.reference_in_original_unit(10, {"10": {"common": [1]}}, {}, THES))


class FormatRefTest(unittest.TestCase):
    def test_none(self):
        self.assertEqual(L.format_ref(None), "")

    def test_magnitudes(self):
        self.assertEqual(L.format_ref((0, 1800)), "[0–1 800]")
        self.assertEqual(L.format_ref((150, 400)), "[150–400]")
        self.assertEqual(L.format_ref((12.5, 30)), "[12.5–30]")
        self.assertEqual(L.format_ref((3.9, 5.6)), "[3.9–5.6]")
        self.assertEqual(L.format_ref((0.25, 0.5)), "[0.25–0.5]")
        self.assertEqual(L.format_ref((0.012, 0.05)), "[0.012–0.05]")
        self.assertEqual(L.format_ref((0.001234, 0.005)), "[0.00123–0.005]")


class ApiKeyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        cfg = Path(self.tmp.name) / "config"
        for name, value in {"CONFIG_DIR": cfg, "KEY_FILE": cfg / "api_key"}.items():
            patcher = mock.patch.object(L, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        env = mock.patch.dict(os.environ, {}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("ORNAMENT_API_KEY", None)

    def test_env_wins(self):
        os.environ["ORNAMENT_API_KEY"] = "  env-key \n"
        L.save_api_key("file-key")
        self.assertEqual(L.load_api_key(), "env-key")

    def test_file_fallback_and_mode(self):
        path = L.save_api_key(" file-key \n")
        self.assertEqual(path.read_text(), "file-key\n")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(L.load_api_key(), "file-key")

    def test_missing_key_exits(self):
        with mock.patch.object(sys, "stderr"), self.assertRaises(SystemExit) as cm:
            L.load_api_key()
        self.assertEqual(cm.exception.code, 2)

    def test_auth_status(self):
        self.assertEqual(L.auth_status(), {"env": False, "file": None, "ready": False})
        L.save_api_key("file-key")
        self.assertEqual(L.auth_status(), {"env": False, "file": str(L.KEY_FILE), "ready": True})


class ThesaurusCacheTest(unittest.TestCase):
    """Fresh cache files are read without any request."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(L, "CACHE_DIR", Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        no_net = mock.patch.object(L, "request", side_effect=AssertionError("network call in an offline test"))
        no_net.start()
        self.addCleanup(no_net.stop)

    def write(self, name: str, data: object) -> None:
        (Path(self.tmp.name) / name).write_text(json.dumps(data))

    def test_biomarkers_keyed_by_id(self):
        self.write("biomarkers_EN+RU.json", {"biomarkers": [{"id": 10, "title": "Glucose"}]})
        self.assertEqual(L.load_biomarker_thesaurus("EN+RU"), {10: {"id": 10, "title": "Glucose"}})

    def test_units_use_first_language(self):
        self.write("units_EN.json", [{"id": 1, "title": "mmol/L"}])
        self.assertEqual(L.load_units("EN+RU"), {1: "mmol/L"})

    def test_categories_accept_list_or_object(self):
        self.write("categories_EN.json", [{"id": 3, "title": "Blood"}])
        self.assertEqual(L.load_biomarker_categories("EN+RU"), {3: {"id": 3, "title": "Blood"}})
        self.write("categories_RU.json", {"categories": [{"id": 4, "title": "Кровь"}]})
        self.assertEqual(L.load_biomarker_categories("RU"), {4: {"id": 4, "title": "Кровь"}})


if __name__ == "__main__":
    unittest.main()
