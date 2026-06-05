# Review: package smoke relocation

Reviewed `c7f19c14b763bd5eb8b218b603db6d90994e9247...adbc9180a7eec8e796705ad0d45041e5b58b2d75` as a branch with no pull request.

Found 7 candidate findings: 2 major, 5 minor.

## 1. Major: the static guard prevents the required relocated negative proof

Location: `desktop/package.json:11` and `desktop/scripts/assert-packaged-imports.mjs:84`

Observation: `package:smoke` starts with `pnpm build`. The changed build script runs `assert-packaged-imports.mjs`, which exits on the runtime `@tm/contract` import before `package-smoke-build.mjs`, `relocatePackage`, or Electron runs.

Impact: the named bad import makes the command fail even if relocation no longer isolates module resolution. The command therefore cannot prove that the relocated app catches the defect. The focused test mocks the executable and writes readiness itself, so it does not preserve that behavioral proof either.

Basis: the brief requires the reintroduced bad import to fail the relocated smoke and permits a static guard only when it does not duplicate the smoke. All three review lenses found this independently.

Caveat: the guard diagnoses the current defect quickly. The engineer separately bypassed it and reached the relocated failure, but the standard command and committed tests do not keep those proofs independent.

Links:

- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/package.json#L10-L15
- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/scripts/assert-packaged-imports.mjs#L83-L90
- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/src/packageSmoke.test.ts#L207-L230

## 2. Major: the staged graph has a separate package definition from electron-builder

Location: `desktop/src/packageSmoke.ts:95` and `desktop/scripts/assert-packaged-imports.mjs:66`

Observation: the smoke stages the hand built `dist/package-smoke` tree. Its builder copies `dist`, `assets`, and `package.json` into an unpacked `resources/app`, omits every production dependency, and includes stale `dist/standalone` and `dist/standalone-app` output. Electron-builder packages an ASAR, collects production dependencies, unpacks native resources, and excludes those three build directories. The new guard encodes the hand built rule by rejecting every bare specifier except Electron and Node builtins. The relocation also preserves symlinks verbatim, including any workspace dependency link that escapes the package.

Impact: a legitimate npm, native, or packaged workspace dependency fails every desktop build even when electron-builder would ship it. An escaping workspace symlink can still satisfy an import after relocation. Existing stale output shows the immediate cost of the divergent file graph: the local package smoke artifact is 1.9 GB, including 320 MB of `standalone` and 1.3 GB of `standalone-app`, and relocation copies the whole artifact again.

Basis: `package-smoke-build.mjs`, `electron-builder.yml`, and electron-builder's installed pnpm production dependency collector define different graphs. The brief specifically asks the staged copy to represent ASAR layout, native modules, and packaged workspace dependencies.

Caveat: the current desktop manifest has no production dependencies, its Electron framework links are internal relative links, and clean CI does not contain stale standalone output. The original runtime `@tm/contract` defect is represented in both main process graphs.

Links:

- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/src/packageSmoke.ts#L90-L107
- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/scripts/assert-packaged-imports.mjs#L65-L80
- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/scripts/package-smoke-build.mjs#L59-L81
- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/electron-builder.yml#L18-L31

## 3. Minor: the new import parser duplicates and weakens the shared parser

Location: `desktop/scripts/assert-packaged-imports.mjs:34`

Observation: `packages/common/src/domainBoundary.ts::moduleSpecifiers` already owns TypeScript AST extraction and reports a nonliteral dynamic import as an offender. The new script copies that traversal. It silently skips `import(name)`, misses template literal specifiers with no substitutions, treats any shadowed identifier named `require` as CommonJS, and accepts every relative specifier without proving that it stays inside the package or resolves.

Impact: equivalent emitted imports can receive different verdicts. A computed package import or an escaping relative import can pass the guard, while a local function named `require` can cause a false build failure. The script still prints that the complete dist graph resolves from the package.

Basis: this is a second `moduleSpecifiers` implementation despite the repository's DRY rule. The existing parser and its tests already encode fail closed handling for unknown imports. It needs a small shared extension for emitted CommonJS rather than a parallel parser.

Caveat: current production output does not contain these import forms. The relocated launch remains a backstop for an evading import when startup executes that path.

Link:

- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/scripts/assert-packaged-imports.mjs#L34-L63

## 4. Minor: relocation setup leaks the temporary package when setup fails

Location: `desktop/src/packageSmoke.ts:64`

Observation: `relocatePackage` creates its temporary root, checks ancestors, and performs the full synchronous copy before the caller enters `try` and `finally`.

Impact: an ancestor assertion, missing source, permission error, interruption, full disk, or partial copy leaves `/tmp/transport-matters-package-*` behind. A partial Electron package can be large, and retries compound disk pressure.

Basis: cleanup ownership begins only after `relocatePackage` returns. No test covers relocation failure. The direct relocation test also leaves its staged root behind.

Caveat: successful relocation and every later launch failure reach the outer finalizer.

Links:

- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/src/packageSmoke.ts#L63-L82
- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/src/packageSmoke.ts#L90-L98

## 5. Minor: timeout cleanup races Electron termination

Location: `desktop/src/packageSmoke.ts:80`

Observation: the timeout sends `SIGTERM`, ignores the result, and rejects immediately. The new `finally` then recursively removes the staged application without waiting for the child's `exit` or `close` event.

Impact: a delayed or ignored signal leaves Electron running while its files are removed. Windows can reject deletion of the live executable and replace the useful timeout error with an `rmSync` error.

Basis: immediate timeout rejection predates this branch. Deleting the live staged package during that gap is new.

Caveat: Electron normally handles `SIGTERM` promptly. CI runs Linux, where deleting open files usually succeeds.

Links:

- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/src/packageSmoke.ts#L74-L82
- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/src/packageSmoke.ts#L228-L251

## 6. Minor: signal exits discard the evidence that explains the two early runs

Location: `desktop/src/packageSmoke.ts:244`

Observation: Node's child `exit` event provides `code` and `signal`. The listener accepts only `code`, so every signal termination becomes `Desktop package smoke exited with code null.`

Impact: the command cannot distinguish `SIGTRAP`, `SIGTERM`, or another signal. The two unexplained runs now have direct evidence: `Electron-2026-08-28-121921.ips` and `Electron-2026-08-28-121938.ips` both show relocated Electron processes running for about 1.8 seconds, entering `NSAlert runModal`, and terminating with `EXC_BREAKPOINT` and `SIGTRAP`. The current listener drops the decisive field.

Basis: the branch adds guidance for silent main process load failures, and the negative proof exposed this diagnostic gap.

Caveat: signal handling predates this branch. The matching crash reports confirm that relocation reached the intended Electron load failure rather than the 15 second timeout.

Link:

- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/src/packageSmoke.ts#L240-L251

## 7. Minor: the returned executable path is deleted before the caller receives it

Location: `desktop/src/packageSmoke.ts:76`

Observation: `runPackagedAppSmoke` puts the staged executable in `PackageSmokeResult`, then its `finally` removes the executable's parent before the promise resolves. `main` prints that dead path.

Impact: the CLI reports an artifact that no longer exists, and a programmatic caller cannot inspect or reuse the path carried by the result.

Basis: before this branch, `executablePath` named the persistent package build output. The relocation changes that result contract without changing the type or output.

Caveat: the current production caller only prints the result, and current tests consume `status`.

Link:

- https://github.com/littleorgans/transport-matters/blob/adbc9180a7eec8e796705ad0d45041e5b58b2d75/desktop/src/packageSmoke.ts#L74-L82

## Verified review boundary

- No pull request exists for `feat/package-smoke-relocate`.
- Reviewed head: `adbc9180a7eec8e796705ad0d45041e5b58b2d75`.
- Baseline: `c7f19c14b763bd5eb8b218b603db6d90994e9247`.
- The diff contains four files. Their head lengths are 27, 92, 236, and 268 lines.
- `git diff --check` is clean.
- Desktop CI still runs `package:smoke` under xvfb.
- No builds, typechecks, or broad tests ran. The review contract prohibited writes outside this findings file.
- The checkout remains on baseline main. The only worktree modification is the owner's out of scope `transport-matters.code-workspace` edit.
