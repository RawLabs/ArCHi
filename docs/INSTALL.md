# Installation notes

Run `./install.sh` from a checked-out ArCHi source tree. The installer copies
the router, default command profile, and helper scripts into standard XDG user
locations. It never writes to `/usr/share/omarchy`.

Defaults:

- scripts: `${ARCHI_BIN_DIR:-$HOME/.local/bin}`;
- router and default registry: `${ARCHI_HOME:-$HOME/.local/share/archi}`;
- voice volume: `${XDG_CONFIG_HOME:-$HOME/.config}/archi/pocket-tts-volume`;
- runtime state: `${XDG_RUNTIME_DIR}/archi`.

To add a push-to-talk binding, add the following to your personal
`~/.config/hypr/bindings.lua` and reload Hyprland:

```lua
hl.bind("SUPER + R", function()
  hl.dispatch(hl.dsp.exec_cmd("archi-control-start"))
  hl.dispatch(hl.dsp.submap("archi_control"))
end, { description = "Start ArCHi control mode" })

hl.define_submap("archi_control", function()
  hl.bind("RETURN", function()
    hl.dispatch(hl.dsp.exec_cmd("archi-control-stop"))
    hl.dispatch(hl.dsp.submap("reset"))
  end, { description = "Run ArCHi command" })

  hl.bind("ESCAPE", function()
    hl.dispatch(hl.dsp.exec_cmd("archi-control-cancel"))
    hl.dispatch(hl.dsp.submap("reset"))
  end, { description = "Cancel ArCHi command" })
end)
```

Optional ArCHi voice-volume bindings:

```lua
hl.bind("SUPER + CTRL + DOWN", function()
  hl.dispatch(hl.dsp.exec_cmd("pocket-tts-volume lower"))
end, { description = "ArCHi voice volume down", repeatable = true })

hl.bind("SUPER + CTRL + UP", function()
  hl.dispatch(hl.dsp.exec_cmd("pocket-tts-volume raise"))
end, { description = "ArCHi voice volume up", repeatable = true })
```

`pocket-tts-volume status` shows the current ArCHi voice level without changing
it. The helper controls ArCHi speech playback only; system volume remains under
the normal Omarchy audio bindings.

Use `hyprctl reload` followed by `hyprctl configerrors` after changing the
binding file.
