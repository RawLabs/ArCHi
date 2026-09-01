/**
 * ArCHi Web Mockup — Interactive Controller
 * Clean, lightweight, zero-dependency JavaScript
 */

// Command Registry Database (mirrors config/commands.toml)
const ARCHI_COMMANDS = [
  {
    id: "open_terminal",
    category: "apps",
    phrases: ["open terminal", "launch terminal", "start terminal"],
    action: "launch",
    argv: '["omarchy-launch-terminal"]',
    reply: "Opening terminal.",
    description: "Launches the configured terminal emulator via Omarchy launcher."
  },
  {
    id: "open_browser",
    category: "apps",
    phrases: ["open browser", "launch browser", "start browser", "open web browser"],
    action: "launch",
    argv: '["omarchy-launch-browser"]',
    reply: "Opening browser.",
    description: "Launches the default web browser."
  },
  {
    id: "open_default_agent",
    category: "apps",
    phrases: ["open agent", "launch agent", "start agent", "open omarchy agent"],
    action: "launch",
    argv: '["omarchy-agent"]',
    reply: "Opening the default Omarchy agent.",
    description: "Invokes the default local Omarchy AI coding/system agent."
  },
  {
    id: "open_files",
    category: "apps",
    phrases: ["open files", "open file manager", "launch file manager", "start files"],
    action: "launch",
    argv: '["omarchy-launch-nautilus"]',
    reply: "Opening files.",
    description: "Opens Nautilus / default file manager."
  },
  {
    id: "open_home",
    category: "apps",
    phrases: ["open home", "open home folder", "open my home folder"],
    action: "launch",
    argv: '["xdg-open", "{home}"]',
    reply: "Opening home.",
    description: "Opens user's $HOME directory in default file manager."
  },
  {
    id: "open_downloads",
    category: "apps",
    phrases: ["open downloads", "open downloads folder"],
    action: "launch",
    argv: '["xdg-open", "{home}/Downloads"]',
    reply: "Opening downloads.",
    description: "Opens the Downloads folder."
  },
  {
    id: "volume_up",
    category: "audio",
    phrases: ["volume up", "turn volume up", "make it louder", "louder"],
    action: "run",
    argv: '["omarchy-audio-output-volume", "raise"]',
    reply: "Volume up.",
    description: "Raises master audio output volume with OSD overlay."
  },
  {
    id: "volume_down",
    category: "audio",
    phrases: ["volume down", "turn volume down", "make it quieter", "quieter"],
    action: "run",
    argv: '["omarchy-audio-output-volume", "lower"]',
    reply: "Volume down.",
    description: "Lowers master audio output volume with OSD overlay."
  },
  {
    id: "mute",
    category: "audio",
    phrases: ["mute", "mute audio", "mute volume"],
    action: "run",
    argv: '["omarchy-audio-output-volume", "mute-toggle"]',
    reply: "Audio mute toggled.",
    description: "Toggles audio mute state."
  },
  {
    id: "read_clipboard",
    category: "readout",
    phrases: ["read clipboard", "read clipboard aloud", "read this aloud", "speak clipboard"],
    action: "launch",
    argv: '["pocket-tts-read-clipboard"]',
    reply: "(Reads textual clipboard aloud via Pocket TTS)",
    description: "Safely reads plain text from wl-clipboard using local Pocket TTS with output stream ducking."
  },
  {
    id: "stop_speaking",
    category: "readout",
    phrases: ["stop speaking", "stop talking", "shut up", "silence", "cancel speech"],
    action: "run",
    argv: '["archi-stop-speaking"]',
    reply: "",
    description: "Immediately stops active speech synthesis and restores background stream volume."
  },
  {
    id: "close_active_window",
    category: "windows",
    phrases: ["close this window", "close current window", "close active window", "close window"],
    action: "run",
    argv: '["hyprctl", "dispatch", "hl.dsp.window.close()"]',
    reply: "Closing window.",
    description: "Closes the focused Hyprland window."
  },
  {
    id: "close_terminal",
    category: "windows",
    phrases: ["close terminal", "quit terminal", "exit terminal"],
    action: "run",
    argv: '["archi-close-target", "terminal"]',
    reply: "Closing terminal.",
    description: "Closes running terminal instance safely."
  },
  {
    id: "close_clarify",
    category: "windows",
    phrases: ["close", "quit", "exit", "dismiss"],
    action: "clarify",
    argv: 'Targets: terminal, browser, files, window',
    reply: "What should I close: terminal, browser, files, or this window?",
    description: "Prompts for target clarification when a bare close command is uttered."
  },
  {
    id: "next_workspace",
    category: "windows",
    phrases: ["next workspace", "switch to next workspace"],
    action: "run",
    argv: '["hyprctl", "dispatch", "hl.dsp.focus({ workspace = \\"e+1\\" })"]',
    reply: "Next workspace.",
    description: "Navigates to next workspace in Hyprland."
  },
  {
    id: "previous_workspace",
    category: "windows",
    phrases: ["previous workspace", "last workspace", "switch to previous workspace"],
    action: "run",
    argv: '["hyprctl", "dispatch", "hl.dsp.focus({ workspace = \\"e-1\\" })"]',
    reply: "Previous workspace.",
    description: "Navigates to previous workspace in Hyprland."
  },
  {
    id: "take_screenshot",
    category: "system",
    phrases: ["take screenshot", "take a screenshot", "screenshot", "capture screenshot"],
    action: "launch",
    argv: '["omarchy-capture-screenshot"]',
    reply: "Taking a screenshot.",
    description: "Captures screen region or full screen using Omarchy screenshot utility."
  },
  {
    id: "lock_computer",
    category: "system",
    phrases: ["lock computer", "lock the computer", "lock screen"],
    action: "run",
    argv: '["loginctl", "lock-session"]',
    reply: "Locking computer.",
    description: "Locks the active session with loginctl."
  },
  {
    id: "off_record",
    category: "system",
    phrases: ["off record", "off the record", "private mode"],
    action: "mode",
    argv: '["archi-mode-toggle", "off_record"]',
    reply: "Logging off.",
    description: "Pauses diagnostic transcript recording for sensitive tasks."
  },
  {
    id: "logging_on",
    category: "system",
    phrases: ["logging on", "back on record", "resume logging"],
    action: "mode",
    argv: '["archi-mode-toggle", "logging_on"]',
    reply: "Logging on.",
    description: "Resumes local diagnostic JSONL command logging."
  }
];

document.addEventListener('DOMContentLoaded', () => {
  initA11yControls();
  initSimulator();
  initCommandCatalog();
  initDocsTabs();
  initCopyButtons();
});

/* ==========================================
   1. Accessibility & Theme Controllers
   ========================================== */
function initA11yControls() {
  const fontBtns = document.querySelectorAll('[data-font-size]');
  const themeBtns = document.querySelectorAll('[data-theme]');

  fontBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      fontBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const size = btn.getAttribute('data-font-size');
      document.body.classList.remove('font-large', 'font-xlarge');
      if (size === 'large') document.body.classList.add('font-large');
      if (size === 'xlarge') document.body.classList.add('font-xlarge');
      localStorage.setItem('archi_font_size', size);
    });
  });

  themeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      themeBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const theme = btn.getAttribute('data-theme');
      document.body.classList.remove('theme-warm', 'theme-high-contrast');
      if (theme === 'warm') document.body.classList.add('theme-warm');
      if (theme === 'contrast') document.body.classList.add('theme-high-contrast');
      localStorage.setItem('archi_theme', theme);
    });
  });

  // Restore saved preferences
  const savedFont = localStorage.getItem('archi_font_size');
  if (savedFont) {
    const target = document.querySelector(`[data-font-size="${savedFont}"]`);
    if (target) target.click();
  }
  const savedTheme = localStorage.getItem('archi_theme');
  if (savedTheme) {
    const target = document.querySelector(`[data-theme="${savedTheme}"]`);
    if (target) target.click();
  }
}

/* ==========================================
   2. Interactive Push-to-Talk Simulator
   ========================================== */
function initSimulator() {
  const pttBtn = document.getElementById('sim-ptt-button');
  const simPhrasePills = document.querySelectorAll('.phrase-pill');
  const transcriptStep = document.getElementById('sim-step-transcript');
  const routerStep = document.getElementById('sim-step-router');
  const argvStep = document.getElementById('sim-step-argv');
  const ttsStep = document.getElementById('sim-step-tts');
  const statusDot = document.getElementById('sim-status-dot');
  const statusText = document.getElementById('sim-status-text');

  let isRecording = false;

  function runSimulatedCommand(phrase) {
    if (!phrase) phrase = "volume up";

    // Set UI to listening
    if (statusDot) statusDot.classList.add('active');
    if (statusText) statusText.textContent = "Voxtype Capture Active...";

    transcriptStep.textContent = `🎙️ "${phrase}"`;
    routerStep.textContent = "Matching against commands.toml allowlist...";
    argvStep.textContent = "Waiting...";
    ttsStep.textContent = "Waiting...";

    setTimeout(() => {
      // Find command match
      const cleanPhrase = phrase.toLowerCase().trim();
      const match = ARCHI_COMMANDS.find(cmd => 
        cmd.phrases.some(p => cleanPhrase.includes(p) || p.includes(cleanPhrase))
      ) || ARCHI_COMMANDS[0];

      routerStep.textContent = `✅ Matched ID: ${match.id} (Action: ${match.action})`;
      argvStep.textContent = `⚙️ Executing: ${match.argv}`;
      
      setTimeout(() => {
        if (match.reply) {
          ttsStep.textContent = `🔊 Pocket TTS: "${match.reply}" [PipeWire ducking applied]`;
        } else {
          ttsStep.textContent = `🔊 (Silent action completed without TTS reply)`;
        }
        if (statusText) statusText.textContent = "Idle — Ready for Push-to-Talk";
        if (statusDot) statusDot.classList.remove('active');
      }, 400);

    }, 350);
  }

  if (pttBtn) {
    pttBtn.addEventListener('mousedown', () => {
      isRecording = true;
      pttBtn.classList.add('recording');
      if (statusText) statusText.textContent = "Recording PTT Audio Stream...";
      if (statusDot) statusDot.classList.add('active');
    });

    const stopRecording = () => {
      if (isRecording) {
        isRecording = false;
        pttBtn.classList.remove('recording');
        runSimulatedCommand("read clipboard");
      }
    };

    pttBtn.addEventListener('mouseup', stopRecording);
    pttBtn.addEventListener('mouseleave', stopRecording);

    // Keyboard support: Hold Spacebar while focused
    pttBtn.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && !isRecording) {
        e.preventDefault();
        isRecording = true;
        pttBtn.classList.add('recording');
        if (statusText) statusText.textContent = "Recording PTT Audio Stream...";
        if (statusDot) statusDot.classList.add('active');
      }
    });
    pttBtn.addEventListener('keyup', (e) => {
      if (e.code === 'Space' && isRecording) {
        e.preventDefault();
        stopRecording();
      }
    });
  }

  simPhrasePills.forEach(pill => {
    pill.addEventListener('click', () => {
      const phrase = pill.getAttribute('data-phrase');
      runSimulatedCommand(phrase);
    });
  });
}

/* ==========================================
   3. Searchable Command Catalog
   ========================================== */
function initCommandCatalog() {
  const container = document.getElementById('command-grid-container');
  const searchInput = document.getElementById('command-search-input');
  const filterChips = document.querySelectorAll('.chip-btn');
  const commandCountSpan = document.getElementById('command-count-span');

  let activeCategory = 'all';
  let searchTerm = '';

  function renderCommands() {
    if (!container) return;

    const filtered = ARCHI_COMMANDS.filter(cmd => {
      const matchesCategory = activeCategory === 'all' || cmd.category === activeCategory;
      const matchesSearch = !searchTerm || 
        cmd.id.toLowerCase().includes(searchTerm) ||
        cmd.description.toLowerCase().includes(searchTerm) ||
        cmd.phrases.some(p => p.toLowerCase().includes(searchTerm)) ||
        cmd.argv.toLowerCase().includes(searchTerm);
      return matchesCategory && matchesSearch;
    });

    if (commandCountSpan) {
      commandCountSpan.textContent = `(${filtered.length} commands)`;
    }

    if (filtered.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 2.5rem; text-align: center; color: var(--text-muted); background: var(--bg-primary); border: 1px dashed var(--border-subtle); border-radius: var(--radius-md);">
          <p style="font-size: 1.1rem; color: var(--text-main);">No matching commands found</p>
          <p style="font-size: 0.88rem;">Try searching for "terminal", "volume", "clipboard", or "workspace".</p>
        </div>
      `;
      return;
    }

    container.innerHTML = filtered.map(cmd => `
      <article class="command-card" role="region" aria-label="Command ${cmd.id}">
        <div>
          <div class="command-card-header">
            <span class="cmd-id">${cmd.id}</span>
            <span class="cmd-action-tag ${cmd.action}">${cmd.action}</span>
          </div>
          <p style="font-size: 0.86rem; margin-top: 0.5rem; margin-bottom: 0.75rem;">${cmd.description}</p>
          <div class="phrases-list" aria-label="Trigger phrases">
            ${cmd.phrases.map(p => `<span class="phrase-tag">"${p}"</span>`).join('')}
          </div>
        </div>

        <div>
          <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700; margin-bottom: 0.25rem;">Argv Execution</div>
          <div class="cmd-argv-preview"><code>${escapeHtml(cmd.argv)}</code></div>
          ${cmd.reply ? `
            <div style="margin-top: 0.5rem;" class="cmd-reply-preview">
              <span style="font-size: 0.75rem; color: var(--text-dim);">Response:</span>
              <span>"${cmd.reply}"</span>
            </div>
          ` : ''}
        </div>
      </article>
    `).join('');
  }

  function escapeHtml(text) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchTerm = e.target.value.toLowerCase().trim();
      renderCommands();
    });
  }

  filterChips.forEach(chip => {
    chip.addEventListener('click', () => {
      filterChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeCategory = chip.getAttribute('data-category');
      renderCommands();
    });
  });

  renderCommands();
}

/* ==========================================
   4. Docs / Quickstart Tab Switcher
   ========================================== */
function initDocsTabs() {
  const tabs = document.querySelectorAll('.tab-nav-btn');
  const panes = document.querySelectorAll('.tab-pane');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      panes.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetId = tab.getAttribute('data-tab-target');
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add('active');
      }
    });
  });
}

/* ==========================================
   5. Clipboard Copy Helper
   ========================================== */
function initCopyButtons() {
  const copyButtons = document.querySelectorAll('[data-copy-target]');

  copyButtons.forEach(btn => {
    btn.addEventListener('click', async () => {
      const targetId = btn.getAttribute('data-copy-target');
      const textToCopy = btn.getAttribute('data-copy-text') || 
        (targetId ? document.getElementById(targetId)?.textContent?.trim() : null);

      if (textToCopy) {
        try {
          await navigator.clipboard.writeText(textToCopy);
          const originalText = btn.innerHTML;
          btn.innerHTML = `<span>✓ Copied!</span>`;
          btn.style.borderColor = 'var(--badge-green-text)';
          setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.borderColor = '';
          }, 2000);
        } catch (err) {
          console.warn('Clipboard copy failed:', err);
        }
      }
    });
  });
}
