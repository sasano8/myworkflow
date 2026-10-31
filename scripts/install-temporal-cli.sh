#!/usr/bin/env bash
set -euo pipefail
# Linux x86_64 development setup; verify the official release checksum.
if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
  echo 'This helper supports Linux x86_64 only; install Temporal CLI for your platform.' >&2
  exit 1
fi
install_dir=${1:?Usage: bash scripts/install-temporal-cli.sh INSTALL_DIRECTORY}
mkdir -p "$install_dir"
archive=temporal_cli_1.9.1_linux_amd64.tar.gz
base=https://github.com/temporalio/cli/releases/download/v1.9.1
curl -fsSL "$base/$archive" -o "$install_dir/$archive"
curl -fsSL "$base/checksums.txt" -o "$install_dir/checksums.txt"
(cd "$install_dir"; awk -v name="$archive" '$2 == name {print}' checksums.txt > selected.sha256; test -s selected.sha256; sha256sum --check selected.sha256)
tar -xzf "$install_dir/$archive" -C "$install_dir" temporal
"$install_dir/temporal" --version
