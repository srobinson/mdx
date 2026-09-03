import argparse
import json
from pathlib import Path

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("reports", nargs="*")
parser.add_argument("--all", action="store_true")
args = parser.parse_args()
assignments = json.loads((root / "assignments.json").read_text())
manifest = json.loads((root / "manifest.json").read_text())
expected_all = {x["number"] for x in manifest["issues"]}
reports = list(assignments) if args.all else args.reports
seen = set()
summary = []
for name in reports:
    data = json.loads((root / f"{name}.json").read_text())
    expected = set(assignments[name]) if name in assignments else expected_all
    numbers = [int(x["number"]) for x in data["issues"]]
    assert len(numbers) == len(set(numbers)), (name, "duplicate issue rows")
    assert set(numbers) == expected, (name, "coverage mismatch", expected - set(numbers), set(numbers) - expected)
    for issue in data["issues"]:
        for field in ["disposition", "canonical_work", "rationale", "evidence", "dependencies", "conflicts", "priority", "effort", "confidence"]:
            assert field in issue, (name, issue["number"], "missing", field)
        assert issue["evidence"], (name, issue["number"], "no evidence")
    if name in assignments:
        assert not seen.intersection(numbers), (name, "overlapping primary assignment")
        seen.update(numbers)
    summary.append({"report": name, "issues": len(numbers), "packages": len(data.get("packages", []))})
if args.all:
    assert seen == expected_all
print(json.dumps({"validated": summary, "primary_coverage": len(seen), "expected": len(expected_all)}, indent=2))
