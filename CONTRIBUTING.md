# Contributing to pii-stripper-middleware

Thank you for your interest in this project!

## Project Status

This is a **personal side project** maintained by one person ([@PerryLink](https://github.com/PerryLink)).
There is no dedicated support team or regular release cadence.
Contributions are welcome, but please set expectations accordingly:
response times may vary and not every PR will be merged.

---

## Reporting Issues

Before opening an issue, please:

1. Check [existing issues](https://github.com/PerryLink/pii-stripper-middleware/issues) to avoid duplicates.
2. Use the latest released version to confirm the bug still exists.

When opening an issue, include:

- A **minimal reproducible example** (input text, command run, full error output).
- Your Python version (`python --version`).
- Whether you installed the `[nlp]` extra and which SpaCy model you downloaded.
- Your operating system.

---

## Development Setup

**Prerequisites**: Python 3.9+, [Poetry](https://python-poetry.org/)

```bash
# 1. Fork and clone the repository
git clone https://github.com/PerryLink/pii-stripper-middleware.git
cd pii-stripper-middleware

# 2. Install all dependencies (including dev)
poetry install

# 3. (Optional) Install NLP extras
pip install presidio-analyzer presidio-anonymizer spacy
python -m spacy download zh_core_web_sm

# 4. Run the test suite
poetry run pytest

# 5. Run tests with coverage
poetry run pytest --cov=src --cov-report=term-missing

# 6. Lint
poetry run ruff check src tests

# 7. Try the demo
poetry run pii-stripper demo
```

---

## Code Style

This project follows **PEP 8** and is enforced with [Ruff](https://docs.astral.sh/ruff/).

Key rules:

- Line length limit: **100 characters** (configured in `pyproject.toml`).
- Use **type annotations** for all public function signatures.
- Keep functions **small and focused** — prefer composition over large methods.
- Write **descriptive variable names**; avoid single-letter names outside loop counters.

Before submitting a PR, run:

```bash
poetry run ruff check src tests
poetry run ruff format src tests
```

---

## Submitting a Pull Request

1. **Open an issue first** for non-trivial changes so we can discuss the approach.

2. **Fork** the repository and create a branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/issue-123
   ```

3. **Write or update tests** for any behaviour you add or change.
   All existing tests must pass:
   ```bash
   poetry run pytest
   ```

4. **Commit** using the [Conventional Commits](https://www.conventionalcommits.org/) format:
   ```
   feat: add passport number regex pattern
   fix: restore mapping fails when placeholder appears twice
   docs: clarify NLP fallback behaviour in README
   ```

5. **Push** your branch and open a Pull Request against `main`.
   In the PR description, explain:
   - What problem this solves.
   - How you tested it.
   - Any trade-offs or limitations.

6. A maintainer will review your PR when available.
   Please be patient — this is a one-person project.

---

## License

By contributing, you agree that your contributions will be licensed under the
[Apache License 2.0](LICENSE).

Contact: novelnexusai@outlook.com
