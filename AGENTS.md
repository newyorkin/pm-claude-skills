# AGENTS.md

## Cursor Cloud specific instructions

This repo (`pm-claude-skills`) is a **Node.js content-library monorepo**, not a client/server app. The product is the `skills/` folder (~466 `SKILL.md` files); everything else builds, validates, or serves that content. See `REPO-MAP.md` for the layout and `package.json` `scripts` for the canonical commands.

### Runtime & dependencies
- Requires **Node.js >= 18** (VM has Node 22). Uses ES Modules (`"type": "module"`).
- The core has **zero runtime npm dependencies** — no `npm install` is needed to run the CLI, MCP server, build scripts, or validators. The update script's `npm install` is effectively a no-op that just runs the harmless `postinstall` banner.

### Lint / validate (this is the primary "test" of the product)
- `node scripts/skillcheck.mjs` — house authoring standard (466 skills).
- `node skillspec/cli.mjs skills/ --min-level 3` — the shipped SKILL.md linter.
- `npm run check` — runs skillcheck + rebuilds all generated artifacts + `git diff --exit-code` to prove nothing drifted. Run this after any change touching `skills/`.

### Generated files — never hand-edit
`exports/`, `tools-pkg/`, `web/skills.json`, `web/samples.json`, and `SKILLS.md` are generated from `skills/` by `scripts/build-*.mjs` / `web/build-skills.mjs`. Regenerate them (or run `npm run check`); editing by hand makes `npm run check` and CI fail.

### Running the surfaces
- **CLI:** `node bin/cli.mjs list|doctor` and `node bin/cli.mjs add <skill> --agent <cursor|claude|...> [--dry-run] [--target <dir>]`.
- **Local MCP server:** `node mcp/server.mjs` — stdio JSON-RPC 2.0 (send `initialize`, then `tools/list` / `tools/call`).
- **Web playground:** static site — serve `web/` (e.g. `cd web && python3 -m http.server 8000`). The command bar matches tasks to skills **locally, no API key**. Actually generating skill output in the playground/CLI needs `ANTHROPIC_API_KEY` (the playground uses the user's own key client-side); not needed for build/lint/serve/browse.

### Web smoke test (optional; Playwright not in package.json)
`node tests/web-smoke.mjs` loads all ~36 interactive pages headlessly and self-serves on `:8123`. It needs Playwright + Chromium installed out-of-tree first:
`npm i --no-save playwright && npx playwright install chromium`.

### Gotchas
- Broken symlink at `templates/pm-launch-agent/skills/launch-checklist/SKILL.md` can cause glob errors when traversing the whole tree; the build/validate scripts handle it, but ad-hoc `find`/glob may complain.
- Pre-commit hooks (`.pre-commit-config.yaml`) run `skillspec` on changed `SKILL.md` files and `skillcheck` on the `skills/` tree.
