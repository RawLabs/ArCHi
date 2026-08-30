#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bin_dir="${ARCHI_BIN_DIR:-$HOME/.local/bin}"
data_dir="${ARCHI_HOME:-$HOME/.local/share/archi}"
refresh_registry=false

case "${1:-}" in
  "") ;;
  --refresh-registry) refresh_registry=true ;;
  --help|-h)
    printf 'Usage: %s [--refresh-registry]\n' "$0"
    printf '  --refresh-registry  Back up and replace the active command registry.\n'
    exit 0
    ;;
  *)
    printf 'Unknown option: %s\n' "$1" >&2
    exit 2
    ;;
esac

install -d -m 755 "$bin_dir" "$data_dir"
install -m 755 "$project_dir"/scripts/* "$bin_dir"/
install -m 644 "$project_dir/src/archi/router.py" "$data_dir/router.py"
install -m 644 "$project_dir/config/commands.toml" "$data_dir/commands.default.toml"

if [[ ! -e "$data_dir/commands.toml" ]]; then
  install -m 644 "$project_dir/config/commands.toml" "$data_dir/commands.toml"
elif [[ "$refresh_registry" == true ]]; then
  registry_backup="$data_dir/commands.toml.bak.$(date +%Y%m%d%H%M%S)"
  install -m 600 "$data_dir/commands.toml" "$registry_backup"
  install -m 644 "$project_dir/config/commands.toml" "$data_dir/commands.toml"
  printf 'Backed up previous command registry: %s\n' "$registry_backup"
else
  printf 'Kept existing command registry: %s\n' "$data_dir/commands.toml"
  printf 'Review updated defaults at %s/commands.default.toml.\n' "$data_dir"
fi

if [[ -f "$project_dir/assets/voice.wav" ]]; then
  install -d -m 700 "$data_dir/assets"
  install -m 600 "$project_dir/assets/voice.wav" "$data_dir/assets/voice.wav"
elif [[ -f "$data_dir/savvy.wav" && ! -e "$data_dir/assets/voice.wav" ]]; then
  install -d -m 700 "$data_dir/assets"
  install -m 600 "$data_dir/savvy.wav" "$data_dir/assets/voice.wav"
  printf 'Migrated legacy voice sample to %s/assets/voice.wav\n' "$data_dir"
fi

printf 'Installed ArCHi scripts to %s and data to %s\n' "$bin_dir" "$data_dir"
