# 471: Logging: make log destination env-configurable and let foreground persist

URL: https://github.com/littleorgans/transport-matters/issues/471
State: open
Labels: enhancement
Updated: 2026-08-26T14:08:12Z

Backend log location and foreground persistence should be environment configuration.

## Today

`cli/desktop_cmd.py::run_desktop_detached` opens `desktop_runtime.py::desktop_log_path`, which is `<channel home>/runtime/desktop.log`. `transport-matters tail <channel>` reads it.

Two consequences:

- `--foreground` persists nothing. Output goes to the tty and is gone when the pane scrolls. Diagnosing a launch required re-running the whole scenario detached purely to obtain a readable log.
- The log lives inside the channel home, so wiping the home deletes the logs that would explain what happened before the wipe.

## Outcome

Log destination is env-configurable, and foreground mode can persist.

## Scope

- Env var for log destination, defaulting to today's `<channel home>/runtime/desktop.log` so nothing changes for existing users.
- `--foreground` writes to that destination as well as the tty (tee), or gains a flag to.
- `transport-matters tail` resolves the same configured path.

## Acceptance

- Foreground run produces a readable log file.
- Log destination outside the channel home survives a home wipe.
- `just check` and `just test` green.


## Sub issues
[]
