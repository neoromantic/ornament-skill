"""Offline tests for the CLI entry point: argument parsing and commands that need no API key."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "scripts" / "ornament.py"
sys.path.insert(0, str(CLI.parent))

import ornament


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "ORNAMENT_API_KEY"}
    return subprocess.run(
        [sys.executable, str(CLI), *args], capture_output=True, text=True, env=env, timeout=30, check=False
    )


class ParserTest(unittest.TestCase):
    def setUp(self):
        self.parser = ornament.build_parser()

    def test_biomarkers_defaults(self):
        args = self.parser.parse_args(["biomarkers"])
        self.assertEqual(args.profile, "me")
        self.assertEqual(args.lang, "RU")
        self.assertFalse(args.abnormal_only)
        self.assertIs(args.func, ornament.cmd_biomarkers)

    def test_biomarkers_flags(self):
        args = self.parser.parse_args(
            ["biomarkers", "--abnormal-only", "--since", "2024-01-01", "--limit", "5", "--lang", "EN+RU", "--json"]
        )
        self.assertTrue(args.abnormal_only)
        self.assertEqual((args.since, args.limit, args.lang, args.json), ("2024-01-01", 5, "EN+RU", True))

    def test_history_by_id(self):
        args = self.parser.parse_args(["history", "--id", "38"])
        self.assertEqual(args.id, 38)
        self.assertIs(args.func, ornament.cmd_history)

    def test_subcommand_required(self):
        with open(os.devnull, "w") as devnull:
            old, sys.stderr = sys.stderr, devnull
            try:
                with self.assertRaises(SystemExit):
                    self.parser.parse_args([])
                with self.assertRaises(SystemExit):
                    self.parser.parse_args(["thesaurus", "diseases"])
            finally:
                sys.stderr = old


class FmtDateTest(unittest.TestCase):
    def test_iso_date(self):
        # Noon UTC, so the local date is the same in every time zone from UTC-11 to UTC+11.
        self.assertEqual(ornament._fmt_date(1_700_000_000 - 1_700_000_000 % 86400 + 43200), "2023-11-14")


class CliTest(unittest.TestCase):
    def test_help(self):
        result = run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("onboard", "auth", "profiles", "biomarkers", "history", "thesaurus", "raw"):
            self.assertIn(command, result.stdout)

    def test_onboard_needs_no_key(self):
        result = run_cli("onboard")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("https://pro.ornament.health/", result.stdout)
        self.assertIn("auth set", result.stdout)


if __name__ == "__main__":
    unittest.main()
