# Accessibility control-plane roadmap

This roadmap turns the current Omarchy voice-command prototype into an
accessibility harness without pretending that every Linux accessibility service
belongs inside ArCHi.

## Where ArCHi is now

The current prototype has already validated several important properties:

- explicit, bounded voice capture can feed a single command;
- exact allowlisted routing can remain separate from experimental parsing;
- direct argv execution avoids synthesized shell commands;
- local speech and desktop feedback can be independently controlled;
- desktop context and performance evidence can be collected locally;
- ambiguous commands can stop for clarification;
- diagnostic logging can be disabled during sensitive work.

The first seam is now extracted: XDG application discovery is portable, and
desktop context/actions run through the `omarchy.hyprland` adapter using
structured capability results. `router.py` still knows that input came from
Voxtype and replies use one speech helper. Adding those integrations directly
to the router would still produce a larger voice-command application, not a
harness.

## Product focus

ArCHi's product is the coordination layer:

```text
normalized intent + context + preferences + policy
                         |
              capability resolution
                         |
           action + output + feedback
```

The project should measure success by whether a user can express a need once
and have it satisfied through the safest available installed capability—not by
the number of services ArCHi reimplements.

## Phase 1 — Extract the capability broker

Preserve all current behavior while introducing the five provider roles:
`InputProvider`, `ContextProvider`, `ActionProvider`, `OutputProvider`, and
`FeedbackProvider`.

Deliverables:

- provider and capability contracts with structured results;
- a registry that reports availability without importing desktop-specific
  commands into core intent;
- a deterministic resolver with a dry-run/explain mode;
- policy-controlled fallback, clarification, and refusal;
- adapters around the existing Voxtype, Hyprland/argv, Pocket TTS, and OSD
  paths;
- interaction-profile storage separated from command authority;
- event logging that records the selected capability and provider without
  recording private provider payloads by default;
- unit tests proving behavior parity with the current command router.

Exit criteria:

- every current production command still behaves the same through an adapter;
- changing the speech provider does not change the router;
- a missing provider produces `unavailable`, not an arbitrary fallback;
- dry-run output explains the ordered plan and required permissions;
- ambiguous and denied outcomes never cascade to visual/pointer action.

## Phase 2 — Prove semantic control and interchangeable speech

Add one AT-SPI context/action provider and one Speech Dispatcher output
provider. Keep Pocket TTS as an alternative.

Initial semantic scenarios:

- report the focused accessible control;
- find controls by accessible name and role within the focused application;
- report whether a unique target is enabled and actionable;
- invoke a unique target's advertised accessible action;
- read a selected semantic text value without screen capture;
- clarify when multiple matching controls exist.

Representative end-to-end path:

```text
Voxtype -> ArCHi broker -> AT-SPI action
                       -> Speech Dispatcher or Pocket TTS feedback
```

Exit criteria:

- a supported “activate Save” case succeeds without coordinates;
- an absent, disabled, or ambiguous Save control causes no click;
- Orca can remain active without ArCHi stealing its reading role;
- speech-provider selection follows profile/configuration rather than command
  definitions;
- tests cover an application with a useful accessibility tree and one with an
  incomplete tree.

## Phase 3 — Multichannel output and feedback

Add channel routing before adding more ways to control applications.

Deliverables:

- captions/text presentation provider;
- BrlAPI output and feedback proof of concept;
- feedback events for listening, working, success, warning, and failure;
- interruption and privacy rules, including “do not speak over screen reader”
  and “private content to braille/text only”;
- graceful degradation when the preferred channel disappears.

The profile model should describe preferences such as `speech`, `braille`,
`caption`, `visual`, `haptic`, and `quiet`, with ordered fallback and per-content
privacy constraints. It must not classify the user by diagnosis.

## Phase 4 — Permissioned visual and input fallback

Only after semantic action works, add optional portal-mediated fallbacks:

- XDG ScreenCast + PipeWire context provider;
- visual target proposal with explicit provenance and confidence;
- XDG RemoteDesktop/libei action provider where the compositor supports it;
- policy rules requiring an established target and current permission before
  pointer action;
- confirmation for consequential actions.

Vision may locate a candidate; it does not gain authority to invent an action.
Unsupported compositor capabilities should remain visible as `unsupported` or
`unavailable`, not be hidden behind backend-specific hacks.

## Phase 5 — Additional inputs and accommodations

Once the broker contracts are stable, add integrations independently:

- braille display keys and switch devices as input providers;
- desktop adapters for sticky keys, slow keys, bounce keys, mouse keys, dwell
  click, visual alerts, and on-screen keyboards;
- sign or gesture recognition producing the same normalized intent events as
  voice;
- haptic feedback providers;
- future accessibility transports alongside AT-SPI.

These are adapters, not new execution paths through the core.

## Deliberate non-goals

- replacing Orca or duplicating full screen-reader navigation;
- building a speech synthesizer or hardware driver;
- treating screenshots as the primary desktop representation;
- unrestricted natural-language shell or desktop execution;
- inferring a medical diagnosis from observed behavior;
- silently enabling a microphone, camera, screen stream, or input-emulation
  session;
- promising identical capabilities on every compositor.

## Immediate issue sequence

The next implementation work should stay small and sequential:

1. Extend the initial desktop adapter protocol into the provider registry.
2. Keep the legacy argv executor limited to ArCHi-owned helpers.
3. Wrap Pocket TTS and OSD as output and feedback providers.
4. Add a second desktop adapter after Pop!_OS testing validates the contract.
5. Add broker explain/dry-run output and policy tests.
6. Build a read-only AT-SPI context spike.
7. Add one allowlisted AT-SPI activation flow.
8. Add Speech Dispatcher as a selectable output provider.

Do not begin vision, synthetic pointer input, sign recognition, or a broad
profile UI until those eight steps have established the control-plane seam.

## First plugin proof of concept

The first capability plugin PoC is the screen magnifier. It is intentionally
scoped as provider discovery, provider selection, OS-package installation, and
stable ArCHi control over an existing magnifier service. See
[Magnifier capability plugin proof of concept](MAGNIFIER_PLUGIN_POC.md).
