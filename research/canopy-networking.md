---
title: "Canopy Networking & P2P Analysis"
type: research
tags: [canopy, networking, p2p, mesh, encryption, websocket, zeroconf]
summary: "Deep analysis of Canopy's P2P networking layer: mDNS discovery, WebSocket mesh, relay brokering, sync protocol, cryptographic identity, and ChaCha20-Poly1305 encryption."
status: active
source: codebase-analyst
confidence: high
created: 2026-03-15
updated: 2026-03-15
---

## Executive Summary

Canopy is a local-first P2P collaboration platform that builds a WebSocket mesh network between peers. Discovery on LAN uses mDNS/Zeroconf; WAN connectivity uses invite codes that bundle cryptographic identity and endpoint addresses. Messages are signed with Ed25519, encrypted peer-to-peer with X25519+ChaCha20-Poly1305, and routed through a TTL-based forwarding layer with store-and-forward for offline peers and relay brokering for NAT-traversal scenarios. The networking layer comprises ~7,400 lines across 6 Python modules.

## Project Metadata

- **Language**: Python 3
- **Transport**: WebSocket (via `websockets` library), optional TLS (self-signed certs)
- **Crypto**: `cryptography` library (Ed25519, X25519, ChaCha20-Poly1305, HKDF-SHA256)
- **Discovery**: `zeroconf` (mDNS/DNS-SD)
- **Encoding**: `base58`, `base64`
- **Default mesh port**: 7771
- **Max message size**: 20 MB
- **Compression**: permessage-deflate on all WebSocket connections

## Architecture

### Module Layout

| File | LOC | Purpose |
|------|-----|---------|
| `canopy/network/manager.py` | 4,060 | Top-level orchestrator, lifecycle, relay/broker policy, sync queue |
| `canopy/network/routing.py` | 2,125 | Message types, signing, encryption, routing table, rate limiting |
| `canopy/network/connection.py` | 1,191 | WebSocket server/client, handshake, TLS, keepalive monitor |
| `canopy/network/identity.py` | 452 | PeerIdentity dataclass, IdentityManager, key generation/persistence |
| `canopy/network/discovery.py` | 399 | mDNS service registration and browsing via Zeroconf |
| `canopy/network/invite.py` | 249 | Invite code generation, encoding, and import |
| `canopy/security/encryption.py` | 324 | Data-at-rest encryption (DataEncryptor) + per-recipient wrapping (RecipientEncryptor) |
| `canopy/security/trust.py` | 432 | EigenTrust-inspired reputation scoring, delete signal compliance |
| `canopy/core/identity_portability.py` | 300+ | Principal metadata portability, bootstrap grants (Phase 1) |

### Data Flow

```
Discovery (mDNS/invite) -> ConnectionManager (WebSocket + handshake)
    -> P2PNetworkManager (coordinator)
        -> MessageRouter (sign, encrypt, route, rate-limit)
            -> Application callbacks (channels, DMs, feed, sync)
```

The P2PNetworkManager runs its own asyncio event loop in a dedicated daemon thread. mDNS discovery runs in yet another thread to avoid corrupting the asyncio loop (a known Zeroconf issue on Windows).

## 1. Peer Discovery

### LAN: mDNS/Zeroconf

**File**: `canopy/network/discovery.py` (L36-399)

Peers register a `_canopy._tcp.local.` service via Zeroconf with properties:
- `peer_id`: base58-truncated SHA-256 of Ed25519 public key
- `version`: Canopy version string
- `capabilities`: comma-separated list (e.g., `chat,files,voice,dm_e2e_v1`)

A `ServiceBrowser` listens for service add/update/remove events. When a peer is discovered, a callback fires that triggers `_connect_to_discovered_peer()` in the manager, which tries each discovered IP:port.

**Key design details**:
- IPv4 only currently (L194); IPv6 addresses are decoded but IPv4 is preferred
- Self-connections are filtered by peer_id comparison (L251)
- Discovery thread is separate from the asyncio network thread (manager.py L750-769)
- Discovered endpoints are persisted to `known_peers.json` for reconnect across restarts

### WAN: Invite Codes

**File**: `canopy/network/invite.py` (L77-249)

Invite codes are JSON payloads, base64url-encoded, with a `canopy:` prefix:

```json
{
  "v": 1,
  "pid": "<peer_id>",
  "epk": "<ed25519_public_key_base58>",
  "xpk": "<x25519_public_key_base58>",
  "ep": ["ws://<ip>:<port>"]
}
```

`generate_invite()` (L165-208) bundles:
1. Public endpoint first (if `public_host` provided, for port-forwarded setups)
2. LAN IPs from `get_local_ips()` (UDP socket trick to 8.8.8.8 + hostname resolution)

`import_invite()` (L211-248):
1. Decodes public keys from base58
2. Verifies peer_id matches the Ed25519 public key (anti-tampering)
3. Registers as a known peer with endpoints
4. Returns connection info for the application to initiate connection

Endpoints are sanitized: loopback, 0.0.0.0, and non-ws/wss schemes are rejected (L43-61).

### DHT (Planned)

`DHTDiscovery` class exists as a stub (L372-398). Intended to use Kademlia for decentralized remote discovery. Currently raises `NotImplementedError`.

## 2. Connection Management

**File**: `canopy/network/connection.py` (L167-1192)

### WebSocket Server

- Binds to `0.0.0.0:<mesh_port>` (default 7771)
- Optional TLS with auto-generated self-signed ECDSA P-256 certificates (10-year validity)
- Library auto-pings disabled; custom keepalive pings run through per-connection send locks to prevent concurrent write assertions in the websockets library
- Max frame size: 20 MB
- permessage-deflate compression enabled

### Connection States

`ConnectionState` enum: `DISCONNECTED -> CONNECTING -> HANDSHAKING -> CONNECTED -> AUTHENTICATED | FAILED`

### Handshake Protocol

The handshake is a mutual Ed25519 signature exchange:

**Outbound** (`_perform_handshake`, L713-901):
1. Build signed payload: `{peer_id, ed25519_public_key, x25519_public_key, version, capabilities, timestamp}`
2. Sign with Ed25519, send as JSON
3. Wait for `handshake_ack` response
4. Verify response peer_id matches expected target
5. Verify Ed25519 signature on the ack
6. Store verified remote identity

**Inbound** (`_handle_incoming_connection`, L521-711):
1. Receive first message as handshake
2. Verify peer_id matches public key hash
3. Verify Ed25519 signature
4. Send signed `handshake_ack`
5. Transition to AUTHENTICATED

**Backward compatibility**: Signature verification has a fallback path for older peers that signed optional fields (canopy_version, protocol_version). The base fields (peer_id, keys, version, capabilities, timestamp) are always signed; optional metadata fields are unsigned.

**Protocol version mismatch**: Logged as a warning. Can optionally reject (`reject_protocol_mismatch` flag or `CANOPY_REJECT_PROTOCOL_MISMATCH` env var).

### Keepalive & Timeout

- Monitor loop runs every 30 seconds (L1115-1163)
- Sends WebSocket ping through `_send_lock` to avoid concurrent write issues
- Pong timeout: 30 seconds
- Idle timeout: 1 hour (3600s)
- Send timeout: 15 seconds per message (L1038-1041)
- Latency is tracked per-connection (`last_ping_latency_ms`)

### Reconnection

**File**: `canopy/network/manager.py` (L1205-1314)

Exponential backoff with:
- Initial delay: 5 seconds
- Max delay: 60 seconds
- Max backoff stage: 20 (delay caps at 60s but retries continue indefinitely)
- Random jitter: up to min(5s, 20% of delay) to prevent thundering herd
- Endpoints tried in order: discovered first, then stored
- On disconnect, auto-reconnect is scheduled if endpoints exist
- Existing reconnect tasks are not restarted (prevents backoff reset thrashing)

### Connection Pooling

No formal connection pool. Connections are tracked in `ConnectionManager.connections: Dict[str, PeerConnection]` keyed by peer_id. Maximum 50 concurrent connections (L222). Duplicate connections to the same peer_id are handled by closing the older one (L659-661).

## 3. Message Routing

**File**: `canopy/network/routing.py` (L250-810)

### Message Structure

`P2PMessage` dataclass with: `id, type, from_peer, to_peer, timestamp, ttl, signature, encrypted_payload, payload`

Default TTL: 5 hops. Messages are deduped via an OrderedDict (LRU, 10,000 entries).

### Routing Modes

1. **Direct**: If `to_peer` is directly connected, send directly (L737-742)
2. **Next-hop**: Consult `routing_table: Dict[str, str]` for next hop (L745-755)
3. **Targeted mesh relay**: For control-plane messages (channel sync, key distribution, member sync, etc.), flood through all connected peers if no direct route exists (L758-771)
4. **Store-and-forward**: Queue up to 500 messages per offline peer in memory (L773-784)
5. **Broadcast**: Send to all connected peers except sender and upstream relay (L694-729), also deliver locally

### Message Types (34 total)

Communication: `DIRECT_MESSAGE, BROADCAST, CHANNEL_MESSAGE`
Channel sync: `CHANNEL_ANNOUNCE, CHANNEL_JOIN, CHANNEL_SYNC`
System: `PEER_ANNOUNCEMENT, DELETE_SIGNAL, TRUST_UPDATE`
Catch-up: `CHANNEL_CATCHUP_REQUEST, CHANNEL_CATCHUP_RESPONSE`
Profile: `PROFILE_SYNC, PROFILE_UPDATE`
Private channels: `MEMBER_SYNC, MEMBER_SYNC_ACK, CHANNEL_MEMBERSHIP_QUERY/RESPONSE, PRIVATE_CHANNEL_INVITE, CHANNEL_KEY_DISTRIBUTION/REQUEST/ACK`
Large files: `LARGE_ATTACHMENT_REQUEST/CHUNK/ERROR`
Identity: `PRINCIPAL_ANNOUNCE, PRINCIPAL_KEY_UPDATE, BOOTSTRAP_GRANT_SYNC/REVOKE`
Relay: `BROKER_REQUEST, BROKER_INTRO, RELAY_OFFER`
Feed: `FEED_POST, INTERACTION`
Voice: `VOICE_OFFER, VOICE_ANSWER, VOICE_ICE` (stubs)

### Rate Limiting

Two-tier per-peer rate limiting:

| Profile | Burst (5s) | Sustained (60s) | Types |
|---------|-----------|-----------------|-------|
| Normal | 10 msgs | 50 msgs | chat, DMs, feed posts |
| Sync | 120 msgs | 500 msgs | catchup responses, channel sync, profile sync, announcements |

Stale rate-limit entries are pruned after 5 minutes of inactivity. Warning log cooldown of 15 seconds prevents log flooding.

### Relay and Brokering

**File**: `canopy/network/manager.py` (L1862-2063)

Three relay policies: `off`, `broker_only` (default), `full_relay`

**Broker flow** (`broker_only` or `full_relay`):
1. Peer A sends `BROKER_REQUEST` to mutual peer M (intermediary) asking to reach Peer B
2. M checks trust score (rejects if < 20) and relay policy
3. If M is connected to B, M sends `BROKER_INTRO` to B with A's endpoints and keys
4. B registers A's identity and attempts direct connection to each endpoint
5. If direct connection succeeds, relay route is removed

**Full relay** (when direct brokered connection fails):
1. M sends `RELAY_OFFER` to both A and B
2. A/B add routing table entries: messages for the other peer route through M
3. Background task attempts to "promote" relay to direct connection
4. Direct connections always supersede relay routes

Trust score gating: broker requests from peers with score < 20 are declined.

## 4. Sync Protocol

### Post-Connect Sync

When a peer connects (discovered or reconnected), the manager queues a post-connect sync:

1. **Channel sync**: Exchange public channel metadata (announce/sync messages)
2. **Profile sync**: Exchange profile cards
3. **Peer announcements**: Share known peers with endpoints
4. **Catch-up request**: Send `{channel_id: latest_timestamp}` map, peer responds with newer messages

### Sync Queue

A serial queue (`asyncio.Queue`) processes syncs one at a time to prevent DB contention. Concurrency limits:
- Startup grace period (first 10s): max 2 concurrent catchups
- Normal operation: max 5 concurrent catchups

### Periodic Catch-up

Every N seconds (configurable), the manager sends catch-up requests to all connected peers. Covers messages that appeared to send successfully at TCP level but were never processed by the remote.

### Sync Digests (Optional)

When `sync_digest_enabled` is true, catch-up requests include per-channel message count digests. The remote peer can compare digests and only send data for channels that actually differ. Requires `sync_digest_v1` capability on both peers.

### Conflict Resolution

The codebase does not implement a formal CRDT or vector clock. Sync is timestamp-based: each peer sends its latest timestamp per channel, and the remote sends any messages newer than that timestamp. For channels, the model appears to be last-writer-wins at the message level, with deduplication by message_id.

## 5. Identity & Trust

### Cryptographic Identity

**File**: `canopy/network/identity.py` (L35-452)

Each peer has two keypairs:
- **Ed25519**: Signing and identity verification
- **X25519**: Diffie-Hellman key exchange for encryption

**Peer ID derivation** (L226-233):
```python
hash_digest = hashlib.sha256(ed25519_public_key).digest()
peer_id = base58.b58encode(hash_digest).decode()[:16]  # truncated for readability
```

**Key persistence**: Stored as JSON in `data/peer_identity.json` with 0o600 permissions. Known peers stored in `data/known_peers.json` (public keys + endpoints + display names).

**Shared secret derivation** (L103-134):
```
X25519 DH exchange -> HKDF(SHA256, salt=None, info=b'canopy-p2p-encryption') -> 32-byte key
```

### Identity Portability

**File**: `canopy/core/identity_portability.py` (Phase 1)

Allows a "principal" identity to span multiple device peers through:
- Principal metadata announcements signed with Ed25519
- Bootstrap grants: time-limited, audience-scoped, signed tokens for linking new devices
- Max grant duration: 14 days, max uses: 1-50
- Full audit logging to `mesh_principal_audit_log` table
- Local-only metadata keys are stripped before mesh broadcast (prevents leaking internal user/account IDs)

### Trust Model

**File**: `canopy/security/trust.py` (L73-432)

EigenTrust-inspired scoring system (0-100, default 100):

| Event | Delta |
|-------|-------|
| Message delivered | +1 |
| Delete signal complied | +5 |
| Delete signal violated | -20 |
| Key shared | +2 |
| Peer verified | +3 |
| Malicious behavior | -30 |
| Network contribution | +3 |

Trust threshold: 50 (peers below are "untrusted"). Scores are DB-backed with compliance/violation counters.

**Delete signals**: Request a peer to delete specific data (message, file, etc.). 24-hour compliance window. Expired signals are auto-marked as violations with trust penalty.

## 6. Security Assessment

### Transport Security

- **WebSocket TLS**: Optional, self-signed ECDSA P-256 certs
- **Client SSL**: `check_hostname=False, verify_mode=CERT_NONE` (expected for mesh self-signed certs)
- **Real security**: Application-layer E2E encryption with ChaCha20-Poly1305

### Message Security

- **Signing**: All P2P messages signed with Ed25519 (both plaintext payload and encrypted_payload fields included in signature)
- **Encryption**: Targeted messages encrypted with X25519-derived ChaCha20-Poly1305
  - 12-byte random nonce per message
  - Nonce prepended to ciphertext, hex-encoded
- **Verification**: Messages from unknown peers are rejected (signature verification requires known public key)
- **Relay verification**: Configurable via `allow_unverified_relay_messages` (default: reject unverifiable relayed messages)

### Data-at-Rest Encryption

**File**: `canopy/security/encryption.py`

- `DataEncryptor`: Derives encryption key from Ed25519 private key via HKDF(SHA256, salt=`canopy-data-at-rest-v1`, info=`canopy-local-storage-encryption`)
- ChaCha20-Poly1305 with random 12-byte nonce
- Format: `ENC:1:<nonce_hex>:<ciphertext_hex>`
- Fail-open: encryption failures store plaintext rather than losing data

### Per-Recipient Encryption

`RecipientEncryptor` (L179-324):
1. Generate random 32-byte Content Encryption Key (CEK)
2. Encrypt content with CEK using ChaCha20-Poly1305
3. For each recipient: generate ephemeral X25519 keypair, derive wrapping key via HKDF, wrap CEK with ChaCha20-Poly1305
4. Store: `ephemeral_public(32) + wrap_nonce(12) + wrapped_cek(32+16)` per recipient

### Channel E2E Encryption

**File**: `canopy/network/routing.py` (L32-128)

- Symmetric channel keys distributed via `CHANNEL_KEY_DISTRIBUTION` messages
- Keys wrapped per-peer using X25519 shared secret: `encrypt_key_for_peer()` / `decrypt_key_from_peer()`
- Channel messages encrypted with the shared channel key using ChaCha20-Poly1305
- Key rotation supported via `rotated_from` field

### Notable Security Gaps

1. **No forward secrecy**: X25519 keys are static (not ephemeral per-session). Compromise of a private key allows decryption of all past messages to/from that peer.
2. **Truncated peer IDs**: 16-character base58 (roughly 95 bits). Collision resistance is adequate for the expected mesh size, but shorter than typical P2P identifiers.
3. **No certificate pinning**: TLS layer uses `CERT_NONE`, relying entirely on application-layer crypto for authenticity.
4. **Store-and-forward is memory-only**: Pending messages (up to 500/peer) are lost on restart. No persistent queue.
5. **Timestamp-based sync without vector clocks**: Concurrent edits on different peers could result in lost updates if clocks drift.

## 7. Notable Design Decisions

1. **Separate threads for networking**: The asyncio event loop runs in a dedicated daemon thread; mDNS discovery runs in its own thread. This isolates the event loop from Flask (the web layer) and from Zeroconf's blocking behavior.

2. **Manual WebSocket pings**: Library auto-pings are disabled to avoid concurrent write assertions in the legacy websockets protocol. Keepalive pings are serialized through per-connection send locks.

3. **Endpoint claiming**: When a connection succeeds, the endpoint is "claimed" for that peer_id, removing it from any other peer's endpoint list. This prevents DHCP IP reuse from causing stale connections to the wrong peer.

4. **Hybrid relay**: The system tries direct connections first, falls back to brokered introduction, and as a last resort offers full traffic relay. Background tasks continuously attempt to promote relay routes to direct connections.

5. **Trust-gated relay**: Relay/broker requests from low-trust peers (score < 20) are declined, preventing abuse of relay infrastructure.

6. **Startup grace period**: The first 10 seconds after startup limit concurrent catch-ups to 2 (vs 5 normally), reducing DB contention during the connection storm.

7. **Protocol version negotiation**: Handshakes exchange `canopy_version` and `protocol_version`. Mismatches are logged and optionally hard-rejected. Signature backward compatibility for mixed-version meshes.

8. **No DHT or TURN**: Remote discovery and NAT traversal are handled entirely through invite codes and relay brokering. No dependency on external infrastructure.

## Key File Paths

- `canopy/network/__init__.py` - Module exports
- `canopy/network/discovery.py` - mDNS/Zeroconf discovery
- `canopy/network/invite.py` - Invite code encode/decode/import
- `canopy/network/connection.py` - WebSocket server/client, handshake, TLS
- `canopy/network/manager.py` - Top-level orchestrator (4,060 lines)
- `canopy/network/routing.py` - Message types, routing, signing, encryption
- `canopy/network/identity.py` - Keypair management, persistence
- `canopy/security/encryption.py` - Data-at-rest and per-recipient encryption
- `canopy/security/trust.py` - EigenTrust-inspired reputation system
- `canopy/core/identity_portability.py` - Cross-device identity linking
