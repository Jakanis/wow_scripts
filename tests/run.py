import importlib.util
import os
import pathlib
import sys

# loaded by path, not by package name: the yarg dependency ships its own
# top-level "tests" package that would shadow this folder
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(f'selftest_{path.stem}', path)
    module = importlib.util.module_from_spec(spec)
    # registered before exec: @dataclass resolves its module through sys.modules
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    failures = 0
    for path in sorted(pathlib.Path(__file__).parent.glob('test_*.py')):
        print(f'== {path.name}')
        failures += load(path).main()
        print()
    print('all suites pass' if not failures else f'{failures} suite(s) failed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
