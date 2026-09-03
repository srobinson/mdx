"""Sample live Python stacks without modifying the target processes."""

import argparse
from collections import Counter
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pids", nargs="*", type=int, default=[59710, 59716])
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--interval", type=float, default=0.05)
    args = parser.parse_args()
    if args.seconds <= 0 or args.interval <= 0:
        parser.error("seconds and interval must be positive")

    from _remote_debugging import RemoteUnwinder

    samplers = {pid: RemoteUnwinder(pid) for pid in args.pids}
    counts = {pid: Counter() for pid in samplers}
    errors = {pid: Counter() for pid in samplers}
    started = time.monotonic()
    passes = 0
    while time.monotonic() - started < args.seconds:
        for pid, sampler in samplers.items():
            try:
                for thread, frames in sampler.get_stack_trace():
                    counts[pid][repr(frames[:20])] += 1
            except (OSError, RuntimeError, UnicodeError) as error:
                errors[pid][f"{type(error).__name__}: {error}"] += 1
        passes += 1
        time.sleep(args.interval)

    print(f"Elapsed: {time.monotonic() - started:.2f}s; passes: {passes}")
    for pid in samplers:
        print(f"\nPID {pid}: most frequent main-thread stacks")
        for stack, count in counts[pid].most_common(15):
            print(f"\n{count} samples:\n{stack}")
        for error, count in errors[pid].items():
            print(f"Sampling error ({count} times): {error}")


if __name__ == "__main__":
    main()
