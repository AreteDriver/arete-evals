from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import yaml
from jsonschema import Draft202012Validator

from arete_evals.cli import main
from arete_evals.project import InputError, audit_project, load_manifest, schema

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 9, 29)


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.manifest = yaml.safe_load((ROOT / "PROJECT_MANIFEST.yaml").read_text())
        self.manifest["standard"]["source"] = "STANDARD.md"
        self.write(
            "STANDARD.md",
            (
                ROOT / "docs/standards/PROJECT_FOLDER_SETUP_EVALUATION_STANDARD.md"
            ).read_text(),
        )
        self.manifest["standard"]["sha256"] = hashlib.sha256(
            (self.root / "STANDARD.md").read_bytes()
        ).hexdigest()
        for record in self.manifest["authority"].values():
            self.write(
                record["path"],
                "Fixture authority with documented purpose and boundaries.\n"
                "<!-- arete:package_version=0.2.0 -->\n"
                "<!-- arete:engine_version=0.2.0 -->\n",
            )
        self.write(
            "pyproject.toml",
            '[project]\nversion="0.2.0"\ndependencies=["evalcore==0.2.0"]\n',
        )
        self.write(".gitignore", ".env\n")
        self.save()
        self.git("init", "-q")
        self.git(
            "remote", "add", "origin", "https://github.com/AreteDriver/arete-evals.git"
        )
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "fixture",
        )

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
            timeout=15,
        )

    def write(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def save(self):
        self.write("PROJECT_MANIFEST.yaml", json.dumps(self.manifest))

    def audit(self, **kwargs):
        return audit_project(self.root, as_of=TODAY, **kwargs)

    def codes(self):
        return {f["code"] for f in self.audit()["findings"]}

    def test_good_fixture_is_conditional_not_certified(self):
        r = self.audit(require_clean=True)
        self.assertEqual(r["outcome"], "PASS WITH CONDITIONS")
        self.assertTrue(r["automated_gates_passed"])
        self.assertEqual(r["certification"], "UNKNOWN")
        self.assertIsNone(r["score"])
        self.assertFalse(r["tests_executed"])
        self.assertEqual(set(r["gates"].values()), {"PASS"})

    def test_broken_fixture_recipes(self):
        recipes = json.loads((ROOT / "tests/fixtures/projects/broken.json").read_text())
        original = copy.deepcopy(self.manifest)
        for recipe in recipes:
            with self.subTest(recipe["name"]):
                if "set" in recipe:
                    target = self.manifest
                    for key in recipe["set"][:-1]:
                        target = target[key]
                    target[recipe["set"][-1]] = recipe["value"]
                    self.save()
                backup = None
                name = recipe.get("remove", recipe.get("write"))
                if name:
                    backup = (self.root / name).read_text()
                    if "remove" in recipe:
                        (self.root / name).unlink()
                    else:
                        self.write(name, recipe["text"])
                self.assertIn(recipe["code"], self.codes())
                self.assertFalse(self.audit()["automated_gates_passed"])
                if backup is not None:
                    self.write(name, backup)
                self.manifest = copy.deepcopy(original)
                self.save()

    def test_yaml_alias_duplicate_tag_and_depth_rejected(self):
        for text in [
            "a: &x [1]\nb: *x",
            "a: 1\na: 2",
            "!!python/object:os.system {}",
            "x: " + "[" * 30 + "0" + "]" * 30,
        ]:
            with self.subTest(text=text[:20]):
                self.write("PROJECT_MANIFEST.yaml", text)
                self.assertIn("manifest.invalid", self.codes())

    def test_yaml_scalar_and_wrong_types_rejected(self):
        for value in [None, [], "hello", 42, {"schema_version": True}]:
            self.write("PROJECT_MANIFEST.yaml", yaml.safe_dump(value))
            self.assertIn("manifest.invalid", self.codes())

    def test_oversized_manifest_rejected(self):
        self.write("PROJECT_MANIFEST.yaml", "x" * 1_048_577)
        self.assertIn("manifest.invalid", self.codes())

    def test_symlink_authority_rejected(self):
        (self.root / "STATUS.md").unlink()
        (self.root / "STATUS.md").symlink_to(self.root / "README.md")
        self.assertIn("authority.invalid", self.codes())

    def test_symlink_manifest_rejected(self):
        (self.root / "PROJECT_MANIFEST.yaml").rename(self.root / "real.yaml")
        (self.root / "PROJECT_MANIFEST.yaml").symlink_to("real.yaml")
        self.assertIn("manifest.invalid", self.codes())

    def test_symlink_directory_and_windows_paths_rejected(self):
        (self.root / "linked").symlink_to(self.root, target_is_directory=True)
        for value in ["linked/STATUS.md", "C:\\secret", "/tmp/secret", "../secret"]:
            self.manifest["authority"]["current_state"]["path"] = value
            self.save()
            self.assertFalse(self.audit()["automated_gates_passed"])

    def test_non_regular_authority_rejected(self):
        (self.root / "STATUS.md").unlink()
        (self.root / "STATUS.md").mkdir()
        self.assertIn("authority.invalid", self.codes())

    def test_future_and_invalid_review_dates_rejected(self):
        for day in ["2030-01-01", "2026-02-31"]:
            self.manifest["project"]["last_reviewed"] = day
            self.save()
            self.assertFalse(self.audit()["automated_gates_passed"])

    def test_actual_package_fact_beats_agreeing_documents(self):
        self.write(
            "pyproject.toml",
            '[project]\nversion="9"\ndependencies=["evalcore==0.2.0"]\n',
        )
        self.assertIn("claim.implementation", self.codes())

    def test_standard_tampering_fails(self):
        self.write("STANDARD.md", "modified")
        self.assertIn("standard.invalid", self.codes())

    def test_unknown_marker_fails(self):
        with (self.root / "README.md").open("a") as handle:
            handle.write("<!-- arete:invented=PASS -->")
        self.assertIn("claim.undeclared", self.codes())

    def test_dirty_checkout_and_clean_requirement(self):
        self.write("new.txt", "change")
        self.assertEqual(self.audit()["outcome"], "PASS WITH CONDITIONS")
        self.assertEqual(self.audit(require_clean=True)["outcome"], "FAIL")

    def test_missing_git_and_nested_root_cannot_pass(self):
        shutil.rmtree(self.root / ".git")
        self.assertIn("git.unavailable", self.codes())
        self.assertFalse(self.audit()["automated_gates_passed"])

    def test_git_error_and_timeout_cannot_pass(self):
        for exc in [OSError(), subprocess.TimeoutExpired("git", 10)]:
            with patch("arete_evals.project._git", side_effect=exc):
                self.assertEqual(self.audit()["gates"]["Canonical Source"], "UNKNOWN")
                self.assertFalse(self.audit()["automated_gates_passed"])

    def test_sensitive_tracked_file_fails_without_content_in_report(self):
        self.write("secrets.json", "private-value-do-not-echo")
        self.git("add", "secrets.json")
        report = self.audit()
        self.assertIn("secrets.tracked", {f["code"] for f in report["findings"]})
        self.assertNotIn("private-value", json.dumps(report))

    def test_manifest_commands_are_never_executed(self):
        self.manifest["verification"]["tests"] = ["sh", "-c", "touch OWNED; exit 0"]
        self.save()
        self.audit()
        self.assertFalse((self.root / "OWNED").exists())

    def test_schema_errors_do_not_echo_secret_values(self):
        self.manifest["project"]["classification"] = "secret-value"
        self.save()
        self.assertNotIn("secret-value", json.dumps(self.audit()))

    def test_report_is_deterministic_and_root_independent(self):
        a = self.audit()
        self.assertEqual(a, self.audit())
        self.assertNotIn(str(self.root), json.dumps(a))
        with tempfile.TemporaryDirectory() as other:
            target = Path(other) / "copy"
            shutil.copytree(self.root, target)
            self.assertEqual(a, audit_project(target, as_of=TODAY))

    def test_cli_json_and_strict_exits(self):
        command = [
            sys.executable,
            "-m",
            "arete_evals.cli",
            "project",
            "audit",
            str(self.root),
            "--format",
            "json",
            "--as-of",
            str(TODAY),
        ]
        env = {**os.environ, "PYTHONPATH": str(ROOT)}
        result = subprocess.run(
            command, env=env, capture_output=True, text=True, timeout=30
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["outcome"], "PASS WITH CONDITIONS")
        self.assertEqual(
            subprocess.run(
                command + ["--strict"], env=env, capture_output=True, timeout=30
            ).returncode,
            1,
        )
        (self.root / "STATUS.md").unlink()
        self.assertEqual(
            subprocess.run(
                command, env=env, capture_output=True, timeout=30
            ).returncode,
            1,
        )

    def test_project_command_does_not_load_evalcore(self):
        with patch("builtins.print"), patch.dict(sys.modules, {"evalcore": None}):
            self.assertEqual(
                main(["project", "audit", str(self.root), "--as-of", str(TODAY)]), 0
            )

    def test_schema_is_valid_and_real_manifest_loads(self):
        Draft202012Validator.check_schema(schema())
        self.assertEqual(load_manifest(ROOT)["project"]["name"], "arete-evals")

    def test_reports_validate_against_packaged_schema(self):
        contract = json.loads(
            (ROOT / "arete_evals/schemas/project-audit-v1.schema.json").read_text()
        )
        validator = Draft202012Validator(contract)
        validator.validate(self.audit())
        (self.root / "STATUS.md").unlink()
        validator.validate(self.audit())

    def test_conflicting_canonical_repository_fails(self):
        self.git("remote", "set-url", "origin", "https://github.com/other/project")
        self.assertIn("canonical.conflict", self.codes())

    def test_negated_secret_exclusion_fails(self):
        self.write(".gitignore", ".env\n!.env\n")
        self.assertIn("secrets.policy", self.codes())

    def test_cannot_replace_the_adopted_standard_with_self_asserted_hash(self):
        self.manifest["standard"]["sha256"] = "0" * 64
        self.save()
        self.assertIn("manifest.invalid", self.codes())

    def test_sensitive_reference_is_rejected(self):
        self.write(".env", "test-private-value")
        self.manifest["authority"]["current_state"]["path"] = ".env"
        self.save()
        self.assertIn("authority.invalid", self.codes())
        self.assertNotIn("test-private-value", json.dumps(self.audit()))

    def test_missing_manifest_is_structured_failure(self):
        (self.root / "PROJECT_MANIFEST.yaml").unlink()
        self.assertEqual(self.audit()["outcome"], "FAIL")
        with self.assertRaises(InputError):
            load_manifest(self.root)
