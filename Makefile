# Local checks. `make check` is the fast dev loop (test, lint, types); `make ci` is the
# FULL gate CI runs -- that plus the packaging assertions on a bare install. CI calls
# `make ci`, so local and CI run the identical thing (one source of truth): run `make ci`
# before any push or release and a green run here means a green run there.
#
# Dev env: `uv venv && uv pip install -e . --group dev` (creates .venv, what BIN points at).
.PHONY: check ci test lint types package

# BIN is the dev venv's bin dir (test/lint/types run from it); PYTHON is the interpreter the
# bare packaging check builds against -- CI passes the matrix version, locally it defaults.
BIN    ?= .venv/bin/
PYTHON ?= python3

check: test lint types

# Everything CI gates on. Run this before push/release.
ci: check package

test:
	$(BIN)python -m pytest -q

lint:
	$(BIN)python -m ruff check src tests

types:
	$(BIN)python -m mypy

# Packaging assertions, on the package installed into a bare venv with only its declared
# runtime deps (no dev extras): it must import, its console script must run, and py.typed
# must ship (PEP 561) -- so a forgotten dependency, a dropped entry point, or a missing
# marker fails here rather than in a user's fresh install.
package:
	rm -rf /tmp/newswatcher-pkgcheck
	uv venv /tmp/newswatcher-pkgcheck --python $(PYTHON)
	uv pip install --python /tmp/newswatcher-pkgcheck/bin/python .
	/tmp/newswatcher-pkgcheck/bin/python -c "import newswatcher; print('newswatcher', newswatcher.__version__, 'imports')"
	/tmp/newswatcher-pkgcheck/bin/newswatcher --help >/dev/null
	/tmp/newswatcher-pkgcheck/bin/newswatcher --version >/dev/null
	/tmp/newswatcher-pkgcheck/bin/python -c "import importlib.util, pathlib; root = pathlib.Path(importlib.util.find_spec('newswatcher').origin).parent; assert (root / 'py.typed').is_file(), 'py.typed missing from the installed package'; print('py.typed ships alongside newswatcher')"
