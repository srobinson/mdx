# CPU incident handoff

Stuart reports zero CPU idle and suspects desktop-close cleanup. He explicitly wants the main agent to orchestrate, delegating detailed diagnosis. Preserve the backlog audit and its research.

Direct observations around 2026-09-05 04:47 to 04:50 UTC:

- top: approximately 2,596 processes, 23,087 threads, 0% CPU idle. Load averages 66.42, 161.53, 343.06. 61 GB memory used, 35 GB unused, 20 GB compressed. No swap IO during the one-second sample.
- docker stats: transport-matters-postgres-1 at 793.08% CPU, 86 PIDs. Other listed Supabase containers individually under 4% CPU. Docker VM process PID 64139 was the top host CPU consumer.
- TM Python processes collectively 358.4% CPU in one ps sample, higher in an earlier sample. Busy PIDs 82261, 82426, 82614, 83341, 83809, 7217, 21060 are children of PID 94154, the preview transport-matters backend. They run addon.py with --mode, --listen-host, --listen-port and --set arguments, consistent with capture proxies.
- PID 48471, python3.14, PPID 1, elapsed approximately 2 days 10 hours, also consumes 50 to 82% CPU; ownership and purpose not identified.
- 1,149 processes had PPID 1, including 368 named node and 334 helioy-bus Python processes. Total command counts include 775 node, 692 helioy-bus Python, 369 additional node executable paths, and numerous esbuild processes under current and historical worktrees. Reparenting is evidence to investigate, not proof every process is leaked or safe to terminate.
- audit-runtime has no runtime.md or runtime.json saved as of the check. Its pane shows over 75 minutes Working, 27 minutes Stalled, and gpt-5.6-luna xhigh although the launch receipt requested high.

Earlier latency investigation observed long upstream requests and websocket failures, but its conclusion that nothing local is slow is invalidated by this CPU evidence. Provider congestion and local saturation can coexist. Determine causality with direct process and database evidence.

Guardrails: no bulk kills, database restart, container restart, agent interruption, or source/GitHub mutation during diagnosis. Attribute ownership, preserve live runs, identify narrowly safe recovery actions, and report quickly. Existing workspace turn_completed watch belongs to the orchestrator; do not add another. Write only assigned report artifacts in this directory. Do not reveal credentials, raw payloads or SQL literals.
