# Local voice controls on Omarchy

ArCHi uses explicit command capture through local Voxtype recognition. Each
phrase is matched against inspectable commands and sent to Omarchy or Hyprland's
existing controls. No chatbot, cloud model, or paid API is involved. ArCHi's
spoken reply uses the configured local TTS helper or local Pocket TTS endpoint.

## Apps from the app menu

Say `open`, `launch`, or `start` followed by an app's menu name, such as
`open Audacity`. Use `close`, `quit`, `exit`, or `dismiss` to request that app's
most recently focused matching window close. Use `switch to`, `focus`, or
`show` to bring an existing app window forward. Optional `the` is accepted:
`close the browser` and `switch to the terminal` work.

ArCHi refreshes menu entries for every command, so app installs and removals
need no manual registry edits. It honors hidden entries, desktop visibility,
`TryExec` availability, and Omarchy's `launcher.hides`. Run `archi-cheatsheet`
to see the apps currently discovered and an accepted opening phrase for each.

Everyday names resolve only to apps in that discovered list:

| Name | Selection |
|---|---|
| browser / web browser / default browser | Default HTTPS handler |
| terminal / console | Default entry reported by `xdg-terminal-exec` |
| files / file manager / file browser | Default directory handler |
| editor / text editor / code editor | Default plain-text handler |
| video player | Default MP4 handler |
| image viewer / photo viewer | Default PNG handler |
| PDF viewer / PDF reader / document viewer | Default PDF handler |
| music / music player | One discovered app with the Music Player alias |
| calculator | One discovered app with the Calculator alias |

Configured defaults resolve role names even when several apps have the same
generic name. Other shared aliases are omitted; use a unique app name instead.
Focus commands require an open matching window. Close commands target one
window and let the app present its own save/discard prompt; they do not force
the process to quit. Browser tabs, navigation, and other in-app actions are
outside this command set.

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

App discovery, everyday app names, and open/close/focus phrases are generated
by the router. Updating with `./install.sh` enables those changes without
refreshing the active command registry.

This first slice is supported on Omarchy/Hyprland. It has automated router and
adapter tests; live zoom behavior must be checked in an active Hyprland session.
