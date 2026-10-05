# ArCHi testing cheat sheet

This sheet describes the bindings active on the current Omarchy test machine
and the phrases accepted by the deterministic production router. Run
`archi-cheatsheet` for the quick reference and currently discovered menu apps
in a terminal.

The supported beta scope and reporting protocol are in [beta operations](BETA.md).

## Key binding map

| Keys | When | Result |
|---|---|---|
| `Super + R` | Normal desktop | Start one ArCHi command capture |
| `Super + R` | ArCHi capture active | Stop capture and run the recognized command |
| say “ArCHi stop” | ArCHi capture active | Stop capture and run the preceding recognized command |
| `Escape` | ArCHi capture active | Cancel without running a command |
| `Super + Shift + R` | Normal desktop | Start dictation/documentation mode |
| `Super + Shift + R` | Dictation active | Stop and submit dictation |
| `Escape` | Dictation active | Cancel dictation |
| `Super + Shift + V` | Normal desktop | Read clipboard aloud |
| `Super + Ctrl + Up` | Normal desktop | Raise ArCHi's voice volume |
| `Super + Ctrl + Down` | Normal desktop | Lower ArCHi's voice volume |

`Super + R` is ArCHi's physical toggle. `Escape` is its physical cancel path,
and the capture submits automatically at the 120-second hard limit. Dictation
remains a separate mode with its own `Super + Shift + R` submit and `Escape`
cancel controls.

## Accepted production command chart

Say any phrase in the Accepted phrases column. ArCHi removes its own name,
basic punctuation, and one polite prefix such as “please” or “can you” before
matching.

| Command | Accepted phrases | Effect / test caution |
|---|---|---|
| `open_app:<desktop-id>` | open, launch, or start + an unambiguous installed app name | Launches the current `.desktop` entry through `gtk-launch` |
| `close_app:<desktop-id>` | close, quit, exit, or dismiss + an unambiguous installed app name | Requests the most recently focused matching app window close |
| `focus_app:<desktop-id>` | switch to, focus, or show + an unambiguous installed app name | Focuses an existing matching window; does not launch a closed app |
| `open_home` | open home; open home folder; open my home folder | Opens a folder |
| `open_downloads` | open downloads; open downloads folder | Opens a folder |
| `volume_up` | volume up; turn volume up; turn the volume up; raise the volume; make it louder; louder | Changes system audio |
| `volume_down` | volume down; turn volume down; turn the volume down; lower the volume; make it quieter; quieter | Changes system audio |
| `zoom_in` | zoom; zoom in; zoom in more; magnify; magnify the screen; make the screen bigger; make everything bigger | Increases native screen zoom |
| `zoom_less` | zoom less; zoom back a little; reduce zoom; magnify less | Decreases zoom by one step |
| `zoom_out` | zoom out; reset zoom; turn off zoom; stop zooming; normal size; back to normal size | Resets zoom to normal |
| `mute` | mute; mute audio; mute volume; mute sound; turn volume off; turn sound off | Mutes system audio |
| `unmute` | unmute; unmute audio; unmute volume; unmute sound; turn volume on; turn sound on | Unmutes system audio |
| `toggle_mute` | toggle mute; toggle audio mute; toggle volume mute | Toggles system mute |
| `lock_computer` | lock computer; lock the computer; lock screen; lock the screen | Locks the session; test last |
| `take_screenshot` | take screenshot; take a screenshot; screenshot; capture screenshot | Creates a screenshot |
| `close_active_window` | close this window; close current window; close active window; close the active window; close window; dismiss this window | Closes the focused window |
| `close_home` | close home; close home folder; quit home; exit home | Closes a Home folder window |
| `close_downloads` | close downloads; close downloads folder; quit downloads; exit downloads | Closes a Downloads folder window |
| `close_clarify` | close; quit; exit; dismiss | Asks which safe target to close |
| `read_clipboard` | read clipboard; read clipboard aloud; read this aloud; speak clipboard; read that aloud | Speaks clipboard contents through the configured TTS helper |
| `stop_speaking` | stop speaking; stop talking; shut up; silence; cancel speech | Stops ArCHi speech |
| `off_record` | off record; off the record; private mode | Stops diagnostic logging |
| `logging_on` | logging on; back on record; back on the record; resume logging | Resumes diagnostic logging |
| `next_workspace` | next workspace; switch to next workspace | Changes workspace |
| `previous_workspace` | previous workspace; last workspace; switch to previous workspace | Changes workspace |
| `identity` | what are you; who are you; identify yourself | Spoken reply only |
| `help` | help; what can you do | Spoken reply only |
| `list_commands` | list commands; show commands; what commands do you know; command list | Spoken reply only |

After zoom or volume adjustments, `more`, `a little more`, `increase it`,
`less`, `a little less`, and `decrease it` adjust the same control for up to
120 seconds. `cancel` restores the original zoom if it has not changed
elsewhere; for volume it only clears the follow-up context.

For the close clarification, answer with `home`, `downloads`, or `window`.
Installed apps should be named in the original command, such as `close cliamp`.
Spaces are accepted in app names, including separately spoken letters such as
`open c l i a m p`. The app-only fallback also treats q, c, and k as equivalent
and accepts one transcription change for an unambiguous name of five or more
letters. It never relaxes operational command matching.
Say `cancel`, `cancel that`, or `never mind` to abandon clarification.

The app rows are generated at command time from XDG, Flatpak, Snap, and Nix
desktop-entry directories. Menu hiding, desktop visibility, `TryExec`, and
Omarchy's `launcher.hides` filter that list. Optional `the` is accepted before
app names. Desktop defaults select everyday names such as browser, terminal,
file manager, editor, video player, image viewer, and PDF viewer. Other shared
aliases are omitted so ArCHi does not guess between two apps. See
[app voice controls](VOICE_CONTROLS.md#apps-from-the-app-menu).

### App discovery and window smoke tests

1. Run `archi-cheatsheet`; compare its app names with the app menu. Hidden or
   unavailable entries should not produce opening commands.
2. Install a disposable test app entry, then dry-run `open` plus its menu name.
   Remove the entry and repeat; the command should become unknown without
   restarting ArCHi or editing its registry.
3. Dry-run `open browser`, `close the browser`, and `switch to browser`. Check
   that all target the same installed default browser. Repeat for terminal,
   file manager, and editor where desktop defaults are available.
4. In an active Hyprland session, open a disposable app window. Focus another
   app, say `switch to` plus the test app name, then request it close. Confirm
   the requested app is targeted. If it asks about unsaved work, ArCHi should
   report attention rather than force it closed.
5. With the test app closed, its focus command should fail without launching
   it or moving focus to an unrelated app.

Automated tests cover menu filters, live registry refresh, default-role
selection, phrase variants, full desktop IDs at launch, and window-address
targeting. Dry runs and unit tests do not establish live speech or compositor
behavior.

## Current prototype evidence matrix

This matrix validates the Phase 0 voice-command slice; it is separate from the
[control-plane roadmap](ROADMAP.md). The target is about 100 deliberate captures
across four short sessions: two on AC power and two on battery. This lets the
log distinguish speech/parser behavior from power-state slowdown.

1. **Binding and capture (10 tests):** exercise `Super+R` start/stop, verbal
   “ArCHi stop,” the 120-second limit, and `Escape` cancellation for ArCHi;
   exercise submit and cancel for dictation. Confirm no stuck submap after
   every exit path.
2. **Accepted baseline:** test one representative phrase for each
   active log-observable command twice, once on AC and once on battery. The
   two logging-mode commands intentionally do not record their own use.
3. **Natural variations (24 tests):** say each probe below once on AC and once
   on battery. Production may reject it while the independent shadow grammar
   proposes a safe command; that is useful `shadow_extension` evidence.
4. **Negative controls (8 tests):** use unrelated or incomplete phrases.
   Both parsers should reject them. Do not include private information.
5. **Stress passes (8 tests):** repeat four safe reply-only phrases during a
   high-load moment and again at idle. Compare transcript wait, router duration,
   and shadow parse time rather than relying on impression alone.

### Natural-variation probes

| Say | Expected shadow command |
|---|---|
| launch my downloads folder | `open_downloads` |
| raise the volume | `volume_up` |
| lower the volume | `volume_down` |
| toggle the mute | `toggle_mute` |
| lock my screen | `lock_computer` |
| take a screen shot | `take_screenshot` |
| close the downloads folder | `close_downloads` |
| read the clipboard aloud | `read_clipboard` |
| stop reading aloud | `stop_speaking` |

### Negative controls

Use phrases such as `open`, `volume`, `next`, `read it`, `do the thing`, and
`open bananas`. Also include a short ordinary sentence that is not a command.
The desired result is production `unknown`, shadow `no_match`, comparison
`agree`.

## Reading the results

Run:

```bash
archi-shadow-report --details
```

| Label | Meaning | Next action |
|---|---|---|
| `agree` | Both parsers chose the same command or both rejected the phrase | Keep as baseline evidence |
| `shadow_extension` | Production rejected it; shadow found a valid command | Candidate phrase/pattern for promotion after repetition |
| `shadow_regression` | Production accepted it; shadow missed it | Fix the diagnostic grammar before judging it |
| `conflict` | Both matched but chose different commands | Highest-priority manual review; never auto-promote |
| `not_comparable` | HassIL/schema unavailable or an older diagnostic could not be compared | Repair instrumentation, then repeat |

Promote a natural variation only after it repeats cleanly, has no conflicts,
and is unambiguous when spoken without desktop context. HassIL remains a
shadow: it cannot execute a command.

To inspect routing without causing desktop effects, pipe a phrase into the
router's dry-run mode. This tests text routing, not microphone capture:

```bash
printf '%s\n' 'open cliamp' | python3 ~/.local/share/archi/router.py --dry-run
```

Dry-run results resolve the selected adapter and capability but do not invoke
the adapter. Adapter unit tests use synthetic desktop entries and Hyprland
client data; live Omarchy smoke tests should use a disposable test window.

## Visual feedback

The default `ARCHI_FEEDBACK=minimal` displays short transparent overlays for
listening, the recognized transcript, and the final outcome. On Omarchy this
uses `omarchy-osd`, so it does not create normal desktop notifications or take
focus. Set `ARCHI_FEEDBACK=off` to suppress visual feedback completely.

Logs contain transcripts and window context. Use `off record` for sensitive
work and never attach an unreviewed raw log to a public issue.
