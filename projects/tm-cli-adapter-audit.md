# tm-cli-adapter-audit — is cli/ a simple adapter?

Audited at main `329e3ef0`, read-only, `code-hygiene` inspection mode. Standard applied: an
adapter parses args, resolves them to domain inputs, calls domain code, renders for a terminal,
and maps errors to exit codes; the tell is whether a non-cli caller would need the behaviour.
Package totals: 44 non-test modules, 8,714 LOC. No file breaches the 700 limit (largest:
`desktop_cmd.py` at 616). Exactly one function breaches the 150 limit:
`diagnose.py::run_doctor` at 206.

**Headline: 28 of 44 modules (21 displaced, 7 mixed), carrying ~6,300 of 8,714 LOC (~73%), are
not adapter code. cli/ is the de facto launch engine wearing an adapter's name.** Eleven of its
modules are already imported from outside cli/ (by `captured/` — the seam the canvas RunManager
and API plane launch through — and `controlplane/provisioning.py`), so the boundary breach is
established fact, not forecast.

## Per-module verdicts

LOC is raw lines; fn is the largest function (name, lines). EXT marks modules imported from
outside cli/ today (`captured/*`, `controlplane/provisioning.py`).

| Module | LOC | Largest fn | Verdict | Displaced symbols → where they belong |
|---|---|---|---|---|
| `runner.py` EXT | 517 | run_client_with_retry 80 | **displaced** | Whole module: two-child process supervision (`ManagedClient`, `run_client_with_retry`, `start_prepared_proxy`) → the launch lifecycle owner (top-level `launch/` exists) |
| `home_overlay.py` | 546 | materialize_runtime_home_template_overlay 57 | **displaced** | Overlay materialization, secret scrubbing, credential linking → settings/home owner (ARCHITECTURE's Settings schema family) |
| `launch_runtime.py` EXT | 423 | prepare_launch 103 | **mixed** | `prepare_launch`, `resolve_working_dir`, `resolve_launch_ports`, `resolve_mitmdump_executable`, `LaunchPreparation` → launch owner; the `*_or_exit` / `raise_*_cli_error` helpers are genuine adapter and stay |
| `codex_cmd.py` EXT | 500 | run_codex 144 | **mixed** | `build_codex_invocation`, `resolve_codex_addons_and_ca`, `_prepare_codex_launch_parts` are imported by `captured/codex.py` — a typer command module inside the capture engine; those move to the launch owner, the command wrapper stays |
| `codex_home.py` | 358 | _relocate_codex_hook_trust_state 31 | **displaced** | TOML trust merge + home seeding → settings/home owner |
| `launch_profile.py` EXT | 318 | prepare_managed_session 32 | **displaced** | Its own docstring calls it "the managed-launch port (§5.2c)": a domain contract, imported 5× by `captured/` → launch owner or harness bundle |
| `credential_source.py` | 243 | assert_claude_client_credential_identity 36 | **displaced** | ARCHITECTURE.md's named credential-isolation boundary; 1.4/1.5 need it from the API plane → top-level leaf (scout-1b D2) |
| `runtime_home.py` EXT | 241 | plan_runtime_home 72 | **displaced** | Home planning imported by `captured/context.py` → launch/home owner; also carries the NOW-chore dead re-export aliases (`RuntimeTemplateRef`/`RuntimeTemplateProvenance`, test-only consumers) |
| `codex_trust.py` | 240 | resolve_codex_ca_certificate_or_exit 69 | **displaced** | CA bundle resolution + process-lifetime cache → trust owner beside `trust.py` |
| `bind_failure.py` | 194 | handle_bind_failure 66 | **displaced** | Its docstring: EADDRINUSE detection and allocate→spawn retry **policy** → launch owner |
| `home_seeders.py` | 186 | _seed_runtime_home_overlay 27 | **displaced** | Seeder orchestration → settings/home owner |
| `claude_home.py` | 161 | apply_claude_proxy_env_settings 28 | **displaced** | Claude home seeding (file writes, config) → settings/home owner |
| `codex_session.py` | 159 | seed_codex_session 29 | **displaced** | Session-uuid mint + rollout pre-seed (§5.2b seam) → codex harness/session owner |
| `trust.py` EXT | 124 | _system_trust_roots_as_pem 26 | **displaced** | SSL trust bundle build, imported by `captured/codex.py` → trust owner |
| `space_bootstrap.py` | 92 | bootstrap_cli_space 44 | **displaced** | `bootstrap_cli_space` composes controlplane services; the desktop launch's missing space bootstrap (prior scout Q5) is exactly a second caller → controlplane composition; `_or_exit` wrapper stays |
| `launch_outcomes.py` | 86 | — | **displaced** | Docstring: "Domain types for the launch lifecycle. Pure data carriers" → launch owner |
| `ports.py` EXT | 70 | allocate_port_pair 32 | **displaced** | Port allocation, imported by `captured/dependencies.py` → launch/net leaf |
| `net.py` EXT | 66 | validate_port_option 20 | **displaced** | Port probing, imported by `captured/` and doctor → net leaf (`validate_port_option` is adapter, trivial) |
| `home_io.py` | 63 | _copy_secret_file_if_missing 24 | **displaced** | Restrictive-mode file IO → moves with the home cluster |
| `prompt.py` EXT | 58 | user_supplied_system_prompt 12 | **displaced** | System-prompt injection policy, imported by `captured/dependencies.py` → launch owner |
| `run_context.py` | 45 | install_codex_run_context 13 | **displaced** | Writes run context into a Codex home → home cluster |
| `home_seed.py` EXT | 27 | — | **displaced** | The facade `controlplane/provisioning.py` and `captured/claude.py` import → public face of the home cluster, moves with it |
| `identity.py` EXT | 4 | — | **displaced** (trivial) | `CLI_COMMAND`/`PRODUCT_LABEL` imported by `captured/` → top-level vocabulary leaf, one-minute move |
| `desktop_cmd.py` | 616 | run_desktop_detached 90 | **mixed** | Backend spawn/detach/env process management (`serve_desktop_backend`, `_build_desktop_backend_command`) → `transport_matters.desktop_runtime` (which already exists; see shim below); command wiring stays |
| `diagnose.py` | 394 | run_doctor 206 ⚠ | **mixed** | Check bodies (the 1b extraction) → new non-cli checks module; rendering and `--reap-orphans` UX stay. The package's only function-limit breach |
| `channel_cmd.py` | 273 | list_channels 28 | **mixed** | `ensure_channel_database`, `_create_database_if_absent`, `run_install_local` (store provisioning effects) → channel/config owner; listing/status rendering stays |
| `desktop_viewer.py` | 172 | spawn_detached_electron 35 | **mixed** | Electron resolution + spawn is process management; sole consumer is the desktop command today, so it can stay until `desktop_runtime` absorbs it |
| `desktop_recovery.py` | 153 | prepare_desktop_runtime_for_launch_or_exit 41 | **mixed** | Recovery/refusal decisions fused with typer exits; the decision half belongs to `desktop_runtime` |
| `__init__.py` | 549 | claude 47 | adapter | Typer app + command wiring; fine |
| `paths.py` | 255 | _storage_for_slug 42 | adapter | Workspace-selector UX and rendering for `paths`; fine |
| `help.py` | 290 | format_help 3 | adapter | Help text and plain renderers; fine |
| `_helpers.py` | 237 | _captured_run_request 29 | adapter | Shared test support (non-collected); fine |
| `launch_options.py` | 161 | — | adapter | Typer option aliases; fine |
| `tail_cmd.py` | 142 | _explain_missing_log 48 | adapter | Log tail UX; fine |
| `runs_health.py` | 133 | orphan_candidates 35 | adapter | Doctor's runs sweep, deliberately unit-testable; stays with the CLI-only doctor surface (scout-1b D1) |
| `start_cmd.py` | 132 | run_start 84 | adapter | Thin over `captured/`; fine |
| `instances.py` | 122 | list_instances 28 | adapter | List output + contention UX; fine |
| `db_cmd.py` | 100 | wire_gc 20 | adapter | Thin over `session/migrate.py`; fine |
| `banner.py` | 56 | print_client_banner 21 | adapter | Terminal rendering; fine |
| `home_constants.py` | 55 | — | adapter (vocabulary) | Shared filenames/modes; moves with whichever cluster consumes it |
| `desktop_runtime.py` | 49 | — | adapter (shim) | Pure re-export of top-level `transport_matters.desktop_runtime` — proof the direction of travel already started; delete once callers migrate |
| `desktop_launch_config.py` | 47 | resolve_desktop_storage_dir 11 | adapter | Config resolvers; fine |
| `channel_options.py` | 47 | _unknown_channel_exit 7 | adapter | Channel option resolution; fine |
| `__main__.py` | 10 | — | adapter | Entry point |

## Answer 1 — class or one-off?

Two different questions hide in "run_doctor's shape". The **function-size breach with logic
fused into render closures is a one-off**: `run_doctor` is the only function in the package over
150 lines. The **displacement is a class**: 28 of 44 modules (21 displaced, 7 mixed), roughly
6,300 of 8,714 LOC. The class has one dominant shape: launch machinery — process supervision,
home materialization, credential policy, trust bundles, port allocation — that grew inside cli/
and is now consumed from outside it. Eleven modules are already imported by `captured/` and
`controlplane/`, including `codex_cmd.py`, a typer command module imported by the capture
engine (`captured/codex.py`). So the one number: **28 of 44**.

## Answer 2 — cheapest correct sequence

**1b needs only the run_doctor extraction.** The check bodies' imports are already all non-cli
(`config`, `gateway_supervisor`, `session/migrate.py`, `capabilities`) except two leaf helpers
the checks call: `launch_runtime.py::resolve_mitmdump_executable` and `net.py::port_in_use`.
Lift those two functions with the checks (both are small, injected-dependency functions) or let
the checks module import them where they sit — `captured/` already imports both modules, so
neither choice makes the boundary worse. Credential readiness, harness detection, and runs
health stay CLI-side per scout-1b D1, which is what keeps the extraction this small. **1b does
not require any broader move.**

**Own hygiene slices, ranked by how fast they get more expensive** (each is one cluster, one
slice, mechanical move plus import fixups): (1) the launch cluster `captured/` already consumes
— `runner`, `launch_outcomes`, `bind_failure`, `launch_profile`, `runtime_home`, `prompt`,
`ports`, `net`, `identity`, plus the displaced halves of `launch_runtime` and `codex_cmd` — into
the existing top-level `launch/` package; (2) the home/settings cluster — `home_overlay`,
`home_seeders`, `home_seed`, `claude_home`, `codex_home`, `home_io`, `home_constants`,
`run_context`, and `credential_source` (with scout-1b D2); (3) `trust` + `codex_trust`;
(4) `desktop_cmd`'s process management into `transport_matters.desktop_runtime`, retiring the
`cli/desktop_runtime.py` shim; (5) `space_bootstrap`'s composition into controlplane when the
desktop gains space bootstrap. **Fine as is:** the sixteen adapter modules — command groups,
options, help, banners, rendering, thin wrappers.

## Answer 3 — displaced code other planes already reach for

The already-imported eleven are the answer, and three are acute because a named roadmap item
adds the next caller: `credential_source.py` (the 1.4 Authenticated row and 1.5 readiness read
it from the API plane), `space_bootstrap.py` (the desktop's empty-store dead end is its missing
second caller), and the doctor check bodies (1b itself). The chronic ones are `runner`,
`launch_runtime`, `launch_profile`, `runtime_home`, and the `home_seed` cluster: every canvas
launch already flows through them via `captured/`, so each new launch feature (the batch verb,
overlay versioning) deepens api-plane dependence on modules named `cli/*`. `codex_cmd.py` is
the worst single fact: capture-engine code importing from a typer command module.

**Conformance, both ways.** cli/'s condition contradicts the owner's adapter standard. But the
governing docs never state that standard: docs/ARCHITECTURE.md's two-plane rule governs
Python-vs-TypeScript and package placement for the product plane, and api/CLAUDE.md's import
DAG (`ir → adapters → rules → pipeline → storage → breakpoint → server`) predates the launch
subsystem entirely — `cli`, `captured`, `launch`, and `controlplane` appear nowhere in it. So
the code is wrong against the directive, and the doc is wrong by omission: whichever hygiene
slice runs first should also write the launch layer and the cli-as-adapter rule into the
import DAG, or the boundary has no test to fail.
