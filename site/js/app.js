/**
 * ArCHi browser demonstration and command reference.
 */

// The catalog is generated from config/commands.toml in commands.js.

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
  const voiceFeedback = document.getElementById('sim-voice-feedback');
  const voiceText = document.getElementById('sim-voice-text');
  const savvyMatched = document.getElementById('sim-savvy-matched');
  const savvyComplete = document.getElementById('sim-savvy-complete');

  let isRecording = false;
  let simulationTimers = [];
  let savvyPrimed = false;

  function primeSavvyAudio() {
    if (savvyPrimed || !savvyMatched) return;
    savvyMatched.muted = true;
    savvyMatched.play().then(() => {
      savvyMatched.pause();
      savvyMatched.currentTime = 0;
      savvyMatched.muted = false;
      savvyPrimed = true;
    }).catch(() => {
      savvyMatched.muted = false;
    });
  }

  function speakSavvy(track, text) {
    if (voiceFeedback && voiceText) {
      voiceText.textContent = text;
      voiceFeedback.hidden = false;
    }
    [savvyMatched, savvyComplete].forEach(audio => {
      if (audio) {
        audio.pause();
        audio.currentTime = 0;
      }
    });
    if (track) {
      track.volume = 0.75;
      track.play().catch(() => {});
    }
  }

  function runSimulatedCommand(phrase) {
    if (!phrase) phrase = "volume up";
    simulationTimers.forEach(clearTimeout);
    simulationTimers = [];
    primeSavvyAudio();

    // Set UI to listening
    if (statusDot) statusDot.classList.add('active');
    if (statusText) statusText.textContent = "Voxtype Capture Active...";

    transcriptStep.textContent = `🎙️ "${phrase}"`;
    routerStep.textContent = "Matching against commands.toml allowlist...";
    argvStep.textContent = "Waiting...";
    ttsStep.textContent = "Waiting...";

    simulationTimers.push(setTimeout(() => {
      // Find command match
      const cleanPhrase = phrase.toLowerCase().trim();
      const match = ARCHI_COMMANDS.find(cmd => cmd.phrases.includes(cleanPhrase));
      if (!match) {
        routerStep.textContent = "No match in this operational-command demo. App names are discovered on your desktop.";
        argvStep.textContent = "No action.";
        ttsStep.textContent = "I don't know that command yet.";
        if (statusText) statusText.textContent = "Idle — Ready";
        if (statusDot) statusDot.classList.remove('active');
        return;
      }

      routerStep.textContent = `✅ Matched ID: ${match.id} (Action: ${match.action})`;
      argvStep.textContent = `⚙️ Simulated operation: ${match.argv}`;
      speakSavvy(savvyMatched, 'Matched a known, allowlisted action.');
      
      simulationTimers.push(setTimeout(() => {
        if (match.reply) {
          ttsStep.textContent = `🔊 Pocket TTS: "${match.reply}" [PipeWire ducking applied]`;
        } else {
          ttsStep.textContent = `🔊 (Silent action completed without TTS reply)`;
        }
        if (statusText) statusText.textContent = "Idle — Ready for Push-to-Talk";
        if (statusDot) statusDot.classList.remove('active');
        speakSavvy(savvyComplete, match.action === 'clarify' ? 'Waiting for your choice.' : 'Demo complete.');
      }, 3000));

    }, 350));
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
          <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700; margin-bottom: 0.25rem;">Operation</div>
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
      filterChips.forEach(c => c.setAttribute('aria-checked', 'false'));
      chip.classList.add('active');
      chip.setAttribute('aria-checked', 'true');
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
      tabs.forEach(t => t.setAttribute('aria-selected', 'false'));
      panes.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
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
