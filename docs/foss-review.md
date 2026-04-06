# FOSS Readiness Review

Assessment of Elsegate against open-source best practices.

## What's Good

| Area | Status | Notes |
|------|--------|-------|
| License | AGPL-3.0 | Clear, copyleft, in repo root |
| No secrets in repo | Clean | API keys via env vars only |
| No hardcoded paths | Clean | All configurable |
| No personal/internal references | Clean | Only author name in pyproject.toml |
| English throughout | Clean | Code, docs, comments, errors |
| Tests | 24 tests, all passing | Config + backend logic covered |
| Documentation | README + config reference + Docker guide | Above average for alpha |
| Minimal dependencies | 4 runtime deps | FastAPI, uvicorn, httpx, pyyaml |
| Clean separation | Strategy + Router patterns | Easy to extend |

## What Should Be Improved

### High Priority

**1. Add CONTRIBUTING.md**

FOSS projects need contributor guidance. Even a minimal one signals that contributions are welcome and sets expectations.

Should cover:
- How to set up the dev environment
- How to run tests
- Code style expectations
- How to submit issues and PRs

**2. Add CHANGELOG.md**

Essential for users tracking changes between versions. Start with the current state and maintain going forward. Follow [Keep a Changelog](https://keepachangelog.com/) format.

**3. Add a `py.typed` marker and type hints**

The code already uses type hints extensively. Adding `py.typed` to the package signals that type checkers (mypy, pyright) can verify downstream usage. Demonstrates quality commitment.

**4. Add GitHub Issue Templates**

Structured bug reports and feature requests reduce noise:
- `bug_report.md`: Steps to reproduce, expected vs actual, config snippet
- `feature_request.md`: Use case, proposed approach

**5. Add CI (GitHub Actions)**

Even a basic workflow that runs `pytest` on push builds trust:
```yaml
# .github/workflows/test.yml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
      - run: pytest
```

### Medium Priority

**6. Add a `[project.scripts]` entry point**

Currently users must run `uvicorn elsegate.server:app`. A proper entry point is more user-friendly:

```toml
[project.scripts]
elsegate = "elsegate.cli:main"
```

With a thin `cli.py` that wraps uvicorn with config loading.

**7. Improve error messages and logging**

- Startup should log which config file was loaded and how many routes were found (already done)
- Failed routes should log clearly which env var is missing (already done)
- Runtime errors (provider timeouts, auth failures) should include the route name and backend type for debugging

**8. Add examples for common providers**

Separate example configs for common setups:
- `examples/mistral.yaml` (tested)
- `examples/openai.yaml` (untested, with disclaimer)
- `examples/multi-provider.yaml`

This makes it easy for users to get started without reading the full reference.

**9. Document the Ollama protocol coverage**

Explicitly state which parts of the Ollama API are implemented and which are not:
- Implemented: `/api/embed`, `/api/embeddings`, `/api/generate`, `/api/chat`, `/api/tags`
- Not implemented: `/api/pull`, `/api/push`, `/api/create`, `/api/copy`, `/api/delete`, `/api/show`, `/api/blobs`
- Not implemented: `stream: true` (silently ignored)

Users should know what to expect.

### Low Priority (Nice to Have)

**10. Add a `SECURITY.md`**

Standard in FOSS. Describe how to report security issues (e.g., private email instead of public GitHub issue).

**11. Add `pre-commit` hooks**

Automated linting and formatting on commit. Reduces PR review friction:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks: [{ id: ruff }, { id: ruff-format }]
```

**12. Consider MIT instead of AGPL**

AGPL is the strongest copyleft license. It requires anyone who runs a modified version (even as a network service) to publish their source code. This is a deliberate choice for projects that want to ensure all improvements come back to the community.

However, AGPL can deter corporate adoption. Many companies have blanket policies against AGPL dependencies. If broad adoption is a goal, MIT or Apache-2.0 are more permissive alternatives.

This is a values question, not a technical one. AGPL is the right choice if the priority is keeping the project open. MIT is the right choice if the priority is maximizing adoption.

**13. Consider semantic versioning and Git tags**

Tag releases (`v0.1.0`, `v0.2.0`) so users can pin to specific versions. Combine with CHANGELOG.md for a complete release history.

## Things to Avoid

**Don't add features before users ask for them.** The current scope (three backends, YAML config) is right-sized. Resist the urge to add load balancing, rate limiting, authentication, or a web UI before there's demand.

**Don't claim compatibility without testing.** The current README honestly marks tested vs untested providers. Keep this discipline.

**Don't over-engineer the Backend protocol.** The current `**kwargs` approach is flexible enough. Don't add a formal plugin system, hook framework, or middleware chain unless the three-backend model proves insufficient.

**Don't add a database.** Configuration is a YAML file. State (if any) belongs in the backends, not in Elsegate. Keep the core stateless.
