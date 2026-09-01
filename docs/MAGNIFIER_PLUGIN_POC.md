# Magnifier capability plugin proof of concept

This document specifies the first ArCHi capability plugin proof of concept:
a user-selectable screen magnifier controlled through ArCHi's accessibility
harness. It is intended to be detailed enough for outside technical review
before implementation.

## Purpose

The PoC validates ArCHi's core product idea: a user expresses an accessibility
need, ArCHi discovers suitable Linux services for the current system, helps the
user select and install one, then exposes a stable control vocabulary over the
selected provider.

The user-facing need is:

```text
I need screen magnification.
```

ArCHi should not become a magnifier engine. It should coordinate an installed
desktop, compositor, or package-provided magnifier.

## User experience target

Primary commands:

```text
archi magnify
archi mag on
archi mag off
archi mag more
archi mag less
archi magnify more
archi magnify less
```

Preferred behavior:

- `mag on` shows a magnified view that follows the pointer.
- `mag off` removes the magnified view and restores normal desktop state.
- `mag more` increases zoom.
- `mag less` decreases zoom.
- Mouse wheel zoom is enabled only while ArCHi has explicitly entered
  magnifier control mode, if the selected backend supports it safely.
- `Escape` remains a universal cancel/exit path where compositor state allows
  it.

Setup flow:

```text
User: archi magnifier setup

ArCHi:
  Magnifier options for this system:
  1. HyprMag - pointer-following lens; install via AUR; known caveat: may
     freeze display content while active.
  2. wl-mirror controller - wlroots-compatible screen mirror; more composable;
     requires ArCHi controller glue for pointer-following region updates.
  3. Hyprland cursor zoom - compositor-local fallback; not a lens.

User selects a provider.
ArCHi requests install approval if missing.
ArCHi saves the selected provider.
ArCHi exposes the same magnifier commands regardless of provider.
```

## Non-goals

- Do not build a new compositor, renderer, or computer-vision magnifier.
- Do not download and run unaudited install scripts.
- Do not silently install packages.
- Do not silently enable screen capture, remote input, or persistent privileged
  services.
- Do not assume GNOME, KDE, Hyprland, or any one package manager.
- Do not make mouse-wheel interception global unless the user explicitly chose
  magnifier mode and the backend can exit reliably.

## Capability model

The PoC introduces one capability family:

```text
capability: visual.magnifier
```

Provider interface:

```text
status() -> MagnifierStatus
available() -> Availability
install_plan() -> InstallPlan
enable(options) -> ActionResult
disable() -> ActionResult
zoom_in(step) -> ActionResult
zoom_out(step) -> ActionResult
set_zoom(level) -> ActionResult
```

Suggested status fields:

```text
provider_id
installed
running
enabled
zoom_level
min_zoom
max_zoom
supports_lens
supports_fullscreen_zoom
supports_pointer_follow
supports_focus_follow
supports_caret_follow
supports_wheel_zoom
supports_crosshairs
requires_screen_capture_permission
requires_compositor_plugin
last_error
```

Action results must be structured:

```text
status: success | unavailable | unsupported | denied | failed
provider_id
message
details
requires_user_action
```

The router should handle `unavailable`, `unsupported`, and `denied` as normal
outcomes. It must not fall through to coordinate clicks or visual guessing.

## Capability catalog

The PoC should add a catalog file, tentatively:

```text
config/capabilities.toml
```

Example shape:

```toml
[[capabilities]]
id = "visual.magnifier"
display_name = "Screen magnifier"
description = "Magnifies the desktop through a native or package-provided provider."

[[capabilities.providers]]
capability = "visual.magnifier"
id = "hyprmag"
display_name = "HyprMag"
desktops = ["hyprland", "wlroots"]
package_managers = ["aur"]
packages.arch_aur = ["hyprmag-git"]
features = ["lens", "pointer_follow", "zoom_factor", "pixel_grid"]
caveats = ["May freeze display content while magnifying; verify on target system."]
adapter = "archi.providers.magnifier.hyprmag"

[[capabilities.providers]]
capability = "visual.magnifier"
id = "wl_mirror"
display_name = "wl-mirror controller"
desktops = ["hyprland", "sway", "wlroots"]
package_managers = ["pacman", "aur"]
packages.arch = ["wl-mirror"]
features = ["windowed_mirror", "region_capture", "cursor_display"]
caveats = ["Requires ArCHi controller glue for pointer-following lens behavior."]
adapter = "archi.providers.magnifier.wl_mirror"

[[capabilities.providers]]
capability = "visual.magnifier"
id = "gnome_zoom"
display_name = "GNOME Zoom"
desktops = ["gnome"]
features = ["native_zoom", "pointer_follow", "lens", "crosshairs", "color_filters"]
caveats = ["Only available in GNOME Shell sessions."]
adapter = "archi.providers.magnifier.gnome_zoom"

[[capabilities.providers]]
capability = "visual.magnifier"
id = "kde_zoom"
display_name = "KDE Plasma Zoom and Magnifier"
desktops = ["kde", "plasma"]
features = ["native_zoom", "magnify_region", "pointer_follow", "focus_follow", "caret_follow"]
caveats = ["Only available in KDE Plasma sessions."]
adapter = "archi.providers.magnifier.kde_zoom"

[[capabilities.providers]]
capability = "visual.magnifier"
id = "hyprland_cursor_zoom"
display_name = "Hyprland cursor zoom"
desktops = ["hyprland"]
features = ["compositor_zoom", "pointer_centered"]
caveats = ["Fallback only; not a movable lens and may lack push tracking."]
adapter = "archi.providers.magnifier.hyprland_cursor_zoom"
```

Catalog entries are metadata, not authority. Install and control adapters still
perform runtime checks before acting.

## Detection

System detection should be read-only and explainable.

Inputs:

- distro ID and version from `/etc/os-release`;
- session type from `XDG_SESSION_TYPE`;
- desktop/compositor from `XDG_CURRENT_DESKTOP`, `DESKTOP_SESSION`, Hyprland
  environment, and `hyprctl version` when available;
- package manager availability, such as `pacman`, `yay`, `paru`, `dnf`, `apt`,
  `zypper`, or `flatpak`;
- installed provider binaries, such as `hyprmag`, `wl-mirror`, `gsettings`,
  `qdbus6`, `kwriteconfig6`, and relevant desktop commands;
- portal availability where a provider needs screen capture.

Output:

```text
provider_id
availability: installed | installable | unsupported | unknown
reason
install_plan_id
features
caveats
```

For the current Omarchy/Hyprland test system, expected detection is:

```text
desktop: hyprland
distro_family: arch
installed_candidates: none known yet
installable_candidates:
  - hyprmag via AUR helper, if yay or paru is present
  - wl-mirror via pacman/AUR, depending on repo availability
fallback_candidates:
  - Hyprland cursor zoom, if controllable through current Hyprland config/IPC
not_primary:
  - GNOME Zoom
  - KDE Plasma Zoom
```

## Install policy

Package installation is a privileged and user-visible operation.

Rules:

- Prefer the operating system package manager.
- Prefer distro packages over AUR or source builds when both satisfy the same
  capability.
- AUR packages require a stronger warning than official repository packages.
- Never install through `curl | sh`.
- Show the exact package manager command before execution.
- Ask for explicit approval before installing.
- Record provider selection separately from package installation.
- If install succeeds but runtime detection fails, report `failed` with the
  provider's diagnostic output.

Install plan example:

```text
provider: hyprmag
manager: yay
command: yay -S hyprmag-git
risk: AUR package; review PKGBUILD before installing
post_check: command -v hyprmag
```

## Provider selection

Selection should be explicit:

```text
archi capability list visual.magnifier
archi capability explain visual.magnifier
archi capability select visual.magnifier hyprmag
archi capability install visual.magnifier hyprmag
```

Persisted selection, tentative:

```toml
[capabilities.visual.magnifier]
provider = "hyprmag"
zoom_level = 2.0
wheel_zoom = false
```

Suggested path:

```text
${XDG_CONFIG_HOME:-$HOME/.config}/archi/capabilities.toml
```

The selected provider should not be considered available until its adapter
reports a successful runtime check.

## Backend notes

### HyprMag

Fit:

- closest match for a pointer-following lens on wlroots/Hyprland;
- simple user model: launch it, move the mouse.

Known review questions:

- Does it block or freeze normal interaction while active?
- Can zoom be changed at runtime, or only at process start?
- Can ArCHi cleanly terminate it without leaving screen/cursor artifacts?
- Does it work across multiple monitors and fractional scaling?
- Is the AUR package acceptable for the target user population?

### wl-mirror controller

Fit:

- composable wlroots building block;
- supports mirrored regions and cursor display;
- better candidate for long-term controller behavior if dynamic region updates
  are reliable.

Known review questions:

- Is `wl-mirror` packaged for the target distro?
- Can stdin/pipectl updates move the mirrored source region fast enough to
  follow the pointer?
- Can the lens window be kept above other windows in Hyprland without fragile
  rules?
- How does it behave under multiple monitors, scale factors, and rotated
  displays?

### GNOME Zoom

Fit:

- mature native magnifier on GNOME;
- supports pointer tracking, lens mode, crosshairs, and visual adjustments.

Control should use GNOME-supported settings or D-Bus, not synthetic input.

Known review questions:

- Which GSettings keys and D-Bus methods are stable enough for adapter use?
- How should ArCHi preserve and restore the user's existing GNOME Zoom
  preferences?

### KDE Plasma Zoom and Magnifier

Fit:

- mature native desktop effects;
- supports full-screen zoom, magnify region, pointer tracking, focus tracking,
  and caret tracking.

Known review questions:

- Which KWin/KConfig interfaces are stable for enabling effects and changing
  zoom?
- Can ArCHi preserve and restore existing user settings cleanly?

### Hyprland cursor zoom

Fit:

- local fallback on the current compositor;
- likely simpler than installing a third-party tool.

Known review questions:

- Is runtime control available through Hyprland IPC/config reload without
  creating a fragile state loop?
- Does it satisfy the user's lens-following-pointer need, or only provide a
  centered zoom fallback?

## Router integration

New intents should map to structured capability requests, not directly to argv.

Examples:

```text
archi magnify       -> visual.magnifier.enable
archi mag on        -> visual.magnifier.enable
archi mag off       -> visual.magnifier.disable
archi mag more      -> visual.magnifier.zoom_in
archi mag less      -> visual.magnifier.zoom_out
magnifier setup     -> capability.setup visual.magnifier
```

The current `commands.toml` can temporarily call a CLI wrapper, but the PoC
should make that wrapper route through the capability broker so the stable
intent is not tied to a specific backend binary.

## Feedback

Feedback must not assume speech-only use.

Minimum feedback events:

```text
magnifier.available_options
magnifier.selected
magnifier.install_required
magnifier.install_started
magnifier.enabled
magnifier.disabled
magnifier.zoom_changed
magnifier.unavailable
magnifier.failed
```

Each event should be routable to speech, caption/OSD, logs, and later braille
or haptic output.

Example:

```text
Speech: "Magnifier on, HyprMag, 2x."
Caption: "Magnifier: on - HyprMag - 2x"
Log: provider_id=hyprmag action=enable status=success
```

## Security and privacy

Risks:

- magnifiers may require screen capture or compositor-level access;
- packages may come from AUR or third-party repositories;
- wheel interception can affect unrelated applications;
- a stuck magnifier can impair usability;
- logs may reveal active desktop context.

Required controls:

- explicit activation;
- explicit install approval;
- visible provider selection;
- no unreviewed install scripts;
- no private screen content in logs by default;
- reliable `off` command and `Escape` path where possible;
- provider failure must leave the desktop in a known state;
- all package/install commands are logged as metadata, not raw screen content.

## Test plan

Read-only tests:

- catalog parses and validates provider IDs;
- system detector identifies distro, session type, compositor, package managers,
  and installed binaries;
- unavailable providers explain why they are unavailable;
- selected provider is rejected if unavailable at runtime.

Router tests:

- `archi magnify` maps to `visual.magnifier.enable`;
- `archi mag off` maps to `visual.magnifier.disable`;
- `archi mag more` maps to `visual.magnifier.zoom_in`;
- `archi mag less` maps to `visual.magnifier.zoom_out`;
- command behavior is unchanged when no magnifier provider is selected except
  for an explicit `unavailable` response.

Install tests:

- dry-run install shows the exact package command;
- install requires approval;
- official repo packages are preferred over AUR when equivalent;
- AUR install plans show an AUR warning;
- failed post-install detection reports `failed` and does not select provider.

Provider acceptance tests on Omarchy/Hyprland:

- setup lists Hyprland-compatible candidates;
- selected provider can turn magnifier on and off three times in a row;
- zoom level can increase and decrease without restarting the desktop;
- pointer-following behavior works on the active monitor;
- failure or cancel leaves no stuck overlay, process, submap, or global wheel
  interception;
- `archi mag off` works when the magnifier is already off.

Manual accessibility review:

- can a low-vision user discover the feature without knowing package names?
- are tradeoffs understandable before installation?
- is the escape path obvious and reliable?
- does the selected backend interact safely with screen readers and speech
  feedback?
- does magnification preserve enough pointer context to be useful?

## Exit criteria

The PoC is successful when:

- ArCHi can list magnifier providers for the current OS/session;
- the user can select one provider through ArCHi;
- ArCHi can install or explain how to install the selected provider using the
  OS package path;
- ArCHi exposes one stable command set over that provider;
- enabling, disabling, and zoom changes are deterministic and logged as
  provider actions;
- unsupported systems produce a clear explanation instead of silent failure;
- the design generalizes cleanly to the next capability family, such as speech
  output, screen reading, captions, or braille.

## Outside review checklist

Ask reviewers to examine:

- whether the provider interface is generic enough for GNOME, KDE, Hyprland,
  and wlroots tools;
- whether provider selection and installation are separated cleanly;
- whether package-manager policy is acceptable for Linux distributions beyond
  Arch/Omarchy;
- whether the security controls are sufficient for screen-capture-adjacent
  providers;
- whether the user-facing vocabulary is stable and accessible;
- whether this PoC proves the ArCHi harness model without overfitting to one
  magnifier backend.

## Source references for provider research

- GNOME screen magnifier:
  <https://help.gnome.org/gnome-help/a11y-mag.html>
- GNOME magnification design notes:
  <https://wiki.gnome.org/Projects%282f%29GnomeShell%282f%29Magnification.html>
- KDE Plasma accessibility Zoom and Magnifier:
  <https://docs.kde.org/stable_kf6/en/plasma-desktop/kcontrol/kcmaccess/index.html>
- wl-mirror:
  <https://github.com/Ferdi265/wl-mirror>
- hyprmag:
  <https://github.com/SIMULATAN/hyprmag>
- Hyprland cursor zoom limitation discussion:
  <https://github.com/hyprwm/Hyprland/issues/5972>
