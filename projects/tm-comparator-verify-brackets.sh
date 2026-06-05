#!/usr/bin/env bash
# Proves every red/green bracket on fix/comparator-truth: each test commit must FAIL
# its own new tests, and its paired fix commit must PASS them.
set -uo pipefail

REPO=/Users/alphab/Dev/LLM/DEV/helioy/transport-matters
WT=${TMPDIR:-/tmp}/cmptr-brackets
VENV=$REPO/api/.venv/bin/python

PAIRS=(
  "U0-consumer 86cfcc9e b1a528d7"
  "U2-canonical 3a6373db b68afc8e"
  "U3-fingerprint 1d2998bb 46b205a4"
  "U4-axes c6870c05 9a4a763f"
  "U5-correlation 5fa903af 39f4ac6d"
  "U6-transcript a50cf740 13e94025"
  "U7-preflight 23452d25 ead2dd60"
  "C1-raw-fingerprint e3bc0ab0 caead545"
  "C2-C6-precedence 44b37b6b eda1af4f"
  "C3-bootstrap 7a259be0 c2ce9985"
  "C4-refusal-details 330f1b17 c3eef8da"
  "C5-preflight-paths 84e372d1 9d8dcd16"
  "E1-N4-nested-presence 0f1f6b27 fcbd20da"
  "E2-launch-extras 22bbf888 47688c85"
  "E3-E5-cli-evidence 4290131a 8f0c8e70"
  "E4-static-pair d2d0b376 10165c99"
  "B1a-identity-both-axes 21f95323 5f5223cd"
  "B1b-refused-subtree 9a9d3179 36b3a9a4"
  "B2-presence-invariant 9cce3f7d 236ebbf3"
  "B3-store-schema 2b935f8b 058a6bf4"
  "B4-timeout-cause 265d7548 72ef3708"
  "F1-presence-cross-product aef3e384 0c7a6a70"
  "F2-F7-removal-verdict 000b2079 44085572"
  "F3-prompt-plan 0d580ed6 a6975ae6"
  "F4-F6-schema-probe 6040622e abdba73c"
  "F8-response-diagnosis 76470f9c 4c965ac0"
  "H1-H3-comparator-sweep ede52d9e d50a5190"
  "H1-mixed-classifications f454b7bf d50a5190"
  "H4-socket-bounds fcb8f6dc a93b3fed"
)

git -C "$REPO" worktree remove --force "$WT" 2>/dev/null
git -C "$REPO" worktree add --quiet --detach "$WT" main || exit 1
trap 'git -C "$REPO" worktree remove --force "$WT" 2>/dev/null' EXIT

run_tests() {
  local sha=$1; shift
  git -C "$WT" checkout --quiet --detach "$sha" || { echo "CHECKOUT-FAILED"; return; }
  ( cd "$WT/api" \
      && PYTHONPATH="$WT/api/src" \
         TRANSPORT_MATTERS_TEST_DATABASE_URL="${TRANSPORT_MATTERS_TEST_DATABASE_URL:-postgresql://tm:tm@localhost:55432/postgres}" \
         "$VENV" -m pytest "$@" -q -p no:cacheprovider 2>&1 \
      | grep -E '^[0-9]+ (passed|failed)|passed|failed|error|no tests ran' | tail -1 )
}

fail=0
for pair in "${PAIRS[@]}"; do
  read -r name tsha fsha <<<"$pair"

  mapfile -t files < <(git -C "$REPO" show --name-only --format= "$tsha" | grep 'test_.*\.py$')
  names=$(for f in "${files[@]}"; do
            git -C "$REPO" show "$tsha" -- "$f" | sed -n 's/^+[[:space:]]*def \(test_[a-zA-Z0-9_]*\).*/\1/p'
          done | sort -u)

  if [ -z "$names" ]; then echo "$name: NO NEW TESTS in $tsha"; fail=1; continue; fi

  args=()
  for f in "${files[@]}"; do args+=("${f#api/}"); done
  args+=(-k "$(echo "$names" | paste -sd'~' - | sed 's/~/ or /g')")

  red=$(run_tests "$tsha" "${args[@]}")
  green=$(run_tests "$fsha" "${args[@]}")
  n=$(echo "$names" | wc -l | tr -d ' ')

  if [[ "$red" == *failed* && "$green" != *failed* && "$green" == *passed* ]]; then
    echo "$name: PASS  ($n new tests)  red=[$red]  green=[$green]"
  else
    echo "$name: FAIL  ($n new tests)  red=[$red]  green=[$green]"
    fail=1
  fi
done

echo
[ $fail -eq 0 ] && echo "ALL BRACKETS PROVEN" || echo "BRACKET VERIFICATION FAILED"
exit $fail
