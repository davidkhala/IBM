#!/usr/bin/env bash
# trust-macos.sh
# Remove the macOS Gatekeeper quarantine flag from cpd-cli binaries.
#
# Usage:
#   bash trust-macos.sh [cpd-cli-root]
#
#   - cpd-cli-root: optional path to the directory where cpd-cli was extracted. Defaults to the current directory.
#
# Why: macOS adds com.apple.quarantine to files downloaded from the internet.
# Gatekeeper blocks execution until the user "trusts" each binary.
# xattr -d removes that flag — equivalent to right-clicking each file and
# selecting Open, but non-interactive.

set -euo pipefail

ROOT="${1:-.}"

COMPONENTS=(
  cpd-cli
  plugins/lib/darwin/config
  plugins/lib/darwin/cpdbr-oadp
  plugins/lib/darwin/cpdctl
  plugins/lib/darwin/cpdtool
  plugins/lib/darwin/health
  plugins/lib/darwin/manage
  plugins/lib/darwin/platform-diag
  plugins/lib/darwin/platform-mgmt
)

for component in "${COMPONENTS[@]}"; do
  target="$ROOT/$component"
  if [[ -e "$target" ]]; then
    xattr -d com.apple.quarantine "$target" 2>/dev/null && \
      echo "✓ trusted: $target" || \
      echo "  skipped (no quarantine flag): $target"
  else
    echo "  not found: $target"
  fi
done

echo ""
echo "Done. You can now run cpd-cli without Gatekeeper prompts."
