"""test_resolve_args.py — Tests for resolve_args() and --preset in stac-search."""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

import stac_search  # noqa: E402


def make_args(**kwargs):
    defaults = dict(
        preset=None,
        endpoint=None,
        collection=None,
        bbox=None,
        place=None,
        datetime=None,
        max_cloud_cover=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestResolveArgs(unittest.TestCase):
    def test_default_endpoint(self):
        args = make_args(collection=["sentinel-2-l2a"])
        resolved, diag = stac_search.resolve_args(args)
        self.assertIn("planetarycomputer", resolved["endpoint"])

    def test_preset_endpoint(self):
        args = make_args(preset="aws-earth-search", collection=["sentinel-2-l2a"])
        resolved, _ = stac_search.resolve_args(args)
        self.assertIn("earth-search.aws", resolved["endpoint"])

    def test_task_preset_fills_collection_and_bbox(self):
        args = make_args(preset="s2-l2a-china-low-cloud", datetime="2024-06-01/2024-06-30")
        resolved, _ = stac_search.resolve_args(args)
        self.assertEqual(resolved["collection"], ["sentinel-2-l2a"])
        self.assertEqual(resolved["bbox"], (73.0, 18.0, 135.0, 54.0))
        self.assertEqual(resolved["max_cloud_cover"], 20.0)
        self.assertIn("planetarycomputer", resolved["endpoint"])

    def test_user_collection_wins_over_preset(self):
        args = make_args(preset="s2-l2a-china-low-cloud", collection=["landsat-c2-l2"])
        resolved, _ = stac_search.resolve_args(args)
        self.assertEqual(resolved["collection"], ["landsat-c2-l2"])

    def test_place_to_bbox(self):
        args = make_args(preset="planetary-computer", collection=["sentinel-2-l2a"],
                         place="北京市")
        resolved, _ = stac_search.resolve_args(args)
        self.assertEqual(resolved["bbox"], (115.7, 39.4, 116.8, 40.3))

    def test_bbox_wins_over_place(self):
        args = make_args(preset="planetary-computer", collection=["sentinel-2-l2a"],
                         place="北京市", bbox=[100, 20, 120, 40])
        resolved, _ = stac_search.resolve_args(args)
        self.assertEqual(resolved["bbox"], (100, 20, 120, 40))


class TestListPresetsFlag(unittest.TestCase):
    def test_list_presets_subcommand(self):
        out, rc = stac_search.run(["--list-presets"])
        self.assertEqual(rc, 0)
        self.assertIn("s2-l2a-china-low-cloud", out)
        self.assertIn("landsat-china-low-cloud", out)


class TestHelpText(unittest.TestCase):
    def test_help_includes_place_and_preset(self):
        proc = subprocess.run(
            [sys.executable, str(SKILL_DIR / "stac-search.py"), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertIn("--place", proc.stdout)
        self.assertIn("--preset", proc.stdout)
        self.assertIn("--list-presets", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
