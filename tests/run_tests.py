"""Minimal runner used where pytest cannot be installed: python tests/run_tests.py"""
import importlib, inspect, sys, traceback, pathlib

here = pathlib.Path(__file__).parent
sys.path.insert(0, str(here)); sys.path.insert(0, str(here.parent / "src"))
failed = passed = skipped = 0
for path in sorted(here.glob("test_*.py")):
    mod = importlib.import_module(path.stem)
    for name, fn in inspect.getmembers(mod, inspect.isfunction):
        if not name.startswith("test_") or inspect.signature(fn).parameters:
            continue
        try:
            fn(); passed += 1; print("PASS", path.stem, name)
        except Exception:
            failed += 1; print("FAIL", path.stem, name); traceback.print_exc()
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
