#!/usr/bin/env python3
"""Deterministic check for final-grooming.json against manifest.json.

Adapted from verify-proposal.py. Adds survivor/precondition consistency, rank
integrity, owner-decision identity and the line limits the review brief sets.
Reads only; the proposed-* originals are left untouched.
"""
import json, sys, pathlib

HERE = pathlib.Path(__file__).parent
man = json.loads((HERE / "manifest.json").read_text())
doc = json.loads((HERE / "final-grooming.json").read_text())
fail = []

original = sorted(i["number"] for i in man["issues"])
if len(original) != 43:
    fail.append(f"manifest has {len(original)} issues, expected 43")

# 0. snapshot identity
if doc["snapshot_sha"] != man["head"]:
    fail.append(f"snapshot_sha {doc['snapshot_sha']} != manifest head {man['head']}")

# 1. every original issue exactly once in issue_dispositions
nums = [d["number"] for d in doc["issue_dispositions"]]
if len(nums) != len(set(nums)):
    fail.append(f"duplicate dispositions: {sorted({n for n in nums if nums.count(n) > 1})}")
if sorted(set(nums)) != original:
    fail.append(f"missing {sorted(set(original) - set(nums))}, extra {sorted(set(nums) - set(original))}")
if len(nums) != 43:
    fail.append(f"{len(nums)} dispositions, expected exactly 43")

# 2. every package issue reference resolves, exactly once overall
pkg_ids = [p["id"] for p in doc["work_packages"]]
if len(pkg_ids) != len(set(pkg_ids)):
    fail.append("duplicate work package ids")
seen = {}
for p in doc["work_packages"]:
    for n in p["issues"]:
        if n not in original:
            fail.append(f"{p['id']} references unknown issue {n}")
        seen.setdefault(n, []).append(p["id"])
uncovered = sorted(set(original) - set(seen))
if uncovered:
    fail.append(f"issues in no package: {uncovered}")
# #611 is owned by WP-07 and is a prerequisite inside WP-17; #459 rides with its survivor.
allowed_multi = {611: ["WP-07", "WP-17"]}
for n, pkgs in sorted(seen.items()):
    if len(pkgs) > 1 and allowed_multi.get(n) != pkgs:
        fail.append(f"issue {n} appears in multiple packages: {pkgs}")

# 3. dependencies resolve, and no package depends on itself
for p in doc["work_packages"]:
    for dep in p["dependencies"]:
        if dep not in pkg_ids:
            fail.append(f"{p['id']} depends on unknown package {dep}")
        if dep == p["id"]:
            fail.append(f"{p['id']} depends on itself")

# 4. no dependency cycles
graph = {p["id"]: list(p["dependencies"]) for p in doc["work_packages"]}
state = {}
def visit(node, stack):
    if state.get(node) == "done":
        return
    if state.get(node) == "open":
        fail.append(f"dependency cycle: {' -> '.join(stack + [node])}")
        return
    state[node] = "open"
    for nxt in graph.get(node, []):
        visit(nxt, stack + [node])
    state[node] = "done"
for node in graph:
    visit(node, [])

# 5. rank integrity: unique, contiguous from 1, and never before a dependency
ranks = [p["rank"] for p in doc["work_packages"]]
if sorted(ranks) != list(range(1, len(ranks) + 1)):
    fail.append(f"ranks are not 1..{len(ranks)} exactly once: {sorted(ranks)}")
rank = {p["id"]: p["rank"] for p in doc["work_packages"]}
for p in doc["work_packages"]:
    for dep in p["dependencies"]:
        if rank.get(dep, 0) > p["rank"]:
            fail.append(f"{p['id']} (rank {p['rank']}) depends on later {dep} (rank {rank[dep]})")

# 6. closures: ledger and close_candidates agree, survivors survive, preconditions exist
closures = sorted(d["number"] for d in doc["issue_dispositions"] if d["action"] == "close_merge")
cand = {c["issue"]: c for c in doc["close_candidates"]}
for n in closures:
    if n not in cand:
        fail.append(f"issue {n} is close_merge in the ledger but has no close candidate record")
for c in doc["close_candidates"]:
    if c["issue"] not in original or c["survivor"] not in original:
        fail.append(f"close candidate {c['issue']} -> {c['survivor']} references an unknown issue")
    if not c.get("preconditions"):
        fail.append(f"close candidate {c['issue']} carries no preconditions")
    if not c.get("requirements_to_transfer"):
        fail.append(f"close candidate {c['issue']} transfers no requirements")
    d = next((x for x in doc["issue_dispositions"] if x["number"] == c["issue"]), None)
    if d and d["survivor"] == c["issue"]:
        fail.append(f"close candidate {c['issue']} is its own survivor in the ledger")
    if d and d["survivor"] != c["survivor"]:
        fail.append(f"close candidate {c['issue']} survivor {c['survivor']} disagrees with ledger {d['survivor']}")
    s = next((x for x in doc["issue_dispositions"] if x["number"] == c["survivor"]), None)
    if s and s["action"] == "close_merge":
        fail.append(f"survivor {c['survivor']} is itself closed")

# 7. every disposition carries evidence and a survivor that exists
for d in doc["issue_dispositions"]:
    if not d["evidence"]:
        fail.append(f"issue {d['number']} has no evidence")
    if d["survivor"] not in original:
        fail.append(f"issue {d['number']} survivor {d['survivor']} is not an original issue")
    if d["action"] != "close_merge" and d["survivor"] != d["number"]:
        fail.append(f"issue {d['number']} is not closed but names survivor {d['survivor']}")

# 8. owner decisions: unique ids, real issues
od_ids = [o["id"] for o in doc["owner_decisions"]]
if len(od_ids) != len(set(od_ids)):
    fail.append("duplicate owner decision ids")
for o in doc["owner_decisions"]:
    if not o.get("recommendation") or not o.get("evidence"):
        fail.append(f"{o['id']} carries no recommendation or no evidence")
    for n in o["affected_issues"]:
        if n not in original:
            fail.append(f"{o['id']} references unknown issue {n}")

# 9. line limits set by the review brief
limits = {
    "grooming-review.md": 200,
    "final-grooming.json": 700,
    "final-grooming.md": 700,
    "final-github-edit-drafts.md": 700,
}
for name, cap in limits.items():
    path = HERE / name
    if not path.exists():
        fail.append(f"{name} is missing")
        continue
    n = len(path.read_text().splitlines())
    if n > cap:
        fail.append(f"{name} is {n} lines, over the {cap} limit")

print(f"issues in manifest:        {len(original)}")
print(f"dispositions:              {len(nums)} ({len(set(nums))} distinct)")
print(f"work packages:             {len(doc['work_packages'])}")
print(f"package issue references:  {sum(len(p['issues']) for p in doc['work_packages'])}")
print(f"unconditional closures:    {len(closures)} -> {closures}")
print(f"conditional close cands:   {[c['issue'] for c in doc['close_candidates'] if c['issue'] not in closures]}")
print(f"owner decisions:           {len(doc['owner_decisions'])} -> {od_ids}")
print(f"unresolved:                {len(doc['unresolved'])}")
for name, cap in limits.items():
    p = HERE / name
    print(f"{name:30s} {len(p.read_text().splitlines()) if p.exists() else '-'} / {cap}")
if fail:
    print("\nFAIL")
    for f in fail:
        print(" -", f)
    sys.exit(1)
print("\nPASS: 43/43 issues covered exactly once; refs, dependencies, ranks, closures and line limits all hold.")
