---
title: Adversarial design review — ephemeral .agent-runtimes homes (TM home overlay)
type: research
tags: [transport-matters, agent-runtimes, home-overlay, design-review, adversarial, codex, claude, auth, pristine-template]
summary: The seed_env auth hook and overlay-extraction claims hold, but "template never mutated" is violated by the Codex rollout seed and symlink write-through, Linux loses Claude auth, and the 4-slice sequencing ships C without the D piece it depends on.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Design review — ephemeral `.agent-runtimes` homes

Reviewed artifact: `~/.mdx/projects/agent-runtimes-tm-homedir-recon--claude.md`,
section **"Design — ephemeral `.agent-runtimes` homes"** + the recon it rests on.
All claims re-verified against `api/src/transport_matters/` HEAD `16b95d7`.
Citations are file + symbol (no line numbers). Read-only; nothing changed.

## Verdict

The mechanism the design leans on is real and the leverage inventory is accurate.
But the headline guarantee — **"template never mutated"** — is violated by two paths
on a pristine template, the **"auth injected from native"** guarantee is **macOS-only**
(it silently fails on Linux), and the **slice sequencing ships work item C without the
piece of D it structurally depends on**. Three substantive issues, one of them a Blocker
against the stated guarantee.

---

## Load-bearing claims: verify / refute

### Claim 1 — `seed_env` is the auth hook → **VERIFIED**
`prepare_runtime_home_overlay` builds `seed_env` and assigns
`seed_env[HOME_DIR_ENV_BY_CLIENT[client_name]] = str(source_home_dir)`, then calls
`seed_home_dir(..., env=seed_env)`. The seeders read auth from that env var:
`ClaudeSeeder.seed` resolves its source via `_default_claude_config_path(env)`
(merges `oauthAccount`/`userID` from `env[CLAUDE_CONFIG_DIR]/.claude.json`);
`CodexSeeder.seed` resolves `_default_codex_home(env)` and copies `auth.json` from there.
So repointing that one assignment at the native home does inject auth from native. **The hook is exactly where the design says it is.**

Caveat that the design should state: the injection is *delta-only and shadowed by the
template*. `ClaudeSeeder.seed` only fills `oauthAccount`/`userID` **`if … not in config`**,
and `CodexSeeder`/`_copy_overlay_local_files` use `_copy_secret_file_if_missing`
(`O_CREAT|O_EXCL`). So "auth from native" holds **only if the template carries no
`oauthAccount` and no `auth.json`**. A non-pristine template silently shadows native auth
with its own. Nothing enforces template-is-secret-free. (Feeds B.)

### Claim 2 — splitting content-source vs auth-source is "a clean parameterization, not a rewrite" → **PARTIALLY REFUTED (Major)**
The split is shape-clean for the `seed_env` pointer, but the design's companion knob —
"`_copy_overlay_local_files` copies secrets from `auth_source`" — is the **wrong knob and leaks native content**.
`_copy_overlay_local_files` copies whole files: Claude `settings.json` + `.claude.json`,
Codex `config.toml` + `auth.json`. Of these, only Codex `auth.json` is a pure secret.
`.claude.json` mixes auth (`oauthAccount`) with content (`projects`, `mcpServers`, history);
`config.toml`/`settings.json` are pure content. Copying `.claude.json`/`config.toml` from
`auth_source=native` would drag native's projects/MCP/model config into a "template" run,
defeating "content from template." The real auth path is already Claim 1 (`seed_env` + the
seeders' delta merge). **Correct parameterization: keep `_copy_overlay_local_files` reading
the content source for config files; drive auth purely through `seed_env`; add a native-sourced
copy/symlink only for the credential *token* (see C).** Also latent: `_copy_overlay_local_files`
passes the operator `env` to `_source_claude_config_path`, which prefers `env[CLAUDE_CONFIG_DIR]`
over `source_home_dir` — for a native launch that env points at `~/.claude`, so even the
content `.claude.json` can come from native rather than the template. The split must pin the
content `.claude.json` to `source_home_dir` and ignore `env` for that read.

### Claim 3 — Codex rollout-seed ordering breaks resume for a pristine template → **VERIFIED, and worse than stated**
Confirmed: `build_captured_run_context` calls `prepare_managed_session(..., home_dir=request.home_dir)`
(the source), and `CodexLaunchProfile.prepare` seeds via `seed_codex_session(sessions_root=codex_sessions_root(home_dir, env))`,
while the child's `CODEX_HOME` is `runtime_home_dir or home_dir` (`build_codex_invocation`).
For native `~/.codex` the overlay symlinks `sessions/` so the seed is visible; for a pristine
template `_symlink_source_home_entries` finds no `sessions/`, so the seed lands at
`<template>/sessions` and the child reads the empty `<runtime>/sessions` → resume breaks.
**Worse:** that seed call *creates* `<template>/sessions/<rollout>` — i.e. it **mutates the
template** (write `True`, `seed_codex_session` does `mkdir`). So Claim 3 is not just a resume
bug, it is a template-mutation bug. Fix (design's C) is correct but see E for the dependency it hides.

### Claim 4 — the overlay block is extractable and reusable by `run_codex` → **VERIFIED (with one trap)**
The overlay block in `build_captured_run_context` (resolve `source_home_dir` →
`runtime_home_root/runtime-home/<client>` → `prepare_runtime_home_overlay` → `stack.callback(rmtree)`)
is already client-agnostic; it runs for both Claude and Codex captured paths.
`run_codex` (CLI) bypasses it and does the direct `seed_home_dir(CLIENT_NAME_CODEX, home_dir=home_dir)`.
`build_codex_invocation` already takes `runtime_home_dir` and prefers `runtime_home_dir or home_dir`
for the child env, so threading it and deleting the direct seed is mechanically sound.
**Trap (see D):** do *not* "simplify" by routing `run_codex` through `build_codex_captured_invocation`
— that builder hardcodes `force_http_fallback=False`, silently dropping the `--force-http-fallback`
CLI flag. Extract the **block only**; keep `run_codex` on `build_codex_invocation`.

### Claim 5 — per-run `<run dir>/runtime-home/<client>` + rmtree is ephemeral and concurrency-safe → **VERIFIED**
`runtime_home_root = prepared.resolved_storage / "runtime-home"`, and `resolved_storage`
is the per-run `run_root(working_dir, run_id)`. Distinct `run_id` per launch → disjoint
roots → no cross-run collision. `stack.callback(shutil.rmtree, runtime_home_root, ignore_errors=True)`
tears the whole root down. Sound. (Only residue is what escaped the root via symlink write-through — see B.)

### Claim 6 — durability via tailer → Tier-1 + Postgres means ephemeral teardown loses nothing → **VERIFIED for transcripts; the inference is too broad (see A)**
`addon_runtime` imports both `make_transcript_snapshot_writer`
(`storage/transcript_snapshot.py`, Tier-1) and `SessionWriter` (`session/writer.py`, Postgres),
matching the project's stated fan-out. The **transcript/wire bytes** are durable, so
rmtree of the home loses no transcript. But "loses nothing the stores need" is false for
**non-transcript home writes** (auth-token refresh, caches, MCP on-disk state) that the
fan-out never sees. That is design hole A, not a refutation of the transcript durability itself.

---

## Design holes

### A. Out-of-band / non-transcript home writes — **Major**
The fan-out captures transcript+wire, not the home filesystem. Writers into the home during
a run that are **not** transcript-visible and are lost at rmtree:
- **Codex `auth.json` token rotation (strongest).** `auth.json` is *copied* into the home
  (`_copy_overlay_local_files` / `CodexSeeder.seed`). A live Codex session refreshes its
  token and rewrites `auth.json` **in the ephemeral home**; rmtree discards it. If the
  provider rotates refresh tokens (single-use), native still holds the now-consumed token →
  the *next* run re-copies a stale token and auth drifts/fails. The stores capture none of
  this. This exists today on the Codex pane path and the design generalizes it to every Codex
  launch. **Fix:** symlink `auth.json` to the auth source (write-through survives) instead of
  copying, or write the refreshed token back to native on teardown. Verify the provider's
  rotation behavior before shipping ephemeral Codex.
- **Claude `.credentials.json`** (Linux token file): same teardown-loss class — but on the
  current overlay it is *symlinked* from source, so refresh writes through and survives.
  The design must preserve that symlink-to-*native* behavior (see C), not copy it.
- Caches/state Claude writes under the config dir (`statsig/`, `shell-snapshots/`, `todos/`,
  project plugin caches): lost, generally acceptable, but enumerate and decide per dir.
- **MCP server on-disk state:** the current set (cm → global store, helioy-bus → `~/.helioy`,
  fmm → repo `.fmm.db`) writes *outside* the home, so it survives. The design is safe **only
  because** today's MCP servers are home-external; any future MCP that persists under the home
  is silently lost. Bake this into the contract: MCP state must be home-external or transcript-derivable.
**One-line fix:** enumerate home writers in the design; symlink (not copy) rotating credential
files to native; assert MCP/home state is external or transcript-recoverable.

### B. "Template never mutated" — **Blocker (against the stated guarantee)**
Two concrete write-backs into a pristine template:
1. **Codex rollout seed** (Claim 3): `seed_codex_session` creates `<template>/sessions/<rollout>`.
2. **Symlink write-through:** `_symlink_source_home_entries` symlinks every source entry not in
   `_overlay_local_names` (only `{auth.json, config.toml}` for Codex, `{.claude.json, settings.json}`
   + daemon names for Claude) and not in `_OVERLAY_NEVER_SYMLINK_NAMES` (`{.git}`). A *template*
   exists precisely to carry reusable content dirs (skills, plugins, MCP working dirs). Any such
   dir is symlinked, and a child/subprocess writing under it (`<runtime>/<dir>/…`) writes
   **through to the template**. "Template never mutated" is therefore guaranteed only for files
   the template doesn't have and dirs the agent never writes into — not a guarantee at all for a
   populated template.
**Fix:** copy (don't symlink) any writable content dir for template mode, and add the history
dirs (`projects/`, `sessions/`) to `_overlay_local_names` so they're local. Work F
("copy vs symlink — does NOT gate the rest") is mislabeled: the materialization choice *is* the
"template never mutated" guarantee and gates it.

### C. macOS Keychain vs Linux — auth-from-native is macOS-only — **Major**
On macOS the Claude OAuth token lives in the login Keychain (per-user, service-keyed, home-path
independent), and `.claude.json` carries only `oauthAccount` metadata, which `ClaudeSeeder.seed`
injects. So an auth-injected home **does** fully auth Claude on macOS. **On Linux the token is a
file** (`~/.claude/.credentials.json`). It is in **none** of `_CLAUDE_OVERLAY_COPIED_NAMES`
(`{.claude.json, settings.json}`), so it is never copied; it is only *symlinked* from the **content
source**. In template mode the content source is the pristine template (no `.credentials.json`) →
the runtime home has no token → **Claude launches unauthenticated on Linux**. The `seed_env` hook
(Claim 1) does not help: it drives `oauthAccount` metadata and the `.claude.json` copy source, never
the token file.
**Fix:** in the split, symlink `.credentials.json` from the **auth source (native)** (preserves
refresh write-through per A). Validate a pristine-template launch on Linux, not only macOS.

### D. Blast radius of routing Codex through the overlay — **Minor (avoidable)**
- `force_http_fallback=False` is hardcoded in `build_codex_captured_invocation`. Avoided as long
  as Claim 4 is done as a block extraction keeping `run_codex` on `build_codex_invocation`
  (which threads the CLI `force_http_fallback` through). Flagged so the implementer doesn't
  collapse the two paths.
- **CA cert: safe.** `build_codex_invocation` passes `codex_ca_certificate` into
  `build_managed_child_env`; it is resolved by `resolve_codex_addons_and_ca` in `run_codex` and is
  independent of the home dir, so moving `CODEX_HOME` to the runtime home doesn't disturb it.
- **Ordering constraint:** the overlay must be built **before** `prepare_managed_session` (so C can
  seed into `runtime_home_dir`) and before `build_codex_invocation`. `run_codex` currently does
  `prepare_managed_session` → `build_codex_invocation` → direct seed; the extracted block must move
  ahead of `prepare_managed_session`, mirroring `build_captured_run_context`'s order.
- `desktop --agent codex` routes through `run_codex`, so it needs no separate change.

### E. The 4-slice sequencing — Slice 1 ships C without the D piece it needs — **Major**
Slice 1 = "B + C" (route Codex through overlay + seed rollout into runtime home), claimed to make
"Codex stop mutating the home." But **C is inert (and still mutating) without the "`sessions/` local"
part of D, which is deferred to Slice 3.** Trace, native Codex, Slice 1 as specified:
1. overlay: `sessions/` is not in `_CODEX_OVERLAY_LOCAL_NAMES`, so `_symlink_source_home_entries`
   makes `<runtime>/sessions` → `<source>/sessions`.
2. C seeds the rollout at `codex_sessions_root(runtime_home_dir)` = `<runtime>/sessions/<rollout>`,
   which **writes through the symlink** into `<source>/sessions`. Native/template still mutated; the
   slice's own goal ("stops mutating") is unmet.
C only redirects the write once `sessions/` is local (i.e. added to `_overlay_local_names`), which is
Work D. **Fix:** ship C and "history dirs local" together — either pull the `sessions/`-local change
into Slice 1 with C, or move C out of Slice 1 down to Slice 3 alongside D. As written, the C-in-1 /
D-in-3 split is the one broken combination. The rest of the ordering (Slice 2 default-preserving, Slice
3 depending on the registry contract, Slice 4 follow-up) is sound.

---

## Net
- Claims 1, 4, 5 verified; 3 verified and worse; 6 verified for transcripts only.
- Claim 2 needs reframing (auth via `seed_env`, not via copying config files from the auth source).
- **Blocker:** B — the "template never mutated" guarantee fails on a pristine template (Codex rollout
  seed + symlink write-through). Gate on the materialization decision (F), which is not optional.
- **Major:** A (rotating-credential teardown loss), C (Linux loses Claude auth), E (C depends on the
  deferred D piece).
- **Minor:** D (avoidable if the extraction stays surgical).
