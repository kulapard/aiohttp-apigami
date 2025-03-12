# Install dependencies
deps:
	uv sync --frozen --all-extras --dev

test:
	uv run pytest

build:
	uv build --verbose

upload: build
	twine upload dist/*

mypy:
	uv run mypy .

pre-commit:
	uv run pre-commit run --all-files

pre-commit-update:
	uv run pre-commit autoupdate

lint: pre-commit mypy

# make set-version VERSION=1.2.3
set-version:
	uv run --no-sync --with toml-cli toml set --toml-path=pyproject.toml project.version $(VERSION)

clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -rf `find . -name ".cache"`
	rm -rf `find . -name ".pytest_cache"`
	rm -rf `find . -name ".mypy_cache"`
	rm -rf `find . -name ".ruff_cache"`
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
	rm -rf dist
