# 611: Capture derived request purpose fixtures with a check mode

URL: https://github.com/littleorgans/transport-matters/issues/611
State: open
Labels: 
Updated: 2026-09-03T20:23:22Z

## Problem

Request purpose classification is proved by synthetic `make_request_ir()` fixtures: shapes written by hand. They cannot become visibly stale when a harness changes its traffic, because nothing ties them to observed traffic.

The launch comparison catches structural schema drift. Request purpose does not depend on structure alone. It depends on values such as tool presence, token budget, beta headers and request class. A harness can hold its schema exactly and change every one of them, and no current check would notice.

Raised on #523 from the evidence in #557 and PR #559. Split out of #523 because it is small, self contained, protects the certify run, and requires no change to the publish path.

## Deliverable

Each audit capture generates a small sanitized request purpose fixture, keyed by:

- harness
- exact harness version
- model
- capture profile
- request class

The projection retains only the request IR and the headers the provider classifier reads. Full raw captures stay outside this repository.

## Check mode

The generator needs a check mode. A changed capture projection fails the check until the fixture and its expected purpose are reviewed. This is the invalidation path the synthetic fixtures lack.

Classifier replay asserts:

- primary agent requests classify as `True`
- known housekeeping and auxiliary requests classify as `False`
- no captured request class capable of prompt collision rests on `None`

## Why this ordering

This gives the synthetic unit tests a measured source without removing them, and it lands before the full certification publication so that a classifier regression is caught by a fixture rather than by a published release.

It changes no publish path and adds no new evidence artifact. It reads captures that already exist.

## Acceptance

- A capture produces a fixture at the five keys above.
- Check mode fails on a changed projection and names what changed.
- Replay asserts the three classifications.
- The existing synthetic fixtures remain, now with a documented measured counterpart.

## Related

#523 for the audit corpus this reads from, #557 and PR #559 for the classifier gap that motivated it.


## Sub issues
[]
