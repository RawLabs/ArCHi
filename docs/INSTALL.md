# Installation notes

Run `./install.sh` from a checked-out ArCHi source tree. The installer copies
the router, adapter modules, default command profile, independent diagnostic
grammar, and helper scripts into standard XDG user locations. It never writes to
`/usr/share/omarchy`.

On later installs, the active `commands.toml` is preserved and the current
project default is written to `commands.default.toml`. Use
`./install.sh --refresh-registry` to back up and replace the active registry.

Defaults:

- scripts: `${ARCHI_BIN_DIR:-$HOME/.local/bin}`;
- router, registry, and `intents.yaml`:
  `${ARCHI_HOME:-$HOME/.local/share/archi}`;
- voice volume: `${XDG_CONFIG_HOME:-$HOME/.config}/archi/pocket-tts-volume`;
- runtime state: `${XDG_RUNTIME_DIR}/archi`.

The current prototype defaults to `ARCHI_DESKTOP_ADAPTER=omarchy`. Other values
are rejected until a corresponding tested adapter exists. This prevents an
untested desktop from receiving Omarchy or Hyprland commands accidentally.

To add ArCHi's toggle-to-talk binding, add the following to your personal
`~/.config/hypr/bindings.lua` and reload Hyprland:

```lua
hl.bind("SUPER + R", function()
  hl.dispatch(hl.dsp.exec_cmd("archi-control-start"))
  hl.dispatch(hl.dsp.submap("archi_control"))
end, { description = "Start ArCHi control mode" })

hl.define_submap("archi_control", function()
  hl.bind("SUPER + R", function()
    hl.dispatch(hl.dsp.exec_cmd("archi-control-stop"))
    hl.dispatch(hl.dsp.submap("reset"))
  end, { description = "Run ArCHi command" })

  hl.bind("ESCAPE", function()
    hl.dispatch(hl.dsp.exec_cmd("archi-control-cancel"))
    hl.dispatch(hl.dsp.submap("reset"))
  end, { description = "Cancel ArCHi command" })
end)
```

Press `Super+R` once to begin listening and again to stop and submit. While
listening, saying “ArCHi stop” also stops and submits through an active-only
local keyword monitor. `Escape` always cancels. ArCHi imposes a 120-second hard
limit and submits automatically when that limit is reached.

Voxtype's own recording limit must be at least as long as ArCHi's. Set this in
`~/.config/voxtype/config.toml` and restart the `voxtype.service` user unit:

```toml
[audio]
max_duration_secs = 120
```

An accessible left-hand pair can use `SUPER + R` for ArCHi and
`SUPER + SHIFT + R` for normal Voxtype dictation:

```lua
hl.bind("SUPER + SHIFT + R", function()
  hl.dispatch(hl.dsp.exec_cmd("voxtype record start"))
  hl.dispatch(hl.dsp.submap("voxtype_dictation"))
end, { description = "Start dictation" })

hl.define_submap("voxtype_dictation", function()
  hl.bind("SUPER + SHIFT + R", function()
    hl.dispatch(hl.dsp.exec_cmd("voxtype record stop"))
    hl.dispatch(hl.dsp.submap("reset"))
  end, { description = "Stop dictation" })

  hl.bind("ESCAPE", function()
    hl.dispatch(hl.dsp.exec_cmd("voxtype record cancel"))
    hl.dispatch(hl.dsp.submap("reset"))
  end, { description = "Cancel dictation" })
end)
```

Optional ArCHi voice-volume bindings:

```lua
o.bind("SUPER + CTRL + DOWN", "ArCHi voice volume down", "pocket-tts-volume lower", { repeating = true })
o.bind("SUPER + CTRL + UP", "ArCHi voice volume up", "pocket-tts-volume raise", { repeating = true })
```

`pocket-tts-volume status` shows the current ArCHi voice level without changing
it. The helper controls ArCHi speech playback only; system volume remains under
the normal Omarchy audio bindings.

ArCHi shows brief `Listening`, `Heard`, and outcome overlays through
`omarchy-osd`. They are not notification-center entries and do not take focus.
Set `ARCHI_FEEDBACK=off` before starting capture to disable these overlays.

Use `hyprctl reload` followed by `hyprctl configerrors` after changing the
binding file.

## Optional integrations

### Optional custom voice

The default Pocket TTS voice is `alba`; a fresh install needs no downloaded
sample. Set `POCKET_TTS_VOICE` to select another named voice supported by your
local endpoint.

To choose your own sample, open the
[ElevenLabs Voice Library](https://elevenlabs.io/app/voice-library) and search
for “Savvy — warm, grounded & natural” or another voice. Download a sample you
have permission to use as a local voice reference. ArCHi does not bundle these
samples or download them automatically.

If the download is MP3, convert it to WAV using `ffmpeg`:

```bash
mkdir -p assets
ffmpeg -i "/path/to/downloaded-sample.mp3" -ac 1 -ar 24000 assets/voice.wav
./install.sh
```

Alternatively, set `POCKET_TTS_VOICE_FILE` to an existing WAV sample's absolute
path in the environment that launches ArCHi. A sample takes precedence over
the named voice. Keep it local; `assets/voice.wav` is excluded from Git.
To return to the default voice, unset `POCKET_TTS_VOICE_FILE` and
`POCKET_TTS_VOICE`, and remove the installed sample at
`${ARCHI_HOME:-$HOME/.local/share/archi}/assets/voice.wav`.
The installer also migrates a legacy `$ARCHI_HOME/savvy.wav` sample into that
location; remove the legacy sample too if present when reverting to default.

### Optional intent diagnostics

Install HassIL into ArCHi's private vendor directory to enable shadow parsing:

```bash
uv pip install --target "${ARCHI_HOME:-$HOME/.local/share/archi}/vendor" 'hassil>=3,<4'
```

HassIL results remain diagnostic-only and cannot choose an executable action.
Use `archi-shadow-report --details` to summarize comparisons, command coverage,
power-state distribution, and phrases that need review.

For the supported beta boundary, update procedure, and test/reporting loop, see
[beta operations](BETA.md).
