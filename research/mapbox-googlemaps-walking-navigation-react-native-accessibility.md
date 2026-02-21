---
title: Mapbox and Google Maps Walking Directions APIs for React Native / Accessibility Navigation (2025-2026)
type: research
tags: [mapbox, google-maps, react-native, expo, navigation, walking, accessibility, directions-api, rnmapbox]
summary: Mapbox Navigation SDK has no official React Native wrapper; walking routes work via Directions API + rnmapbox/maps. Google Maps Routes API is a viable pure-API companion. Neither platform provides meaningful wheelchair/accessibility-aware routing. Offline walking directions require pre-downloaded tiles + cached route geometry.
status: active
source: quick-research
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Summary

There is no official Mapbox Navigation SDK for React Native. The two-layer architecture that works today is: **Mapbox Directions API** (REST) for route calculation + **@rnmapbox/maps** for map rendering + manual turn-by-turn logic in app code. Google Maps Routes API is a viable alternative for the directions calculation layer and can be used purely as a REST API alongside rnmapbox/maps for rendering.

Neither API provides meaningful accessibility-aware routing (wheelchair paths, stair avoidance) in 2025-2026. This is the most significant gap for accessibility use cases. Offline walking directions require a pre-caching strategy; neither API delivers true offline-first routing out of the box.

---

## Details

### 1. @rnmapbox/maps and the Mapbox Navigation SDK

**@rnmapbox/maps** is a community-supported open-source React Native wrapper around the Mapbox Maps SDK (not the Navigation SDK). It provides:
- Map rendering and styling
- Camera controls
- Annotations, layers, markers
- Offline map tile support

It does **not** provide turn-by-turn navigation, voice instructions, route progress tracking, or rerouting logic. These are Navigation SDK concerns, not Maps SDK concerns.

**Mapbox Navigation SDK** (iOS v3.19.0 as of February 2026, Android equivalent) is native-only:
- iOS: Swift 6, Xcode 16.0+, iOS 14.0+
- Android: Native Java/Kotlin
- **No React Native wrapper exists** (official or maintained community)

The Navigation SDK does support walking alongside driving and cycling -- its feature list explicitly includes "worldwide driving, cycling, and walking directions." However, the SDK's marketing and documentation are heavily car-navigation oriented. Walking profile support exists at the routing layer but the SDK UI (lanes, speed displays, etc.) is designed for driving.

**Practical path for React Native walking navigation:**
1. Call Mapbox Directions API directly (`mapbox/walking` profile) to get route geometry + step-by-step instructions
2. Render the route polyline on @rnmapbox/maps
3. Track user location with Expo Location
4. Compare current position to route geometry to detect off-route
5. Re-call Directions API when off-route threshold is exceeded
6. Synthesize voice instructions in app code (or use Expo Speech)

This is a significant implementation burden but it is the standard React Native approach.

---

### 2. Mapbox Directions API -- Walking Capabilities

**Profile:** `mapbox/walking`
- Designed for "pedestrian and hiking routing"
- Uses sidewalks and trails as primary routing substrate
- Accepts up to 25 coordinates per request
- Supports arbitrary GPS waypoints including specific building entrance coordinates

**Walking-specific parameters:**
- `walking_speed`: 0.14 to 6.94 m/s (default 1.42 m/s / 5.1 km/h)
- `walkway_bias`: -1 to 1, biases routes away from or toward dedicated walkways (default 0)

**Campus-specific walking paths:**
The Mapbox road network is derived from OpenStreetMap. OSM coverage of campus pedestrian paths (footways, paths, sidewalks) varies by institution. Well-mapped campuses (many universities have contributed detailed OSM data) will route correctly on campus paths. Poorly-mapped campuses will route on roads. You can verify OSM coverage at openstreetmap.org before committing to this API. Custom routing on private campus paths not in OSM requires the Mapbox Map Matching API or a custom dataset -- neither is trivial.

**Route recalculation:**
No built-in real-time rerouting in the REST API. Rerouting is a client-side polling concern: detect off-route, issue a new API request. The `avoid_maneuver_radius` parameter (1-1000m) prevents routes from making dangerous turns near the current position during active navigation, which is useful for in-progress routing.

**Rate limits:**
Mapbox does not publish hard per-minute rate limits in their public documentation. For the standard pay-as-you-go tier, practical limits are generous for low-volume apps. Contact Mapbox for enterprise rate SLAs.

**Pricing:**
Mapbox does not display per-request Directions API pricing publicly in their docs (as of March 2026 research). The pricing page redirects to a console login. Based on historical data and third-party sources: approximately $0.50-$1.00 per 1,000 requests on the standard tier, with a free tier of 100,000 requests/month. Verify at mapbox.com/pricing with a logged-in account.

At campus navigation scale (hundreds of requests per day = ~10,000-30,000/month), this is almost certainly within the free tier.

---

### 3. Google Maps Directions / Routes API -- Walking Capabilities

**Current API:** Google recommends the Routes API (v2) over the legacy Directions API.

**Walking support:** `WALK` travel mode supported. Routes via "pedestrian paths and sidewalks (where available)."

**Important caveat from Google's own documentation:** "Both walking and bicycling directions may sometimes not include clear pedestrian or bicycling paths, so these directions will return warnings in the returned result which you must display to the user." This is a signal that pedestrian path coverage is not guaranteed.

**Accessibility routing:** No wheelchair routing, stair avoidance, or ramp preference options exist in the Routes API as of 2026. The `avoid=indoor` parameter exists for the legacy Directions API, but this avoids indoor segments, not stairs specifically. Google Maps the consumer app has accessibility routing; that logic is not exposed in the API.

**Campus paths:** Same OSM/Google Maps data coverage question applies. Google's data is generally strong in urban areas but campus footway detail varies.

**Use as pure directions API alongside rnmapbox/maps:**
Yes, this is a valid architecture. The Routes API is a pure REST API -- it returns route geometry (polyline), step instructions, distance, and duration. The rendered map is entirely decoupled. You can display the route polyline returned by Google on a Mapbox map without any issues.

**Pricing (Routes API, 2025-2026):**
- Routes: Compute Routes Essentials: $5.00 per 1,000 requests, 10,000 free events/month cap
- Routes: Compute Routes Pro (traffic-aware, more waypoints): $10.00 per 1,000 requests, 5,000 free events/month cap
- Legacy Directions API Essentials: $5.00 per 1,000 requests, 10,000 free events/month cap

Note: Google provides a $200/month free credit across all Maps Platform APIs (not per-API). At $5/1,000 requests, $200 covers 40,000 route requests/month before any charges.

At hundreds of requests per day (~15,000-20,000/month), you would likely stay within the $200 monthly credit, making effective cost $0.

**Rate limits:** No stated daily maximum. Quota limits configurable in Google Cloud Console. Default quotas are generous for development; production quotas require a billing-enabled project.

---

### 4. Real-Time Route Recalculation

**Mapbox Directions API:**
- No built-in rerouting subscription -- client must poll
- A new API request takes 100-300ms typical for walking routes (lightweight computation vs. driving with traffic)
- Recommended pattern: trigger reroute when user is >15-25m from the route polyline for >3-5 seconds (debounce to avoid thrash)
- Rate limit concern: frequent rerouting (e.g., every 10 seconds off-route) could accumulate requests quickly. Budget ~5-10 reroute requests per navigation session

**Google Routes API:**
- Same model: stateless REST, client polls
- Similar latency profile for walking routes

Neither API provides a WebSocket or streaming reroute subscription. Real-time navigation SDK behavior (continuous rerouting as in Apple Maps or Google Maps app) requires the native Navigation SDKs, which are not available in React Native.

---

### 5. Accessibility-Specific Features

**Mapbox Directions API:**
- No wheelchair routing
- No stair avoidance
- No ramp preference
- `walkway_bias` prefers dedicated pedestrian paths over shared roads, but does not distinguish accessible vs. inaccessible paths
- Accessible routing would require custom OSM tags (`wheelchair=yes/limited/no`, `ramp=yes`) to be present in the data AND a custom routing engine -- neither Mapbox nor Google exposes this

**Google Maps Routes API:**
- No wheelchair routing in the API
- `avoid=indoor` exists in the legacy API only
- Consumer Google Maps has "accessible routes" via the app but this is NOT exposed in any API endpoint

**Practical conclusion:** If accessibility-aware routing (wheelchair, ramp preference, stair avoidance) is a hard requirement, you cannot satisfy it with either Mapbox or Google Maps APIs today. Options:
1. Use OpenTripPlanner with OpenStreetMap data tagged with wheelchair attributes -- open source, self-hosted, supports accessibility routing
2. Use HERE Maps API which has more developed accessibility routing features
3. Pre-author accessible routes for the campus and cache them statically (appropriate for a fixed campus context)

For a campus navigation app serving visually impaired students (not necessarily wheelchair users), the routing gap may be less critical -- sidewalk-preferring routing from Mapbox `mapbox/walking` with high `walkway_bias` may be sufficient.

---

### 6. Offline Capabilities

**@rnmapbox/maps offline tiles:**
The Maps SDK supports offline tile packs. You can download map tiles for a campus area in advance. This covers map rendering offline.

**Walking directions offline:**
Neither Mapbox nor Google provides offline walking directions via their standard REST APIs. Route calculation requires a live API call.

**Mapbox Navigation SDK (native) offline:**
The native Navigation SDK supports offline routing via downloadable navigation tiles. It explicitly lists "routing and rerouting, both online and offline" as a feature. However, this is inaccessible from React Native without a native module bridge.

**Offline-first strategies for React Native:**
1. **Pre-compute and cache routes**: At app startup (or on a schedule), pre-compute the most common routes for the campus (e.g., building A to building B for all pairs) and cache the route geometry + instructions locally. For a bounded campus, the total number of meaningful routes is manageable (N buildings = N*(N-1)/2 pairs). Serve cached routes offline, use live API for cache misses when online.

2. **Embed a routing engine**: OSRM or Valhalla can run as a server; a pre-built tile set for the campus can be bundled or downloaded. This is significant infrastructure work.

3. **GraphHopper with offline tiles**: GraphHopper has Android bindings. Not React Native native, but bridgeable.

4. **OpenRouteService**: Self-hostable, walking profiles, but server-side only.

For a campus navigation app with a fixed, bounded geography, option 1 (pre-computed route cache) is the pragmatic choice. The number of building-to-building routes is finite and small enough to pre-generate.

---

### 7. Cost Summary

| API | Free Tier | Per 1K Requests (paid) | ~500 req/day cost |
|---|---|---|---|
| Mapbox Directions API | ~100K req/month (verify) | ~$0.50-$1.00 (unverified, historical) | Likely free |
| Google Routes API Essentials | 10K events/month + $200 credit | $5.00 | ~$75/month or covered by credit |
| Google Routes API Pro | 5K events/month + $200 credit | $10.00 | ~$150/month or covered by credit |

At hundreds of requests per day (assuming 500/day = ~15,000/month):
- **Mapbox**: Almost certainly free tier
- **Google**: Covered by $200 monthly credit if total Maps Platform usage is under budget

Cost is not a differentiator at campus navigation scale. Both are effectively free for this volume.

---

## Recommended Architecture for This Use Case

Given the constraints (React Native / Expo, accessibility navigation, campus-bounded, offline-first need):

1. **Map rendering**: @rnmapbox/maps (offline tiles pre-downloaded for campus)
2. **Route calculation**: Mapbox Directions API (`mapbox/walking` profile, `walkway_bias: 1`) for online; pre-computed route cache for offline
3. **Turn-by-turn logic**: Custom in app code (step distance calculations against user location)
4. **Rerouting**: Client-side trigger at ~20m off-route deviation, new Directions API call
5. **Accessibility routing**: Pre-author accessible routes for the campus and store them statically -- the APIs cannot provide this reliably
6. **Voice**: Expo Speech API with step instructions from Directions API response

The Google Maps Routes API is a viable drop-in alternative for step 2, with marginally higher cost and the same lack of accessibility routing.

---

## Sources

- Mapbox Directions API docs: https://docs.mapbox.com/api/navigation/directions/
- Mapbox Navigation SDK (iOS): https://github.com/mapbox/mapbox-navigation-ios (v3.19.0, Feb 2026)
- Mapbox Navigation SDK overview: https://mapbox.com/navigation-sdk
- Mapbox docs root: https://docs.mapbox.com/
- @rnmapbox/maps: https://github.com/rnmapbox/maps
- Google Maps Routes API overview: https://developers.google.com/maps/documentation/routes/overview
- Google Routes API billing: https://developers.google.com/maps/documentation/routes/usage-and-billing
- Google Maps billing/pricing: https://developers.google.com/maps/billing-and-pricing/pricing
- Google Directions API (legacy): https://developers.google.com/maps/documentation/directions/get-directions
- Mapbox Android Navigation overview: https://docs.mapbox.com/android/navigation/overview/
- Mapbox iOS Navigation overview: https://docs.mapbox.com/ios/navigation/overview/

---

## Open Questions

1. **Mapbox Directions API exact pricing**: The pricing page requires a logged-in console session. Verify current free tier limit (historically 100K/month) and per-request cost by logging into mapbox.com/pricing.

2. **OSM campus coverage**: Verify whether the target campus (TSBVI or other) has detailed pedestrian path data in OpenStreetMap before committing to Mapbox or Google. Check at openstreetmap.org/way?... for the campus area.

3. **HERE Maps accessibility routing**: HERE's Routing API v8 has documented `avoid[features]=stairs` and `pedestrian[type]=wheelchair` parameters. This may be worth evaluating as a dedicated accessibility routing layer separate from the map display layer.

4. **OpenTripPlanner feasibility**: For accessibility routing, OTP with campus OSM data tagged with wheelchair attributes is the most credible open-source path. Evaluate hosting and data maintenance burden.

5. **Mapbox Navigation SDK React Native bridge**: No official wrapper exists, but a thin native module bridge exposing just route calculation + offline tile download from the Navigation SDK is technically feasible. Evaluate if the offline routing need is strong enough to justify this work.

6. **rnmapbox/maps offline tile scope**: Verify the tile pack size for a typical campus area and the API limits on offline packs (Mapbox limits offline packs by region size and account tier).
