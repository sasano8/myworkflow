#!/bin/sh
set -eu
cd "$(git rev-parse --show-toplevel)"
configured_hooks="$(git config --get core.hooksPath || true)"
if [ -n "$configured_hooks" ] && [ "$configured_hooks" != .githooks ]; then
    echo "Existing core.hooksPath is configured; refusing to replace it: $configured_hooks" >&2
    exit 1
fi
if [ -z "$configured_hooks" ] && [ -x "$(git rev-parse --git-path hooks/pre-commit)" ]; then
    echo 'An active pre-commit hook already exists; integrate the generator with that hook first.' >&2
    exit 1
fi
git config --local core.hooksPath .githooks
printf '%s\n' 'Installed pre-commit document generation (.githooks).'
