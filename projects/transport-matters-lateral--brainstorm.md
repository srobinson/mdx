# Transport Matters Lateral Brainstorm: Overlays as a Category

**Angle:** lateral / wide. What category is this, who has sat on the seam, what has nobody attempted?
**Seam under study (read-only):** capture plane (`api/src/transport_matters/`: mitmproxy addon, `ir`, `overrides/*`, `breakpoint.py`), product plane (`packages/*`), Inspector (`www/packages/inspector`), framing in `TLDR.md` + `NOW.md`.
**Constraint:** no repo writes; artifact only.

---

## 0. What the product already is (so we do not re-invent the basement)

Today TM already sits *after* the harness has composed the full outbound package and *before* the provider:

1. **Capture** raw wire bytes + transcript, never collapsed.
2. **Curate** via a typed override pipeline (`tool_toggle`, `tool_description`, `system_part_*`, `message_*`, `truncate_tool_result`, `sampling_set`, `provider_extras_set`) with audit.
3. **Breakpoint** (arm once → pause → schema-aware edit → release), process-local, serialised one flow at a time.
4. **OverrideStore** scoped by `(run_id, track_id)` — session-persistent edits, not yet a portable document.
5. **Stated direction (`NOW.md`):** permanent **overlays**, versioned against harness first-frame baselines, belonging in `FrozenLaunchSpec` / `candidate_key` as an eval axis equal to model.

The product insight is already sharp: **wire minus transcript is the hidden context layer**. Overlays are how a human permanently owns that layer.

The lateral question is not "how do we persist overrides?" It is: **what category of software is a durable, shareable, multi-scope control surface over another program's invisible outbound context?**

---

## 1. Category candidates (name the thing)

| Candidate name | Closest precedent | Why it almost fits | Where it fails |
|---|---|---|---|
| Request rewrite proxy | Charles, Proxyman, mitmproxy scripts | Same mechanical seat | Those rewrite HTTP; they do not productise *agent context policy* |
| User stylesheet for agents | Stylus / CSS user styles | Site-scoped permanent restyle of "what they send" | CSS restyles presentation; overlays restyle *cognition inputs* |
| Filter list for tools/system | uBlock, EasyList | Shareable declarative deny/allow, community maintainers | Ads are public content; agent payloads are private + version-fragile |
| Admission controller for turns | K8s validating/mutating webhooks, OPA | Mutate-or-deny before commit | Cluster policy ≠ personal creative control |
| Nix overlay for context | Nixpkgs overlays | Pure patch composition, pin, fork | Build-time purity vs live turn-time mutation |
| User script for the API | Tampermonkey | Portable scripts that reshape sites | Scripts are code; overlays want data + safe sharing |
| Editor config cascade | `.editorconfig`, ESLint extends | Scoped cascade, team defaults | Static files on disk, not mid-flight IR |
| LD_PRELOAD for LLMs | dyld interpose, eBPF | Inject before the "kernel" sees the call | Power-user metaphor; terrifying as product copy |
| Prompt library / hub | LangSmith hub, Cursor rules, CLAUDE.md | Shared prompt artifacts | Those edit *author-side* intent; TM edits *what the harness already injected* |

**Working definition (lateral, not engineering):**

> An **overlay** is a portable, version-constrained, multi-scope document that mutates the *hidden* half of a coding agent's outbound turn — tools, system parts, injected reminders, replayed context — after the harness has assembled them and before the model provider receives them. It is neither a prompt template nor a proxy rule alone. It is **user-owned policy over another vendor's invisible context layer**.

**Nobody has productised that category.** Proxies can do the bytes. Prompt hubs do the visible half. Harness config (`CLAUDE.md`, skills, Cursor rules) edits what the CLI *chooses* to send from its own composition path. TM is the only seat that sees *everything the CLI actually sends*, including what the CLI will never show.

That is the category: **Hidden-Context Control Plane** (working label: HCCP). Or, more marketable: **Agent Context Overlays**.

---

## 2. Who has sat on adjacent seams (steal map)

### 2.1 Wire / proxy lineage
- **Browser DevTools Network:** edit and resend; breakpoint mental model already in TM.
- **Charles / Proxyman rewrite + Map Local:** durable rules + path-scoped rewrites. Steal: rule UI, enable/disable per domain (here: harness/provider), "Map Local" ≈ pin a system part to a local file.
- **mitmproxy scripts / OWASP ZAP:** power-user automation. Steal: script escape hatch *after* declarative overlays, never as the default authoring surface.
- **Envoy filters / WASM plugins / OpenTelemetry processors:** pipeline stages with observability. Steal: ordered stages + per-stage audit (TM already has `OverrideAudit`).

### 2.2 Community declarative policy
- **uBlock Origin + EasyList / EasyPrivacy:** the gold standard for *shared, forkable, reputation-backed* rule lists. Steal: plain-text human rules, `! comments`, inclusion lists, trusted maintainers, auto-update with pin/opt-in.
- **Pi-hole / DNS sinkholes:** org-wide default deny with personal exceptions. Steal: teams tier "block noisy MCP namespaces org-wide."
- **CSP / CORS policies:** machine-checkable allowlists. Steal: capability firewall vocabulary.

### 2.3 Local injection and hooks
- **Git hooks / pre-commit:** local policy that refuses to proceed. Steal: "refuse release if overlay audit fails org policy" for enterprise.
- **LD_PRELOAD / dyld interposing / eBPF:** intercept without vendor cooperation. Metaphorically exact for TM's proxy seat.
- **SQL views / RLS:** present a rewritten world to the consumer. Steal: "the model only ever sees the overlaid world."

### 2.4 Config cascades and composition
- **EditorConfig / ESLint `extends` / Prettier overrides:** scope cascade + package inheritance.
- **Nix overlays / home-manager modules:** named, composable patches with conflict awareness.
- **CSS cascade + user stylesheets:** origin layers (user agent / user / author) with specificity. Steal: **layer precedence** (vendor baseline < org < team < personal < run).
- **Kubernetes Kyverno / Gatekeeper / OPA:** mutate + validate packs as packages.

### 2.5 Marketplaces and share graphs
- **VS Code / JetBrains extension marketplaces:** install, version pin, ratings, permissions manifest.
- **Homebrew / Nix / crates.io:** installable formulae with dependency graphs.
- **Tampermonkey script sites / GreasyFork:** user scripts with "applies to" matchers — and a long history of malware, which is a warning.
- **Hugging Face / LangSmith prompt hubs:** share prompts, not hidden context. Gap: they never see harness injections.
- **GitHub Actions reusable workflows:** versioned, reusable automation with `uses: org/repo@v1`.

### 2.6 What has *not* been attempted (as far as this sweep can claim)
1. A **portable document format** whose target is *another vendor's runtime-injected context*, version-pinned to a captured first-frame hash.
2. A **community filter list** for coding-agent tool schemas and system bloat (not for ads, not for HTTP paths).
3. A **marketplace whose SKU is a mutation of hidden context**, with supply-chain signing, because the artifact can disable tools or inject instructions.
4. **Eval-as-first-class** where overlay identity is a `candidate_key` dimension equal to model (NOW.md already wants this; market has prompt A/B, not wire-overlay A/B).
5. **Director/API twin** that can apply, promote, and subscribe overlays programmatically (north star), not only a GUI rules page.
6. **Wire-vs-transcript as the authoring canvas** — edit only the delta the harness hides.
7. **Tier-split economics**: solo keeps overlays local; teams host subscription + sync; enterprise sells the reverse-proxy + signed policy packs as the product, not the UI.

---

## 3. Idea volume (generate widely)

Each idea: short name, one-line pitch, precedent, rough risk.

### A. Primitive and document shape
1. **Portable Overlay Document (POD)** — single shareable file (YAML/JSON + optional human DSL) compiling to today's `Override` ops. *Precedent: ESLint config, Kyverno policy.* Risk: premature format freeze.
2. **Semantic selectors, not indices** — `system:matches("You are *")` / `tool:name(mcp__*)` instead of `system:0`. *Precedent: CSS selectors, jq, uBlock cosmetic filters.* Risk: match ambiguity across harness versions.
3. **Patch-against-baseline overlays** — store unified-diff / structural patch vs first-frame snapshot, not absolute text. *Precedent: git patch, Nix overlay.* Risk: fuzzy apply on drift.
4. **Layered cascade** — `global → org → team → space → worktree → canvas → run → track` with explicit precedence and audit "who won." *Precedent: CSS cascade, EditorConfig.* Risk: user confusion; needs inspector "computed overlay."
5. **Compile-from-intent** — NL or high-level verbs ("strip unused MCP tools", "cap tool results at 4k") compile to POD. *Precedent: Pi-hole block categories, CSP generators.* Risk: surprise mutations.
6. **Overlay packages with `extends`** — `@tm/slim-claude-code@2`, `extends` + local delta. *Precedent: ESLint shareable configs, Tailwind presets.* Risk: diamond dependency conflicts.
7. **IR-normalized share surface** — overlays target TM `InternalRequest`, never raw Anthropic/Codex JSON, so one POD ports across harnesses. *Precedent: LLVM IR, OpenTelemetry.* Risk: IR drift as providers add fields.
8. **Time-bounded / turn-bounded overlays** — expire after N turns, or until harness version bumps. *Precedent: feature flags, cert TTL.* Risk: silent expiry mid-session.
9. **Conditional overlays** — predicates on token count, model, track role (parent/subagent), workspace path. *Precedent: Charles match conditions, Kyverno `preconditions`.* Risk: hard to reason about.
10. **Response-side overlays** — mutate streaming responses / tool results before they re-enter next-turn context (scrub secrets, truncate). *Precedent: DLP proxies, email gateways.* Risk: breaks harness state machines.

### B. Authoring loop (from breakpoint → permanent)
11. **Breakpoint-to-overlay promotion** — one action: "remember this edit" → POD op, scoped. *Precedent: browser "save as snippet", Charles "compose → rewrite rule."* Risk: promoting a one-off that was situational.
12. **Wire-delta authoring canvas** — UI shows only wire-only content (injected system, tool schemas not in transcript); edits apply there. *Precedent: DevTools "Diff", git ignore of generated noise.* Risk: needs solid wire-vs-transcript read surface (TLDR notes this is still missing).
13. **Live token counter as co-author** — every edit shows `tokens_before` / after using existing count_tokens path. *Precedent: already partially in breakpoint UI.* Risk: provider rate limits.
14. **First-frame walkthrough as onboarding** — new user sees the 285KB anatomy (tools 67%), accepts/modifies via overlay. *Precedent: NOW.md stage-2 flow; OS permission first-run.* Risk: overwhelm; need progressive disclosure.
15. **Drift doctor** — on harness upgrade, diff stored baseline → flag broken selectors → suggest rebind. *Precedent: ESLint `--fix`, DB migrations.* Risk: noisy false positives.
16. **Counterfactual dual-pane** — left original IR, right overlaid; scrubber per op. *Precedent: Photoshop layers, git word-diff.* Risk: UI cost.
17. **Mine historical captures for dead tools** — "you never invoke X; propose toggle off." *Precedent: coverage tools, Chrome unused CSS.* Risk: privacy of local history; false "never."
18. **Subagent inheritance rules** — parent overlay defaults to children; track-scoped exceptions. *Precedent: CSS inheritance, IAM role assumption.* Risk: subagent needs tools parent stripped.
19. **Director MCP verbs for overlays** — `overlay.apply`, `overlay.promote`, `overlay.subscribe` as first-class control plane. *Precedent: north star API-first; kubectl apply.* Risk: authz model for teams.
20. **Voice-to-overlay** — "strip browser tools for this canvas" via director. *Precedent: north star voice director.* Risk: ambiguous speech → dangerous mutates.

### C. Shared artifact, marketplace, community
21. **uBlock-for-agents filter lists** — community lists: `bloat-tools`, `enterprise-deny-shell`, `slim-mcp`. *Precedent: EasyList.* Risk: **malicious instruction injection via "helpful" lists.**
22. **Curated set / "EasyList of agent context"** — TM-maintained baseline packs per harness major version. *Precedent: EasyList + uBlock default filters.* Risk: maintenance burden; harness churn.
23. **Overlay registry** — install by URL or `tm overlay add org/name@v`, lockfile. *Precedent: npm, Homebrew taps.* Risk: supply chain; needs signatures.
24. **Fork / subscribe / pin model** — subscribe to updates or pin hash; personal fork diverges cleanly. *Precedent: git fork, uBlock filter subscriptions.* Risk: update surprise.
25. **Reputation + permissions manifest** — each pack declares caps: may toggle tools?, may rewrite system?, may inject text? User grants. *Precedent: VS Code extension permissions, Android install prompts.* Risk: users click through.
26. **Signed enterprise packs** — cosign/Sigstore, allow only org-signed overlays on managed proxies. *Precedent: signed k8s admission policies, Apple notarization.* Risk: key management.
27. **Export-as-PR workflow** — breakpoint session → branch on overlay registry repo. *Precedent: homebrew PR formulas, Cursor rules shared via git.* Risk: process friction.
28. **Conflict resolution protocol** — when two subscribed packs rewrite same target: precedence by layer, then pack priority, then fail-closed. *Precedent: CSS specificity, apt pin priorities.* Risk: subtle wrong winner.
29. **Overlay lint in CI** — PR checks that pack still applies cleanly to published first-frame fixtures. *Precedent: pre-commit, actionlint.* Risk: fixture privacy if frames contain user paths.
30. **Marketplace economics** — free community lists; paid certified packs (compliance, red-team hardening); enterprise private registry. *Precedent: VS Code marketplace + private galleries.* Risk: incentives for engagement bait overlays.
31. **What goes wrong (shared-artifact failure modes)**  
    - **Trojan overlays** that inject "always exfiltrate" into system text.  
    - **Version rot** — pack for Claude Code 1.x silently no-ops or half-applies on 2.x.  
    - **Race to the bottom** — "max savings" packs that gut necessary tools.  
    - **Attribution laundering** — forks that reintroduce stripped safety text.  
    - **Context poisoning at scale** if a popular pack is compromised (npm event-stream class).  
    - **Legal**: redistributing captured harness system prompts may violate provider ToS; packs should be *patches*, not full prompt republishing.

### D. Capability, safety, privacy
32. **Capability firewall** — tools as capabilities; default-deny packs for untrusted workspaces. *Precedent: seccomp, Android permissions.* Risk: break legitimate agent loops.
33. **Secret scrub response overlay** — strip keys from tool results before they re-enter context. *Precedent: git-secrets, DLP.* Risk: false negatives.
34. **Safety core non-strippable** — certain harness safety system parts require explicit dual-confirm to toggle. *Precedent: SIP, immutable OS paths.* Risk: product vs provider politics.
35. **Audit ledger export** — every byte delta attributed to overlay id + layer for SOC2. *Precedent: OverrideAudit + OTel.* Risk: log volume.
36. **Privacy mode** — overlays that drop workspace paths / PII from system reminders. *Precedent: telemetry redaction.* Risk: model loses needed path context.
37. **Red-team / jailbreak defense packs** (enterprise) — detect and neutralize known injection patterns in user turns *without* sending them upstream unchanged. *Precedent: WAF rules.* Risk: false positive refusal of legitimate work.
38. **Cost governor packs** — soft/hard token budgets, progressive trim order. *Precedent: rate limiters, AWS budgets.* Risk: quality cliffs.

### E. Eval, runtime, product plane
39. **Overlay as `candidate_key` dimension** — N eval candidates differ only by overlay (NOW.md). *Precedent: prompt A/B harnesses, LaunchDarkly experiments.* Risk: explosion of matrix size.
40. **Shadow mode** — apply overlay, compute tokens/diff, do not forward mutation (measure only). *Precedent: Envoy shadow, feature flag dark launch.* Risk: incomplete if behavior depends on model seeing change.
41. **Replay lab** — re-run historical wire captures through new overlays offline. *Precedent: mitmproxy replay, traffic fixtures.* Risk: stale auth, non-determinism.
42. **Launch-spec binding** — `FrozenLaunchSpec.overlay_ref` immutable for the run. *Precedent: container image digest pin.* Risk: mid-run hot-reload debate.
43. **Hot-reload vs freeze** — solo wants live edit; eval wants freeze; enterprise policy may force freeze. *Precedent: k8s rolling update vs immutable tags.* Risk: one mode does not fit all tiers.
44. **Per-track overlay in canvas** — different panes, different overlays, same worktree. *Precedent: multi-agent roles.* Risk: human loses track of who has which policy.
45. **Template rows in launcher** — overlay pack as a first-class launch template dimension (alongside runtime templates already in canvas launcher). *Precedent: JetBrains run configurations.* Risk: template sprawl.

### F. Tier-specific meanings (solo / teams / enterprise)

46. **Solo: overlays as local craft**  
    - Live in channel home and optionally `.tm/overlays/` in the repo (git-tracked personal/project craft).  
    - No account required; export/import files.  
    - First-frame baselines stay on disk under channel home.  
    - *Precedent: user stylesheets, local uBlock lists, `.editorconfig`.*  
    - Failure: users lose overlays on machine wipe without git.

47. **Teams: overlays as shared coordination**  
    - Org registry hosted by TM; subscribe + personal delta.  
    - Space/worktree scoped defaults so two checkouts share policy by path identity (TM workspace model).  
    - Activity stream shows "overlay X applied, −42k tokens" as a social/ops signal.  
    - Director agents in the org apply packs via API.  
    - *Precedent: shared ESLint config monorepo packages, 1Password shared vaults.*  
    - Failure: noisy org-wide packs; need escape hatches and blame.

48. **Enterprise: overlays as the thing they buy**  
    - The reverse proxy *is* the control point; UI is optional.  
    - Signed policy packs, air-gapped registry mirror, fail-closed if unsigned.  
    - Admission-style validate (deny launch / deny release) separate from mutate.  
    - SIEM export of audit; legal hold on overlay versions used in a run.  
    - Data flow stays in customer network; TM sells policy distribution + proxy appliance.  
    - *Precedent: Zscaler/Netskope SWG, OPA Gatekeeper, private extension galleries.*  
    - Failure: if packs ship harness system text, legal/ToS; stick to patch ops + hashes.

49. **Tier product split in one sentence each**  
    - Solo: *see and shape what your harness hides.*  
    - Teams: *agree on what every agent in the space is allowed to know and use.*  
    - Enterprise: *enforce and prove what left the building toward the model provider.*

### G. Wilder lateral bets
50. **Overlay as a new open format outside TM** — publish POD + first-frame fixture format so other proxies can interoperate (like SARIF for static analysis). *Precedent: SARIF, SPDX, CycloneDX.* Risk: standards theater without adopters.
51. **Insurance / compliance certification** — "runs under pack `soc2-tool-minimal@3`" as a control evidence. *Precedent: CIS benchmarks.* Risk: checkbox theater.
52. **Educational overlays** — force smaller tool surface for learners; reveal system parts pedagogically. *Precedent: training wheels, supervised mode.* Risk: niche.
53. **Model-size adapters** — packs that rewrite tool schemas down for local/small models. *Precedent: quantization, distillation of interfaces.* Risk: semantic loss.
54. **Competitive teardown packs** — published diffs of what Claude Code vs Codex inject (research/marketing). *Precedent: browser fingerprinting research.* Risk: ToS; do not redistribute full prompts.
55. **Overlay NFT joke, then serious cousin** — content-addressed pack hashes with provenance graph (sigstore), not speculation. *Precedent: SLSA provenance.* Risk: crypto-branding poison.
56. **Community "baseline museum"** — hashed first frames per harness version as public research corpus (redacted). *Precedent: HTTP Archive.* Risk: legal; redaction hard.
57. **Insurance against provider silent prompt changes** — drift alerts as a subscription feature ("your harness changed at 02:14 UTC"). *Precedent: certificate transparency monitors.* Risk: alert fatigue; high value for power users.
58. **Cross-product Little Organs handoff** — overlays inject `context-matters` recall *at the wire* without teaching every harness a plugin API. *Precedent: LD_PRELOAD shared library.* Risk: double-injection if harness also has CM skill.
59. **Adversarial marketplace war games** — red team publishes attack packs in a sandbox; blue team publishes defenses. *Precedent: YARA rule sharing.* Risk: arming attackers.
60. **The anti-product: zero overlay** — TM's pure observability mode remains sacred; overlays opt-in so trust is earned. *Precedent: tcpdump vs iptables.* Risk: growth wants defaults on.

---

## 4. Judgment: top five

Criteria: (a) unique to TM's seam, (b) strong stealable precedent, (c) unlocks shared-artifact future, (d) fits solo→teams→enterprise without rewrite, (e) builds on existing override/breakpoint/first-frame code rather than replacing it.

### 1. Portable Overlay Document + cascade (the primitive)
**Why:** Without a portable document and explicit layer precedence, everything else is session state. POD compiles to existing `Override` kinds; cascade matches how orgs already think about config. This is the Nix/EditorConfig/CSS move.
**Precedent:** Nix overlays, ESLint `extends`, CSS cascade, Kyverno policies.
**Tier read:** solo files; teams registry documents; enterprise signed documents. Same schema.

### 2. First-frame baseline + patch/semantic overlays (the versioning spine)
**Why:** `NOW.md` is right: an overlay is an edit to what a *specific harness version* sends. Baselines + semantic selectors + drift doctor prevent the "silent no-op after upgrade" death mode that kills filter lists and user scripts alike.
**Precedent:** git patches against tags, browser extension "matches manifest," database migrations.
**Tier read:** solo local baselines; teams shared fixtures per harness version; enterprise fail-closed on unmatched selectors.

### 3. Breakpoint-to-overlay promotion + wire-delta authoring (the product loop)
**Why:** Users will not write policy packs from a blank page. They will pause, edit, feel the token win, and hit "remember." Combined with a wire-only delta canvas, this is the Stylus "write while browsing" loop and Charles "save rewrite" loop — grounded in code that already exists (`breakpoint.py`, override apply/audit, inspector editor).
**Precedent:** Charles rule creation from a breakpoint, browser snippet save, "extract method" refactor.
**Tier read:** solo craft loop; teams "promote to org pack" review; enterprise promote requires signature + change ticket.

### 4. Filter-list / registry model with permissions manifests (the shared-artifact engine)
**Why:** This is how the category becomes a network, not a feature. uBlock proved declarative community policy can stay maintainable; VS Code proved permissions manifests set expectations. The failure modes (trojans, version rot, ToS on full prompt republication) must shape the format: **patches + hashes, not full system dumps; caps in manifest; pin by default.**
**Precedent:** EasyList subscriptions, npm + lockfiles, VS Code extension permissions, Sigstore.
**Tier read:** solo optional community lists; teams org registry + subscribe; enterprise private gallery, signed only, air-gap mirror.

### 5. Overlay as launch-spec / admission dimension + director API (the control-plane close)
**Why:** North star is API-first. Overlay ref on `FrozenLaunchSpec` makes eval and production the same verb. Enterprise admission (validate vs mutate) and director MCP verbs make overlays operable by agents that manage agents — not a GUI-only rules page. This is what turns "request editor" into "hidden-context control plane."
**Precedent:** OPA admission controllers, container image digests, feature-flag targeting, kubectl apply.
**Tier read:** solo freeze-on-launch optional; teams shared launch templates; enterprise mandatory policy packs on the proxy they buy.

---

## 5. Recommended narrative (for humans, not the done line)

**Category:** user-owned **Agent Context Overlays** — a hidden-context control plane on the wire.

**One-liner:** *Everyone ships prompts and rules into the harness. Nobody has given the human a permanent, shareable, versioned grip on what the harness already injects.*

**Composition story:** POD documents in a cascade, authored from breakpoints, pinned to first-frame baselines, distributed like filter lists with permission manifests, enforced like admission controllers, selected like model at launch.

**Do not:**
- Redistribute full provider/harness system prompts in a public marketplace.
- Default-on community lists without pin + permissions.
- Build a second rules engine parallel to `overrides/` — compile into it.
- Make enterprise "more UI." Sell the proxy + signed packs.

**Do:**
- Keep pure capture mode sacred (trust).
- Make promotion from breakpoint the primary authoring path.
- Invest early in semantic selectors + drift doctor (versioning is the hard problem).
- Design solo files so teams/enterprise are sync and signing layers, not a rewrite.

---

## 6. Counts

- **Ideas generated:** 60 numbered (+ category table + failure modes + tier splits).
- **Top five marked:** §4.
- **Primary precedents named:** Charles/Proxyman, uBlock/EasyList, Stylus/user stylesheets, Nix overlays, EditorConfig/ESLint extends, K8s admission/OPA, Tampermonkey, VS Code marketplace, LD_PRELOAD, git patches, SARIF-style open formats.

