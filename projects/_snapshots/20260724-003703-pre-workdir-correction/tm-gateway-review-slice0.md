# PR 200 Gateway slice 0 adversarial review

- Severity: Major
  Path: packages/gateway/src/main.ts:6
  Fact: The process entry builds and listens on a Fastify instance but never handles SIGINT/SIGTERM or closes the app on startup failure, so the first serving root cannot run Fastify close hooks when the supervisor stops it.
  Suggested fix: Move startup into a small async runner that catches build/listen failures, closes the app when one exists, and registers SIGINT/SIGTERM handlers that await `app.close()` before exiting.

- Severity: Minor
  Path: packages/AGENTS.md:25
  Fact: The serving-root guidance says `@tm/gateway` is the product-plane origin, but the locked P1 state keeps Python as the interim origin, so the guide overstates the current topology.
  Suggested fix: Reword this as the target product-plane gateway or future origin, and include serving roots in the one-import-surface rule at packages/AGENTS.md:60.
