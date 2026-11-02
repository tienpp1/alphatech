"""Offline dependency-policy contracts; no Django setup, network or database."""

from pathlib import Path
import shlex
import unittest

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


ROOT = Path(__file__).resolve().parents[1]


def requirements_by_name():
    requirements = {}
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            requirement = Requirement(line)
            requirements[canonicalize_name(requirement.name)] = requirement
    return requirements


def install_commands(path, *, workflow=False):
    """Read single-line shell install commands without executing build/migrations."""
    commands = []
    for line in path.read_text(encoding="utf-8").splitlines():
        command = line.strip()
        if workflow:
            if not command.startswith(("- run:", "run:")):
                continue
            command = command.split("run:", 1)[1].strip()
        tokens = shlex.split(command, comments=True)
        if tokens[:4] == ["python", "-m", "pip", "install"]:
            commands.append(tokens)
        elif tokens[:2] == ["pip", "install"]:
            commands.append(tokens)
    return commands


class DependencySecurityFloorTests(unittest.TestCase):
    def test_django_rejects_vulnerable_versions_on_every_supported_branch(self):
        specifier = requirements_by_name()["django"].specifier
        vulnerable = (
            [f"5.2.{patch}" for patch in range(18)]
            + [f"6.0.{patch}" for patch in range(9)]
            + ["6.0", "6.1", "6.1.0", "6.1.1"]
        )
        for version in vulnerable:
            with self.subTest(version=version):
                self.assertNotIn(version, specifier)

    def test_django_preserves_patched_lts_and_both_six_series_branches(self):
        specifier = requirements_by_name()["django"].specifier
        for version in ["5.2.18", "5.2.19", "6.0.9", "6.0.10", "6.1.2", "6.1.3"]:
            with self.subTest(version=version):
                self.assertIn(version, specifier)
        for version in ["4.2.30", "5.1.15", "7.0"]:
            with self.subTest(version=version):
                self.assertNotIn(version, specifier)

    def test_application_dependencies_exclude_known_vulnerable_releases(self):
        requirements = requirements_by_name()
        cases = [
            ("djangorestframework", "3.18.0", "3.18.2"),
            ("pillow", "12.3.0", "13.0.0"),
            ("pypdf", "6.21.3", "6.21.4"),
            ("sqlparse", "0.5.5", "0.6.0"),
            ("autobahn", "26.7.1", "26.10.1"),
            ("twisted", "26.4.0", "26.10.0"),
            ("certifi", "2026.7.22", "2026.10.18"),
            ("urllib3", "2.7.0", "2.8.0"),
            ("msgpack", "1.2.2", "1.2.3"),
        ]
        for name, vulnerable, patched in cases:
            with self.subTest(package=name):
                self.assertIn(name, requirements)
                specifier = requirements[name].specifier
                self.assertNotIn(vulnerable, specifier)
                self.assertIn(patched, specifier)

    def test_transitive_floors_preserve_consumer_major_version_limits(self):
        requirements = requirements_by_name()
        for name, compatible, incompatible in [
            ("urllib3", "2.8.0", "3.0.0"),
            ("msgpack", "1.2.4", "2.0.0"),
        ]:
            with self.subTest(package=name):
                self.assertIn(name, requirements)
                self.assertIn(compatible, requirements[name].specifier)
                self.assertNotIn(incompatible, requirements[name].specifier)

    def test_tooling_fixes_do_not_become_application_requirements(self):
        requirements = requirements_by_name()
        for name in ["pip", "pip-audit", "filelock", "bandit", "coverage"]:
            with self.subTest(package=name):
                self.assertNotIn(name, requirements)

    def assert_patched_bootstrap_first(self, commands):
        self.assertGreaterEqual(len(commands), 2)
        for tokens in commands:
            self.assertEqual(tokens[:4], ["python", "-m", "pip", "install"])
        bootstrap = commands[0][4:]
        self.assertIn("--upgrade", bootstrap)
        bootstrap_requirements = [
            Requirement(token) for token in bootstrap if not token.startswith("-")
        ]
        pip = next((r for r in bootstrap_requirements if r.name == "pip"), None)
        self.assertIsNotNone(pip, "Bootstrap must upgrade pip, not just dependencies")
        self.assertEqual(str(pip.specifier), "==26.2.2")
        self.assertTrue(any(tokens[-2:] == ["-r", "requirements.txt"] for tokens in commands[1:]))

    def test_ci_bootstraps_patched_pip_before_project_and_tool_installs(self):
        path = ROOT / ".github" / "workflows" / "quality.yml"
        commands = install_commands(path, workflow=True)
        self.assert_patched_bootstrap_first(commands)
        tool_command = next(tokens for tokens in commands if "pip-audit" in tokens)
        tool_requirements = {
            canonicalize_name(r.name): r
            for r in (Requirement(token) for token in tool_command[4:])
        }
        self.assertTrue({"pip-audit", "bandit", "coverage", "filelock"} <= tool_requirements.keys())
        filelock = tool_requirements["filelock"].specifier
        self.assertNotIn("4.2.0", filelock)
        self.assertIn("4.2.1", filelock)

    def test_ci_audits_with_the_selected_python_interpreter(self):
        workflow = (ROOT / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")
        audit_commands = []
        for line in workflow.splitlines():
            command = line.strip()
            if command.startswith(("- run:", "run:")) and "--progress-spinner" in command:
                audit_commands.append(shlex.split(command.split("run:", 1)[1]))
        self.assertEqual(len(audit_commands), 1)
        self.assertEqual(audit_commands[0][:3], ["python", "-m", "pip_audit"])
        self.assertEqual(audit_commands[0][3:], ["--progress-spinner", "off", "--format", "json", "--output", "pip-audit.json"])

    def test_build_bootstraps_patched_pip_before_installing_project_requirements(self):
        self.assert_patched_bootstrap_first(install_commands(ROOT / "build.sh"))


if __name__ == "__main__":
    unittest.main()
