# Beta Operations

ArCHi `0.1.0b1` is a local beta for the Omarchy/Hyprland voice-command slice.
It is suitable for deliberate day-to-day testing, not unattended control or
use on an untested desktop adapter.

## Supported beta scope

- explicit push-to-talk capture through Voxtype;
- local transcript routing through the allowlisted operational registry;
- live XDG application discovery for `open`, `launch`, `start`, `close`,
  `quit`, and `exit` commands;
- Omarchy/Hyprland actions through `omarchy.hyprland`;
- local Pocket TTS-compatible speech output;
- transparent, non-focus-stealing Omarchy OSD feedback;
- local diagnostic logging and optional HassIL shadow comparison.

The beta does not provide a wake word, always-on microphone, voice-triggered
dictation mode, AT-SPI control, a general provider broker, a plugin loader, or
support for GNOME, COSMIC, KDE, X11, or Pop!_OS. Normal Voxtype dictation may
remain configured on its separate hotkey, but it is not controlled by ArCHi.

## Normal operation

1. Press `Super + R` to start a command capture. A short `Listening` OSD
   confirms that recording began.
2. Press `Super + R` again, say `ArCHi stop`, or wait for the 120-second limit.
3. ArCHi briefly displays `Heard: ...`, resolves the phrase, and then displays
   the result. The OSD is an overlay, not a notification-center entry, and it
   never takes keyboard or pointer focus.
4. On a successful app request, the selected XDG desktop entry is launched or
   the best matching app window is closed. On an unknown or ambiguous phrase,
   no desktop action is run.

`Escape` cancels an active command capture. `ARCHI_FEEDBACK=off` disables the
visual overlays. Routine command speech remains controlled by the command
registry and Pocket TTS configuration.

## App matching policy

Operational commands are exact allowlisted phrases. Installed apps refresh from
the live XDG registry for every routed command. App matching accepts spaces,
separately spoken letters, q/c/k equivalence, and one character correction for
an unambiguous name of at least five characters. A candidate shared by more
than one installed app is rejected rather than guessed.

## Updating the beta

Run `./install.sh` from the checked-out source tree. It updates scripts,
router modules, adapters, default registry, diagnostic grammar, and docs in the
installed ArCHi directory. It preserves the active `commands.toml`.

Use `./install.sh --refresh-registry` only when intentionally replacing the
active operational registry. The installer creates a timestamped backup first.

## Beta test loop

Use the [testing sheet](TESTING.md) for the detailed command matrix. For each
test session, verify at least one success, one unknown phrase, one cancelled
capture, one open/close app pair, and one visual feedback sequence. Test a
destructive action such as close or lock only after confirming the target.

Review the local log after a session:

```bash
tail -n 40 ~/.local/state/archi/commands.jsonl | jq -r \
  '(.timestamp | todateiso8601) + " | " + .result + " | " + (.normalized_phrase // "") + " | " + (.matched_command_id // "-")'
```

Keep transcripts private. Use `off record` before sensitive work. Do not attach
raw logs, voice samples, or recordings to a public report without review.

## What to record as a beta issue

Record the time, the exact spoken phrase, normalized phrase, selected command
ID, result, provider ID, and whether the OSD appeared. Describe unintended
actions immediately; do not work around them by adding broad aliases. Repeated
recognition misses can justify a narrow, tested app-resolution change.
