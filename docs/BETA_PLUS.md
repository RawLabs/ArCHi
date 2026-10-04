# Beta+ delivery path

This document records bounded beta extensions on Omarchy/Hyprland. Background
close confirmation and spoken aliases are implemented; dialog actions remain
planned. These extensions do not expand the supported platform.

## Beta 1.1 — Background application close confirmation

**Goal:** close an unambiguous named application even when it is on another
workspace, without moving the user away from the workspace or window they are
currently using.

### Behavior

1. ArCHi refreshes the XDG application registry and resolves a unique named
   app using the existing deterministic app-routing rules.
2. The Omarchy adapter reads Hyprland's live client list and selects the
   matching window address.
3. It sends a normal address-targeted Hyprland close request.  It does not
   switch workspace, focus the target, synthesize a keyboard shortcut, or
   force-terminate a process.
4. It checks briefly whether Hyprland still lists that exact address.
5. If the address disappears, ArCHi reports that the application closed.  If
   it remains, ArCHi reports that the app **needs attention**.  This is not an
   error and does not assume the reason; an unsaved-changes prompt is one
   possible explanation.
6. A user-owned spoken-alias registry can map a repeated speech-recognition
   spelling to a currently installed desktop entry.  This supplements the
   XDG-derived name; it does not create a command for an absent application.

### Safety boundaries

- Test only with disposable documents and non-critical applications.
- `close` remains a normal application close request.  It is never a kill or
  force-quit action.
- A remaining window must never be reported as closed.
- ArCHi must not inspect, press, or infer the meaning of an unseen dialog in
  Beta 1.1.
- Spoken aliases remain unique.  If two installed apps claim the same alias,
  ArCHi omits it rather than guessing.

### Exit criteria

- Closing a uniquely matched app on another workspace leaves the current
  workspace and focus unchanged.
- A disappearing target produces a confirmed-close reply.
- A persistent target produces the exact user-facing outcome “<app> needs
  attention.”
- A missing or ambiguous target produces no desktop action.
- Automated tests cover both confirmed close and needs-attention behavior.

## Beta 1.2 — Scoped dialog actions, where semantically supported

**Goal:** only where a supported application exposes an accessible,
unambiguous native dialog, let ArCHi describe and invoke its actual `Save`,
`Discard`, or `Cancel` control without moving the user to that workspace.

### Preconditions

- A read-only semantic context provider can identify the application and the
  modal dialog with high confidence.
- The dialog exposes real, unique accessible actions; ArCHi does not use
  unseen `Tab`, `Enter`, or coordinate clicks.
- The follow-up response is bound to one short-lived dialog context.

### Guardrails

- Speak and show the offered choices before acting.
- `Discard` always requires a second explicit confirmation: “confirm discard.”
- If ArCHi cannot establish the dialog and button identity, it stops at
  “<app> needs attention.”
- This is capability-by-capability and application-by-application, not a
  claim of universal save-dialog support.
