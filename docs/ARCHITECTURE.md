# Architecture notes

ArCHi is an accessibility control plane. Its job is to translate a user's
request into a bounded intent, combine that intent with relevant context and
policy, select an installed capability provider, and report the outcome through
the user's chosen channels.

The current code is a working vertical slice, not yet the complete broker
described here. This document marks those two states explicitly.

## The AʳCHⁱ Architectural Formulation

The brand and architecture share a unified mathematical formulation:

$$\mathbf{A^r \cdot CH^i} \quad\Longleftrightarrow\quad \left(\mathbf{Artificial}\right)^{\mathbf{Restorative}} \cdot \left(\mathbf{Computer\ Harness}\right)^{\mathbf{Intelligence}}$$

- **01. The Computer Harness — A·C·H:** Linux already has a remarkable collection of tools: window controls, audio systems, accessibility services, input devices, magnifiers, and speech tools. ArCHi's Computer Harness connects to what is already available on your system, learns where the useful pieces are, and gives them a common place to work from. No need to replace Linux—the penguin was here first.
- **02. Restorative Intelligence — r·i:** Restorative Intelligence turns human intent into an action the computer understands. Spoken commands, dictated instructions, keyboard actions, pointer movements, or accessibility controls all represent the same thing: intent. Less hunting through menus, less mouse mileage, and considerably less finger gymnastics.
- **03. ArCHi:** Put the two together and you get ArCHi: a harness that understands the Linux system beneath it, and an intelligence that understands the person in front of it. Magnification beside hands-free control, dictation beyond typing—because sometimes the accessibility problem isn't that the tool doesn't exist; it's that the tools won't talk to each other.

## Architectural boundary

ArCHi owns:

- normalized intent and event contracts;
- capability discovery and provider selection;
- user interaction preferences;
- policy, consent state, and action allowlists;
- deterministic fallback and clarification;
- outcome routing and local diagnostics.

ArCHi does not own:

- application accessibility trees or widget semantics;
- screen-reader navigation and reading behavior;
- speech synthesis engines;
- braille display drivers;
- compositor security decisions;
- generic keyboard, pointer, or touch emulation;
- desktop accessibility settings themselves.

Those belong to existing Linux services. ArCHi integrates them through narrow
adapters and must continue to work when one implementation is exchanged for
another.

The implementation now enforces the first such boundary:

```text
router.py -> capability ID + payload -> DesktopAdapter
                                      -> ActionResult

applications.py -> XDG desktop entries -> portable application metadata

adapters/omarchy.py -> Omarchy and Hyprland commands
```

`ActionResult` has four outcomes: `success`, `unsupported`, `unavailable`, and
`failed`. The router records the selected provider and capability. It does not
fall back to another machine command implicitly.

## Target runtime

```text
 InputProvider(s)
 voice | keys | switches | braille | gesture
                  |
                  v
          normalized input event
                  |
                  v
        intent + context + policy
                  |
          capability broker
                  |
       deterministic resolution plan
                  |
    +-------------+--------------+
    |                            |
 ActionProvider(s)       Output/FeedbackProvider(s)
    |                            |
 AT-SPI, app APIs,       speech, braille, captions,
 desktop, portals        visual cues, haptics
```

The core requests capabilities rather than implementations. For example:

```text
context.focused_control()
context.find_control(name="Save", role="button")
action.activate(target=control_ref)
action.type_text(text=...)
output.present(content=..., purpose="readout")
feedback.emit(kind="success", message="Saved")
```

`hyprctl`, Pocket TTS, Speech Dispatcher, AT-SPI, BrlAPI, and libei belong
inside providers. They must not leak into normalized user intent.

## Provider roles

### `InputProvider`

Produces a normalized input event. The event records its source and confidence
or certainty where applicable, but downstream policy does not assume that voice
is the only input modality.

Examples: Voxtype explicit capture, keyboard bindings, switch devices, braille
display keys, gesture or sign recognition.

### `ContextProvider`

Returns read-only state with provenance and freshness. Context is gathered on
demand and should be no broader than the request needs.

Examples: focused Hyprland window, AT-SPI accessible object, current workspace,
portal-granted screen stream.

### `ActionProvider`

Performs one policy-approved operation. It returns a structured result and does
not silently choose a materially different target when its requested target is
missing or ambiguous.

Examples: invoke an AT-SPI action, call an application command, dispatch a
desktop shortcut, or send input through a compositor-approved libei path.

### `OutputProvider`

Presents user-requested content. Output selection follows interaction-channel
preferences and content constraints.

Examples: Speech Dispatcher, Pocket TTS, BrlAPI, captions, large-text views.

### `FeedbackProvider`

Emits short operational cues such as listening, working, success, warning, or
failure. Feedback is separate from output so “read this document” and “confirm
that it was saved” can use different channels and interruption policies.

Examples: a spoken cue, OSD, sound, display flash, braille status cell, or
haptic pattern.

A provider may implement more than one role, but it registers each capability
separately. Provider identity is diagnostic information, not part of intent.

## Capability resolution

Each provider advertises capability IDs, availability, required permissions,
supported targets or media, and a priority appropriate to its semantic
specificity. The broker produces an inspectable resolution plan before causing
side effects.

Every provider attempt returns one of a small set of outcomes:

- `success` — the requested capability completed;
- `unsupported` — this provider cannot satisfy this request;
- `unavailable` — the provider exists but cannot currently operate;
- `permission_required` or `denied` — consent is absent or refused;
- `not_found` — no matching target exists;
- `ambiguous` — multiple plausible targets exist;
- `failed` — execution began but did not complete safely.

Only outcomes explicitly allowed by policy advance to another provider. In
particular, `ambiguous`, `denied`, and an uncertain target must not turn into a
coordinate click.

### Semantic action fallback

For a request such as “activate Save,” the default policy is:

1. Find a unique accessible control and invoke its semantic action through
   AT-SPI.
2. Use a known application-native command or API.
3. Use a known desktop/compositor command or shortcut.
4. If the user has permitted visual context, locate the target in a
   portal-granted window or screen stream.
5. If the target is established and input control is permitted, act through a
   compositor-approved input provider such as libei.
6. Otherwise clarify or report that the capability is unavailable.

This is a policy ladder, not a promise that every installation implements every
step. Visual targeting and synthetic input are optional fallbacks, not the
default interaction model.

## Interaction profiles

Profiles express channel preferences and constraints, not medical diagnoses.
They may state, for example:

- content output: braille first, speech second;
- operational feedback: visual and haptic, never audio;
- private content: braille or local text only;
- confirmations: required before destructive actions;
- input: switch scanning plus push-to-talk;
- interruption: do not speak over a screen reader.

The same normalized outcome can therefore be presented by speech, captions,
braille, visual cues, haptics, or a deliberate combination. A profile changes
presentation and policy; it does not create new action authority.

## Existing Linux integration points

The initial adapter map deliberately builds on established interfaces:

| Need | Integration boundary | Intended ArCHi role |
|---|---|---|
| Semantic application context/actions | [AT-SPI](https://gnome.pages.gitlab.gnome.org/at-spi2-core/devel-docs/architecture.html) | Context and action provider |
| Screen reading | [Orca](https://gnome.pages.gitlab.gnome.org/orca/help/introduction.html) | Cooperating assistive technology, not replaced by ArCHi |
| Speech synthesis routing | [Speech Dispatcher](https://github.com/brailcom/speechd) | Output provider |
| Braille devices and clients | [BRLTTY/BrlAPI](https://brltty.app/doc/Manual-BRLTTY/English/BRLTTY.html) | Input, output, and feedback providers |
| Permissioned pixels | [XDG ScreenCast portal](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.ScreenCast.html) and PipeWire | Optional visual context provider |
| Permissioned remote input | [XDG RemoteDesktop portal](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html) and [libei](https://libinput.pages.freedesktop.org/libei/) | Optional action provider |
| Motor-access settings | Desktop accessibility settings | Desktop-specific action providers |

AT-SPI is the first semantic provider target. The interface remains provider
neutral so a future accessibility transport can coexist with or replace it
without changing ArCHi intents.

## Current runtime: Phase 0

Today, the prototype takes this path:

1. `archi-control-start` creates a private runtime directory under
   `${XDG_RUNTIME_DIR}/archi`, starts a bounded Voxtype recording, assigns a
   session ID, and launches an active-only local monitor for “ArCHi stop.”
2. A second `Super+R`, the verbal terminator, or the 120-second limit invokes
   `archi-control-stop`. It stops Voxtype, reads the transcript, and pipes it to
   `router.py`. `Escape` cancels instead. The wrapper exports capture-session
   and post-stop transcript-wait timing so AC/battery behavior can be compared
   later.
3. `router.py` normalizes the phrase, strips an optional `ArCHi` or `archie`
   prefix, reloads installed applications from standard XDG/Flatpak/Snap
   desktop-entry directories, and matches the result against those applications
   plus the operational commands in `commands.toml`. Exact phrases win. When an
   app phrase misses exactly, ArCHi can resolve one unambiguous desktop-entry
   alias with spaces removed, separately spoken letters, q/c/k equivalence, or
   a one-character transcription correction for names of at least five letters.
4. The matched operational command requests a capability. The selected desktop
   adapter advertises support, captures desktop context, and translates that
   capability into its local implementation. A small legacy argv path remains
   only for ArCHi-owned helpers such as clipboard speech.
5. Spoken responses go through `pocket-tts-say`, which calls the configured
   Pocket TTS-compatible endpoint, ducks other output streams while ArCHi is
   speaking, and plays the result with PipeWire. Speech jobs are serialized.
   In parallel, `feedback.py` asks the selected desktop adapter for a
   best-effort transient status overlay. Feedback is not a system notification,
   never receives focus, and cannot block command execution.
6. When HassIL is available, it independently evaluates `intents.yaml`. The log
   labels its relationship to production as `agree`, `shadow_extension`,
   `shadow_regression`, `conflict`, or `not_comparable`.

The present router still combines intent lookup, output, policy, and diagnostics.
Desktop context and action execution have moved behind the first adapter
contract. Output and input providers remain later extraction boundaries.

Clipboard readout has a deliberately narrow boundary: `wl-paste --type text`
selects only an advertised textual clipboard representation, the helper rejects
invalid UTF-8 or binary data, and `pocket-tts-say` verifies that the HTTP body is
a readable PCM RIFF/WAVE stream before PipeWire can play it. Clipboard contents
are neither logged nor passed through the command router.

## Current state locations

- Runtime files live under `${XDG_RUNTIME_DIR}/archi`.
- Persistent voice volume lives at
  `${XDG_CONFIG_HOME:-$HOME/.config}/archi/pocket-tts-volume`.
- Command diagnostics default to
  `$HOME/.local/state/archi/commands.jsonl`, unless `ARCHI_LOG_PATH` is set.
- Installed router and command defaults live under `ARCHI_HOME`, defaulting to
  `$HOME/.local/share/archi`.
- The active registry is `commands.toml`; the latest installed project default
  is kept separately as `commands.default.toml` for safe comparison.
- The independent, project-managed shadow grammar is `intents.yaml`.

## Trust boundaries

`config/commands.toml` is trusted local configuration. Operational entries name
capabilities and bounded payloads; ArCHi-owned helper entries may still contain
argv arrays. Installed `.desktop` entries form the application registry. The
selected adapter decides how to launch or close them, so adding or changing a
desktop entry changes the apps ArCHi can address. Review both sources as
executable local configuration.

Adapters are providers, not plugins. A future plugin may package a capability
and several provider adapters, but dynamic plugin loading is intentionally
deferred until a second desktop validates the contract. See
[platform support](SUPPORT.md).

`hassil`, when installed, is used only as a shadow parser for diagnostics. Its
grammar maps only to IDs present in the trusted command registry. Its result is
logged for comparison and never decides which command runs.

Future semantic context may contain private text, control names, document
content, and application state. Providers must request the narrowest context
needed, label its provenance, avoid logging content by default, and respect an
off-record mode across the entire broker rather than only the voice path.

Portal and compositor permission decisions remain authoritative. ArCHi may
explain why a permission is useful; it must not bypass, simulate, or persist
consent outside the platform mechanism.

Wake-word activation is out of scope for the default setup. Adding it would
require a separate, explicit always-on local listener and visible user controls.

Voice-controlled dictation is also out of scope for the beta. The existing
Voxtype dictation hotkey is independent of ArCHi command capture; a future
voice-driven mode switch must be an explicit capture-controller state, not a
router alias that types into an uncertain focused target.
