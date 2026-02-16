# CLAUDE.md — codex-playground

## Project Overview

This is a playground/experimentation repository (`codex-playground`). It is currently in its initial state with no source code, build tooling, or dependencies configured yet.

## Repository Structure

```
codex-playground/
├── README.md        # Project readme (minimal)
├── CLAUDE.md        # This file — guidance for AI assistants
└── .git/            # Git repository
```

## Current State

- **Language/Framework:** Not yet established
- **Package manager:** Not yet established
- **Build system:** Not yet configured
- **Testing:** Not yet configured
- **Linting/Formatting:** Not yet configured
- **CI/CD:** Not yet configured

## Development Workflow

Since this is a fresh repository, follow these guidelines when adding code:

### Setting Up a New Project

1. Initialize with a package manager (e.g., `npm init`, `cargo init`, `go mod init`)
2. Add a `.gitignore` appropriate for the chosen language/framework
3. Set up linting and formatting tools
4. Add a test runner and write tests alongside new code
5. Update this file as the project takes shape

### Git Conventions

- **Remote:** `origin` (surf7777/codex-playground)
- **Default branch:** `master`
- Write clear, concise commit messages that explain *why* a change was made
- Keep commits focused — one logical change per commit

## Guidelines for AI Assistants

- **Read before writing:** Always read existing files before proposing changes
- **Keep it simple:** Avoid over-engineering. Only add what is directly needed
- **Update this file:** When adding new tooling, dependencies, or conventions, update CLAUDE.md to reflect the current state
- **No secrets:** Never commit `.env` files, API keys, credentials, or other sensitive data
- **Test your changes:** If a test runner is configured, run tests before considering work complete
- **Respect existing patterns:** As code is added, follow the conventions already established in the codebase
