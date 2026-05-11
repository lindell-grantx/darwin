# Contributing to Darwin

Thank you for your interest in contributing to Darwin. This document covers the development setup, conventions, and process for submitting changes.

## Development setup

### Prerequisites

- Node.js 24+
- Python 3.12+
- A MongoDB Atlas cluster (free tier works for development)
- Voyage AI and Anthropic API keys

### Install

```bash
git clone https://github.com/lindell-grantx/darwin.git
cd darwin
npm run install:all
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

### Configure

```bash
cp server/.env.example server/.env
# Fill in MONGODB_URI, VOYAGE_API_KEY, ANTHROPIC_API_KEY
```

Export the same variables for the Python side:

```bash
export MONGODB_URI="mongodb+srv://..."
export VOYAGE_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

### Run locally

```bash
npm run dev          # Hono API + React frontend
python scripts/run_all.py  # Python evolution engine (separate terminal)
```

## Branch conventions

Create feature branches from `main`:

- `feat/description` — new functionality
- `fix/description` — bug fixes
- `docs/description` — documentation changes

## Commit messages

Use [conventional commits](https://www.conventionalcommits.org/):

```
feat: add tournament selection with elitism
fix: handle empty population in crossover
docs: update quickstart prerequisites
refactor: extract fitness scoring into separate module
test: add smoke test for seed_corpus
```

## Pull requests

1. Create a branch from `main`.
2. Make your changes with clear, focused commits.
3. Run the smoke test before pushing: `python -m pytest tests/smoke.py -v`
4. Open a PR with a title that follows commit conventions and a body explaining what changed and why.
5. A maintainer will review your PR. CI must pass before merge.

## What to work on

Check [GitHub Issues](https://github.com/lindell-grantx/darwin/issues) — issues labeled `good-first-issue` are a good starting point.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Please read it before participating.
