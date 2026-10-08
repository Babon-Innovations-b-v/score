# No loose files outside the carve-out

**Status:** accepted

Every directory in this repo contains subdirectories only, plus the framework-required files named
in the carve-out below. Anything else loose moves into a named subdirectory.

The rule exists because a directory is the cheapest boundary a codebase has, and loose files are
how that boundary rots. A directory with twenty files in it has stopped telling a reader anything;
the reader has to open files to learn what lives where, which is the work the directory was meant
to save. Every repo that got hard to navigate got there one convenient loose file at a time, and
each one looked harmless.

The carve-out is for files a framework or tool requires to sit at an exact path, where moving them
breaks the tool. It is not for files that are merely conventional.

## Carve-out

- `__init__.py`
- `conftest.py`
- `pyproject.toml`
- `uv.lock`
- `package.json`
- `package-lock.json`
- `tsconfig.json`
- `vite.config.ts`
- `build.gradle`
- `build.gradle.kts`
- `settings.gradle`
- `settings.gradle.kts`
- `gradle.properties`
- `gradlew`
- `gradlew.bat`
- `Makefile`
- `Dockerfile`
- `docker-compose.yml`
- `README.md`
- `CLAUDE.md`
- `CONTEXT.md`
- `LICENSE`
- `docs/bible.md`

Amended 2026-10-08: `vendor/` is exempt wholesale, as in the game 2099 (its ADR-0002, the owner's call there): it holds third-party code kept exactly as released, each tool pinned to one upstream commit with its own licence, and reshaping it would break the upgrade path. It came with the framework's move from 2099 (JoeyKardolus/2099#129): `image-to-3dlab` (Apache-2.0), `infinigen` and `infinigen2` (BSD-3-Clause, with Blender-derived GPL files that run only inside Blender on a rented machine, never linked into this repo's code), `procfunc` (BSD-3-Clause). Our own code never goes in `vendor/`.

The list is append-only by ADR amendment: a new entry is an edit to this file and to root
`CLAUDE.md`, which keeps its own copy so a session reads the rule without opening the ADR. The two
copies are checked against each other by `python3 docs/adr/tools/check_index.py`, so they cannot
drift silently.

Dotfiles at the repository root (`.gitignore`, `.gitattributes`, `.mcp.json` and the like) sit
outside this rule: they are configuration the tool locates by name, and they are invisible in an
ordinary listing, which is the harm the rule is aimed at.
