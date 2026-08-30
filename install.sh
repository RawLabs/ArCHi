#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bin_dir="${ARCHI_BIN_DIR:-$HOME/.local/bin}"
data_dir="${ARCHI_HOME:-$HOME/.local/share/archi}"

install -d -m 755 "$bin_dir" "$data_dir"
install -m 755 "$project_dir"/scripts/* "$bin_dir"/
install -m 644 "$project_dir/src/archi/router.py" "$data_dir/router.py"

if [[ ! -e "$data_dir/commands.toml" ]]; then
  install -m 644 "$project_dir/config/commands.toml" "$data_dir/commands.toml"
else
  printf 'Kept existing command registry: %s\n' "$data_dir/commands.toml"
  printf 'Review %s/config/commands.toml for new defaults.\n' "$project_dir"
fi

printf 'Installed ArCHi scripts to %s and data to %s\n' "$bin_dir" "$data_dir"
