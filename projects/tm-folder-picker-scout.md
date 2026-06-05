# Folder-picker scout (t3code → transport-matters)

Status: **read-only scout**  
Date: 2026-07-24  
Source repo: `~/Dev/LLM/DEV/helioy/t3code`  
Consumer: transport-matters canvas CMDK (`www/packages/canvas/src/launcher/`), create-workdir path selection  
No writes to either tree.

---

## 1. Reuse map (t3code)

### 1.1 What the UX is

Keyboard-driven directory navigator embedded in the **command palette** (not a standalone modal component name). Path-shaped query text switches the palette into **browse mode**: path bar is the palette input; list is a "Directories" group with optional `..` up-row; footer shows Navigate / Select / Back / Esc; header action is **Add** (or Create & Add) with **⌘Enter** / Enter; optional **Open in Finder/File Explorer** when a desktop bridge exists.

### 1.2 Component surface (framework + files)

| Layer | Location | Role |
|-------|----------|------|
| Shell UI | `apps/web/src/components/CommandPalette.tsx` (`CommandPalette`, browse state, key handlers, Add + Open-in-file-manager) | Orchestrates browse mode, submits selection |
| Browse list builder | `apps/web/src/components/CommandPalette.logic.ts` (`buildBrowseGroups`, `filterBrowseEntries`, `getCommandPaletteMode`) | Pure list model: `..` + directory rows |
| Results render | `apps/web/src/components/CommandPaletteResults.tsx` | Renders command groups |
| Dialog primitives | `apps/web/src/components/ui/command.tsx` (`CommandDialog`, `CommandDialogPopup`, `CommandPanel`, `CommandFooter`) | **React 19 + `@base-ui/react/dialog`** (Base UI), Tailwind, lucide icons — not Tauri, not Electron for the in-palette browser itself |
| Path helpers (web re-export) | `apps/web/src/lib/projectPaths.ts` | Re-exports client-runtime path helpers |
| Path helpers (authority) | `packages/client-runtime/src/state/projects.ts` (`isFilesystemBrowseQuery`, `hasTrailingPathSeparator`, `getBrowseDirectoryPath`, `getBrowseLeafPathSegment`, `appendBrowsePathSegment`, `getBrowseParentPath`, `canNavigateUp`, `ensureBrowseDirectoryPath`, `resolveProjectPathForDispatch`) | Client-side path math |
| Browse query atom | `packages/client-runtime/src/state/filesystem.ts` (`createFilesystemEnvironmentAtoms.browse`) | Wraps RPC tag |
| Contracts | `packages/contracts/src/filesystem.ts` (`FilesystemBrowseInput`, `FilesystemBrowseEntry`, `FilesystemBrowseResult`, `FilesystemBrowseError`) | Wire schema |
| RPC method name | `packages/contracts/src/rpc.ts` (`WS_METHODS.filesystemBrowse` = `"filesystem.browse"`, `WsFilesystemBrowseRpc`) | WebSocket RPC, not REST |
| Server browse impl | `apps/server/src/workspace/WorkspaceEntries.ts` (`WorkspaceEntries.browse`, `expandHomePath`, `resolveBrowseTarget`) | **Node `fs/promises.readdir({ withFileTypes: true })`**, directories only |
| WS handler | `apps/server/src/ws.ts` (`[WS_METHODS.filesystemBrowse]` → `workspaceEntries.browse`) | Auth-scoped RPC dispatch |
| Native OS picker (optional) | `apps/desktop/src/electron/ElectronDialog.ts` (`pickFolder` → `Electron.dialog.showOpenDialog` with `openDirectory`), preload IPC `pickFolder`, web `localApi.dialogs.pickFolder` | **Electron-only** "Open in Finder/Explorer" path |

**Framework summary:** React web app + Base UI command dialog + Effect atoms over WebSocket RPC to a Node server. Optional Electron IPC for native folder dialog. No Tauri. No dedicated npm "folder-picker" package.

### 1.3 Data source (list directories)

Primary path for the keyboard navigator:

1. Client detects browse mode when the query looks like a path (`isFilesystemBrowseQuery`).
2. Client derives directory stem (`getBrowseDirectoryPath`) and optional leaf filter (`getBrowseLeafPathSegment`).
3. Client calls **`filesystem.browse`** via environment RPC:

```ts
// apps/web CommandPalette → filesystemEnvironment.browse
{
  environmentId: <env>,
  input: {
    partialPath: browseDirectoryPath,  // e.g. "~/Dev/LLM/" or "/Users/…/repo/"
    cwd?: currentProjectCwd            // only for relative ./ ../ paths
  }
}
```

4. Server `WorkspaceEntries.browse`:
   - Expand `~` / `~/…` with `os.homedir()` (`expandHomePath`)
   - Resolve absolute or relative-to-cwd (`path.resolve`)
   - If `partialPath` ends with separator (or is `~`): list **that** directory; else list **parent** and filter basenames by typed prefix
   - `readdir(parentPath, { withFileTypes: true })`
   - Keep **directories only** (`dirent.isDirectory()`)
   - Hide dot dirs unless query starts with `.` or ends with separator (hidden filter also mirrored client-side in `filterBrowseEntries`)
   - EACCES/EPERM → empty list (not hard fail)
   - Sort by name

**Request / response (contracts):**

| Field | Shape |
|-------|--------|
| **In** `FilesystemBrowseInput` | `partialPath: string` (trimmed, non-empty, max 512); optional `cwd: string` |
| **Out** `FilesystemBrowseResult` | `parentPath: string`; `entries: { name, fullPath }[]` |
| **Err** `FilesystemBrowseError` | failures: `windows_path_unsupported` \| `current_project_required` \| `read_directory_failed` |

**Read-only:** yes for browse — only `readdir` / resolve; no mkdir on the browse path. (Separate "Create & Add" project flow can create folders; that is product-create, not the list API.)

**Secondary path:** desktop native picker via `window.desktopBridge.pickFolder` / Electron `showOpenDialog({ properties: ["openDirectory"] })`. Not available in plain browser.

### 1.4 Path handling

| Concern | Where | Behavior |
|---------|-------|----------|
| Home `~` | server `expandHomePath` | `~` → homedir; `~/x` / `~\x` → join |
| Browse activation | client `isFilesystemBrowseQuery` | `./` `../` `/` `~/` (and Windows abs if platform win) |
| Trailing `/` | client + server | Means "this directory is the list target"; without it, last segment is prefix filter |
| Descend | client `browseTo` → `appendBrowsePathSegment` | Appends `name` + preferred separator |
| Up `..` | client `browseUp` → `getBrowseParentPath` + row `buildBrowseGroups` value `browse:up` | Parent path string; root has no parent (`canNavigateUp`) |
| Canonicalize | server `path.resolve` after home expand | Absolute resolved path; `fullPath` via `path.join` |
| Relative paths | need `cwd` (active project); else `current_project_required` | TM workdir create can require absolute paths only (matches existing `worktree_mutations._canonical_absolute_path`) |
| Commit selection | `resolvedAddProjectPath` | Trailing sep → `parentPath` / current dir; else exact entry `fullPath` or raw query; **⌘Enter** commits even when a row is highlighted |

### 1.5 Dependencies

| Kind | Packages / modules |
|------|-------------------|
| UI | `react`, `react-dom`, `@base-ui/react`, `lucide-react`, Tailwind (`tailwind-merge`, etc.) |
| State / RPC | `effect`, `@effect/atom-react`, `@t3tools/contracts`, `@t3tools/client-runtime`, `@t3tools/shared` |
| Server FS | Node builtins only: `node:fs/promises`, `node:os`, Effect `Path` |
| Desktop optional | Electron `dialog.showOpenDialog`, IPC preload bridge |
| **No** | dedicated folder-picker npm package, native Node addon for listing |

Icons: `FolderIcon`, `CornerLeftUpIcon` from lucide.

---

## 2. transport-matters gap map

| TM area | Today | Relevance |
|---------|-------|-----------|
| Launcher | `www/packages/canvas/src/launcher/` — custom CMDK (`CommandCenter`, `commandModel`, `commandRows`, `workdirRows`); already has `create-workdir` command kind in `commandTypes` | Natural host for a **browse submode**, not a foreign Base UI CommandDialog |
| UI stack | React + Ark UI Combobox (launcher) | Different dialog primitive than t3code Base UI — **do not import t3code UI** |
| Create workdir API | REST `POST /v1/spaces/{space_id}/worktrees` + `createWorkdir` in `@tm/core` | Needs a **path string**; picker only has to return absolute path |
| Detection | `space/detection.py` `detect_space` | Git/plain classification of a **known path**, not directory listing |
| Local file HTTP | `api/v1/local_file_routes.py` `GET /local-file` | Reads **file** content; **rejects directories**; host-origin gated — not a list API |
| Desktop bridge | Not a t3code-style Electron shell for canvas | "Open in Finder" is **optional / omit v1** unless TM later adds a native host |

**Backend gap (confirmed):** no arbitrary directory-listing endpoint. Without one, a browser-served canvas cannot see host FS entries.

---

## 3. Recommendation

### Verdict: **ADAPT (UX + path rules + browse algorithm); REBUILD UI + HTTP backend**

| Piece | Leverage | Adapt | Rebuild |
|-------|----------|-------|---------|
| Keyboard UX (path bar, Directories, `..`, ↑↓ Enter Backspace Esc, Add ⌘Enter) | Pattern only | Map to TM launcher rows/hotkeys | Full component in `www/packages/canvas/src/launcher/` |
| Path helpers | — | Port/slim `projects.ts` browse helpers (unix-first: `~`, `/`, trailing `/`, parent, append) | Small TS module under canvas or `@tm/core` |
| List-dir data plane | Algorithm in `WorkspaceEntries.browse` | Same semantics in Python | **New FastAPI read-only endpoint** |
| Base UI Command / Effect WS RPC / multi-env WSL routing | — | — | Out of scope; wrong stack |
| Electron "Open in Finder" | — | — | Defer unless TM desktop host exists |

**Do not** copy-paste CommandPalette or pull t3code packages into TM. **Do** treat t3code as the product reference for browse semantics.

### Minimal FastAPI list-dir (ports t3code browse)

Suggested surface (names illustrative):

```
GET /v1/fs/directories?path=<partialPath>
  origin-gated like other trusted local REST
  owner/local desktop only

200 {
  "parentPath": "/Users/me/Dev/LLM/",
  "entries": [
    { "name": "helioy", "fullPath": "/Users/me/Dev/LLM/helioy" }
  ]
}
```

Server algorithm (mirror `WorkspaceEntries.browse`):

1. Reject empty / non-absolute after expand (TM create_workdir already requires absolute paths — prefer **absolute + `~` only**, skip relative+cwd complexity in v1).
2. Expand `~` with `Path.home()`; `resolve()`.
3. Trailing `/` or bare `~` → list that dir; else list parent, prefix-filter basename.
4. `os.scandir` / `Path.iterdir`; **directories only**; optional hide dotdirs unless filter starts with `.`.
5. Sort by name; return `parentPath` + entries.
6. Permission errors → empty entries or typed 403; missing path → 404.

Non-goals for v1: files in list, recursive tree, create-on-disk, Windows/WSL multi-env, native Finder bridge.

Client flow for create-workdir:

1. CMDK action "Add workdir" → enter browse mode with seed path (e.g. `~/` or last space cwd).
2. On path change, debounce `GET /v1/fs/directories`.
3. Render Directories + `..`; Enter descends or Add commits.
4. Commit → existing `createWorkdir(spaceId, absolutePath)`.

### Effort shape

1. **Backend** (small): one route + pure list helper + tests (empty, `~`, trailing slash, prefix filter, permission).
2. **Path helpers** (small): adapt unix subset from t3code `projects.ts` browse functions.
3. **Launcher UI** (medium): browse mode in existing CMDK — not a new product shell.
4. **Wire to create-workdir** (small): already have REST/MCP create.

---

## 4. Decision-needed

None for scout. Implementation defaults if unchallenged:

- **Unix-first** absolute + `~` only (matches TM create path rules).
- **No** "Open in Finder" in first slice.
- **No** folder create-on-disk in picker (inventory existing dirs only; matches S3 detected create_workdir).
- Endpoint under trusted local origin gate, same class as space REST mutations.

---

## 5. One-line for orchestrator

`adapt UX+path+browse-algo; rebuild Ark/CMDK UI + FastAPI list-dir (t3code filesystem.browse ports, no direct reuse)`
