# Platform support

ArCHi does not claim uniform support across every Linux desktop. Linux provides
portable discovery standards, but window management, workspaces, screenshots,
audio integration, and accessibility settings are desktop-specific.

## Current support boundary

| Layer | Current status | Boundary |
|---|---|---|
| Core router, policy, logging | Portable | Python 3.11+ on Linux |
| Installed application discovery | Portable | XDG `.desktop` entries, including common Flatpak and Snap export locations |
| Desktop context and actions | Beta supported | Omarchy on Hyprland through `omarchy.hyprland` |
| Pop!_OS | Planned validation | Adapter depends on whether the test system uses COSMIC or GNOME |
| GNOME, COSMIC, KDE, other Wayland compositors, X11 | Unsupported today | Requires a tested adapter; core must not guess |

The beta defaults to the `omarchy` desktop adapter. An unknown adapter is an
explicit `unavailable` result. ArCHi must never compensate for a missing
desktop capability with broad process termination, synthetic shell commands,
or an uncertain window target.

## Adapter contract

A desktop adapter:

- identifies itself with a stable provider ID;
- advertises supported capability IDs;
- returns structured `success`, `attention`, `unsupported`, `unavailable`, or `failed`
  results;
- captures only the desktop context owned by that integration;
- contains every compositor- or distribution-specific command;
- validates targets before performing a consequential action.

The current adapter is `src/archi/adapters/omarchy.py`. The core registry asks
for capabilities such as `app.open`, `app.close`, `app.focus`, `window.close_active`, and
`workspace.next`; it never names `hyprctl` or an `omarchy-*` executable.

## Adapters and plugins

Adapters connect a stable ArCHi capability to an existing system implementation.
Plugins are future packages that may contribute capabilities, provider metadata,
and adapters. They are not interchangeable terms: a magnifier can be a plugin,
while Hyprland, GNOME, or COSMIC implementations are provider adapters within
that capability.

No dynamic plugin loader is part of the current prototype. A second tested
desktop, beginning with Pop!_OS, should validate the adapter contract before the
project commits to plugin discovery or compatibility guarantees.
