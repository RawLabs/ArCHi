# ArCHi

**ArCHi — Artificial Restorative Computer Harness Intelligence** — is a local,
deterministic, push-to-talk desktop command layer for Omarchy and Hyprland. It
is intended to make common desktop actions easier to access without sending a
command transcript to a cloud service.

ArCHi is the normal product name. The expanded name is used for formal project
descriptions and reinforces its role:

- **Artificial** — the AI layer.
- **Restorative** — restoring or compensating for lost or difficult computer
  interaction.
- **Computer Harness** — connecting existing desktop capabilities instead of
  replacing them.
- **Intelligence** — the reasoning and orchestration layer.

The “Harness” concept also guides the visual language: connected components,
structural lines, bridging, support, and attachment points. It reinforces the
architectural arch without relying on a literal accessibility symbol.

ArCHi is deliberately **not** an always-listening assistant. The microphone is
opened only during an explicitly started push-to-talk command.

## What it does

- routes recognized phrases through a small allowlisted command registry;
- provides spoken responses through a local Pocket TTS-compatible endpoint;
- keeps ArCHi's spoken-response volume separate from the system volume and
  shows an Omarchy OSD volume indicator;
- supports read-aloud, system audio, windows, screenshots, and workspace
  actions through an Omarchy profile;
- records local command diagnostics by default, with an “off record” command;
- keeps the intent-parser integration observational: it never chooses commands.

## Status

This is an early Omarchy-focused project. It has no wake word, no background
microphone listener, and no network requirement beyond whichever TTS endpoint a
user chooses to configure.

## Requirements

- Omarchy / Hyprland
- Python 3.11+
- [Voxtype](https://github.com/seriousm4x/voxtype) for push-to-talk capture
- PipeWire tools: `pw-play`, `wpctl`, and `pw-dump`
- `curl`, `jq`, `wl-clipboard`, and `hyprctl`
- a Pocket TTS-compatible HTTP endpoint (defaults to `http://127.0.0.1:8000/tts`)

`hassil` is optional. When installed, it only compares parsing results for
diagnostics; it does not execute commands.

## Install locally

Review the files first, then run:

```bash
./install.sh
```

This installs scripts to `~/.local/bin` and ArCHi data to
`~/.local/share/archi`. It does not overwrite an existing command registry and
does not add keybindings automatically. See [installation notes](docs/INSTALL.md).

Every install refreshes `commands.default.toml` for comparison. To replace an
existing active registry with the current defaults, while preserving a
timestamped backup, run `./install.sh --refresh-registry`.

Useful override variables:

- `ARCHI_HOME`: installed ArCHi data directory, default `~/.local/share/archi`;
- `ARCHI_BIN_DIR`: helper script directory, default `~/.local/bin`;
- `ARCHI_COMMANDS_PATH`: command registry path;
- `ARCHI_INTENTS_PATH`: independent HassIL diagnostic grammar path;
- `ARCHI_LOG_PATH`: command diagnostic log path;
- `ARCHI_TTS_SAY`: speech helper used by the router;
- `ARCHI_TRANSCRIPT_WAIT_TICKS`: transcript wait in tenths of a second,
  default `50` (five seconds);
- `POCKET_TTS_URL`, `POCKET_TTS_VOICE`, `POCKET_TTS_VOICE_FILE`, and
  `POCKET_TTS_VOLUME`: speech endpoint, voice, voice sample, and volume;
- `POCKET_TTS_TIMEOUT_SECONDS`: timeout for each TTS request, default `15`;
- `POCKET_TTS_DUCK_FACTOR`: volume multiplier for other playback while ArCHi
  speaks, default `0.25`.

The custom voice file is optional. Put a private sample at `assets/voice.wav`
before installing, or set `POCKET_TTS_VOICE_FILE`; otherwise ArCHi requests the
configured named voice, which defaults to `alba`.

To enable optional HassIL shadow comparison without modifying the system
Python environment:

```bash
uv pip install --target "${ARCHI_HOME:-$HOME/.local/share/archi}/vendor" 'hassil>=3,<4'
```

## Safety and privacy

ArCHi runs command definitions from `config/commands.toml`; commands are argv
arrays, never shell strings. Treat that registry as trusted configuration.

The default log contains command transcripts and desktop context. Use “off
record” before sensitive work, or set `ARCHI_LOG_PATH` to a location you
control. Do not commit logs or voice recordings.

## Project layout

```text
src/archi/       deterministic command router
config/          allowlisted command profile and diagnostic intent grammar
scripts/         push-to-talk, TTS, and utility entry points
docs/            installation and architecture notes
tests/           router behavior tests
```

See the [testing cheat sheet](docs/TESTING.md) for the current key map, every
accepted phrase, and the next-phase test matrix. See
[architecture notes](docs/ARCHITECTURE.md) for the runtime flow and trust
boundaries.

## Before publishing

Choose a license, replace user-specific command examples as needed, test on a
fresh Omarchy account, and add contribution and security guidance.
