## Evaluation: this is a strong first ArCHi PoC

The core choice is right. Magnification is small enough to implement, immediately testable by a human, but complicated enough to prove the actual ArCHi proposition: **need → discovery → provider selection → installation/control → stable vocabulary → feedback/failure handling**. That is exactly what the document describes rather than trying to turn ArCHi into another magnifier. 

I would rate the architecture **8.5/10 as a PoC specification**. I would make several changes before implementation.

### 1. Promote Hyprland native zoom to Provider #1

For the Omarchy machine, I would reverse the current ordering:

| Order | Provider             | Role in PoC                             |
| ----- | -------------------- | --------------------------------------- |
| **1** | Hyprland cursor zoom | Built-in baseline                       |
| **2** | wl-mirror            | External-package / richer-provider test |
| **3** | HyprMag              | Experimental alternative                |
| 4     | GNOME Zoom           | Catalog/probe initially                 |
| 5     | KDE Zoom             | Catalog/probe initially                 |

Hyprland's `cursor:zoom_factor` is runtime controllable today. Recent Hyprland Lua-config discussions show reading/changing it dynamically, including increment/decrement logic and zoom modes. ([GitHub][1])

That's actually ideal for ArCHi.

The first successful interaction becomes:

```text
$ archi magnifier setup

Detected:
  Hyprland native zoom
  Status: built in
  Install: none
  Pointer follow: yes
  Lens: no
  Push tracking: no

Use it?
```

Then:

```text
archi mag on
archi mag more
archi mag less
archi mag off
```

If that works, you've proved **ArCHi**, without first having to prove some third-party software.

Hyprland's limitation is also useful to the architecture: users have specifically requested KDE-style push-on-edge behavior because Hyprland's cursor zoom does not provide it. ([GitHub][2])

So ArCHi can truthfully say:

> Built-in magnification is available. It follows the pointer but does not provide a movable lens or push tracking. Two additional providers are available.

That's precisely the broker behavior you're trying to demonstrate.

---

## 2. wl-mirror is stronger than the document currently gives it credit for

One factual update: on current Arch, **`wl-mirror` is in the official `extra` repository**, version 0.18.5 in the current Arch documentation. So on Omarchy it should be:

```toml
package_managers = ["pacman"]
packages.arch = ["wl-mirror"]
```

not “pacman/AUR depending on repo availability.” ([Arch Manual Pages][3])

More importantly, upstream already supports:

* custom screen regions;
* displaying the cursor;
* runtime region changes;
* stream input;
* fractional scaling;
* rotated/flipped outputs;
* multiple capture backends. ([GitHub][4])

So this:

> requires ArCHi controller glue for pointer-following region updates

is accurate, but the glue is considerably less speculative than it sounds. The primitive needed by the controller is already explicitly supported.

That makes `wl-mirror` an excellent **second-stage provider** because it proves another fundamental ArCHi idea:

```text
same capability
same user vocabulary
completely different implementation
```

That's the architectural test that matters.

---

## 3. Keep HyprMag, but mark it EXPERIMENTAL

The current document treats its freeze behavior appropriately as a caveat, but I would go one step stronger.

HyprMag itself explicitly says it **“Freezes” your displays while magnifying**. Its interface is essentially launch, move mouse, with startup options for radius, scale and grid. ([GitHub][5])

Therefore:

```toml
stability = "experimental"
recommended = false
```

or equivalent.

It shouldn't ever win automatic preference simply because it offers the closest feature match.

That itself proves another worthwhile ArCHi concept:

> Feature count is not provider ranking.

A provider can support `lens` and still rank below a simpler provider because its operational caveat is severe.

---

# The biggest architectural item missing: **state ownership**

This is the main thing I would add before coding.

Suppose a GNOME user already has:

```text
Zoom = enabled
Zoom = 1.75x
Crosshairs = enabled
Pointer tracking = push
```

Then they say:

```text
archi mag on
archi mag more
archi mag off
```

What does **off** mean?

It must not necessarily mean:

```text
disable GNOME magnification
reset everything
```

ArCHi needs to distinguish:

```text
SYSTEM STATE
    ↓
ArCHi acquires capability session
    ↓
snapshot existing state
    ↓
ArCHi makes temporary changes
    ↓
ArCHi releases capability session
    ↓
restore appropriate prior state
```

I'd therefore add something like:

```text
snapshot() -> ProviderState
restore(state) -> ActionResult
```

or put equivalent ownership in the capability broker itself.

This becomes much more important with:

* magnification;
* screen readers;
* speech;
* captions;
* pointer settings;
* contrast;
* keyboard accessibility;
* input remapping.

**ArCHi shouldn't assume it owns accessibility state just because it can control it.**

That is probably the biggest reusable lesson this first plugin can establish.

---

# Second architecture change: separate detection concepts more clearly

Right now:

```text
installed
running
enabled
```

works for HyprMag, but gets muddy for GNOME/KDE/Hyprland.

Hyprland zoom isn't really “installed.” It's a compositor feature.

I'd model something closer to:

```text
provider_id
present
usable
active

source:
  builtin
  system_package
  user_package
  third_party

install_state:
  not_applicable
  missing
  installed

runtime_state:
  inactive
  active
  degraded
  unknown
```

Then:

```text
Hyprland zoom:
present=true
usable=true
source=builtin
install_state=not_applicable
runtime_state=inactive
```

versus:

```text
wl-mirror:
present=false
usable=false
source=system_package
install_state=missing
```

Much cleaner for future capabilities.

---

# Third: make provider ranking an actual concept

Your detection currently returns candidates, but ArCHi will eventually need to answer:

> Which one should I use?

I'd add provider metadata such as:

```toml
maturity = "stable"
trust = "official_repo"
integration = "native"
```

and let the broker produce something like:

```text
Recommended

1. Hyprland Zoom
   Built in
   No installation
   Reliable
   Basic magnification

2. wl-mirror
   Official Arch package
   Richer magnifier possible
   Requires ArCHi controller

Experimental

3. HyprMag
   AUR
   True lens
   Freezes displayed content while active
```

That's much more ArCHi-like than blindly enumerating software.

---

# GNOME and KDE validate that your capability abstraction isn't overfitted

The research checks out.

GNOME's native magnifier provides magnification factor, mouse tracking, magnifier position, crosshairs, inversion and visual adjustments. ([GNOME Help][6])

Current KDE Plasma 6.6 exposes substantially more: fullscreen and region magnification, pointer tracking modes including proportional/centered/push, focus tracking, caret tracking, pointer handling and very high zoom factors. ([KDE Documentation][7])

That means fields such as:

```text
supports_lens
supports_fullscreen_zoom
supports_pointer_follow
supports_focus_follow
supports_caret_follow
supports_crosshairs
```

aren't speculative abstraction for abstraction's sake. Real providers actually vary across those dimensions.

That's a good sign.

---

# I would cut the implementation scope

The **document** should retain all five providers because it demonstrates generality.

But the **first implementation** should be only:

```text
visual.magnifier
│
├── hyprland_cursor_zoom     ← working
├── wl_mirror                ← working or experimental working
├── hyprmag                  ← detectable / installable
├── gnome_zoom               ← catalog + detector
└── kde_zoom                 ← catalog + detector
```

Do not burn the PoC building five complete adapters.

The decisive demonstration is this:

```text
archi mag on
        │
        ▼
visual.magnifier.enable
        │
        ▼
Capability Broker
        │
        ├── Hyprland → compositor IPC
        │
        ├── wl-mirror → process/controller
        │
        ├── GNOME → GNOME interface
        │
        └── KDE → KWin interface
```

If **two fundamentally different providers** run behind that same command, the hypothesis has been proven.

---

# The command model is excellent

This part I would essentially leave alone:

```text
archi magnify
archi mag on
archi mag off
archi mag more
archi mag less
```

Especially:

```text
archi magnify -> visual.magnifier.enable
```

rather than toggle.

That's deterministic. For accessibility controls, deterministic commands beat clever toggles because the user can always issue:

> magnifier off

without needing to know its current state.

Your decision that unsupported/denied/unavailable are **normal structured outcomes rather than triggers for GUI coordinate guessing** is also important. 

That's a rule worth carrying into ArCHi globally.

---

# One wording change: plugin vs provider

I'd standardize the terminology now:

```text
ArCHi Capability Plugin
    visual.magnifier
          │
          ├── Provider adapter: Hyprland
          ├── Provider adapter: wl-mirror
          ├── Provider adapter: HyprMag
          ├── Provider adapter: GNOME
          └── Provider adapter: KDE
```

Because Hyprland itself has the concept of compositor **plugins**.

Calling every backend an ArCHi “plugin” will get confusing very quickly.

**Magnifier is the plugin/capability. Hyprland, GNOME, wl-mirror, etc. are providers/adapters.**

---

## What this PoC really proves

The important thing is not that ArCHi can magnify a screen.

It's this:

```text
User need
   "I need screen magnification"
             │
             ▼
      ArCHi capability
       visual.magnifier
             │
      ┌──────┴──────┐
      ▼             ▼
 discover         explain
 system           tradeoffs
      │             │
      └──────┬──────┘
             ▼
        user selects
             │
             ▼
    install if necessary
             │
             ▼
       provider adapter
             │
             ▼
 stable ArCHi vocabulary
```

Then the next capability can be:

```text
audio.speech_output
visual.captions
input.pointer_assist
visual.high_contrast
speech.dictation
screen.reader
braille.output
```

without redesigning the harness.

That is why I think **magnifier is a very good first plugin**. It has native providers, package providers, differing feature levels, runtime state, accessibility-specific failure consequences, installation policy and input-mode questions—all in something small enough to actually finish.

My only significant design requirement before the build would be **state snapshot/restore + ownership**. Everything else can evolve from the PoC.

[1]: https://github.com/hyprwm/Hyprland/discussions/14330?utm_source=chatgpt.com "`cursor:zoom_factor` in Lua config - how to set/get correctly? · hyprwm Hyprland · Discussion #14330 · GitHub"
[2]: https://github.com/hyprwm/Hyprland/issues/5972?utm_source=chatgpt.com "cursor zoom/magnifier must have push-on-edge option like in kde plasma · Issue #5972 · hyprwm/Hyprland · GitHub"
[3]: https://man.archlinux.org/man/wl-mirror.1.en?utm_source=chatgpt.com "wl-mirror(1) — Arch manual pages"
[4]: https://github.com/Ferdi265/wl-mirror?utm_source=chatgpt.com "GitHub - Ferdi265/wl-mirror: a simple Wayland output mirror client · GitHub"
[5]: https://github.com/SIMULATAN/hyprmag?utm_source=chatgpt.com "GitHub - SIMULATAN/hyprmag: A wlroots-compatible Wayland screen magnifier, based on hyprpicker · GitHub"
[6]: https://help.gnome.org/gnome-help/a11y-mag.html?utm_source=chatgpt.com "Magnify a screen area"
[7]: https://docs.kde.org/stable_kf6/en/plasma-desktop/kcontrol/kcmaccess/index.html?utm_source=chatgpt.com 
