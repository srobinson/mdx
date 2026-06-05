---
title: lilo-moon-template instantiation rehearsal
type: projects
tags: [lilo-moon-template, rehearsal, instantiate, moon, leftover, rust]
summary: First-user walk of docs/how-to-instantiate.md on main 306be34, then a real library+app, daily loop, and rust-only moon ci.
status: active
project: lilo-moon-template
confidence: high
---

# Instantiation rehearsal (issue #15)

Walked as a new user against `littleorgans/lilo-moon-template` `306be34` (`fix: install CI moon from .prototools`). Throwaway clones under the assigned scratchpad. Template worktrees and the primary checkout were not modified.

Machine already had moon `2.5.1`, just `1.58.0`, Node `24.19.0`, pnpm `11.22.0`. proto was not on `PATH`. Times below are that machine, with warm toolchain caches.

## Verdict

The graph works. The docs are a release behind the tree. Follow `docs/how-to-instantiate.md` and you still get a green `just ci` after the prune, because `moon.yml` `tasks.project-refs` now fails the old #32 hole. Trust README or leftover.yml comments and you will skip gates that already exist, or believe `just ci` still passes on dangling `tsconfig.json` `references`.

I would start a project with this template after a docs pass that matches main.

## What I did

1. `git clone https://github.com/littleorgans/lilo-moon-template.git your-repo` (guide command; I used `--depth 1`). `git remote set-url`, `just setup`, `pnpm install`, `just ci`.
2. Renamed identity to `@acme` / `acme/widgets` / MIT, added `LICENSE`, grepped leftovers, generated `billing` and `console`, proved `billing:test` red, deleted `packages/collections` and `apps/web`, pruned `tsconfig.json` `references`, `tsc --build`, `just ci`, `npm pack --dry-run` from billing.
3. Wired console to billing, wrote a test that fails when `formatLabel` is wrong, `just check`, `just ci`, committed through leftover, `moon run console:dev`, edited billing source while Vite was up.
4. `changeset add --patch @acme/billing` then `pnpm run changeset:version`.
5. Second clone with only `services/ping` kept; `moon ci` before and after pruning `references`.

## Clone to green

Fine, on a machine that already has moon `2.5.1` and just.

| Step | Result | Time |
|---|---|---|
| clone | `306be34` | 4s |
| `just setup` | skip-cached rust/node/pnpm; proto setup skipped | <1s |
| `pnpm install` | 258 packages; leftover `prepare` installed `commit-msg` and `pre-commit` | 3s |
| `just ci` | 18 tasks green (collections, web, ping, root lint/format/audit/secrets/project-refs) | 7s |

`pnpm install` printed `Scope: all 3 workspace projects`. ping is not a pnpm project. Expected.

Shallow clone made moon print `Detected a shallow checkout` and disable affected checks, so `moon ci` ran everything. The guide's clone is full history. I used `--depth 1`. Not a template defect.

## Steps that are wrong

Quoted from `docs/how-to-instantiate.md` unless noted.

**"`just ci` can still pass, because each member typechecks from its own directory. A root `tsc --build` and the editor both read the stale paths and fail with TS6053. That is #32."**

After `rm -rf packages/collections apps/web` + `pnpm install` + `moon sync`, `tsconfig.json` `references` still listed `./apps/web` and `./packages/collections`. `moon project collections` and `moon project web` failed as the guide says. `just ci` did **not** pass. `moon.yml` `tasks.project-refs` ran `tsc --build --pretty --dry` and failed with TS6053, exit 1. README still says the same false-green, and lists #32 under "Not in this repository yet".

The prune instruction after that paragraph is still the right repair. I pruned to `./apps/console` and `./packages/billing`. Then `pnpm exec tsc --build --pretty` exit 0, `just ci` exit 0. The defect the paragraph describes is already gated. The paragraph is false.

**"`services/` is an empty glob... Rust and Python toolchains are commented out... The proof that a repo with no TypeScript still works is #14 and is unbuilt."**

On this SHA, `.moon/toolchains.yml` `rust.version` is `"1.95"` with `components: ["clippy"]`. `services/ping` exists. `just ci` ran `ping:build`, `ping:lint`, `ping:test`. README workspace members list only collections and web.

**"Changesets (#6), git hooks (#7), and supply chain gates (#11) are not there to help you."**

On this SHA they are there: `.changeset/config.json`, `lefthook.yml`, `commitlint.config.js`, `package.json` `scripts.prepare` leftover, `moon.yml` `tasks.secrets` and `tasks.audit`. README "Not in this repository yet" also lists #6, #7, #11, #29, #32. #29 is this SHA.

**leftover.yml still says `# Issue #11 adds moon task root:secrets. When that task exists on main, add:`** and leaves the leftover `secrets` command commented. `moon.yml` `tasks.secrets` already exists. leftover pre-commit is format + lint only.

**leftover remaining-hits list is incomplete.** After every table row plus `pnpm install`, `git grep -n 'lilo-moon\|littleorgans\|@lilo-moon'` still hit `.changeset/config.json` (`changelog.repo` `littleorgans/lilo-moon-template`, `ignore` `@lilo-moon/web`). The guide says remaining hits are the instantiate page, AGENTS.md CI URLs, and `Independent of littleorgans` in `.moon/workspace.yml`. A reader who trusts that list will leave littleorgans in changesets. I changed it because grep found it. After deleting web, `ignore` still named `@acme/web` (the renamed dead package), not `@acme/console`.

**"`moon-version` in `.github/workflows/ci.yml`"** (README pins list). That literal is gone. CI uses `moonrepo/setup-toolchain` with `auto-install: true`.

## False green

One that I actually produced.

leftover committed `docs: mention a token` with a `ghp_` GitHub token in `README.md`. leftover pre-commit ran `root:format-check` on the markdown and skipped lint (no JS). commitlint passed. `moon run root:secrets` on that commit failed: `[GITHUB_TOKEN] found GitHub Token` via `@secretlint/secretlint-rule-github`, exit 1. I reset the commit.

So: leftover green, `just ci` would be red. leftover.yml's commented secrets block is why. This is the class of defect the brief asked for.

#32 is the inverse: docs still advertise a false green that `tasks.project-refs` already closed.

## Knowledge the docs did not give me

**Moon and just install.** README: "Moon `2.5.1` must be on `PATH`." The instantiate page starts at `git clone` then `just setup`. Neither page says how to get moon 2.5.1 or just. proto was missing here; `just setup` still succeeded because homebrew moon was already present.

**How a generated app consumes a generated library.** `just new-package billing` and `just new-app console` worked. console `package.json` has no workspace dependency. console `vite.config.ts` has the `@acme/source` condition and no `optimizeDeps.exclude`. I imported `formatLabel` from `@acme/billing`. `moon sync` did **not** write the dependency (`javascript.syncProjectWorkspaceDependencies` is true; it still did not). `console:typecheck` TS2307 `Cannot find module '@acme/billing'`. I copied `"@acme/billing": "workspace:*"` from `git show HEAD:apps/web/package.json` after I had already deleted the exemplar. Then `moon sync` wrote `apps/console/tsconfig.json` `references` to `../../packages/billing` and `moon project console` showed `Depends on: billing (production)`.

The instantiate page tells you to generate, then delete the exemplars. It never says to copy the web→collections wiring. After the delete, the only worked example is gone.

## Friction

- Docs, leftover.yml comments, and README "unbuilt" lists contradict the tree. I stopped trusting the guide and read `moon.yml` / leftover.yml / `.changeset/config.json`.
- `console:dev` printed `Port 5173 is in use, trying another one` and served `http://localhost:5174/`. No documented port.
- ping `build`/`lint`/`test` blocked on cargo's package-cache lock, then passed.
- moon printed the 2.5.2 upgrade banner on almost every run.
- `moon clean` (guide recovery after renaming the directory) default lifetime 7 days deleted 0 files. Cache still contained `your-repo` paths. `moon clean --all` is the switch that actually resets. After `mv your-repo widgets` without clean, `moon run console:test` still passed, so I did not hit the absolute-path failure the guide warns about.
- Generated library is always described as "Formats delimited labels for display" and always tested in `tests/library.test.ts`. Fine as a scaffold, odd once the package is named billing.
- rust-only `moon ci` still `pnpm install`s 251 JS packages because root oxlint/oxfmt/secretlint/audit live in the root Node project.

## Missing on day one

- Install moon `2.5.1` and just. Clone-to-green does not start without them.
- A documented `workspace:*` + `moon sync` step for attaching a generated application to a generated library, before deleting the exemplar that currently is the only example.
- leftover.yml is not in "What you must not delete". `.changeset/` and `commitlint.config.js` are not either. They are on main now.

Not missing, despite README: changesets. `pnpm exec changeset add --patch @acme/billing -m "..."` then `pnpm run changeset:version` wrote `packages/billing/CHANGELOG.md` and bumped `@acme/billing` `0.0.0` → `0.0.1`.

Not in this rehearsal, as briefed: identity/auth, persistence, `engines.node` tera literal, `strictDepBuilds`.

## Daily loop

| Action | Result |
|---|---|
| `just check` | green, 3s |
| `just ci` | green, 1s (cached) |
| leftover commit `feat(console): show formatted billing account names` | leftover v2.1.10 pre-commit format+lint, commit-msg commitlint, 3s, `6ffdbaf` |
| leftover + GitHub token in README | leftover green, `root:secrets` red (see False green) |
| `moon run console:dev` | Vite 8.2.1 on 5174 |
| edit `packages/billing/src/index.ts` `formatLabel` while the server ran | Vite `hmr update /src/app.tsx`; transformed app imported `/@fs/.../packages/billing/src/index.ts?t=...`; served module returned the new body. `@acme/source` did this. The generated vite config has no `optimizeDeps.exclude`. I did not need the web exemplar's exclude for this edit to show up. |

The app test is real: `App` heading is `formatLabel("acme_console")` → `Acme Console`. A `formatLabel` that returns the raw string fails `console:test` (`expected '<main><h1>acme_console</h1>...'`).

`npm pack --dry-run` in `packages/billing` listed `dist` and `src`. `dist/index.js.map` and `dist/index.d.ts.map` `sources` are `../src/index.ts` (inside the package).

## Polyglot (only ping)

Second clone, `rm -rf apps packages`. `just ci` failed on `root:project-refs` TS6053 for web and collections. Empty `tsconfig.json` `references`, left `compilerOptions.outDir`. `just ci` then green: ping build/lint/test plus root lint/format/audit/secrets/project-refs. 20s including install. rust-only still pays the JS root toolchain.

Guide said this proof is unbuilt. It is built. The remaining footgun is the same prune, and CI now catches it.

## Fine

- `just new-package billing` / `just new-app console` non-interactive with `just`'s `--name`. Destination `packages/billing` and `apps/console`. `@acme/...` names because I had already edited the templates.
- `moon project billing` and `moon project console` printed project id, layer (`library` / `application`), inherited tasks.
- Deliberate wrong `formatLabel` failed `billing:test` (assertion `' moon_generator '` vs `'Moon Generator'`).
- Type error `export const _boom: number = "no"` failed `billing:typecheck` TS2322.
- Floating `_never()` failed `root:lint` `typescript/no-floating-promises`.
- Single quotes failed `root:format-check`.
- leftover format/lint/commitlint on a conventional commit.
- Source-condition HMR from a library into the generated app.

## Counts

| Class | n | What |
|---|---|---|
| blockers | 2 | leftover remaining-hits list omits `.changeset/config.json`; leftover secrets hook still commented while `moon.yml` `tasks.secrets` is live |
| false-greens | 1 | leftover commit of a GitHub token; `root:secrets` fails |
| friction | 4 | docs a release behind; no moon/just install; undocumented app→library wiring; rust-only still installs the JS root toolchain |
| missing | 2 | moon 2.5.1 + just install; how to attach a generated app to a generated library before deleting the exemplar |
