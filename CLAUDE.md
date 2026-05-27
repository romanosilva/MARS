# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

This repository (`romanosilva/MARS`) is currently a bare scaffold. The working tree contains only `LICENSE` (AGPL-3.0) and this file — no source code, README, build manifests, package configs, CI workflows, or tests have been added yet. History is a single "Initial commit".

Because nothing has been built yet, there are no real build, lint, test, or run commands to document. **Do not invent them.** When the user starts adding code, update this file to reflect what actually exists rather than guessing at conventions.

## License

The project is licensed under the **GNU Affero General Public License v3.0**. AGPL-3.0 is a strong copyleft license with a network-use clause: any derivative work — including code offered to users over a network — must be made available under the same license. Keep this in mind when introducing dependencies (their licenses must be AGPL-compatible) and when suggesting integrations that would link MARS into proprietary systems.

Preserve the `LICENSE` file at the repository root and include AGPL-3.0 license headers in new source files if the user adopts that convention.

## What to do on the first real change

When code is first introduced, replace the placeholder sections above with:

1. **Build / run / test commands** — only what actually works locally, including how to run a single test.
2. **Architecture overview** — the "big picture" that requires reading several files to understand (entry points, module boundaries, data flow). Skip anything trivially discoverable from a directory listing.
3. **Project-specific conventions** — anything non-obvious about how this codebase wants to be edited (naming, layering rules, code generation, etc.).

If the user adds a README, Cursor rules (`.cursor/rules/`, `.cursorrules`), or Copilot instructions (`.github/copilot-instructions.md`), fold the important parts into this file at that time.
