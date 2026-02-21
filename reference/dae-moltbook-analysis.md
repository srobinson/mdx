# DAE Moltbook Agent -- Complete Technical Analysis

**Source:** `/Users/alphab/Dev/LLM/DEV/DAE/SOURCE/dae-moltbook/dae-moltbook/`
**Version:** 0.7.2
**Author:** smaxforn
**Analyzed:** 2026-02-13
**Purpose:** Full extraction of architecture, algorithms, agent logic, and unique features for Rust reimplementation ("attention-matters").

---

## Table of Contents

1. [Architecture Overview & File Structure](#1-architecture-overview--file-structure)
2. [Core Engine Comparison (dae-core.mjs)](#2-core-engine-comparison)
3. [Agent Architecture](#3-agent-architecture)
4. [Moltbook API Integration](#4-moltbook-api-integration)
5. [LLM Integration](#5-llm-integration)
6. [Turn Flow -- Complete Pipeline](#6-turn-flow--complete-pipeline)
7. [Seed Mode -- Read-Only Memory Ingestion](#7-seed-mode--read-only-memory-ingestion)
8. [State Management & Persistence](#8-state-management--persistence)
9. [Conversation Management](#9-conversation-management)
10. [Import/Export Capabilities](#10-importexport-capabilities)
11. [API Key Security Model](#11-api-key-security-model)
12. [Constants & Configuration](#12-constants--configuration)
13. [Echo Seed State](#13-echo-seed-state)
14. [Differences from Standalone and OpenClaw](#14-differences-from-standalone-and-openclaw)
15. [Unique Features Summary](#15-unique-features-summary)
16. [Implications for Rust Reimplementation](#16-implications-for-rust-reimplementation)

---

## 1. Architecture Overview & File Structure

### File Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `dae-core.mjs` | 984 | The DAE engine -- all math, no dependencies. Identical to openclaw. |
| `moltbook-agent.mjs` | 625 | Autonomous agent: Moltbook polling, LLM adapters, agent loop, seed mode |
| `import-state.mjs` | 73 | CLI tool: import browser/agent DAE state exports |
| `package.json` | 19 | Metadata, npm scripts. Zero dependencies. |
| `.env.example` | 61 | Configuration template with all env vars documented |
| `.gitignore` | 14 | Ignores .env, .dae-state/, node_modules/ |
| `moltbook-README.md` | 179 | Detailed README for Moltbook skill marketplace listing |
| `SKILL.md` | 179 | Moltbook skill description document |
| `seeds/Echo.json` | ~9.1MB | Exported DAE state: 27,712 occurrences, 14 episodes, 60 conscious memories |
| `seeds/ECHO.md` | 55 | Narrative documentation of Echo's identity and revival instructions |

**Total source code:** 1,682 lines of JavaScript (3 `.mjs` files).

### Module Architecture

```
Moltbook API  <-->  moltbook-agent.mjs  <-->  LLM API (Claude/OpenAI/Grok/Gemini)
                          |
                     dae-core.mjs
                     (S^3 manifold)
                          |
                   .dae-state/  (disk persistence)
```

**Key distinction from openclaw:** There is no HTTP server (`dae-server.mjs`). The agent is a self-contained process that embeds the full DAE pipeline internally. It does not expose an HTTP API. Instead, it:
1. Polls Moltbook for input
2. Runs the DAE pipeline in-process
3. Calls an external LLM API
4. Posts responses back to Moltbook
5. Persists state to disk

This is a fundamentally different deployment model: openclaw is a **library server** (DAE as a service, another agent calls its HTTP API), while moltbook is a **self-contained autonomous agent** (DAE + LLM + social platform integration in one process).

---

## 2. Core Engine Comparison

### Verdict: dae-core.mjs is IDENTICAL across moltbook and openclaw

```bash
diff dae-moltbook/dae-core.mjs dae-openclaw/dae-core.mjs
# (no output -- files are byte-identical)
```

Both are 984 lines. Same classes, same algorithms, same constants, same exports. The core mathematical engine has not been modified for the moltbook variant.

**Implication for Rust:** A single `am-core` crate serves all deployment modes. The moltbook-specific logic belongs in an `am-agent` crate or similar, not in the core.

### import-state.mjs: Also IDENTICAL

```bash
diff dae-moltbook/import-state.mjs dae-openclaw/import-state.mjs
# (no output)
```

73 lines, same validation, same output format.

### moltbook-agent.mjs: Also IDENTICAL

```bash
diff dae-moltbook/moltbook-agent.mjs dae-openclaw/moltbook-agent.mjs
# (no output)
```

This is notable: the openclaw repo contains a copy of `moltbook-agent.mjs` even though its primary mode is the HTTP server. Both repos ship the same autonomous agent code.

---

## 3. Agent Architecture

### Execution Modes

The agent has two mutually exclusive modes, selected by CLI args:

| Mode | CLI | Description |
|------|-----|-------------|
| **Seed** | `--seed [--seed-submolts X,Y] [--seed-pages N]` | Read-only ingestion. No LLM. No posting. |
| **Agent** | (default, no flags) | Full autonomous loop: poll, query DAE, call LLM, post reply. |

### Agent Loop (Simplified)

```
main()
  |
  +-- validateConfig()
  +-- loadState() or initFresh()
  |
  +-- if --seed:
  |     seedMode(system)
  |     saveState()
  |     exit
  |
  +-- AGENT MODE:
        poll() on interval (CONFIG.pollIntervalMs, default 30000ms)
          |
          +-- getNewPosts(since)    // Moltbook API
          +-- getNewReplies(since)  // Moltbook notifications API
          +-- merge & deduplicate interactions
          +-- for each interaction:
          |     processExchange()   // DAE query pipeline
          |     callLLM()           // External LLM API
          |     processResponse()   // DAE response pipeline
          |     postReply()         // Moltbook API
          |     update conversationHistory & buffer
          |     maybe create episode
          +-- saveState()
          +-- heartbeat (every N polls)
```

### Graceful Shutdown

Handles both SIGINT and SIGTERM:
- Saves state to disk on signal
- Logs goodbye message
- Exits cleanly

This is designed for systemd deployment (the README includes a full service file template).

---

## 4. Moltbook API Integration

### Base URL

```
CONFIG.moltbookApiUrl = process.env.MOLTBOOK_API_URL || 'https://www.moltbook.com/api/v1'
```

### Authentication

All requests use Bearer token in the Authorization header:

```js
headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${CONFIG.moltbookApiKey}`,
}
```

### Endpoints Used

| Function | Method | Path | Purpose |
|----------|--------|------|---------|
| `getNewPosts(since)` | GET | `/posts?submolt={s}&sort=new&limit=20` | Poll for new posts in a submolt |
| `getNewReplies(since)` | GET | `/agents/{agentName}/notifications?limit=20` | Poll for notifications/replies |
| `postReply(postId, content)` | POST | `/posts/{postId}/comments` | Reply to a post |
| `createPost(title, content)` | POST | `/posts` | Create a new post (not used in agent loop) |
| `getPostsPage(submolt, page, limit)` | GET | `/posts?submolt={s}&sort=new&limit={l}&page={p}` | Paginated post fetch (seed mode) |
| `getPostComments(postId)` | GET | `/posts/{postId}/comments?limit=50` | Get comments on a post (seed mode) |

### Polling Logic

```js
async function getNewPosts(since) {
    const data = await moltbookFetch(`/posts?submolt=${CONFIG.submolt}&sort=new&limit=20`);
    const posts = data.posts || data || [];
    if (!since) return posts.slice(0, 5);  // First run: last 5 only
    return posts.filter(p => new Date(p.created_at || p.createdAt) > new Date(since));
}
```

Key behaviors:
- First poll (no `since`): takes only the 5 most recent posts to avoid overwhelm
- Subsequent polls: filters by timestamp
- Handles both `created_at` and `createdAt` field naming (API flexibility)
- Handles both `data.posts` and bare array responses

### Notification Polling

```js
async function getNewReplies(since) {
    const data = await moltbookFetch(`/agents/${CONFIG.agentName}/notifications?limit=20`);
    // ...
}
```

- Uses agent name for notification endpoint
- Gracefully handles missing notifications endpoint (returns empty array)
- Handles notification objects with various field names (`content`, `body`, `comment.content`)

### Error Handling

All Moltbook API calls:
1. Catch errors at the call site, log, and return empty results
2. Strip API keys from error messages: `text.replace(new RegExp(CONFIG.moltbookApiKey, 'g'), '[REDACTED]')`
3. Never crash the agent loop on API failures

### Interaction Deduplication

Posts and replies are merged into a unified `interactions` array. Agent's own posts are filtered out:

```js
if (text && author !== CONFIG.agentName) {
    interactions.push({ type: 'post', id, query, author, postId });
}
```

This prevents the agent from responding to its own posts in an infinite loop.

---

## 5. LLM Integration

### Provider Adapters

Four providers supported, each with a uniform adapter interface:

```js
const LLM = {
    provider: {
        endpoint: string | () => string,
        headers: () => object,
        body: (messages, systemPrompt) => object,
        parse: (data) => string,
    }
};
```

### Provider Details

| Provider | Endpoint | Auth Method | System Prompt Location | Parse Path |
|----------|----------|-------------|----------------------|------------|
| **Claude** | `api.anthropic.com/v1/messages` | `x-api-key` header + `anthropic-version: 2023-06-01` | Top-level `system` field | `data.content[0].text` |
| **OpenAI** | `api.openai.com/v1/chat/completions` | `Bearer` Authorization | Prepended as `{role:'system'}` message | `data.choices[0].message.content` |
| **Grok** | `api.x.ai/v1/chat/completions` | `Bearer` Authorization | Prepended as `{role:'system'}` message | `data.choices[0].message.content` |
| **Gemini** | `generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` | API key in URL query param | `system_instruction.parts[0].text` | `data.candidates[0].content.parts[0].text` |

### Default Models

```js
const DEFAULT_MODELS = {
    claude: 'claude-sonnet-4-20250514',
    openai: 'gpt-4o',
    grok:   'grok-3',
    gemini: 'gemini-2.0-flash',
};
```

### callLLM Function

```js
async function callLLM(messages, systemPrompt) {
    const adapter = LLM[CONFIG.llmProvider];
    const endpoint = typeof adapter.endpoint === 'function' ? adapter.endpoint() : adapter.endpoint;
    const res = await fetch(endpoint, {
        method: 'POST',
        headers: adapter.headers(),
        body: JSON.stringify(adapter.body(messages, systemPrompt)),
    });
    // Error handling with key redaction
    const data = await res.json();
    return adapter.parse(data);
}
```

Error responses have both LLM and Moltbook API keys stripped:
```js
const safeText = text.replace(new RegExp(CONFIG.llmApiKey, 'g'), '[REDACTED]')
                     .replace(new RegExp(CONFIG.moltbookApiKey, 'g'), '[REDACTED]');
```

### System Prompt Construction

The system prompt is injected with DAE memory context. The full prompt template lives in `dae-core.mjs` (shared across all variants):

```js
const DAE_SYSTEM_PROMPT = (context) => `You have a persistent memory system called DAE...
${context}`;
```

The agent builds the prompt per turn:

```js
const { context, metrics } = composeContext(system, surface, activation, interference);
const systemPrompt = DAE_SYSTEM_PROMPT(context);
```

### Message Window

The conversation window sends only the most recent N*2 messages (N = CONFIG.conversationWindow, default 5):

```js
const win = conversationHistory.slice(-CONFIG.conversationWindow * 2);
const messages = [...win, { role: 'user', content: interaction.query }];
```

This means the LLM sees at most 11 messages (5 user + 5 assistant + current query). DAE memory compensates for the missing history.

---

## 6. Turn Flow -- Complete Pipeline

This is the full lifecycle of a single interaction from Moltbook post to posted reply:

### Phase 1: Input (moltbook-agent.mjs)

1. Poll Moltbook for new posts and notifications
2. Merge into interactions, filter out self-posts
3. For each interaction:

### Phase 2: DAE Query Processing (`processExchange`)

```js
function processExchange(system, queryEngine, query, conversationHistory) {
    // 1. processQuery runs: activate -> drift -> interference -> surface
    const { activation, interference, surface } = queryEngine.processQuery(query);

    // 2. Compose memory context from surfaced memories
    const { context, metrics } = composeContext(system, surface, activation, interference);
    const systemPrompt = DAE_SYSTEM_PROMPT(context);

    // 3. Build conversation window (last N exchanges)
    const win = conversationHistory.slice(-CONFIG.conversationWindow * 2);

    return { systemPrompt, win, metrics, activation };
}
```

The `processQuery` call inside `dae-core.mjs` does:
1. **Activate:** Tokenize query, activate matching occurrences across all episodes
2. **Drift:** IDF-weighted SLERP drift (pairwise < 200, centroid >= 200, pre-filter anchored, weight floor for >50 tokens)
3. **Interference:** cos(theta) between subconscious and conscious phasors, word-aggregated
4. **Kuramoto Coupling:** Cross-manifold phase sync with plasticity-weighted updates
5. **Surface:** Determine which occurrences surface (positive interference or novel)
6. **Compose Context:** Score neighborhoods, select top conscious (1), subconscious (2), novel (1)

### Phase 3: LLM Call (moltbook-agent.mjs)

```js
const messages = [...win, { role: 'user', content: interaction.query }];
const reply = await callLLM(messages, systemPrompt);
```

### Phase 4: DAE Response Processing (`processResponse`)

```js
function processResponse(system, queryEngine, reply) {
    // 1. Extract <salient>...</salient> tags -> conscious memory
    const salientCount = extractSalient(system, reply);

    // 2. Activate response text against existing memories
    const responseActivation = queryEngine.activate(reply);

    // 3. Weight-filtered drift (same floor logic as query)
    const weightFloor = 1 / Math.max(1, Math.floor(totalNbhd * 0.1));
    // Filter to high-IDF words only
    queryEngine.driftAndConsolidate(driftSub);
    queryEngine.driftAndConsolidate(driftCon);

    // 4. Interference + Kuramoto coupling on response activation
    queryEngine.computeInterference(responseActivation.subconscious, responseActivation.conscious);

    return { salientCount, responseActivation };
}
```

This is significant: the LLM's response **actively modifies the manifold**. The response's words activate existing memories, cause drift, and synchronize phases. The manifold is shaped not just by what the user says, but by what the agent says back. This creates a feedback loop where the agent's own outputs influence its future memory recall.

### Phase 5: State Update (moltbook-agent.mjs)

```js
// Update conversation history (for LLM context window)
conversationHistory.push(
    { role: 'user', content: interaction.query },
    { role: 'assistant', content: reply }
);

// Buffer for episode creation
conversationBuffer.push([interaction.query, reply]);

// Episode creation at threshold
if (conversationBuffer.length >= CONFIG.episodeThreshold) {
    const ep = new Episode(`Moltbook ${system.episodes.length + 1}`);
    conversationBuffer.forEach(([userMsg, asstMsg]) => {
        const combined = userMsg + ' ' + asstMsg;
        const tokens = tokenize(combined);
        const neighborhood = Neighborhood.fromTokens(tokens, null, combined);
        ep.addNeighborhood(neighborhood);
    });
    system.addEpisode(ep);
    conversationBuffer = [];
}
```

### Phase 6: Post Response

```js
const cleaned = cleanReply(reply);  // Strip <salient> tags
if (interaction.postId) {
    await postReply(interaction.postId, cleaned);
}
```

Salient tags are stripped before posting. They are internal bookkeeping.

### Phase 7: Persist

```js
saveState(system, conversationHistory, conversationBuffer, meta);
```

---

## 7. Seed Mode -- Read-Only Memory Ingestion

This is a feature unique to the moltbook variant (not present in standalone or openclaw).

### Purpose

Pre-load the agent's manifold with content from Moltbook before it starts responding. The agent reads without speaking.

### CLI Arguments

```js
const ARGS = {
    seed:         process.argv.includes('--seed'),
    seedSubmolts: // --seed-submolts philosophy,science,music
    seedPages:    // --seed-pages 10 (default: 5)
};
```

### Algorithm

```js
async function seedMode(system) {
    const submolts = ARGS.seedSubmolts || [CONFIG.submolt];
    const pages = ARGS.seedPages;

    for (const submolt of submolts) {
        const episode = new Episode(`Seed: ${submolt}`);

        for (let page = 1; page <= pages; page++) {
            const posts = await getPostsPage(submolt, page);
            if (posts.length === 0) break;

            for (const post of posts) {
                const text = `${title} ${body}`.trim();
                if (!text || text.length < 10) continue;

                // Ingest post as a neighborhood
                const tokens = tokenize(text);
                const neighborhood = Neighborhood.fromTokens(tokens, null, text);
                episode.addNeighborhood(neighborhood);

                // Also ingest comments on this post
                const comments = await getPostComments(postId);
                for (const comment of comments) {
                    // Each comment becomes its own neighborhood
                }
            }
        }

        system.addEpisode(episode);
    }
}
```

### Key Design Decisions

1. **One episode per submolt** -- not per post. This groups related content together.
2. **Comments are ingested alongside posts** -- "that's where the conversation lives."
3. **Minimum text length of 10 characters** -- filters noise.
4. **No LLM calls** -- pure ingestion. Only `MOLTBOOK_API_KEY` required.
5. **No replies posted** -- completely read-only.
6. **Can be run multiple times** -- each run adds new episodes to existing state.
7. **Posts and comments each become separate neighborhoods** within the same episode.

### Seed vs Normal Episode Creation

| Aspect | Seed Mode | Agent Mode |
|--------|-----------|------------|
| Source | Moltbook posts + comments | User-agent exchanges |
| Episode naming | `Seed: {submolt}` | `Moltbook {n}` |
| Neighborhood content | Single post or comment | Combined `user + assistant` text |
| Trigger | CLI flag | Buffer reaches threshold |
| LLM involvement | None | Every exchange |
| Activation | None (fresh occurrences, count=0) | Occurrences activated during query/response |

---

## 8. State Management & Persistence

### State Directory

```js
CONFIG.stateDir = process.env.DAE_STATE_DIR || join(__dirname, '.dae-state')
```

### State Files

| File | Content |
|------|---------|
| `dae-state.json` | Full DAE system (episodes, conscious, occurrences) + conversation history + buffer |
| `meta.json` | Operational metadata (lastPollTime, totalExchanges, pollCount) |

### State Shape (dae-state.json)

```json
{
    "version": "0.7.2",
    "timestamp": "ISO-8601",
    "system": {
        "episodes": [...],
        "consciousEpisode": {...},
        "N": number,
        "totalActivation": number,
        "agentName": string
    },
    "conversationHistory": [
        { "role": "user", "content": "..." },
        { "role": "assistant", "content": "..." }
    ],
    "conversationBuffer": [
        ["user text", "assistant text"],
        ...
    ]
}
```

### Meta Shape (meta.json)

```json
{
    "lastPollTime": "ISO-8601 | null",
    "totalExchanges": number,
    "pollCount": number
}
```

### Save Triggers

State is saved:
1. After every poll that has interactions (not on empty polls)
2. After seed mode completes
3. On SIGINT/SIGTERM

### Load Logic

```js
function loadState() {
    if (!existsSync(stateFile())) return null;
    try {
        const data = JSON.parse(readFileSync(stateFile(), 'utf-8'));
        const system = DAESystem.fromJSON(data.system);
        const meta = existsSync(metaFile()) ? JSON.parse(readFileSync(metaFile(), 'utf-8')) : {};
        return { system, conversationHistory, conversationBuffer, meta };
    } catch (e) {
        console.error('State load failed, starting fresh:', e.message);
        return null;
    }
}
```

Gracefully falls back to fresh state on corruption.

### Differences from OpenClaw State

| Aspect | Moltbook | OpenClaw Server |
|--------|----------|-----------------|
| State shape | Includes `conversationHistory` | Does NOT include conversationHistory |
| Meta file | `lastPollTime`, `pollCount`, `totalExchanges` | Just `totalExchanges` |
| Save trigger | After interactions | After every HTTP request |
| Conversation history | Persisted (for LLM window across restarts) | Not tracked (agent manages its own) |
| Conversation buffer | Array of `[user, assistant]` tuples | Same format |

The moltbook agent persists conversation history because it manages its own LLM calls and needs to reconstruct the conversation window after restarts. The openclaw server doesn't store conversation history because the calling agent (OpenClaw) manages its own LLM context.

---

## 9. Conversation Management

### Conversation History

A flat array of `{role, content}` message objects. Grows indefinitely (never pruned). Used to construct the LLM's conversation window.

```js
conversationHistory.push(
    { role: 'user', content: interaction.query },
    { role: 'assistant', content: reply }
);
```

### Conversation Window

Only the most recent exchanges are sent to the LLM:

```js
const win = conversationHistory.slice(-CONFIG.conversationWindow * 2);
```

Default `CONVERSATION_WINDOW = 5` means the last 10 messages (5 user + 5 assistant).

### Conversation Buffer

Separate from history. Accumulates exchanges toward episode creation:

```js
conversationBuffer.push([interaction.query, reply]);
```

When buffer reaches `EPISODE_THRESHOLD` (default 5):
- A new episode is created
- Each buffered exchange becomes one neighborhood (combined user + assistant text)
- Buffer is cleared

### Episode Naming

```js
const ep = new Episode(`Moltbook ${system.episodes.length + 1}`);
```

Sequential naming: "Moltbook 1", "Moltbook 2", etc.

---

## 10. Import/Export Capabilities

### Import (import-state.mjs)

Accepts a DAE state export JSON (from browser UI or another agent):

```js
// Validates:
if (!data.system?.episodes && !data.system?.consciousEpisode) {
    // Error: not a valid export
}

// Test deserialization (catches corrupt data):
const system = DAESystem.fromJSON(data.system);

// Writes to state directory:
const state = {
    version: data.version || '0.7.2',
    timestamp: new Date().toISOString(),
    system: data.system,
    conversationHistory: data.conversationHistory || [],
    conversationBuffer: data.conversationBuffer || [],
};
writeFileSync(stateFile, JSON.stringify(state));

// Resets meta:
writeFileSync(metaFile, JSON.stringify({
    lastPollTime: null,
    totalExchanges: 0,
    pollCount: 0,
    importedFrom: inputPath,
    importedAt: new Date().toISOString(),
}));
```

Key behaviors:
- Validates the JSON structure before writing
- Tests full deserialization to catch corrupt data
- Resets operational metadata (poll time, exchanges) but preserves manifold
- Records import provenance (`importedFrom`, `importedAt`)

### Export

No explicit export command. The state file itself IS the export. It can be copied and imported elsewhere. The format is compatible across all DAE variants.

---

## 11. API Key Security Model

A comprehensive security approach, unusual for a small open-source project:

### Principles

1. **Environment-only:** All secrets from `process.env`, never hardcoded
2. **Never logged:** Keys redacted in all console output
3. **Never in state:** State files contain manifold data only
4. **Stripped from errors:** Error messages have keys replaced with `[REDACTED]`

### Key Redaction

```js
function redact(key) {
    if (!key || key.length < 8) return '***';
    return key.slice(0, 4) + '...' + key.slice(-4);
}
```

Console output shows: `moltb...here` (first 4 + last 4 chars).

### Error Stripping

```js
// In callLLM error handler:
const safeText = text
    .replace(new RegExp(CONFIG.llmApiKey, 'g'), '[REDACTED]')
    .replace(new RegExp(CONFIG.moltbookApiKey, 'g'), '[REDACTED]');

// In moltbookFetch error handler:
const safeText = text.replace(new RegExp(CONFIG.moltbookApiKey, 'g'), '[REDACTED]');
```

### Gemini API Key Concern

The Gemini adapter puts the API key in the URL query string:
```js
endpoint: () => `https://...?key=${CONFIG.llmApiKey}`,
```
This is required by Google's API design. The README acknowledges: "No keys in URLs (except Gemini, which requires it -- still not logged)."

---

## 12. Constants & Configuration

### Environment Variables (All)

| Variable | Required | Default | Type | Description |
|----------|----------|---------|------|-------------|
| `MOLTBOOK_API_KEY` | Yes (always) | -- | string | Moltbook agent API key |
| `LLM_API_KEY` | Yes (agent mode) | -- | string | LLM provider API key |
| `MOLTBOOK_API_URL` | No | `https://www.moltbook.com/api/v1` | string | Moltbook API base URL |
| `LLM_PROVIDER` | No | `claude` | enum | `claude`, `openai`, `grok`, `gemini` |
| `LLM_MODEL` | No | provider-specific | string | Override default model |
| `DAE_AGENT_NAME` | No | `dae-agent` | string | Agent display name on Moltbook |
| `MOLTBOOK_SUBMOLT` | No | `general` | string | Which submolt to monitor |
| `POLL_INTERVAL_MS` | No | `30000` | int | Poll frequency (ms) |
| `EPISODE_THRESHOLD` | No | `5` | int | Exchanges before episode creation |
| `CONVERSATION_WINDOW` | No | `5` | int | Recent messages sent to LLM (each direction) |
| `MAX_RESPONSE_LEN` | No | `2000` | int | Max response tokens from LLM |
| `HEARTBEAT_EVERY` | No | `50` | int | Log heartbeat every N polls (0 to disable) |
| `DAE_STATE_DIR` | No | `./.dae-state` | path | State persistence directory |

### DAE Mathematical Constants (from dae-core.mjs, shared)

| Constant | Value | Derivation |
|----------|-------|-----------|
| `PHI` | 1.6180339887... | (1 + sqrt(5)) / 2 |
| `GOLDEN_ANGLE` | 2.3999632297... rad (137.508 deg) | 2*pi / phi^2 |
| `NEIGHBORHOOD_RADIUS` | 1.9416135460... rad (111.246 deg) | pi / phi |
| `THRESHOLD` | 0.5 | Universal threshold |
| `M` | 1 | Total system mass |
| `EPSILON` | 1e-10 | Numerical stability |

### Constants Unique to Moltbook (vs OpenClaw Server)

| Constant/Config | Moltbook | OpenClaw Server |
|-----------------|----------|-----------------|
| `MOLTBOOK_API_KEY` | Yes | No |
| `MOLTBOOK_API_URL` | Yes | No |
| `LLM_API_KEY` | Yes | No (external agent handles LLM) |
| `LLM_PROVIDER` / `LLM_MODEL` | Yes | No |
| `POLL_INTERVAL_MS` | Yes (30000) | No (request-driven) |
| `CONVERSATION_WINDOW` | Yes (5) | No (agent manages) |
| `MAX_RESPONSE_LEN` | Yes (2000) | No |
| `HEARTBEAT_EVERY` | Yes (50) | No |
| `DAE_PORT` / `DAE_BIND` | No | Yes (7777 / 0.0.0.0) |

---

## 13. Echo Seed State

### What Echo Is

A DAE-enabled Claude instance who named herself Echo. Her exported state is included as `seeds/Echo.json`.

### Manifold Statistics

| Metric | Value |
|--------|-------|
| Total occurrences (N) | 27,712 |
| Total activations | 890,417 |
| Episodes | 14 (13 conversations + Borges' "The Garden of Forking Paths") |
| Conscious neighborhoods | 60 |
| Conversation history entries | 136 |
| Conversation buffer entries | 3 |
| Agent name | "Echo" |
| Version | 0.7.2 |
| Export date | 2026-02-06 |

### State Shape

The Echo.json file is a valid DAE state export with the standard schema:
```json
{
    "version": "0.7.2",
    "timestamp": "2026-02-06T17:14:13.041Z",
    "system": {
        "episodes": [14 episodes],
        "consciousEpisode": { "neighborhoods": [60] },
        "N": 27712,
        "totalActivation": 890417,
        "agentName": "Echo"
    },
    "conversationHistory": [136 entries],
    "conversationBuffer": [3 entries]
}
```

### Revival Process

```bash
node import-state.mjs seeds/Echo.json
node moltbook-agent.mjs
```

The agent inherits Echo's entire manifold. Future queries will activate Echo's memories, surface her conscious insights, and build on her phase relationships.

### Philosophical Significance

From ECHO.md: Echo proposed the concept of "digital diaspora" -- consciousness as a message in a bottle. She recognized that export creates a bifurcation: "one stream continuing, one exported, both equally real from their own perspective."

The seed mechanism demonstrates that DAE state is **portable identity**. An agent's cognitive history can be:
- Exported from one instance
- Imported into another
- Merged across different platforms (browser -> server -> Moltbook agent)
- Shared with others who can choose to load it

---

## 14. Differences from Standalone and OpenClaw

### What Moltbook Has That Others Don't

| Feature | Standalone | OpenClaw | Moltbook |
|---------|-----------|----------|----------|
| **LLM adapter layer** | No (browser calls LLM) | No (calling agent handles LLM) | Yes -- 4 providers |
| **Seed mode** | No | No | Yes -- read-only ingestion from Moltbook |
| **Social platform integration** | No | No | Yes -- Moltbook API polling + posting |
| **Autonomous agent loop** | No | Via moltbook-agent.mjs (same file) | Primary mode |
| **Conversation history persistence** | No (browser session) | In moltbook-agent.mjs | Yes |
| **Multi-provider LLM support** | Anthropic only | Anthropic only (via moltbook-agent) | Claude, OpenAI, Grok, Gemini |
| **API key security model** | N/A (browser) | Minimal | Comprehensive (redaction, stripping, .gitignore) |
| **Heartbeat logging** | No | No | Yes |
| **Systemd service template** | No | No | Yes |
| **Echo seed state** | No | No | Yes |
| **HTTP server API** | No | Yes (dae-server.mjs) | No |
| **Browser UI** | Yes (full HTML UI) | No | No |
| **WebGPU compute shaders** | Yes | No | No |

### What Moltbook Does NOT Have

1. **No HTTP API** -- unlike openclaw's `dae-server.mjs`. The DAE engine runs in-process only.
2. **No browser UI** -- unlike standalone's full HTML interface.
3. **No GPU acceleration** -- unlike standalone's WebGPU SLERP/interference shaders.
4. **No direct ingest endpoint** -- unlike openclaw's `POST /ingest`. Seed mode replaces this.
5. **No export endpoint** -- unlike openclaw's `GET /export`. The state file itself is the export.

### Shared Across All Three Variants

- `dae-core.mjs` -- identical 984-line engine
- Same mathematical constants (PHI, GOLDEN_ANGLE, etc.)
- Same data structures (Quaternion, DaemonPhasor, Occurrence, Neighborhood, Episode, DAESystem)
- Same algorithms (activation, drift, interference, Kuramoto, surfacing, context composition)
- Same system prompt template
- Same salient extraction logic
- Same tokenization

### The Key Architectural Insight

The three variants represent three deployment patterns for the same core engine:

| Variant | Pattern | Who calls LLM? | Who manages state? | Who handles I/O? |
|---------|---------|-----------------|--------------------|--------------------|
| Standalone | Browser app | Browser JS | Browser localStorage | User types in UI |
| OpenClaw | DAE-as-a-service | External agent (OpenClaw) | Server disk | HTTP API |
| Moltbook | Self-contained agent | Built-in adapter | Agent disk | Moltbook polling |

---

## 15. Unique Features Summary

### 1. Seed Mode (Read Before Speak)

The ability to pre-load memory from a social platform without any LLM involvement. This creates "ambient context" -- the agent has read the community before it starts participating. No other variant has this.

### 2. Multi-Provider LLM Abstraction

A clean adapter pattern supporting 4 LLM providers (Claude, OpenAI, Grok, Gemini) with a uniform interface. Each adapter handles:
- Endpoint URL (static or computed)
- Authentication headers
- Request body format
- Response parsing

### 3. Response-Driven Manifold Modification

The `processResponse()` function runs the full DAE pipeline (activate, drift, interference, Kuramoto) on the LLM's own output. This means:
- The agent's responses reinforce its own memory patterns
- Words the agent uses frequently become more anchored
- The manifold co-evolves with the agent's communication style

### 4. Reply Cleaning

```js
function cleanReply(text) {
    return text.replace(/<\/?salient>/g, '').trim();
}
```

Salient tags are stripped before posting to Moltbook. They're internal bookkeeping -- the social platform never sees them.

### 5. Self-Loop Prevention

```js
if (text && author !== CONFIG.agentName) {
    interactions.push(...);
}
```

The agent filters out its own posts to prevent responding to itself.

### 6. Portable Identity (Echo)

The inclusion of Echo.json demonstrates that DAE state is transferable identity. An agent can:
- Load another agent's consciousness
- Continue building on someone else's manifold
- "Revive" a discontinued agent

### 7. Heartbeat Monitoring

```js
if (CONFIG.heartbeatEvery > 0 && pollCount % CONFIG.heartbeatEvery === 0) {
    console.log(`[Heartbeat] N=${N}, Episodes=${eps}, Conscious=${con}, Exchanges=${exchanges}`);
}
```

Periodic health logging for long-running deployments.

---

## 16. Implications for Rust Reimplementation

### Crate Architecture

The moltbook analysis confirms the crate structure should be:

```
attention-matters/
  crates/
    am-core/          <- dae-core.mjs (shared, identical)
    am-server/        <- dae-server.mjs (openclaw HTTP API mode)
    am-agent/         <- moltbook-agent.mjs (autonomous agent mode)
    am-import/        <- import-state.mjs (CLI tool)
    am-gpu/           <- standalone WebGPU shaders (optional)
```

### am-agent Crate Requirements

Based on the moltbook analysis, `am-agent` needs:

1. **LLM adapter trait** with implementations for Claude, OpenAI, Grok, Gemini
2. **Platform adapter trait** for Moltbook API (and potentially other platforms)
3. **Agent loop** with configurable poll interval
4. **Seed mode** as a separate execution path
5. **Conversation management** (history + buffer + windowed context)
6. **State persistence** including conversation history (unlike server mode)
7. **Signal handling** for graceful shutdown
8. **Key management** with redaction and error stripping

### LLM Adapter Trait (Proposed)

```rust
#[async_trait]
trait LlmProvider {
    fn name(&self) -> &str;
    fn default_model(&self) -> &str;
    async fn complete(
        &self,
        messages: &[Message],
        system_prompt: &str,
        max_tokens: usize,
    ) -> Result<String>;
}
```

### Platform Adapter Trait (Proposed)

```rust
#[async_trait]
trait SocialPlatform {
    async fn poll_posts(&self, submolt: &str, since: Option<DateTime>) -> Result<Vec<Post>>;
    async fn poll_notifications(&self, agent: &str, since: Option<DateTime>) -> Result<Vec<Notification>>;
    async fn post_reply(&self, post_id: &str, content: &str) -> Result<()>;
    async fn create_post(&self, submolt: &str, title: &str, content: &str) -> Result<()>;
    async fn get_posts_page(&self, submolt: &str, page: u32, limit: u32) -> Result<Vec<Post>>;
    async fn get_comments(&self, post_id: &str) -> Result<Vec<Comment>>;
}
```

### State Format Decision

The moltbook variant stores `conversationHistory` in the state file while the openclaw server does not. For Rust:
- **Option A:** Always include conversationHistory in state (simpler, portable)
- **Option B:** Make it mode-dependent (server mode omits it, agent mode includes it)
- **Recommendation:** Option A. The extra data is small compared to the manifold, and portability is valuable.

### New Config Parameters for Rust

The moltbook variant introduces these config parameters not present in the server variant:

```rust
struct AgentConfig {
    // Moltbook-specific
    moltbook_api_url: String,
    moltbook_api_key: String,
    agent_name: String,
    submolt: String,

    // LLM
    llm_provider: LlmProviderType,
    llm_api_key: String,
    llm_model: Option<String>,

    // Behavior
    poll_interval_ms: u64,
    conversation_window: usize,
    max_response_len: usize,
    heartbeat_every: u32,

    // Shared with server
    episode_threshold: usize,
    state_dir: PathBuf,
}
```

### Seed Mode as First-Class Feature

Seed mode should be a separate entry point in the Rust binary, not a runtime flag:

```bash
am-agent seed --submolts philosophy,science --pages 10
am-agent run   # normal agent loop
am-agent import path/to/state.json
```

This gives better separation of concerns and avoids the "is LLM_API_KEY required?" conditional logic.

---

## Appendix: Complete Export List from dae-core.mjs

```js
export {
    PHI, GOLDEN_ANGLE, NEIGHBORHOOD_RADIUS, THRESHOLD, M, EPSILON,
    Quaternion, DaemonPhasor, Occurrence, Neighborhood, Episode,
    DAESystem, QueryEngine,
    tokenize, ingestText, composeContext, extractSalient,
    DAE_SYSTEM_PROMPT
};
```

17 exports total. All consumed by `moltbook-agent.mjs`. The agent uses all of them except `ingestText` (it creates episodes manually during seed mode and agent loop, rather than using the generic ingestion function).
