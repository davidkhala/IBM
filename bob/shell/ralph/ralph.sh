#!/usr/bin/env bash
# Ralph loop for Bob-Shell: feed the same prompt to a fresh `bob` session until done.
#
# Usage: ./ralph.sh [-p PROMPT_FILE] [-n MAX_ITERATIONS] [-m CHAT_MODE] [-s SLEEP_SECONDS]
#
# Each iteration is a brand-new non-interactive session. State lives only in the
# workspace (files, git history, progress file), never in the conversation.
# The loop stops when Bob's output contains the line <promise>COMPLETE</promise>
# or when MAX_ITERATIONS is reached.

set -u

PROMPT_FILE="PROMPT.md"
MAX_ITERATIONS=20
CHAT_MODE=""
SLEEP_SECONDS=2
DONE_MARKER="<promise>COMPLETE</promise>"
LOG_DIR=".ralph/logs"

while getopts "p:n:m:s:h" opt; do
  case "$opt" in
    p) PROMPT_FILE="$OPTARG" ;;
    n) MAX_ITERATIONS="$OPTARG" ;;
    m) CHAT_MODE="$OPTARG" ;;
    s) SLEEP_SECONDS="$OPTARG" ;;
    h|*) sed -n '2,10p' "$0"; exit 0 ;;
  esac
done

command -v bob >/dev/null 2>&1 || { echo "bob not found in PATH" >&2; exit 127; }
[ -f "$PROMPT_FILE" ] || { echo "prompt file not found: $PROMPT_FILE" >&2; exit 2; }

mkdir -p "$LOG_DIR"

args=(--yolo --hide-intermediary-output)
[ -n "$CHAT_MODE" ] && args+=(--chat-mode="$CHAT_MODE")

for ((i = 1; i <= MAX_ITERATIONS; i++)); do
  log="$LOG_DIR/iteration-$(printf '%03d' "$i").log"
  echo "=== Ralph iteration $i/$MAX_ITERATIONS ($(date '+%F %T')) ==="

  # Re-read the prompt every iteration so it can be edited while the loop runs.
  bob -p "$(cat "$PROMPT_FILE")" "${args[@]}" 2>&1 | tee "$log"

  if grep -qxF "$DONE_MARKER" "$log"; then
    echo "=== Completed at iteration $i ==="
    exit 0
  fi
  sleep "$SLEEP_SECONDS"
done

echo "=== Reached max iterations ($MAX_ITERATIONS) without completion ===" >&2
exit 1
