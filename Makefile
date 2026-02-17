.PHONY: format lint typecheck test ci

# Auto-fix formatting (same as what CI does on push)
format:
	black src/ tests/ scripts/ main.py
	ruff check --fix src/ tests/ scripts/ main.py

# Strict check (same as what CI does on PRs)
lint:
	black --check src/ tests/ scripts/ main.py
	ruff check src/ tests/ scripts/ main.py

# Type checking
typecheck:
	mypy src/ scripts/ main.py --ignore-missing-imports

# Run tests
test:
	python -m pytest tests/ -v

# Full CI pipeline locally
ci: format typecheck test
