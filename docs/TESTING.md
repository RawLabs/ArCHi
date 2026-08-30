# ArCHi testing cheat sheet

This sheet describes the bindings active on the current Omarchy test machine
and the phrases accepted by the deterministic production router. Run
`archi-cheatsheet` for the same quick reference in a terminal.

## Key binding map

| Keys | When | Result |
|---|---|---|
| `Super + R` | Normal desktop | Start one ArCHi command capture |
| `Enter` | ArCHi capture active | Stop capture and run the recognized command |
| `Escape` | ArCHi capture active | Cancel without running a command |
| `Super + Shift + R` | Normal desktop | Start dictation/documentation mode |
| `Enter` | Dictation active | Stop and submit dictation |
| `Escape` | Dictation active | Cancel dictation |
| `Super + Shift + V` | Normal desktop | Read clipboard aloud |
| `Super + Ctrl + Up` | Normal desktop | Raise ArCHi's voice volume |
| `Super + Ctrl + Down` | Normal desktop | Lower ArCHi's voice volume |
| `F9` | Normal desktop | Legacy dictation push-to-talk |
| `Super + Ctrl + X` | Normal desktop | Legacy dictation toggle |
| Copilot key / `Super + Space` | Normal desktop | Open the Omarchy app menu |

`Super + R` and `Super + Shift + R` are the preferred one-hand paths. The
standalone `Enter` and `Escape` actions only apply after their mode has begun.

## Accepted production command chart

Say any phrase in the Accepted phrases column. ArCHi removes its own name,
basic punctuation, and one polite prefix such as “please” or “can you” before
matching.

| Command | Accepted phrases | Effect / test caution |
|---|---|---|
| `open_terminal` | open terminal; launch terminal; start terminal | Opens an app |
| `open_browser` | open browser; launch browser; start browser; open web browser | Opens an app |
| `open_default_agent` | open agent; launch agent; start agent; open omarchy agent; open default agent | Opens an app |
| `open_files` | open files; open file manager; launch file manager; start files | Opens an app |
| `open_home` | open home; open home folder; open my home folder | Opens a folder |
| `open_downloads` | open downloads; open downloads folder | Opens a folder |
| `volume_up` | volume up; turn volume up; make it louder; louder | Changes system audio |
| `volume_down` | volume down; turn volume down; make it quieter; quieter | Changes system audio |
| `mute` | mute; mute audio; mute volume | Toggles system mute |
| `lock_computer` | lock computer; lock the computer; lock screen; lock the screen | Locks the session; test last |
| `take_screenshot` | take screenshot; take a screenshot; screenshot; capture screenshot | Creates a screenshot |
| `close_active_window` | close this window; close current window; close active window; close the active window; close window; dismiss this window | Closes the focused window |
| `close_terminal` | close terminal; quit terminal; exit terminal | Closes a terminal window |
| `close_browser` | close browser; quit browser; exit browser | Closes a browser window |
| `close_files` | close files; quit files; close file manager | Closes a Files window |
| `close_clarify` | close; quit; exit; dismiss | Asks which safe target to close |
| `read_clipboard` | read clipboard; read clipboard aloud; read this aloud; speak clipboard; read that aloud | Speaks clipboard contents |
| `stop_speaking` | stop speaking; stop talking; shut up; silence; cancel speech | Stops ArCHi speech |
| `off_record` | off record; off the record; private mode | Stops diagnostic logging |
| `logging_on` | logging on; back on record; back on the record; resume logging | Resumes diagnostic logging |
| `next_workspace` | next workspace; switch to next workspace | Changes workspace |
| `previous_workspace` | previous workspace; last workspace; switch to previous workspace | Changes workspace |
| `identity` | what are you; who are you; identify yourself | Spoken reply only |
| `help` | help; what can you do | Spoken reply only |
| `list_commands` | list commands; show commands; what commands do you know; command list | Spoken reply only |

For the close clarification, answer with `terminal`, `browser`, `files`, or
`window`. Say `cancel`, `cancel that`, or `never mind` to abandon it.

## Next-phase test matrix

The target is 80–100 deliberate captures across four short sessions: two on AC
power and two on battery. This lets the log distinguish speech/parser behavior
from power-state slowdown.

1. **Binding and capture (8 tests):** exercise start, submit, and cancel for
   both ArCHi command mode and dictation, from both left- and right-hand
   positions. Confirm no stuck submap after every cancel.
2. **Accepted baseline (46 tests):** test one representative phrase for each
   of the 23 log-observable commands twice—once on AC and once on battery. The
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
| open the browser | `open_browser` |
| launch console | `open_terminal` |
| start the file manager | `open_files` |
| launch my downloads folder | `open_downloads` |
| raise the volume | `volume_up` |
| lower the volume | `volume_down` |
| toggle the mute | `mute` |
| lock my screen | `lock_computer` |
| take a screen shot | `take_screenshot` |
| close terminal window | `close_terminal` |
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
printf '%s\n' 'open the browser' | python ~/.local/share/archi/router.py --dry-run
```

Logs contain transcripts and window context. Use `off record` for sensitive
work and never attach an unreviewed raw log to a public issue.
