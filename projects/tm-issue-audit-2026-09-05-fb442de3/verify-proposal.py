#!/usr/bin/env python3
"""Deterministic coverage check for proposed-grooming.json against manifest.json."""
import json, sys, pathlib

HERE = pathlib.Path(__file__).parent
man = json.loads((HERE / "manifest.json").read_text())
doc = json.loads((HERE / "proposed-grooming.json").read_text())
fail = []

original = sorted(i["number"] for i in man["issues"])
if len(original) != 43:
    fail.append(f"manifest has {len(original)} issues, expected 43")

if doc["snapshot_sha"] != man["head"]:
    fail.append(f"snapshot_sha {doc['snapshot_sha']} != manifest head {man['head']}")

# 1. every original issue exactly once in issue_dispositions
nums = [d["number"] for d in doc["issue_dispositions"]]
if len(nums) != len(set(nums)):
    dupes = sorted({n for n in nums if nums.count(n) > 1})
    fail.append(f"duplicate dispositions: {dupes}")
if sorted(set(nums)) != original:
    fail.append(f"missing {sorted(set(original) - set(nums))}, extra {sorted(set(nums) - set(original))}")

# 2. every package issue reference resolves to an original issue, exactly once overall
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
# #611 appears in WP-07 (owner) and WP-17 (prerequisite); #459 rides with its survivor.
allowed_multi = {611: ["WP-07", "WP-17"]}
for n, pkgs in sorted(seen.items()):
    if len(pkgs) > 1 and allowed_multi.get(n) != pkgs:
        fail.append(f"issue {n} appears in multiple packages: {pkgs}")

# 3. every package dependency resolves to a package id
for p in doc["work_packages"]:
    for dep in p["dependencies"]:
        if dep not in pkg_ids:
            fail.append(f"{p['id']} depends on unknown package {dep}")

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

# 5. a package never precedes a package it depends on
rank = {p["id"]: p["rank"] for p in doc["work_packages"]}
for p in doc["work_packages"]:
    for dep in p["dependencies"]:
        if rank.get(dep, 0) > p["rank"]:
            fail.append(f"{p['id']} (rank {p['rank']}) depends on later {dep} (rank {rank[dep]})")

# 6. close candidates and owner decisions reference real issues; survivors stay open
for c in doc["close_candidates"]:
    if c["issue"] not in original or c["survivor"] not in original:
        fail.append(f"close candidate {c['issue']} -> {c['survivor']} references an unknown issue")
    disp = next((d for d in doc["issue_dispositions"] if d["number"] == c["issue"]), None)
    if disp and disp["survivor"] == c["issue"]:
        fail.append(f"close candidate {c['issue']} is its own survivor in the ledger")
for o in doc["owner_decisions"]:
    for n in o["affected_issues"]:
        if n not in original:
            fail.append(f"owner decision references unknown issue {n}")

# 7. every disposition carries evidence and a survivor that exists
for d in doc["issue_dispositions"]:
    if not d["evidence"]:
        fail.append(f"issue {d['number']} has no evidence")
    if d["survivor"] not in original:
        fail.append(f"issue {d['number']} survivor {d['survivor']} is not an original issue")

closures = [d["number"] for d in doc["issue_dispositions"] if d["action"] == "close_merge"]
print(f"issues in manifest:        {len(original)}")
print(f"dispositions:              {len(nums)} ({len(set(nums))} distinct)")
print(f"work packages:             {len(doc['work_packages'])}")
print(f"package issue references:  {sum(len(p['issues']) for p in doc['work_packages'])}")
print(f"unconditional closures:    {len(closures)} -> {closures}")
print(f"conditional close cands:   {[c['issue'] for c in doc['close_candidates'] if c['issue'] not in closures]}")
print(f"owner decisions:           {len(doc['owner_decisions'])}")
print(f"unresolved:                {len(doc['unresolved'])}")
if fail:
    print("\nFAIL")
    for f in fail:
        print(" -", f)
    sys.exit(1)
print("\nPASS: 43/43 issues covered exactly once; every package reference and dependency resolves.")
