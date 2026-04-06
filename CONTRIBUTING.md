# Contributing to Elsegate

Thanks for your interest. Elsegate is in early alpha -- bug reports, test results with other providers, and documentation improvements are especially valuable.

## Development Setup

```bash
git clone https://github.com/wizz-cmd/elsegate.git
cd elsegate
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
```

Tests are in `tests/`. They cover config loading, message consolidation, and tool handling. They do not call external APIs -- all backend tests are unit tests against the protocol logic.

## Code Style

- Python 3.11+, type hints throughout
- Docstrings on all public classes and functions (Sphinx/Google style)
- No linter is enforced yet, but keep it clean and consistent with existing code

## Submitting Changes

1. Fork the repo and create a branch
2. Make your changes
3. Run `pytest` -- all tests must pass
4. Open a pull request with a clear description of what changed and why

## Reporting Bugs

Open a GitHub issue with:
- What you expected to happen
- What actually happened
- Your `elsegate.yaml` (redact API keys)
- The backend and provider you were using
- Python version and OS

## Testing with New Providers

If you test Elsegate with a provider that isn't listed as tested (OpenAI, Groq, Together, etc.), please report your results -- whether it works or not. This helps everyone.

## License

By contributing, you agree that your contributions will be licensed under AGPL-3.0.
