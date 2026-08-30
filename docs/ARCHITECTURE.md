# Architecture notes

ArCHi is intentionally small: push-to-talk capture produces one transcript,
the router matches that transcript against an allowlisted registry, and the
matched argv array is executed directly. There is no shell command synthesis and
no always-on microphone listener.

## Runtime flow

1. `archi-control-start` creates a private runtime directory under
   `${XDG_RUNTIME_DIR}/archi`, starts a short Voxtype recording, and assigns a
   session id.
2. `archi-control-stop` stops Voxtype, reads the transcript, and pipes it to
   `router.py`. It exports capture-session and post-stop transcript-wait timing
   so AC/battery behavior can be compared later.
3. `router.py` normalizes the phrase, strips an optional `ArCHi` or `archie`
   wake-style prefix, and matches the result against `commands.toml`.
4. The matched command either replies, updates logging state, asks for
   clarification, launches a background process, or runs a foreground argv
   command.
5. Spoken responses go through `pocket-tts-say`, which calls the configured
   Pocket TTS-compatible endpoint, ducks other output streams while ArCHi is
   speaking, and plays the result with PipeWire. Speech jobs are serialized so
   one ArCHi response cannot duck or overwrite another response's state.
6. When HassIL is available, it independently evaluates `intents.yaml`. The log
   labels its relationship to production as `agree`, `shadow_extension`,
   `shadow_regression`, `conflict`, or `not_comparable`.

## State

- Runtime files live under `${XDG_RUNTIME_DIR}/archi`.
- Persistent voice volume lives at
  `${XDG_CONFIG_HOME:-$HOME/.config}/archi/pocket-tts-volume`.
- Command diagnostics default to
  `$HOME/.local/state/archi/commands.jsonl`, unless `ARCHI_LOG_PATH` is set.
- Clipboard read diagnostics default to `clipboard.jsonl` beside the command
  log. They contain only byte count, SHA-256 digest, and success/failure state;
  clipboard text is never logged.
- Installed router and command defaults live under `ARCHI_HOME`, defaulting to
  `$HOME/.local/share/archi`.
- The active registry is `commands.toml`; the latest installed project default
  is kept separately as `commands.default.toml` for safe comparison.
- The independent, project-managed shadow grammar is `intents.yaml`.

## Trust boundaries

`config/commands.toml` is trusted local configuration. It stores argv arrays
instead of shell snippets, but a command in that file can still launch programs
or alter the desktop. Review command changes as code.

`hassil`, when installed, is used only as a shadow parser for diagnostics. Its
grammar maps only to IDs present in the trusted command registry. Its result is
logged for comparison and never decides which command runs.

Wake-word activation is out of scope for the current default setup. Adding it
would require a separate, explicit always-on local listener and visible user
controls.
