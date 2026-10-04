# Local voice controls on Omarchy

ArCHi uses explicit command capture through local Voxtype recognition. Each
phrase is matched against inspectable commands and sent to Omarchy or Hyprland's
existing controls. No chatbot, cloud model, or paid API is involved. ArCHi's
spoken reply uses the configured local TTS helper or local Pocket TTS endpoint.

## Zoom conversation

Press the ArCHi capture hotkey for each phrase (or use the active-capture verbal
stop). A short sequence can be:

```text
"zoom"       -> increase Omarchy's native cursor zoom by one step
"more"       -> increase zoom again
"less"       -> decrease zoom by one step, stopping at normal size
"zoom out"   -> reset zoom to 1x, like Omarchy's reset-zoom binding
"cancel"     -> restore the zoom level from before ArCHi started adjusting it
```

Other phrases include `zoom in`, `magnify the screen`, `make everything bigger`,
`zoom less`, `reduce zoom`, `reset zoom`, and `normal size`. Omarchy's own zoom
bindings continue to work. ArCHi reads and changes the same Hyprland
`cursor:zoom_factor` setting; it does not simulate keypresses or draw a separate
magnifier.

`more` and `less` refer to the last zoom or volume adjustment for two minutes.
For example, `volume up`, `more`, `less` changes system volume through Omarchy's
audio command. Another recognized command ends that adjustment context. With no
context, `more` and `less` do nothing. `cancel` ends volume adjustment context;
it does not undo a prior volume change.

When ArCHi starts zooming, it remembers the previous factor. `cancel` restores
that factor. If a keyboard binding or another tool changed zoom meanwhile,
ArCHi leaves that newer setting alone. `zoom out` explicitly resets to 1x.

## Installing updated commands

`./install.sh` updates the router and adapter while preserving an existing
active `commands.toml`. To enable the new zoom phrases in that active registry,
review `${ARCHI_HOME:-$HOME/.local/share/archi}/commands.default.toml`, then
run `./install.sh --refresh-registry`. The installer backs up the active
registry before replacing it. Reapply any local command edits from that backup.

This first slice is supported on Omarchy/Hyprland. It has automated router and
adapter tests; live zoom behavior must be checked in an active Hyprland session.
