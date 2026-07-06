# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`im-squonk2-client` is a Python 3 package (PyPI: `im-squonk2-client`,
import name `squonk2`) providing simplified access to the Informatics
Matters Squonk2 REST APIs: Authentication (Keycloak), Data Manager (DM),
Account Server (AS) and the Data Manager UI.

Client major versions map to specific Squonk2 component API versions. See
the compatibility matrix in `README.rst` before making API changes — the
current branch is `7.0` (AS 4.x, DM 5.x, UI 6.x). PRs target `6.0`, but
current development happens on `7.0`.

## Commands

The project uses `uv` for all project management. There is no `pip install`
of dependencies — use `uv`.

```
uv venv                                              # create the virtualenv
uv sync --group dev                                  # install deps + dev tools
uv run pre-commit install -t commit-msg -t pre-commit  # install git hooks
```

Linting / static analysis (run before committing; CI runs the same):

```
uv run pre-commit run --all-files    # runs ruff, ty, pyroma, etc.
uv run ruff check .                  # lint only
uv run ruff format .                 # format only
uv run ty check .                    # type check only
```

Build and docs:

```
uv build                                        # build sdist/wheel into dist/
uv run sphinx-build -b html docs _readthedocs/html/   # build docs
```

## Testing

There is **no unit-test suite**. `test.py` is an integration/smoke test
(a `typer` CLI) that exercises real API methods against a live Squonk2
deployment. It requires a running Data Manager and these environment
variables:

```
export SQUONK2_DMAPI_URL=https://data-manager-test.example.com/data-manager-api
export SQUONK2_KEYCLOAK_URL=https://keycloak-test.example.com/auth
export SQUONK2_KEYCLOAK_REALM=squonk
export SQUONK2_KEYCLOAK_DM_CLIENT_ID=data-manager-api-test
export SQUONK2_KEYCLOAK_USER=dmit-user-admin
export SQUONK2_KEYCLOAK_USER_PASSWORD=password1234

uv run test.py
```

`test.py` asserts the installed client is major version 7 (see
`REQUIRED_CLIENT_MAJOR_VERSION`). When you add an API method, extend
`test.py` to exercise it. On recent Python you may need
`export SSL_CERT_FILE=$(python -m certifi)`.

## Architecture

Source lives under `src/squonk2/`. The public surface is a set of classes
whose methods are almost all `@classmethod` — the classes act as namespaces
holding class-level state (API URLs, SSL settings) rather than being
instantiated.

- `auth.py` — `Auth.get_access_token()`. Fetches/caches Keycloak access
  tokens. Callers pass the returned token into every DM/AS/UI call.
- `dm_api.py` — `DmApi`. Projects, Instances (Jobs), Files, Workflows.
  The largest module (~2500 lines).
- `as_api.py` — `AsApi`. Organisations, Units, Products, Assets, charges.
- `ui_api.py` — `UiApi`. Data Manager UI endpoints.
- `api.py` — `ApiRv`, the common return type for essentially every public
  method (see below).
- `enumerations.py` — shared enums (`ScopeEnum`, `EventStreamFormat`,
  `DefaultProductPrivacyEnum`).
- `environment.py` — `Environment`. Optional convenience loader for a
  KUBECONFIG-like YAML file (default `~/.squonk2/environments`, override
  with `SQUONK2_ENVIRONMENTS_FILE`) so connection details for multiple
  environments live in one file instead of many env vars.
- `examples/` — runnable example scripts shipped inside the package (e.g.
  `examples/data_manager/job_chain.py`). Excluded from ruff and ty.

### Request/response pattern

Each API class has a **private `__request()` classmethod** that all public
methods funnel through. It builds the URL, injects the `Authorization:
Bearer <token>` header, applies timeouts and SSL verification, and wraps the
`requests` response.

Every public method returns an **`ApiRv`** (`api.py`), a dataclass with:
- `success: bool`
- `msg: dict` — the response content
- `defaultmunch_msg` — a `DefaultMunch` view of `msg` allowing attribute
  access (`rv.defaultmunch_msg.some_field`); undefined fields return a
  sentinel rather than raising
- `http_status_code: int`

Methods do not raise on API failure; callers check `rv.success`. Mutations
of shared state use `@synchronized` (from `wrapt`) for thread safety.

### Configuration

Each API resolves its base URL from an environment variable, or can be set
programmatically via `set_api_url()`:
- DM: `SQUONK2_DMAPI_URL` (SSL toggle `SQUONK2_DMAPI_VERIFY_SSL_CERT`)
- AS: `SQUONK2_ASAPI_URL` (`SQUONK2_ASAPI_VERIFY_SSL_CERT`)
- UI: `SQUONK2_UIAPI_URL` (`SQUONK2_UIAPI_VERIFY_SSL_CERT`)

Set `SQUONK2_API_DEBUG_REQUESTS=yes` to log request args and responses.

## Conventions

- **Conventional Commits are enforced** by commitizen via the commit-msg
  hook. Allowed types: `feat`, `fix`, `perf`, `refactor`, `remove`,
  `style`, `test`, `build`, `docs`, `ci`. Non-conforming messages are
  rejected at commit time.
- The package version is `0.0.0` in `pyproject.toml`; the real version is
  injected from the git tag at publish time (`uv version $GITHUB_REF_SLUG`).
  Do not hand-edit the version.
- When adding a public API method, also update the method list in
  `README.rst` and the Sphinx docs under `docs/`.
