#!/bin/bash
# Stop hook: remind about doc updates when code changed but no docs did.
input=$(cat)
# Prevent re-fire loop: if we already blocked once this stop, allow stopping.
echo "$input" | grep -q '"stop_hook_active"[[:space:]]*:[[:space:]]*true' && exit 0

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" || exit 0
changed=$(git status --porcelain 2>/dev/null | awk '{print $NF}')
[ -z "$changed" ] && exit 0

code_changed=$(echo "$changed" | grep -E '^(backend/|frontend/|docker-compose\.yml)' | grep -vE '\.md$')
docs_changed=$(echo "$changed" | grep -E '(^CLAUDE\.md$|^docs/.*\.md$)')

if [ -n "$code_changed" ] && [ -z "$docs_changed" ]; then
  echo "Code changed but no docs/CLAUDE.md updated. Check the Documentation Map in CLAUDE.md and update affected docs, or state explicitly that no doc changes are needed." >&2
  exit 2
fi
exit 0
