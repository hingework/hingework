import builtins
import importlib.util
import io
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch


class AdoptionSafetyTests(unittest.TestCase):
    def test_fresh_import_config_and_examples_do_not_adopt_policy(self):
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as scratch:
            home = Path(scratch)
            protected = {name: home / name for name in ("AGENTS.md", "router.json", "model-defaults.json")}
            for p in protected.values():
                p.write_text("synthetic policy", encoding="utf-8")
            config = home / "selected.yaml"
            config.write_text("{}", encoding="utf-8")
            before = {p.name: p.read_bytes() for p in home.iterdir()}
            actual_open, actual_io_open = builtins.open, io.open
            def guarded(actual):
                def call(file, mode="r", *args, **kwargs):
                    if any(flag in mode for flag in "wax+"):
                        raise AssertionError("unexpected write")
                    return actual(file, mode, *args, **kwargs)
                return call
            with patch.dict(os.environ, {"HOME": scratch, "USERPROFILE": scratch}), \
                 patch("builtins.open", guarded(actual_open)), patch("io.open", guarded(actual_io_open)), \
                 patch.object(Path, "mkdir", side_effect=AssertionError("unexpected directory")), \
                 patch("subprocess.run", side_effect=AssertionError("unexpected process")), \
                 patch("requests.sessions.Session.request", side_effect=AssertionError("unexpected HTTP")):
                environment = dict(os.environ)
                spec = importlib.util.spec_from_file_location("hingework_import_probe", repository / "src/__init__.py",
                                                              submodule_search_locations=[str(repository / "src")])
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                try:
                    spec.loader.exec_module(module)
                    module.load_execution_config(config)
                    for example in (repository / "examples").glob("*.py"):
                        runpy.run_path(str(example))
                finally:
                    for name in list(sys.modules):
                        if name == "hingework_import_probe" or name.startswith("hingework_import_probe."):
                            del sys.modules[name]
                self.assertEqual(dict(os.environ), environment)
            self.assertEqual({p.name: p.read_bytes() for p in home.iterdir()}, before)

    def test_packaging_has_no_custom_install_hooks(self):
        import tomllib
        repository = Path(__file__).resolve().parents[1]
        config = tomllib.loads((repository / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(config["build-system"]["build-backend"], "setuptools.build_meta")
        self.assertNotIn("backend-path", config["build-system"])
        self.assertFalse((repository / "setup.py").exists())
        self.assertNotIn("scripts", config["project"])
        self.assertNotIn("entry-points", config["project"])
