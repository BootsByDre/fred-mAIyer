# fred-mAIyer

## What This Project Is

A CLI-driven grocery cart automation tool for Fred Meyer (Kroger). Instead of building a bespoke UI, this project is designed to be used **directly within Claude Code** — the user describes what groceries they want in natural language, and the tool populates their Fred Meyer online cart automatically. The user then logs into fredmeyer.com to review and place the order.

**The workflow:**
1. User tells Claude Code what they need ("I need milk, eggs, sourdough bread, and 2 lbs of chicken thighs")
2. Claude Code uses this tool to search Fred Meyer's product catalog, select the best matches, and add them to the user's cart
3. User opens fredmeyer.com, reviews the cart, and checks out

## Architecture

### Core Components

- **Auth module** — Handles authentication with the Kroger API (Fred Meyer is a Kroger subsidiary). Manages OAuth2 tokens and refresh flows.
- **Product search** — Searches the Kroger product catalog by keyword, filters by location/store, and ranks results by relevance.
- **Cart manager** — Adds, removes, and updates items in the user's Kroger cart via API.
- **Store locator** — Resolves the user's preferred Fred Meyer store (by ZIP or store ID) so search results reflect local inventory and pricing.

### Tech Stack

- **Language:** Python 3.11+
- **API:** Kroger Public API (https://developer.kroger.com)
- **Auth:** OAuth2 (Authorization Code Grant for user cart access)
- **HTTP client:** `httpx` (async support built in)
- **Data models:** Pydantic for typed API response/request models
- **Package manager:** `uv`
- **Testing:** `pytest` + `respx` (mocked async HTTP)
- **Linting:** `ruff` (replaces flake8, isort, and black in one tool)

### Project Structure (planned)

```
fred-mAIyer/
├── CLAUDE.md              # This file — project guide for AI assistants
├── README.md              # Public-facing project description
├── pyproject.toml         # Project metadata, dependencies, tool config
├── uv.lock                # Lockfile (committed)
├── .python-version        # Pinned Python version for uv
├── .env.example           # Template for required env vars (never commit .env)
├── src/
│   └── fred_maiyer/
│       ├── __init__.py
│       ├── auth.py        # Kroger OAuth2 authentication
│       ├── products.py    # Product search and selection
│       ├── cart.py         # Cart operations (add/remove/update/list)
│       ├── store.py        # Store location resolution
│       └── models.py       # Pydantic models for API responses/requests
├── tests/
│   ├── conftest.py        # Shared fixtures
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_cart.py
│   └── test_store.py
└── .github/
    └── workflows/
        └── ci.yml         # CI pipeline
```

## Kroger API Overview

Fred Meyer is owned by Kroger. All automation goes through the **Kroger Public API**:

- **Base URL:** `https://api.kroger.com/v1`
- **Auth:** OAuth2 — requires a registered application at https://developer.kroger.com
- **Key endpoints:**
  - `GET /products` — Search products by term, filter by location
  - `GET /locations` — Find stores by ZIP or coordinates
  - `PUT /cart/add` — Add items to the authenticated user's cart
- **Rate limits:** Be respectful; add reasonable delays between bulk operations
- **Scopes needed:** `product.compact`, `cart.basic:write`

### Authentication Flow

1. User registers an app at developer.kroger.com and gets `CLIENT_ID` and `CLIENT_SECRET`
2. User completes an OAuth2 Authorization Code flow in their browser to grant cart write access
3. The tool stores and refreshes tokens locally (never committed to git)

## Environment Variables

Required in `.env` (see `.env.example`):

```
KROGER_CLIENT_ID=       # From developer.kroger.com
KROGER_CLIENT_SECRET=   # From developer.kroger.com
KROGER_ACCESS_TOKEN=    # Obtained after OAuth2 flow
KROGER_REFRESH_TOKEN=   # For automatic token refresh
KROGER_STORE_ID=        # Preferred Fred Meyer store ID (use store locator to find)
```

## Development Conventions

### Code Style
- Use `async/await` with `httpx.AsyncClient` for all HTTP calls
- Prefer plain functions over classes unless truly necessary
- Keep modules focused — one concern per file
- Use Pydantic models for all API request/response shapes
- Type hints on all function signatures

### Error Handling
- Wrap all API calls with clear error messages that include the HTTP status and endpoint
- Never swallow errors silently
- Raise specific exception subclasses so callers can handle distinct failure modes

### Testing
- Run tests: `uv run pytest`
- Write tests for all API-facing modules using mocked HTTP responses (do not call the real API in tests)
- Use `respx` to mock `httpx` calls in tests
- Test files live in `tests/` and mirror the `src/` structure

### Git
- Branch naming: `claude/<description>-<sessionId>`
- Commit messages: imperative tense, concise ("Add product search module", not "Added product search")
- Never commit `.env`, tokens, or secrets

### Commands
- `uv sync` — Install/sync dependencies
- `uv run pytest` — Run test suite
- `uv run ruff check .` — Lint
- `uv run ruff format .` — Format code
- `uv run ruff check --fix .` — Auto-fix lint issues

## Design Decisions

1. **No custom UI** — Claude Code *is* the interface. The user talks to Claude, Claude uses this tool. No web app, no TUI needed.
2. **Kroger API over browser automation** — Using the official API is more reliable, faster, and doesn't break on UI changes. Avoids Selenium/Playwright fragility.
3. **Python + Pydantic** — Type safety for API response shapes via Pydantic models, great ecosystem, fast iteration, no compile step.
4. **Minimal dependencies** — `httpx` for HTTP, `pydantic` for models, `python-dotenv` for config. Avoid heavy frameworks.
5. **uv for package management** — Fast, modern Python package manager with lockfile support and built-in virtual environment handling.

## Usage with Claude Code (MCP Tool Pattern)

The end-state goal is for this project to expose functions that Claude Code can invoke as tools, either via MCP or direct CLI calls. Example interactions:

```
User: "Add a gallon of whole milk and a dozen eggs to my Fred Meyer cart"

Claude Code:
  1. Calls product search for "whole milk gallon" at the user's store
  2. Selects the best match (e.g., Kroger Vitamin D Whole Milk, 1 gal)
  3. Calls product search for "eggs dozen"
  4. Selects the best match (e.g., Kroger Large Grade A Eggs, 12 ct)
  5. Adds both to cart via the cart API
  6. Reports back: "Added 2 items to your Fred Meyer cart: ..."
```

```
User: "What's in my cart right now?"

Claude Code:
  1. Fetches current cart contents
  2. Displays item names, quantities, and prices
```

## What's Not In Scope (for now)

- Checkout / payment — user always reviews and pays in the browser
- Coupon clipping — possible future addition
- Delivery scheduling — user handles this at checkout
- Price comparison across stores
- Recipe parsing (could be a future Claude Code skill)
