
  // ── Demo mode flag (set by Jinja2) ─────────────────────────────────────────
  const IS_DEMO = false;
  const CROSSFADE_ENABLED = false;

  function showDemoModal() {
    document.getElementById('demo-modal').classList.add('open');
  }
  function closeDemoModal() {
    document.getElementById('demo-modal').classList.remove('open');
  }
  // Close modal on backdrop click
  document.getElementById('demo-modal').addEventListener('click', function(e) {
    if (e.target === this) closeDemoModal();
  });

  function esc(s) {
    return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // Parse JSON from a fetch response; falls back to { detail: <raw text> } if the
  // server returns a non-JSON body (e.g. "Internal Server Error" on a 500).
  async function safeJson(res) {
    const text = await res.text();
    try { return JSON.parse(text); } catch { return { detail: text || 'Unknown error' }; }
  }

  let isDark = true;
  let isWaDark = true;
  let isAppDark = false;
  let currentPage = 0;
  let totalPages = 1;
  let currentClip = 0;
  let totalClips = 0;

  // ── Session info ───────────────────────────────────────────────────────────────
  async function loadMe() {
    if (IS_DEMO) return;
    try {
      const res = await fetch('/me');
      if (res.status === 401) { window.location.href = '/'; return; }
      const d = await safeJson(res);
      document.getElementById('user-name').textContent = d.discord_name || '—';
      const pct = d.credits_total > 0 ? (d.credits_remaining / d.credits_total * 100) : 0;
      const fill = document.getElementById('credits-fill');
      fill.style.width = pct + '%';
      fill.style.background = pct > 50 ? 'oklch(0.72 0.17 150)' : pct > 20 ? 'oklch(0.75 0.18 75)' : 'oklch(0.62 0.22 25)';
      document.getElementById('credits-label').textContent = d.credits_remaining + ' credits';
      // Load voice settings
      if (d.voice_model !== undefined) _applyVoiceSettings(d);
    } catch {}
  }

  function _applyVoiceSettings(d) {
    const modelEl = document.getElementById('voice-model');
    if (modelEl) modelEl.value = d.voice_model || 'eleven_multilingual_v2';

    const langEl = document.getElementById('voice-language');
    if (langEl) langEl.value = d.voice_language || 'en';

    const audioSpeedEl = document.getElementById('voice-audio-speed');
    if (audioSpeedEl) {
      audioSpeedEl.value = Math.round((d.voice_audio_speed || 1.0) * 100);
      document.getElementById('val-speed').textContent = (d.voice_audio_speed || 1.0).toFixed(2) + '×';
    }
    const ttsSpeedEl = document.getElementById('voice-tts-speed');
    if (ttsSpeedEl) {
      ttsSpeedEl.value = Math.round((d.voice_tts_speed || 1.0) * 100);
      document.getElementById('val-tts-speed').textContent = (d.voice_tts_speed || 1.0).toFixed(2) + '×';
    }
    const stabilityEl = document.getElementById('voice-stability');
    if (stabilityEl) {
      stabilityEl.value = Math.round((d.voice_stability || 0.50) * 100);
      document.getElementById('val-stability').textContent = stabilityEl.value;
    }
    const similarityEl = document.getElementById('voice-similarity');
    if (similarityEl) {
      similarityEl.value = Math.round((d.voice_similarity || 0.70) * 100);
      document.getElementById('val-similarity').textContent = similarityEl.value;
    }
  }

  let _voiceSaveTimer = null;
  function onVoiceSettingChange() {
    clearTimeout(_voiceSaveTimer);
    _voiceSaveTimer = setTimeout(async () => {
      if (IS_DEMO) return;
      try {
        await fetch('/api/voice_settings', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            voice_model:       document.getElementById('voice-model').value,
            voice_language:    document.getElementById('voice-language').value,
            voice_audio_speed: +(document.getElementById('voice-audio-speed').value) / 100,
            voice_tts_speed:   +(document.getElementById('voice-tts-speed').value)   / 100,
            voice_stability:   +(document.getElementById('voice-stability').value)   / 100,
            voice_similarity:  +(document.getElementById('voice-similarity').value)  / 100,
          }),
        });
      } catch {}
    }, 800);
  }

  async function fetchQuota() {
    const el = document.getElementById('el-char-count');
    const dot = document.getElementById('el-status-dot');
    el.textContent = 'Checking…';
    try {
      const res = await fetch('/api/eleven_quota');
      const d = await safeJson(res);
      el.textContent = d.message;
      if (dot) dot.style.background = d.ok ? 'var(--success)' : 'var(--destructive)';
    } catch(e) {
      el.textContent = 'Error: ' + e.message;
      if (dot) dot.style.background = 'var(--destructive)';
    }
  }

  // ── ElevenLabs profiles ────────────────────────────────────────────────────────
  async function loadElevenProfiles() {
    try {
      const res = await fetch('/api/eleven_profiles');
      const profiles = await safeJson(res);
      const sel = document.getElementById('el-profile-select');
      const current = sel.value;
      sel.innerHTML = '<option value="">— none —</option>';
      profiles.forEach(p => {
        const opt = document.createElement('option');
        opt.value = opt.textContent = p.name;
        sel.appendChild(opt);
      });
      // Restore previously selected, or auto-select the active profile
      if (current && [...sel.options].some(o => o.value === current)) {
        sel.value = current;
      } else {
        const active = profiles.find(p => p.active);
        if (active) { sel.value = active.name; fetchQuota(); }
      }
    } catch(e) {}
  }

  async function onProfileSelect(name) {
    if (!name) return;
    try {
      await fetch(`/api/eleven_profiles/${encodeURIComponent(name)}/activate`, { method: 'POST' });
      fetchQuota();
    } catch(e) {}
  }

  async function saveElevenProfile() {
    const key  = document.getElementById('el-api-key').value.trim();
    const name = document.getElementById('el-new-profile').value.trim();
    if (!key)  { setStatus('Paste your ElevenLabs API key first.'); return; }
    if (!name) { setStatus('Enter a profile name.'); return; }
    const res = await fetch('/api/eleven_profiles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, key }),
    });
    if (res.ok) {
      await loadElevenProfiles();
      document.getElementById('el-profile-select').value = name;
      await onProfileSelect(name);
      document.getElementById('el-new-profile').value = '';
      document.getElementById('el-char-count').textContent = 'Profile saved — checking quota…';
    }
  }

  async function deleteElevenProfile() {
    const name = document.getElementById('el-profile-select').value;
    if (!name) { setStatus('Select a profile to delete.'); return; }
    await fetch(`/api/eleven_profiles/${encodeURIComponent(name)}`, { method: 'DELETE' });
    await loadElevenProfiles();
  }

  // Keep old saveElevenKey for direct key save (no profile name)
  async function saveElevenKey() {
    const key = document.getElementById('el-api-key').value.trim();
    if (!key) return;
    const res = await fetch('/api/eleven_key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key }),
    });
    if (res.ok) {
      document.getElementById('el-char-count').textContent = 'Saved — checking quota…';
      fetchQuota();
    }
  }

  // ── Asset lists (music + gameplay) ────────────────────────────────────────────
  function _populateSelect(selId, files) {
    const sel = document.getElementById(selId);
    if (!sel) return;
    const cur = sel.value;
    sel.innerHTML = '<option value="">none</option>';
    files.forEach(f => { const o = document.createElement('option'); o.value = o.textContent = f; sel.appendChild(o); });
    if (cur && [...sel.options].some(o => o.value === cur)) sel.value = cur;
  }

  async function loadMusicList() {
    try {
      const files = await safeJson(await fetch('/api/assets/music'));
      _populateSelect('bg-sound-select', files);
      _populateSelect('wa-bg-sound-select', files);
    } catch(e) {}
  }

  async function loadGameplayList() {
    try {
      const files = await safeJson(await fetch('/api/assets/gameplay'));
      _populateSelect('gameplay-select', files);
      _populateSelect('wa-gameplay-select', files);
    } catch(e) {}
  }

  async function deleteSelectedMedia(type) {
    if (IS_DEMO) { showDemoModal(); return; }
    const isWA = _currentStyle === 'whatsapp';
    const selectId = type === 'music'
      ? (isWA ? 'wa-bg-sound-select' : 'bg-sound-select')
      : (isWA ? 'wa-gameplay-select' : 'gameplay-select');
    const sel = document.getElementById(selectId);
    const filename = sel.value;
    if (!filename || filename === 'none' || filename === '') return;
    if (!confirm(`Delete "${filename}"?`)) return;
    const res = await fetch(`/api/upload/${type}/${encodeURIComponent(filename)}`, { method: 'DELETE' });
    if (res.ok) {
      if (type === 'music') loadMusicList();
      else loadGameplayList();
    } else {
      alert('Error deleting file.');
    }
  }

  async function uploadMediaFile(input, type) {
    if (IS_DEMO) { showDemoModal(); return; }
    const file = input.files[0];
    if (!file) return;
    const statusId = (_currentStyle === 'whatsapp') ? `wa-${type}-upload-status` : `${type}-upload-status`;
    const statusEl = document.getElementById(statusId);
    const maxBytes = CROSSFADE_ENABLED ? Infinity : 500 * 1024 * 1024;
    if (file.size > maxBytes) {
      statusEl.textContent = 'File too large (max 500 MB)';
      statusEl.style.color = 'oklch(0.6 0.2 25)';
      input.value = '';
      return;
    }
    statusEl.textContent = 'Uploading...';
    statusEl.style.color = 'oklch(0.6 0.1 140)';
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch('/api/upload/' + type, { method: 'POST', body: form });
      if (!res.ok) {
        const err = await safeJson(res).catch(() => ({}));
        statusEl.textContent = err.detail || 'Upload failed';
        statusEl.style.color = 'oklch(0.6 0.2 25)';
      } else {
        statusEl.textContent = 'Uploaded!';
        statusEl.style.color = 'oklch(0.6 0.1 140)';
        if (type === 'music') loadMusicList();
        else loadGameplayList();
        setTimeout(() => statusEl.textContent = '', 3000);
      }
    } catch(e) {
      statusEl.textContent = 'Upload failed';
      statusEl.style.color = 'oklch(0.6 0.2 25)';
    }
    input.value = '';
  }

  async function doLogout() {
    await fetch('/logout', { method: 'POST' });
    window.location.href = '/';
  }

  // ── Dark mode ──────────────────────────────────────────────────────────────────
  function toggleDarkMode() {
    isAppDark = !isAppDark;
    document.documentElement.classList.toggle('dark', isAppDark);
    const sunInner = '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>';
    const moonInner = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
    ['dark-icon', 'dark-icon-demo'].forEach(id => {
      const icon = document.getElementById(id);
      if (icon) icon.innerHTML = isAppDark ? sunInner : moonInner;
    });
    saveSettings();
  }

  // ── Script parser ──────────────────────────────────────────────────────────────
  function parseScript(text) {
    const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    const messages = [];
    // contacts = group names (non-message lines, same logic as Python parser)
    // These are the keys used for contact_photo_map in the backend
    const contacts = [];
    const contactsSeen = new Set();
    const skipKeywords = new Set(['wing', 'rizz', 'plug']);
    let pendingWing = false, pendingRizz = false, pendingPlug = false;

    for (const line of lines) {
      const isMsg = /^[12]:\s*/i.test(line);
      const lower = line.toLowerCase();

      if (/^---\s*$/.test(line)) continue;  // group separator, not a contact name
      if (lower === 'wing' || lower === 'wing (bot)') { pendingWing = true; pendingRizz = false; pendingPlug = false; continue; }
      if (lower === 'rizz') { pendingRizz = true; pendingWing = false; pendingPlug = false; continue; }
      if (lower === 'plug') { pendingPlug = true; pendingWing = false; pendingRizz = false; continue; }

      if (isMsg) {
        const m = line.match(/^(1|2):\s*([^>]+?)\s*>\s*(.+)$/);
        if (m) messages.push({ side: m[1], name: m[2].trim(), text: m[3].trim() });
        pendingWing = false; pendingRizz = false; pendingPlug = false;
      } else {
        // Non-message line: if wing/rizz/plug pending it's a voice name, skip
        if (pendingWing || pendingRizz || pendingPlug) { pendingWing = false; pendingRizz = false; pendingPlug = false; continue; }
        // Otherwise it's a group/contact name
        if (!contactsSeen.has(line)) { contactsSeen.add(line); contacts.push(line); }
      }
    }
    return { messages, contacts };
  }

  // ── Settings snapshot ─────────────────────────────────────────────────────────
  function getPreviewBody(page) {
    // Returns a plain object sent as POST JSON — avoids GET URL length limits for long scripts
    if (_currentStyle === 'whatsapp') {
      return {
        script:          document.getElementById('script-input').value,
        project:         _currentProject,
        page,
        style:           'whatsapp',
        wa_theme:        isWaDark ? 'dark' : 'light',
        font_size:       +(document.getElementById('wa-font-size')?.value ?? 50),
        bubble_max_pct:  +(document.getElementById('wa-bubble-max-pct')?.value ?? 82),
        name_font_size:  +(document.getElementById('wa-name-font-size')?.value ?? 40),
        chat_y:          +(document.getElementById('wa-chat-y')?.value ?? 280),
        container_scale: +(document.getElementById('wa-container-scale')?.value ?? 100) / 100,
        chat_height_pct: +(document.getElementById('wa-chat-height')?.value ?? 100),
        rounded_corners: document.querySelector('#wa-corners-seg button.active')?.textContent?.trim() === 'Rounded' ? 1 : 0,
        corner_radius:   +(document.getElementById('wa-corner-radius')?.value ?? 35),
        container_shadow: document.getElementById('wa-switch-shadow')?.classList.contains('on') ? 1 : 0,
      };
    }
    return {
      script:          document.getElementById('script-input').value,
      project:         _currentProject,
      page,
      style:           'ios',
      theme:           isDark ? 'dark' : 'light',
      bubble_scale:    +(document.getElementById('slider-bubble-scale')?.value ?? 120),
      font_size:       Math.round(46 * +(document.getElementById('slider-bubble-scale')?.value ?? 120) / 115),
      bubble_max_pct:  +(document.querySelector('input[oninput*="val-maxw"]')?.value   ?? 58),
      min_bubble_w:    +(document.querySelector('input[oninput*="val-minw"]')?.value   ?? 120),
      bubble_gap:      16,
      line_spacing:    6,
      padding_h:       26,
      padding_v:       18,
      msgs_per_page:   +(document.querySelector('input[oninput*="val-mpp"]')?.value    ?? 6),
      chat_y:          +(document.querySelector('input[oninput*="val-chaty"]')?.value  ?? 350),
      container_scale: +(document.querySelector('input[oninput*="val-cscale"]')?.value ?? 100) / 100,
      chat_top_pad:    35,
      header_name_size:+(document.querySelector('input[oninput*="val-nsize"]')?.value  ?? 40),
      header_name_x:   15,
      header_name_y:   33,
      rounded_corners:       document.querySelector('#video-content .segmented button.active')?.textContent?.trim() === 'Rounded' ? 1 : 0,
      corner_radius:         +(document.getElementById('corner-radius')?.value ?? 35),
      header_persistent:     document.getElementById('switch-header-persistent')?.classList.contains('on') ? 1 : 0,
      header_gradient:       document.getElementById('switch-header-gradient')?.classList.contains('on') ? 1 : 0,
      badge_count:           +(document.getElementById('unread-badge')?.value ?? 0),
      bubble_fade:           document.getElementById('switch-bfade')?.classList.contains('on') ? 1 : 0,
      bubble_fade_intensity: +(document.querySelector('input[oninput*="val-bfade"]')?.value ?? 60),
      container_shadow:      document.getElementById('switch-container-shadow')?.classList.contains('on') ? 1 : 0,
    };
  }

  let _previewTimer = null;
  let _previewBlobUrl = null;

  function refreshPreview() {
    clearTimeout(_previewTimer);
    _previewTimer = setTimeout(async () => {
      try {
        const res = await fetch(`/preview/${currentPage}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(getPreviewBody(currentPage)),
        });
        if (!res.ok) return;
        const tp = res.headers.get('X-Total-Pages');
        if (tp) {
          totalPages = Math.max(1, parseInt(tp, 10));
          document.getElementById('page-label').textContent = `${currentPage + 1} / ${totalPages}`;
        }
        const blob = await res.blob();
        const newUrl = URL.createObjectURL(blob);
        document.getElementById('preview-img').src = newUrl;
        if (_previewBlobUrl) URL.revokeObjectURL(_previewBlobUrl);
        _previewBlobUrl = newUrl;
      } catch(e) {}
    }, 300);  // debounce 300ms so sliders don't spam the server
  }


  // ── Preview update ─────────────────────────────────────────────────────────────
  function updatePreview() {
    const text = document.getElementById('script-input').value;
    const { messages, contacts } = parseScript(text);
    document.getElementById('msg-count').textContent = messages.length + ' msgs';
    // totalPages will be updated from X-Total-Pages header after first preview fetch
    totalPages = Math.max(1, Math.ceil(messages.length / 6));
    currentPage = 0;
    document.getElementById('page-label').textContent = `1 / ${totalPages}`;

    // Update contact list
    const list = document.getElementById('contact-list');
    list.innerHTML = '';
    contacts.forEach(name => {
      const safeId = 'avatar-' + name.replace(/[^a-z0-9]/gi, '_');
      const hasPhoto = _contactPhotoCache.has(name);
      const photoUrl = hasPhoto ? `/api/contact_photo/${encodeURIComponent(name)}?style=${_currentStyle}&t=${_contactPhotoCache.get(name)}` : '';
      const row = document.createElement('div');
      row.className = 'contact-row';
      const avatarInner = hasPhoto ? '' : esc(name[0]?.toUpperCase() ?? '?');
      const avatarStyle = hasPhoto ? `background-image:url('${esc(photoUrl)}');background-size:cover;background-position:center;` : '';
      row.innerHTML = `
        <div style="display:flex;align-items:center;gap:8px">
          <div id="${esc(safeId)}" class="contact-avatar-sm" style="${avatarStyle}">${avatarInner}</div>
          <span style="font-size:13px">${esc(name)}</span>
        </div>
        <div style="display:flex;gap:6px">
          <button class="btn btn-xs btn-save" style="width:auto;padding:0 10px" data-name="${esc(name)}" onclick="uploadContactPhoto(this.dataset.name)">Upload</button>
          ${hasPhoto ? `<button class="btn btn-xs btn-del" style="width:auto;padding:0 8px" data-name="${esc(name)}" onclick="deleteContactPhoto(this.dataset.name)">✕</button>` : ''}
        </div>`;
      list.appendChild(row);
    });
    updateScriptImages();

    refreshPreview();
  }

  function setTheme(t) {
    isDark = t === 'dark';
    document.getElementById('btn-dark').classList.toggle('active', isDark);
    document.getElementById('btn-light').classList.toggle('active', !isDark);
    refreshPreview();
  }

  function setWaTheme(t) {
    isWaDark = t === 'dark';
    document.getElementById('btn-wa-dark').classList.toggle('active', isWaDark);
    document.getElementById('btn-wa-light').classList.toggle('active', !isWaDark);
    saveSettings();
    refreshPreview();
  }

  // ── Tabs ───────────────────────────────────────────────────────────────────────
  function setTab(btn, t) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
    document.getElementById('panel-' + t).classList.remove('hidden');
  }

  // ── Page navigation ────────────────────────────────────────────────────────────
  function navPage(dir) {
    currentPage = Math.max(0, Math.min(totalPages - 1, currentPage + dir));
    document.getElementById('page-label').textContent = `${currentPage + 1} / ${totalPages}`;
    refreshPreview();
  }

  // ── Disclosures ────────────────────────────────────────────────────────────────
  function toggleHowTo() {
    document.getElementById('howto-content').classList.toggle('hidden');
    document.getElementById('howto-chev').classList.toggle('open');
  }

  function toggleEl() {
    const c = document.getElementById('el-content');
    const chev = document.getElementById('el-chev');
    c.style.display = c.style.display === 'none' ? 'flex' : 'none';
    chev.classList.toggle('open');
  }

  function toggleDisc(id) {
    document.getElementById(id + '-content').classList.toggle('hidden');
    document.getElementById(id + '-chev').classList.toggle('open');
  }

  // ── Switches ───────────────────────────────────────────────────────────────────
  function toggleSwitch(btn) { btn.classList.toggle('on'); }

  function onSyncScale(slider) {
    const scale = +slider.value;
    const font  = Math.round(46 * scale / 115);
    document.getElementById('val-scale').textContent = scale + '% · font ' + font;
  }

  // ── Custom clip player ────────────────────────────────────────────────────
  (function initClipPlayer() {
    const audio = document.getElementById('clip-player');
    const seek  = document.getElementById('cc-seek');
    const time  = document.getElementById('cc-time');
    const playIcon  = document.getElementById('cc-play-icon');
    const pauseIcon = document.getElementById('cc-pause-icon');

    function fmtTime(s) {
      if (!isFinite(s)) return '0:00';
      const m = Math.floor(s / 60), sec = Math.floor(s % 60);
      return m + ':' + String(sec).padStart(2, '0');
    }
    function updateUI() {
      const cur = audio.currentTime || 0, dur = audio.duration || 0;
      seek.value = dur ? (cur / dur) * 100 : 0;
      time.textContent = fmtTime(cur) + ' / ' + fmtTime(dur);
      playIcon.style.display  = audio.paused ? '' : 'none';
      pauseIcon.style.display = audio.paused ? 'none' : '';
    }
    audio.addEventListener('timeupdate', updateUI);
    audio.addEventListener('loadedmetadata', updateUI);
    audio.addEventListener('play',  updateUI);
    audio.addEventListener('pause', updateUI);
    audio.addEventListener('ended', updateUI);
  })();

  function ccTogglePlay() {
    const audio = document.getElementById('clip-player');
    if (!audio.src && !audio.currentSrc) return;
    audio.paused ? audio.play() : audio.pause();
  }

  function ccSeek(input) {
    const audio = document.getElementById('clip-player');
    if (audio.duration) audio.currentTime = (input.value / 100) * audio.duration;
  }

  // ── Custom full-audio player ───────────────────────────────────────────────
  (function initCustomPlayer() {
    const audio = document.getElementById('preview-player');
    const seek  = document.getElementById('cp-seek');
    const time  = document.getElementById('cp-time');
    const playIcon  = document.getElementById('cp-play-icon');
    const pauseIcon = document.getElementById('cp-pause-icon');

    function fmtTime(s) {
      if (!isFinite(s)) return '0:00';
      const m = Math.floor(s / 60), sec = Math.floor(s % 60);
      return m + ':' + String(sec).padStart(2, '0');
    }
    function updateUI() {
      const cur = audio.currentTime || 0, dur = audio.duration || 0;
      seek.value = dur ? (cur / dur) * 100 : 0;
      time.textContent = fmtTime(cur) + ' / ' + fmtTime(dur);
      playIcon.style.display  = audio.paused ? '' : 'none';
      pauseIcon.style.display = audio.paused ? 'none' : '';
    }
    audio.addEventListener('timeupdate', updateUI);
    audio.addEventListener('loadedmetadata', updateUI);
    audio.addEventListener('durationchange', updateUI);
    audio.addEventListener('play',  updateUI);
    audio.addEventListener('pause', updateUI);
    audio.addEventListener('ended', updateUI);
  })();

  function cpTogglePlay() {
    const audio = document.getElementById('preview-player');
    if (!audio.src && !audio.currentSrc) return;
    audio.paused ? audio.play() : audio.pause();
  }

  function cpSeek(input) {
    const audio = document.getElementById('preview-player');
    if (audio.duration) audio.currentTime = (input.value / 100) * audio.duration;
  }

  function toggleCornerRadius() {
    const isRounded = document.querySelector('#video-content .segmented button.active')?.textContent?.trim() === 'Rounded';
    document.getElementById('corner-radius').style.display = isRounded ? 'block' : 'none';
  }

  function toggleBubbleFade() {
    const on = document.getElementById('switch-bfade').classList.contains('on');
    document.getElementById('bfade-intensity').style.display = on ? 'flex' : 'none';
  }

  function toggleGameplay() {
    const on = document.getElementById('switch-gameplay').classList.contains('on');
    document.getElementById('gameplay-options').style.display = on ? 'flex' : 'none';
    document.getElementById('crossfade-row').style.display = (on && CROSSFADE_ENABLED) ? 'flex' : 'none';
  }
  function toggleWaGameplay() {
    const on = document.getElementById('wa-switch-gameplay').classList.contains('on');
    document.getElementById('wa-gameplay-options').style.display = on ? 'flex' : 'none';
  }

// ── Segmented ──────────────────────────────────────────────────────────────────
  function segClick(btn) {
    btn.closest('.segmented').querySelectorAll('button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    refreshPreview();
  }

  // ── Style toggle ──────────────────────────────────────────────────────────────
  let _currentStyle = 'ios';

  function toggleWaCornerRadius() {
    const isRounded = document.querySelector('#wa-corners-seg button.active')?.textContent?.trim() === 'Rounded';
    document.getElementById('wa-corner-radius').style.display = isRounded ? 'block' : 'none';
    refreshPreview();
  }

  let _pendingStyle = '';
  async function switchStyle(style, { silent = false } = {}) {
    if (style === _currentStyle) return;
    if (!silent) {
      // Save and close current project before switching styles
      if (_currentProject) {
        await _autoSaveProject();
        _currentProject = '';
      } else if (_hasUnsavedContent()) {
        // Show in-page warning — restore toggle visually until user confirms
        _pendingStyle = style;
        document.getElementById('style-btn-ios').classList.toggle('active', _currentStyle === 'ios');
        document.getElementById('style-btn-wa').classList.toggle('active',  _currentStyle === 'whatsapp');
        showConfirm('style-switch-warning-row');
        return;
      }
      // Reset select BEFORE loadProjectList so `cur` inside it captures '' and never restores
      const _selPS = document.getElementById('project-select');
      _selPS.innerHTML = '<option value="">Select a project\u2026</option>';
      await loadProjectList();
      _selPS.value = '';
      _clearAllContent();
    }
    _currentStyle = style;
    document.getElementById('panel-ios').style.display        = style === 'ios'       ? '' : 'none';
    document.getElementById('panel-whatsapp').style.display   = style === 'whatsapp'  ? '' : 'none';
    document.getElementById('ios-theme-toggle').style.display  = style === 'ios'       ? '' : 'none';
    document.getElementById('wa-theme-toggle').style.display   = style === 'whatsapp'  ? '' : 'none';
    document.getElementById('badge-field').style.display       = style === 'ios'       ? '' : 'none';
    document.getElementById('style-btn-ios').classList.toggle('active', style === 'ios');
    document.getElementById('style-btn-wa').classList.toggle('active',  style === 'whatsapp');
    // Reload contact photos for the new style
    _contactPhotoCache.clear();
    loadContactPhotoCache();
    refreshPreview();
  }

  // ── Settings snapshot (for API calls) ────────────────────────────────────────
  function getSettings() {
    if (_currentStyle === 'whatsapp') return getSettingsWA();
    const sw = id => document.getElementById(id)?.classList.contains('on') ?? false;
    return {
      style:                'ios',
      theme:                isDark ? 'dark' : 'light',
      bubble_scale:         +(document.getElementById('slider-bubble-scale')?.value ?? 120),
      font_size:            Math.round(46 * +(document.getElementById('slider-bubble-scale')?.value ?? 120) / 115),
      bubble_max_pct:       +(document.querySelector('input[oninput*="val-maxw"]')?.value   ?? 58),
      min_bubble_w:         +(document.querySelector('input[oninput*="val-minw"]')?.value   ?? 120),
      bubble_gap:           16,
      line_spacing:         6,
      padding_h:            26,
      padding_v:            18,
      msgs_per_page:        +(document.querySelector('input[oninput*="val-mpp"]')?.value    ?? 6),
      chat_y:               +(document.querySelector('input[oninput*="val-chaty"]')?.value  ?? 350),
      container_scale:      +(document.querySelector('input[oninput*="val-cscale"]')?.value ?? 100) / 100,
      chat_top_pad:         35,
      header_name_size:     +(document.querySelector('input[oninput*="val-nsize"]')?.value  ?? 40),
      header_name_x:        15,
      header_name_y:        33,
      bubble_fade:          sw('switch-bfade'),
      bubble_fade_intensity:+(document.querySelector('input[oninput*="val-bfade"]')?.value  ?? 60),
      group_fade:           sw('switch-group-fade'),
      notif_sound:          sw('switch-notif-sound'),
      header_persistent:    sw('switch-header-persistent'),
      header_gradient:      sw('switch-header-gradient'),
      end_fade_out:         sw('switch-end-fade'),
      container_shadow:     sw('switch-container-shadow'),
      use_popin:            sw('switch-popin'),
      music_fade_out:       sw('switch-music-fade'),
      badge_count:          +(document.getElementById('unread-badge')?.value ?? 0),
      corner_radius:        +(document.getElementById('corner-radius')?.value ?? 35),
      bg_sound_volume:      +(document.getElementById('bg-sound-volume')?.value ?? 0),
    };
  }

  function getSettingsWA() {
    const waRounded = document.querySelector('#wa-corners-seg button.active')?.textContent?.trim() === 'Rounded';
    const waAnim    = document.querySelector('#wa-anim-seg button.active')?.textContent?.trim() === 'Slide down';
    const sw = id => document.getElementById(id)?.classList.contains('on') ?? false;
    return {
      style:            'whatsapp',
      wa_theme:         isWaDark ? 'dark' : 'light',
      font_size:        +(document.getElementById('wa-font-size')?.value ?? 50),
      bubble_max_pct:   +(document.getElementById('wa-bubble-max-pct')?.value ?? 82),
      name_font_size:   +(document.getElementById('wa-name-font-size')?.value ?? 40),
      chat_y:           +(document.getElementById('wa-chat-y')?.value ?? 280),
      container_scale:  +(document.getElementById('wa-container-scale')?.value ?? 100) / 100,
      chat_height_pct:  +(document.getElementById('wa-chat-height')?.value ?? 100),
      rounded_corners:  waRounded,
      corner_radius:    +(document.getElementById('wa-corner-radius')?.value ?? 35),
      use_animation:    waAnim,
      container_shadow: sw('wa-switch-shadow'),
      use_popin:        sw('wa-switch-popin'),
      group_fade:       sw('wa-switch-group-fade'),
      notif_sound:      sw('wa-switch-notif-sound'),
      music_fade_out:   sw('wa-switch-music-fade'),
      end_fade_out:     sw('wa-switch-end-fade'),
      audio_speed:      +(document.getElementById('wa-audio-speed')?.value ?? 100) / 100,
      bg_sound_file:    document.getElementById('wa-bg-sound-select')?.value ?? '',
      bg_sound_start:   document.getElementById('wa-bg-sound-start')?.value ?? '0:00',
      bg_sound_volume:  +(document.getElementById('wa-bg-sound-volume')?.value ?? 0),
      gameplay_on:      sw('wa-switch-gameplay'),
      gameplay_file:    document.getElementById('wa-gameplay-select')?.value ?? '',
      gameplay_start:   document.getElementById('wa-gameplay-start')?.value ?? '0:00',
    };
  }

  // ── Status box ─────────────────────────────────────────────────────────────────
  function setStatus(msg) {
    document.getElementById('status-box').textContent = msg;
  }

  // ── Audio generation ───────────────────────────────────────────────────────────
  let _audioClips = [];
  let _videoDownloadUrl = null;

  async function doGenerateAudio() {
    if (IS_DEMO) { showDemoModal(); return; }
    const script = document.getElementById('script-input').value.trim();
    if (!script) { setStatus('Script is empty.'); return; }

    const btn = document.getElementById(_currentStyle === 'whatsapp' ? 'wa-btn-gen-audio' : 'btn-gen-audio');
    btn.disabled = true;
    const orig = btn.innerHTML;
    btn.textContent = 'Generating…';
    setStatus('Generating audio — this may take a minute…');

    let _progressPollInterval = null;
    try {
      _progressPollInterval = setInterval(async () => {
        try {
          const pr = await fetch('/api/audio_progress');
          if (pr.ok) {
            const pd = await pr.json();
            if (pd.step) setStatus(`Generating audio — ${pd.step}/${pd.total}: ${pd.label}`);
          }
        } catch(_) {}
      }, 600);

      const res = await fetch('/api/generate_audio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script, settings: getSettings(), project: _currentProject }),
      });
      const d = await safeJson(res);
      if (!res.ok) { setStatus('Error: ' + (d.detail || 'Unknown error')); return; }

      _audioClips = d.clips;
      totalClips = d.clips.length;
      currentClip = 0;
      setStatus(`✅ ${d.clips.length} clips · ${(d.total_ms/1000).toFixed(1)}s · ${d.credits_used} credits used`);
      _updateRenderEstimate();

      const _pp1 = document.getElementById('preview-player');
      _pp1.src = '/api/audio_full'; _pp1.load();
      loadClip(0);

      // Switch to audio tab
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
      const audioBtn = [...document.querySelectorAll('.tab-btn')].find(b => b.textContent.trim() === 'audio');
      if (audioBtn) audioBtn.classList.add('active');
      document.getElementById('panel-audio').classList.remove('hidden');

      loadMe();
      await _autoSaveProject();
    } catch(e) {
      setStatus('Error: ' + e.message);
    } finally {
      clearInterval(_progressPollInterval);
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  }

  // ── Update audio (new lines only) ─────────────────────────────────────────────
  async function doUpdateAudio() {
    if (IS_DEMO) { showDemoModal(); return; }
    const script = document.getElementById('script-input').value.trim();
    if (!script) { setStatus('Script is empty.'); return; }
    if (!_audioClips.length) { setStatus('No existing audio — use Generate Audio first.'); return; }

    const btn = document.getElementById(_currentStyle === 'whatsapp' ? 'wa-btn-update-audio' : 'btn-update-audio');
    btn.disabled = true;
    const orig = btn.innerHTML;
    btn.textContent = 'Updating…';
    setStatus('Updating audio — generating only new/changed lines…');

    try {
      const res = await fetch('/api/update_audio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script, settings: getSettings(), project: _currentProject }),
      });
      const d = await safeJson(res);
      if (!res.ok) { setStatus('Error: ' + (d.detail || 'Unknown error')); return; }

      _audioClips = d.clips;
      totalClips = d.clips.length;
      currentClip = 0;
      const credMsg = d.credits_used > 0 ? `${d.credits_used} credits used` : 'no credits used';
      setStatus(`✅ Updated — ${d.new_clips} new, ${d.reused_clips} reused · ${credMsg}`);

      const _pp2 = document.getElementById('preview-player');
      _pp2.src = '/api/audio_full'; _pp2.load();
      loadClip(0);

      // Switch to audio tab
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
      const audioBtn = [...document.querySelectorAll('.tab-btn')].find(b => b.textContent.trim() === 'audio');
      if (audioBtn) audioBtn.classList.add('active');
      document.getElementById('panel-audio').classList.remove('hidden');

      if (d.credits_used > 0) loadMe();
      await _autoSaveProject();
    } catch(e) {
      setStatus('Error: ' + e.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  }

  // ── Regenerate single clip ─────────────────────────────────────────────────────
  async function doRegenerateClip() {
    if (IS_DEMO) { showDemoModal(); return; }
    if (!_audioClips.length) { setStatus('No audio generated yet.'); return; }

    const text = document.getElementById('clip-text').value.trim();
    const btn = document.getElementById('btn-regen-clip');
    btn.disabled = true;
    const orig = btn.innerHTML;
    btn.textContent = 'Regenerating…';
    setStatus(`Regenerating clip ${currentClip + 1}…`);

    try {
      const res = await fetch('/api/regenerate_clip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index: currentClip, text, settings: getSettings() }),
      });
      const d = await safeJson(res);
      if (!res.ok) { setStatus('Error: ' + (d.detail || 'Unknown error')); return; }

      // Update local cache
      _audioClips[currentClip] = {
        ..._audioClips[currentClip],
        duration_ms: d.duration_ms,
        text: d.text,
      };

      const credMsg = d.credits_used > 0 ? `${d.credits_used} credits used` : 'no credits (identical text)';
      setStatus(`✅ Clip ${currentClip + 1} regenerated · ${credMsg}`);

      // Reload clip player + invalidate full preview src (rebuilds in background via executor)
      loadClip(currentClip);
      _autoSaveProject();
      const _pp3 = document.getElementById('preview-player');
      if (_pp3) { _pp3.src = '/api/audio_full?t=' + Date.now(); _pp3.load(); }
      if (d.credits_used > 0) loadMe();
    } catch(e) {
      setStatus('Error: ' + e.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  }

  function loadClip(index, { autoPlay = true } = {}) {
    if (!_audioClips.length) return;
    currentClip = Math.max(0, Math.min(_audioClips.length - 1, index));
    const clip = _audioClips[currentClip];
    document.getElementById('clip-label').textContent = `${currentClip + 1} / ${_audioClips.length}`;
    document.getElementById('clip-meta').textContent =
      `${clip.voice}  ·  ${(clip.duration_ms/1000).toFixed(1)}s  ·  ${clip.side === '1' ? 'received' : 'sent'}`;
    document.getElementById('clip-text').value = clip.text;
    const player = document.getElementById('clip-player');
    player.src = `/api/audio/${currentClip}?t=${Date.now()}`;
    player.load();
    if (autoPlay) player.play().catch(() => {});
    document.getElementById('cc-seek').value = 0;
    document.getElementById('cc-time').textContent = '0:00 / 0:00';
    document.getElementById('cc-play-icon').style.display = '';
    document.getElementById('cc-pause-icon').style.display = 'none';
  }

  // Override navClip
  function navClip(dir) { loadClip(currentClip + dir); }

  // ── Video generation ───────────────────────────────────────────────────────────
  let _currentVideoToken = null;
  let _currentVideoDuration = 0;

  function _switchToVideoTab() {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
    const videoBtn = [...document.querySelectorAll('.tab-btn')].find(b => b.textContent.trim() === 'video');
    if (videoBtn) videoBtn.classList.add('active');
    document.getElementById('panel-video').classList.remove('hidden');
  }

  function _enableDownload(url) {
    const dl = document.getElementById('btn-download-video');
    if (dl) { dl.disabled = false; dl.onclick = () => window.location.href = url; }
    const wrap = document.getElementById('video-wrap');
    if (wrap) {
      wrap.innerHTML = `<video src="${url}" controls playsinline style="width:100%;height:100%;object-fit:contain;border-radius:12px"></video>`;
    }
    const fullUrl = window.location.origin + url;
    let linkEl = document.getElementById('video-temp-link');
    if (!linkEl) {
      linkEl = document.createElement('div');
      linkEl.id = 'video-temp-link';
      linkEl.style.cssText = 'display:flex;align-items:center;gap:6px;margin-top:4px';
      const btn = document.getElementById('btn-download-video');
      btn?.parentNode?.insertBefore(linkEl, btn.nextSibling);
    }
    linkEl.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;background:var(--muted);border:1px solid var(--border);border-radius:10px;padding:7px 10px;width:100%;min-width:0">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;opacity:.45"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
        <span style="flex:1;font-size:10px;color:var(--muted-fg);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:var(--font-mono);min-width:0">${fullUrl}</span>
        <span style="font-size:10px;color:var(--muted-fg);opacity:.6;white-space:nowrap;flex-shrink:0">30 min</span>
        <button onclick="navigator.clipboard.writeText('${fullUrl}').then(()=>{this.textContent='Copied!';setTimeout(()=>this.textContent='Copy',1500)})" style="flex-shrink:0;padding:0 10px;height:26px;font-size:11px;font-weight:500;background:var(--primary);color:var(--primary-fg);border:none;border-radius:6px;cursor:pointer;white-space:nowrap">Copy</button>
      </div>`;
  }

  function _buildVideoPayload(s) {
    const gameplayOn    = document.getElementById('switch-gameplay')?.classList.contains('on') ?? false;
    const gameplayFile  = document.getElementById('gameplay-select')?.value ?? '';
    const gameplayStart = document.getElementById('gameplay-start')?.value ?? '0:00';
    const bgSoundFile   = document.getElementById('bg-sound-select')?.value ?? '';

    if (_currentStyle === 'whatsapp') {
      const speed        = +(document.getElementById('wa-audio-speed')?.value ?? 100) / 100;
      const waGpOn       = document.getElementById('wa-switch-gameplay')?.classList.contains('on') ?? false;
      const waGpFile     = document.getElementById('wa-gameplay-select')?.value ?? '';
      const waGpStart    = document.getElementById('wa-gameplay-start')?.value ?? '0:00';
      const waBgSound    = document.getElementById('wa-bg-sound-select')?.value ?? '';
      return {
        settings:         s,
        project:          _currentProject,
        rounded_corners:  s.rounded_corners,
        corner_radius:    s.corner_radius,
        use_animation:    s.use_animation,
        use_popin:        s.use_popin,
        container_shadow: s.container_shadow,
        group_fade:       s.group_fade,
        notif_sound:      s.notif_sound,
        container_scale:  s.container_scale,
        music_fade_out:   s.music_fade_out,
        end_fade_out:     s.end_fade_out,
        speed_factor:     speed,
        bg_sound_file:    waBgSound === 'none' ? '' : waBgSound,
        bg_sound_start:   document.getElementById('wa-bg-sound-start')?.value ?? '0:00',
        bg_sound_volume:  +(document.getElementById('wa-bg-sound-volume')?.value ?? 0),
        gameplay_on:      waGpOn,
        gameplay_file:    waGpFile === 'none' ? '' : waGpFile,
        gameplay_start:   waGpStart,
      };
    }

    const speed         = +(document.getElementById('voice-audio-speed')?.value ?? 100) / 100;
    const segmenteds    = document.querySelectorAll('#video-content .segmented');
    const corners       = segmenteds[0]?.querySelector('button.active')?.textContent?.trim();
    const animation     = segmenteds[1]?.querySelector('button.active')?.textContent?.trim();
    return {
      settings:          s,
      project:           _currentProject,
      animation_mode:    animation?.toLowerCase().includes('slide') ? 'slide' : 'crop',
      rounded_corners:   corners === 'Rounded',
      corner_radius:     +(document.getElementById('corner-radius')?.value ?? 35),
      group_fade:        s.group_fade,
      notif_sound:       s.notif_sound,
      header_persistent: s.header_persistent,
      end_fade_out:      s.end_fade_out,
      container_shadow:  s.container_shadow,
      music_fade_out:    s.music_fade_out,
      use_popin:         s.use_popin,
      container_scale:   s.container_scale,
      speed_factor:      speed,
      badge_count:       +(document.getElementById('unread-badge')?.value ?? 0),
      bg_sound_file:     bgSoundFile === 'none' ? '' : bgSoundFile,
      bg_sound_start:    document.getElementById('bg-sound-start')?.value ?? '0:00',
      bg_sound_volume:   +(document.getElementById('bg-sound-volume')?.value ?? 0),
      gameplay_on:       gameplayOn,
      gameplay_file:     gameplayFile === 'none' ? '' : gameplayFile,
      gameplay_start:    gameplayStart,
      crossfade_out:     CROSSFADE_ENABLED ? (document.getElementById('crossfade-out')?.value.trim() || null) : null,
      crossfade_in:      CROSSFADE_ENABLED ? (document.getElementById('crossfade-in')?.value.trim() || null) : null,
    };
  }

  async function doGenerateVideo() {
    if (IS_DEMO) { showDemoModal(); return; }
    if (!_audioClips.length) { setStatus('Generate audio first.'); return; }

    const btn = document.getElementById(_currentStyle === 'whatsapp' ? 'wa-btn-gen-video' : 'btn-gen-video');
    btn.disabled = true;
    const orig = btn.innerHTML;
    btn.textContent = 'Building video…';
    setStatus('Building video — starting…');

    let _progressPoll = null;
    _progressPoll = setInterval(async () => {
      try {
        const pr = await fetch('/api/video_progress');
        if (!pr.ok) return;
        const pd = await pr.json();
        if (!pd.active) return;
        const msg = pd.msg || '';
        const isEncoding = msg.toLowerCase().includes('encoding');
        let statusStr;
        if (isEncoding) {
          const elapsed = pd.elapsed_s || 0;
          statusStr = `Building video — Encoding with FFmpeg… (${elapsed}s elapsed)`;
        } else {
          const pct = pd.pct;
          statusStr = `Building video — ${msg} (${pct}%)`;
          if (pd.eta_s !== null && pd.eta_s !== undefined && pd.eta_s > 0) {
            const etaMin = Math.floor(pd.eta_s / 60);
            const etaSec = pd.eta_s % 60;
            const etaStr = etaMin > 0 ? `${etaMin}m ${etaSec}s` : `${etaSec}s`;
            statusStr += ` — ~${etaStr} remaining`;
          }
        }
        setStatus(statusStr);
      } catch(_) {}
    }, 2000);

    try {
      const s = getSettings();
      const _genStart = Date.now();
      const res = await fetch('/api/generate_video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(_buildVideoPayload(s)),
      });
      clearInterval(_progressPoll);
      const d = await safeJson(res);
      if (!res.ok) { setStatus('Error: ' + (d.detail || 'Unknown error')); return; }

      _currentVideoToken = d.token;
      _currentVideoDuration = d.duration_s || 0;
      _videoDownloadUrl = d.download_url;
      _updateShortenVisibility();

      _switchToVideoTab();
      _enableDownload(_videoDownloadUrl);

      const mins = Math.floor(_currentVideoDuration / 60);
      const secs = Math.round(_currentVideoDuration % 60);
      const durStr = `${mins}:${secs.toString().padStart(2, '0')}`;
      const genSecs = ((Date.now() - _genStart) / 1000).toFixed(1);

      const _shortenId  = _currentStyle === 'whatsapp' ? 'wa-switch-shorten' : 'switch-shorten';
      const autoShorten = document.getElementById(_shortenId)?.classList.contains('on');
      if (autoShorten && _currentVideoDuration > 179) {
        setStatus(`Video is ${durStr} — auto-shortening to 2:59…`);
        await doShortenVideo();
      } else if (_currentVideoDuration > 179) {
        setStatus(`✅ Video ready! ${durStr} · generated in ${genSecs}s — over 2:59, use Shorten if needed.`);
      } else {
        setStatus(`✅ Video ready! ${durStr} · generated in ${genSecs}s`);
      }
      await _autoSaveProject();
    } catch(e) {
      // Network drop (e.g. mobile screen lock) — video may have finished on the server
      const isNetworkError = e instanceof TypeError && e.message.toLowerCase().includes('fetch');
      if (isNetworkError) {
        setStatus('Connection lost — video is still generating, please wait…');
        try {
          for (let i = 0; i < 180; i++) {
            await new Promise(r => setTimeout(r, 5000));
            const rec = await fetch('/api/last_video');
            const rd = rec.ok ? await rec.json() : {};
            if (rd.download_url) {
              _currentVideoToken = rd.token;
              _currentVideoDuration = rd.duration_s || 0;
              _videoDownloadUrl = rd.download_url;
              _updateShortenVisibility();
              _switchToVideoTab();
              _enableDownload(_videoDownloadUrl);
              const mins = Math.floor(_currentVideoDuration / 60);
              const secs = Math.round(_currentVideoDuration % 60);
              setStatus(`✅ Video ready! ${mins}:${secs.toString().padStart(2,'0')}`);
              await _autoSaveProject();
              return;
            }
          }
        } catch(_) {}
        setStatus('Connection lost — video may still be processing, please wait.');
      } else {
        setStatus('Error: ' + e.message);
      }
    } finally {
      clearInterval(_progressPoll);
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  }

  function _updateShortenVisibility() {
    const show = _currentVideoDuration > 179;
    document.getElementById('btn-shorten').style.display  = show ? '' : 'none';
    document.getElementById('shorten-hint').style.display = show ? '' : 'none';
  }

  // ── Shorten to 2:59 ────────────────────────────────────────────────────────────
  async function doShortenVideo() {
    if (IS_DEMO) { showDemoModal(); return; }
    if (!_currentVideoToken) { setStatus('Generate video first.'); return; }
    if (_currentVideoDuration > 0 && _currentVideoDuration <= 179) {
      setStatus('Video is already under 2:59.'); return;
    }

    const btn = document.getElementById('btn-shorten');
    btn.disabled = true;
    const orig = btn.innerHTML;
    btn.textContent = 'Shortening…';
    setStatus('Shortening to 2:59 — re-rendering at higher speed…');

    try {
      const s = getSettings();
      const payload = { token: _currentVideoToken, ..._buildVideoPayload(s) };
      const res = await fetch('/api/shorten', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const d = await safeJson(res);
      if (!res.ok) { setStatus('Error: ' + (d.detail || 'Unknown error')); return; }

      _currentVideoToken = d.token;
      _currentVideoDuration = d.duration_s || 0;
      _videoDownloadUrl = d.download_url;
      _updateShortenVisibility();

      _enableDownload(_videoDownloadUrl);
      const mins = Math.floor(d.duration_s / 60);
      const secs = Math.round(d.duration_s % 60);
      setStatus(`✅ Shortened to ${mins}:${secs.toString().padStart(2, '0')}`);
    } catch(e) {
      setStatus('Error: ' + e.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  }

  // ── Settings persistence (localStorage) ──────────────────────────────────────
  const _SK = 'imsg_settings_v1';

  function saveSettings() {
    if (IS_DEMO) return;
    const data = { theme: isDark ? 'dark' : 'light', wa_theme: isWaDark ? 'dark' : 'light', appDark: isAppDark };
    const voicesContent = document.getElementById('voices-content');
    document.querySelectorAll('input[type=range]').forEach(el => {
      if (voicesContent && voicesContent.contains(el)) return; // saved in DB
      const dsKey = el.dataset.settingsKey;
      if (dsKey) { data['dsk_' + dsKey] = el.value; return; }
      const m = (el.getAttribute('oninput') || '').match(/val-([\w-]+)/);
      if (m && m[1] !== 'speed') data['sl_' + m[1]] = el.value;
    });
    try { localStorage.setItem(_SK, JSON.stringify(data)); } catch(e) {}
  }

  function loadSettings() {
    try {
      const raw = localStorage.getItem(_SK);
      if (!raw) return;
      const data = JSON.parse(raw);
      const voicesContent = document.getElementById('voices-content');
      // Restore sliders (fire oninput so display spans update)
      document.querySelectorAll('input[type=range]').forEach(el => {
        if (voicesContent && voicesContent.contains(el)) return; // restored from DB
        const dsKey = el.dataset.settingsKey;
        if (dsKey) {
          if (data['dsk_' + dsKey] !== undefined) { el.value = data['dsk_' + dsKey]; el.dispatchEvent(new Event('input')); }
          return;
        }
        const m = (el.getAttribute('oninput') || '').match(/val-([\w-]+)/);
        if (m && m[1] !== 'speed' && data['sl_' + m[1]] !== undefined) {
          el.value = data['sl_' + m[1]];
          el.dispatchEvent(new Event('input'));
        }
      });
      // Restore render theme
      if (data.theme) setTheme(data.theme);
      if (data.wa_theme) setWaTheme(data.wa_theme);
      // Restore app UI dark mode
      if (data.appDark !== undefined && data.appDark !== isAppDark) toggleDarkMode();
    } catch(e) {}
  }

  // ── Sliders → refresh preview + save ─────────────────────────────────────────
  document.querySelectorAll('input[type="range"]').forEach(s => {
    s.addEventListener('input', () => { refreshPreview(); saveSettings(); });
  });

  // ── Contact photos ─────────────────────────────────────────────────────────────
  const _contactPhotoCache = new Map();  // name → timestamp (cache buster)

  async function loadContactPhotoCache() {
    try {
      const names = await safeJson(await fetch(`/api/contact_photos?style=${_currentStyle}`));
      names.forEach(n => { if (!_contactPhotoCache.has(n)) _contactPhotoCache.set(n, Date.now()); });
    } catch(e) {}
  }

  async function uploadContactPhoto(name) {
    if (IS_DEMO) { showDemoModal(); return; }
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append('file', file);
      try {
        const res = await fetch(`/api/contact_photo/${encodeURIComponent(name)}?style=${_currentStyle}`, { method: 'POST', body: fd });
        if (res.ok) {
          _contactPhotoCache.set(name, Date.now());
          updatePreview();  // rebuild contact list with new photo
          refreshPreview();
        } else {
          setStatus('Error uploading photo.');
        }
      } catch(e) {
        setStatus('Error uploading photo: ' + e.message);
      }
    };
    input.click();
  }

  async function deleteContactPhoto(name) {
    await fetch(`/api/contact_photo/${encodeURIComponent(name)}?style=${_currentStyle}`, { method: 'DELETE' });
    _contactPhotoCache.delete(name);
    updatePreview();
    refreshPreview();
  }

  // ── Script images ──────────────────────────────────────────────────────────────
  const _scriptImageCache = new Map();  // name → timestamp

  function parseImageNames(script) {
    const names = [], seen = new Set();
    for (const line of script.split(/\r?\n/)) {
      const m = line.trim().match(/^[12]:\s*img:\s*(.+)/i);
      if (m) {
        const name = m[1].trim();
        if (!seen.has(name)) { seen.add(name); names.push(name); }
      }
    }
    return names;
  }

  async function loadScriptImageCache() {
    // preload which images already exist — not a separate endpoint, just try serving them
  }

  function updateScriptImages() {
    const script = document.getElementById('script-input').value;
    const names = parseImageNames(script);
    const container = document.getElementById('script-images-list');
    const counter = document.getElementById('script-images-counter');
    if (!container) return;
    if (!names.length) {
      container.innerHTML = '<span style="font-size:11px;color:var(--muted-fg)">Add img: lines to script</span>';
      if (counter) counter.style.display = 'none';
      return;
    }
    const uploaded = names.filter(n => _scriptImageCache.has(n)).length;
    if (counter) { counter.textContent = `${uploaded}/${names.length}`; counter.style.display = ''; }
    container.innerHTML = '';
    names.forEach(name => {
      const hasImg = _scriptImageCache.has(name);
      const row = document.createElement('div');
      row.style.cssText = 'display:flex;align-items:center;justify-content:space-between;gap:6px;padding:3px 0;border-bottom:1px solid var(--border)';
      row.innerHTML = `
        <span style="font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(name)}</span>
        <div style="display:flex;gap:4px;flex-shrink:0">
          <button class="btn btn-xs btn-save" style="width:auto;padding:0 8px;height:28px;font-size:11px" data-name="${esc(name)}" onclick="uploadScriptImage(this.dataset.name)">
            ${hasImg ? '↺' : '+'}
          </button>
          ${hasImg ? `<button class="btn btn-xs btn-del" style="width:auto;padding:0 6px;height:28px" data-name="${esc(name)}" onclick="deleteScriptImage(this.dataset.name)">✕</button>` : ''}
        </div>`;
      container.appendChild(row);
    });
  }

  async function uploadScriptImage(name) {
    if (IS_DEMO) { showDemoModal(); return; }
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch(`/api/script_image/${encodeURIComponent(name)}`, { method: 'POST', body: fd });
      if (res.ok) {
        _scriptImageCache.set(name, Date.now());
        updateScriptImages();
        refreshPreview();
      }
    };
    input.click();
  }

  async function deleteScriptImage(name) {
    await fetch(`/api/script_image/${encodeURIComponent(name)}`, { method: 'DELETE' });
    _scriptImageCache.delete(name);
    updateScriptImages();
    refreshPreview();
  }

  // ── Settings apply (for project load) ────────────────────────────────────────
  function applySettings(s) {
    if (!s || typeof s !== 'object') return;
    // iOS settings — only when loading iOS projects (WA handled explicitly below)
    if (s.style !== 'whatsapp') {
      const keyToPattern = {
        bubble_scale: 'val-scale', bubble_max_pct: 'val-maxw',
        min_bubble_w: 'val-minw',
        msgs_per_page: 'val-mpp',
        chat_y: 'val-chaty', header_name_size: 'val-nsize',
        bubble_fade_intensity: 'val-bfade',
        container_scale: 'val-cscale',
      };
      // Keys stored as 0-1 float but slider uses integer percentage
      const pctKeys = { container_scale: true };
      document.querySelectorAll('#panel-ios input[type=range]').forEach(el => {
        // Match by data-settings-key first (e.g. bubble_scale)
        const dsKey = el.dataset.settingsKey;
        if (dsKey) {
          if (s[dsKey] !== undefined) { el.value = s[dsKey]; el.dispatchEvent(new Event('input')); }
          return;
        }
        // Match by oninput pattern
        const m = (el.getAttribute('oninput') || '').match(/val-([\w-]+)/);
        if (!m) return;
        const pattern = 'val-' + m[1];
        const key = Object.keys(keyToPattern).find(k => keyToPattern[k] === pattern);
        if (key && s[key] !== undefined) {
          el.value = pctKeys[key] ? Math.round(s[key] * 100) : s[key];
          el.dispatchEvent(new Event('input'));
        }
      });
      if (s.theme) setTheme(s.theme);
      [
        ['switch-group-fade', 'group_fade'], ['switch-notif-sound', 'notif_sound'],
        ['switch-header-persistent', 'header_persistent'], ['switch-header-gradient', 'header_gradient'], ['switch-bfade', 'bubble_fade'],
        ['switch-end-fade', 'end_fade_out'], ['switch-container-shadow', 'container_shadow'],
        ['switch-music-fade', 'music_fade_out'], ['switch-popin', 'use_popin'],
      ].forEach(([id, key]) => {
        if (s[key] === undefined) return;
        const btn = document.getElementById(id);
        if (btn) btn.classList.toggle('on', !!s[key]);
      });
      toggleBubbleFade();
      if (s.badge_count !== undefined) {
        const badgeEl = document.getElementById('unread-badge');
        if (badgeEl) { badgeEl.value = s.badge_count; badgeEl.dispatchEvent(new Event('input')); }
      }
      if (s.corner_radius !== undefined) {
        const crEl = document.getElementById('corner-radius');
        if (crEl) { crEl.value = s.corner_radius; crEl.dispatchEvent(new Event('input')); }
      }
      if (s.bg_sound_volume !== undefined) {
        const volEl = document.getElementById('bg-sound-volume');
        if (volEl) volEl.value = s.bg_sound_volume;
      }
      toggleCornerRadius();
    }
    // Restore style toggle if project has a style set
    if (s.style && s.style !== _currentStyle) switchStyle(s.style, { silent: true });
    // Restore WA sliders if whatsapp project
    if (s.style === 'whatsapp') {
      const wf = document.getElementById('wa-font-size');
      const wm = document.getElementById('wa-bubble-max-pct');
      const wn = document.getElementById('wa-name-font-size');
      if (wf && s.font_size !== undefined) { wf.value = s.font_size; document.getElementById('wa-val-font').textContent = s.font_size; }
      if (wm && s.bubble_max_pct !== undefined) { wm.value = s.bubble_max_pct; document.getElementById('wa-val-maxw').textContent = s.bubble_max_pct + '%'; }
      if (wn && s.name_font_size !== undefined) { wn.value = s.name_font_size; document.getElementById('wa-val-namefont').textContent = s.name_font_size; }
      const wcy = document.getElementById('wa-chat-y');
      const wcs = document.getElementById('wa-container-scale');
      if (wcy && s.chat_y !== undefined) { wcy.value = s.chat_y; document.getElementById('wa-val-chaty').textContent = s.chat_y; }
      if (wcs && s.container_scale !== undefined) { const pct = Math.round(s.container_scale * 100); wcs.value = pct; document.getElementById('wa-val-csize').textContent = pct + '%'; }
      const wch = document.getElementById('wa-chat-height');
      if (wch && s.chat_height_pct !== undefined) { wch.value = s.chat_height_pct; document.getElementById('wa-val-chatheight').textContent = s.chat_height_pct + '%'; }
      if (s.rounded_corners !== undefined) {
        const btns = document.querySelectorAll('#wa-corners-seg button');
        btns.forEach(b => b.classList.toggle('active', b.textContent.trim() === (s.rounded_corners ? 'Rounded' : 'Square')));
        if (s.corner_radius !== undefined) document.getElementById('wa-corner-radius').value = s.corner_radius;
        toggleWaCornerRadius();
      }
      if (s.use_animation !== undefined) {
        const btns = document.querySelectorAll('#wa-anim-seg button');
        btns.forEach(b => b.classList.toggle('active', b.textContent.trim() === (s.use_animation ? 'Slide down' : 'Crop (instant)')));
      }
      const wss = document.getElementById('wa-switch-shadow');
      if (wss && s.container_shadow !== undefined) { wss.classList.toggle('on', !!s.container_shadow); }
      const wsp = document.getElementById('wa-switch-popin');
      if (wsp && s.use_popin !== undefined) { wsp.classList.toggle('on', !!s.use_popin); }
      const wsgf = document.getElementById('wa-switch-group-fade');
      if (wsgf && s.group_fade !== undefined) { wsgf.classList.toggle('on', !!s.group_fade); }
      const wsns = document.getElementById('wa-switch-notif-sound');
      if (wsns && s.notif_sound !== undefined) { wsns.classList.toggle('on', !!s.notif_sound); }
      const wsmf = document.getElementById('wa-switch-music-fade');
      if (wsmf && s.music_fade_out !== undefined) { wsmf.classList.toggle('on', !!s.music_fade_out); }
      const wsef = document.getElementById('wa-switch-end-fade');
      if (wsef && s.end_fade_out !== undefined) { wsef.classList.toggle('on', !!s.end_fade_out); }
      // Audio speed
      const waSpd = document.getElementById('wa-audio-speed');
      if (waSpd && s.audio_speed !== undefined) { const pct = Math.round(s.audio_speed * 100); waSpd.value = pct; document.getElementById('wa-val-speed').textContent = (s.audio_speed).toFixed(2) + '×'; }
      // Background sound
      if (s.bg_sound_file !== undefined) { const sel = document.getElementById('wa-bg-sound-select'); if (sel) { for (const o of sel.options) { if (o.value === s.bg_sound_file) { sel.value = s.bg_sound_file; break; } } } }
      if (s.bg_sound_start !== undefined) { const el = document.getElementById('wa-bg-sound-start'); if (el) el.value = s.bg_sound_start; }
      if (s.bg_sound_volume !== undefined) { const el = document.getElementById('wa-bg-sound-volume'); if (el) el.value = s.bg_sound_volume; }
      // Gameplay
      const wsgp = document.getElementById('wa-switch-gameplay');
      if (wsgp && s.gameplay_on !== undefined) { wsgp.classList.toggle('on', !!s.gameplay_on); toggleWaGameplay(); }
      if (s.gameplay_file !== undefined) { const sel = document.getElementById('wa-gameplay-select'); if (sel) { for (const o of sel.options) { if (o.value === s.gameplay_file) { sel.value = s.gameplay_file; break; } } } }
      if (s.gameplay_start !== undefined) { const el = document.getElementById('wa-gameplay-start'); if (el) el.value = s.gameplay_start; }
    }
  }

  // ── Projects ───────────────────────────────────────────────────────────────────
  let _currentProject = '';
  let _pendingProject  = '';   // target to load after unsaved warning resolves

  function _hasUnsavedContent() {
    const script = document.getElementById('script-input').value.trim();
    return script.length > 0 || _audioClips.length > 0;
  }

  async function _autoSaveProject() {
    if (!_currentProject) return;
    try {
      await fetch(`/api/projects/${encodeURIComponent(_currentProject)}/save`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          script: document.getElementById('script-input').value,
          settings: getSettings(),
        }),
      });
    } catch(e) {}
  }

  let _autoSaveTimer = null;
  function _scheduleAutoSave() {
    if (!_currentProject) return;
    const projectAtSchedule = _currentProject;
    clearTimeout(_autoSaveTimer);
    _autoSaveTimer = setTimeout(async () => {
      if (_currentProject !== projectAtSchedule) return;
      await _autoSaveProject();
      const sb = document.getElementById('status-box');
      if (sb && !sb.textContent.startsWith('Error')) {
        const prev = sb.textContent;
        if (!prev.includes('(auto-saved)')) sb.textContent = prev + ' (auto-saved)';
      }
    }, 3000);
  }

  async function _updateRenderEstimate() {
    const el = document.getElementById('render-estimate');
    if (!el || !_audioClips.length) { if (el) el.textContent = ''; return; }
    try {
      const settings = getSettings();
      const mode = settings.animation_mode || 'crop';
      const r = await fetch(`/api/estimate_render_time?msg_count=${_audioClips.length}&animation_mode=${mode}`);
      if (r.ok) {
        const rd = await r.json();
        el.textContent = `~${rd.seconds}s estimated`;
      }
    } catch(_) {}
  }

  function _clearAllContent() {
    // Clear script
    const scriptEl = document.getElementById('script-input');
    if (scriptEl) { scriptEl.value = ''; }
    // Clear audio
    _audioClips = []; totalClips = 0; currentClip = 0;
    document.getElementById('clip-label').textContent = '— / —';
    document.getElementById('clip-meta').textContent = 'No audio generated yet';
    document.getElementById('clip-text').value = 'Generate audio first to review clips here.';
    const player = document.getElementById('preview-player');
    if (player) player.removeAttribute('src');
    const clipPlayer = document.getElementById('clip-player');
    if (clipPlayer) clipPlayer.removeAttribute('src');
    document.getElementById('cc-seek').value = 0;
    document.getElementById('cc-time').textContent = '0:00 / 0:00';
    document.getElementById('cc-play-icon').style.display = '';
    document.getElementById('cc-pause-icon').style.display = 'none';
    // Clear video
    _currentVideoToken = null; _currentVideoDuration = 0; _videoDownloadUrl = null;
    const dl = document.getElementById('btn-download-video');
    if (dl) { dl.disabled = true; dl.removeAttribute('href'); dl.removeAttribute('download'); }
    const linkEl = document.getElementById('video-temp-link');
    if (linkEl) linkEl.remove();
    // Clear contact photo & image caches
    _contactPhotoCache.clear();
    _scriptImageCache.clear();
    updatePreview();
  }

  async function loadProjectList() {
    try {
      const projects = await safeJson(await fetch('/api/projects'));
      const sel = document.getElementById('project-select');
      const cur = sel.value;
      sel.innerHTML = '<option value="">Select a project…</option>';
      projects.forEach(p => {
        const opt = document.createElement('option');
        const styleLabel = p.style === 'whatsapp' ? ' [WA]' : ' [iOS]';
        opt.value = p.name;
        opt.textContent = p.name + styleLabel;
        opt.dataset.style = p.style || 'ios';
        sel.appendChild(opt);
      });
      if (cur && [...sel.options].some(o => o.value === cur)) sel.value = cur;
    } catch(e) {}
  }

  async function onProjectSelect(val) {
    if (!val || val === _currentProject) {
      // Reset dropdown if user picked blank
      return;
    }
    // Check if project style matches current mode
    const sel = document.getElementById('project-select');
    const selectedOpt = [...sel.options].find(o => o.value === val);
    const projStyle = selectedOpt?.dataset?.style || 'ios';
    // Has unsaved content without an active project → warn
    if (!_currentProject && _hasUnsavedContent()) {
      _pendingProject = val;
      document.getElementById('project-select').value = '';  // reset dropdown
      showConfirm('unsaved-warning-row');
      return;
    }
    // Has an active project → auto-save BEFORE switching style (so getSettings reads correct style)
    if (_currentProject) {
      await _autoSaveProject();
    }
    // Now switch style if needed (after saving old project with its own style)
    if (projStyle !== _currentStyle) {
      await switchStyle(projStyle, { silent: true });
    }
    await doLoadProject(val);
  }

  // ── New project ────────────────────────────────────────────────────────────────
  async function doNewProject() {
    if (IS_DEMO) { showDemoModal(); return; }
    // Has an active project → save it silently, then show create form
    if (_currentProject) {
      await _autoSaveProject();
      _showCreateProjectRow();
      return;
    }
    // Has unsaved content without a project → warn first
    if (_hasUnsavedContent()) {
      _pendingProject = '@@crear@@';
      showConfirm('unsaved-warning-row');
      return;
    }
    _showCreateProjectRow();
  }

  function _showCreateProjectRow() {
    document.getElementById('new-project-name').value = '';
    const errEl = document.getElementById('create-project-err');
    errEl.textContent = ''; errEl.style.display = 'none';
    showConfirm('create-project-row');
  }

  async function doCreateProjectConfirm() {
    const name = document.getElementById('new-project-name').value.trim();
    const errEl = document.getElementById('create-project-err');
    if (!name) { errEl.textContent = 'Project name cannot be empty.'; errEl.style.display = 'block'; return; }
    const res = await fetch('/api/projects/create', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ name, style: _currentStyle }),
    });
    if (!res.ok) {
      const d = await safeJson(res);
      errEl.textContent = d.detail || 'Error creating project.';
      errEl.style.display = 'block';
      return;
    }
    hideConfirm('create-project-row');
    _clearAllContent();
    _currentProject = name;
    await loadProjectList();
    document.getElementById('project-select').value = name;
    document.getElementById('project-label').textContent = name;
    setStatus(`✅ Project '${name}' created.`);
  }

  // ── Unsaved warning callbacks ──────────────────────────────────────────────────
  async function doDiscardWork() {
    hideConfirm('unsaved-warning-row');
    const pending = _pendingProject;
    _pendingProject = '';
    // Clear audio and script since the user chose to discard
    _audioClips = []; totalClips = 0; currentClip = 0;
    document.getElementById('clip-label').textContent = '— / —';
    document.getElementById('clip-meta').textContent = 'No audio generated yet';
    document.getElementById('clip-text').value = 'Generate audio first to review clips here.';
    const _pp = document.getElementById('preview-player');
    if (_pp) _pp.removeAttribute('src');
    const _cp = document.getElementById('clip-player');
    if (_cp) _cp.removeAttribute('src');
    document.getElementById('script-input').value = '';
    if (pending === '@@crear@@') {
      _showCreateProjectRow();
    } else if (pending) {
      await doLoadProject(pending);
    }
  }

  function doSaveFirst() {
    hideConfirm('unsaved-warning-row');
    document.getElementById('save-current-name').value = '';
    const errEl = document.getElementById('save-current-err');
    errEl.textContent = ''; errEl.style.display = 'none';
    showConfirm('save-current-row');
  }

  async function doSaveAndContinue() {
    const name = document.getElementById('save-current-name').value.trim();
    const errEl = document.getElementById('save-current-err');
    if (!name) { errEl.textContent = 'Name cannot be empty.'; errEl.style.display = 'block'; return; }
    const createRes = await fetch('/api/projects/create', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ name, preserve_assets: true, style: _currentStyle }),
    });
    if (!createRes.ok) {
      const d = await safeJson(createRes);
      errEl.textContent = d.detail || 'Error creating project.';
      errEl.style.display = 'block';
      return;
    }
    _currentProject = name;
    await _autoSaveProject();
    await loadProjectList();
    document.getElementById('project-select').value = name;
    document.getElementById('project-label').textContent = name;
    hideConfirm('save-current-row');

    const pending = _pendingProject;
    _pendingProject = '';
    if (pending === '@@crear@@') {
      _showCreateProjectRow();
    } else if (pending) {
      await doLoadProject(pending);
    } else {
      setStatus(`✅ Saved as "${name}".`);
    }
  }

  // ── Style switch warning callbacks ────────────────────────────────────────────
  async function doConfirmStyleSwitch() {
    hideConfirm('style-switch-warning-row');
    const style = _pendingStyle;
    _pendingStyle = '';
    if (style) await switchStyle(style);
  }
  function doCancelStyleSwitch() {
    hideConfirm('style-switch-warning-row');
    _pendingStyle = '';
  }

  function showConfirm(id) {
    // Hide all project-flow rows before showing new one
    ['create-project-row','unsaved-warning-row','save-current-row','delete-confirm-row',
     'style-switch-warning-row','confirm-audio','confirm-update','confirm-video'].forEach(rid => {
      if (rid !== id) { const el = document.getElementById(rid); if (el) el.style.display = 'none'; }
    });
    const el = document.getElementById(id);
    if (el) el.style.display = el.style.display === 'none' ? 'flex' : 'none';
  }
  function hideConfirm(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  }

  async function doContinueWithoutProject() {
    if (IS_DEMO) { showDemoModal(); return; }
    // Save current project first if any
    if (_currentProject) await _autoSaveProject();
    _currentProject = '';
    document.getElementById('project-select').value = '';
    document.getElementById('project-label').textContent = 'Untitled';
    _clearAllContent();
    setStatus('Started without a project. Nothing will be saved automatically.');
  }

  async function doSaveProject() {
    if (IS_DEMO) { showDemoModal(); return; }
    const name = _currentProject || document.getElementById('project-select').value;
    if (!name) {
      document.getElementById('save-as-name').value = '';
      document.getElementById('save-as-err').style.display = 'none';
      showConfirm('save-as-row');
      setTimeout(() => document.getElementById('save-as-name').focus(), 50);
      return;
    }
    setStatus('Saving project…');
    const res = await fetch(`/api/projects/${encodeURIComponent(name)}/save`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        script: document.getElementById('script-input').value,
        settings: getSettings(),
      }),
    });
    if (res.ok) {
      setStatus(`✅ Project "${name}" saved.`);
    } else {
      const d = await safeJson(res);
      setStatus('Save error: ' + (d.detail || 'unknown'));
    }
  }

  async function doSaveAsConfirm() {
    const name = document.getElementById('save-as-name').value.trim();
    const errEl = document.getElementById('save-as-err');
    if (!name) { errEl.textContent = 'Enter a project name.'; errEl.style.display = 'block'; return; }
    const createRes = await fetch('/api/projects/create', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ name, preserve_assets: true, style: _currentStyle }),
    });
    if (!createRes.ok) {
      const d = await safeJson(createRes);
      errEl.textContent = d.detail || 'Could not create project.';
      errEl.style.display = 'block';
      return;
    }
    hideConfirm('save-as-row');
    _currentProject = name;
    await loadProjectList();
    document.getElementById('project-select').value = name;
    document.getElementById('project-label').textContent = name;
    setStatus('Saving project…');
    const res = await fetch(`/api/projects/${encodeURIComponent(name)}/save`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        script: document.getElementById('script-input').value,
        settings: getSettings(),
      }),
    });
    if (res.ok) {
      setStatus(`✅ Project "${name}" saved.`);
    } else {
      const d = await safeJson(res);
      setStatus('Save error: ' + (d.detail || 'unknown'));
    }
  }

  function _showLoadingOverlay(title, sub) {
    const ov = document.getElementById('loading-overlay');
    document.getElementById('loading-title').textContent = title;
    document.getElementById('loading-sub').textContent = sub;
    document.getElementById('loading-bar').style.width = '0%';
    ov.style.display = 'flex';
    // Animate bar to 80% while waiting for server
    let pct = 0;
    ov._barInterval = setInterval(() => {
      pct = Math.min(80, pct + (80 - pct) * 0.06 + 0.3);
      document.getElementById('loading-bar').style.width = pct + '%';
    }, 120);
  }
  function _hideLoadingOverlay() {
    const ov = document.getElementById('loading-overlay');
    clearInterval(ov._barInterval);
    document.getElementById('loading-bar').style.width = '100%';
    setTimeout(() => { ov.style.display = 'none'; }, 300);
  }

  async function doLoadProject(name) {
    setStatus(`Loading project "${name}"…`);
    _showLoadingOverlay('Loading project…', 'Reading audio clips from disk');
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(name)}/load`);
      const d = await safeJson(res);
      if (!res.ok) { _hideLoadingOverlay(); setStatus('Load error: ' + (d.detail || 'unknown')); return; }

      _currentProject = name;
      document.getElementById('project-label').textContent = name;
      document.getElementById('project-select').value = name;

      // Restore script
      const scriptEl = document.getElementById('script-input');
      if (scriptEl) { scriptEl.value = d.script || ''; }

      // Restore settings
      if (d.settings) applySettings(d.settings);

      // Clear stale caches before loading
      _contactPhotoCache.clear();
      _scriptImageCache.clear();

      // Restore audio clips UI
      const clipCount = d.clip_metadata?.length || 0;
      let audioReady = Promise.resolve();
      if (d.clip_metadata && d.clip_metadata.length > 0) {
        _audioClips = d.clip_metadata.map((c, i) => ({
          index: i, duration_ms: c.duration_ms, text: c.text, voice: c.voice, side: c.side,
        }));
        totalClips = _audioClips.length;
        currentClip = 0;
        const _ppL = document.getElementById('preview-player');
        document.getElementById('loading-sub').textContent = 'Loading audio preview…';
        audioReady = new Promise(resolve => {
          const onDuration = () => {
            if (isFinite(_ppL.duration) && _ppL.duration > 0) {
              _ppL.removeEventListener('durationchange', onDuration);
              resolve();
            }
          };
          _ppL.addEventListener('durationchange', onDuration);
          _ppL.addEventListener('error', resolve, { once: true });
          // Safety timeout: never block more than 25s
          setTimeout(resolve, 25000);
          _ppL.src = '/api/audio_full'; _ppL.load();
        });
        loadClip(0, { autoPlay: false });
      } else {
        _audioClips = []; totalClips = 0; currentClip = 0;
        document.getElementById('clip-label').textContent = '— / —';
        document.getElementById('clip-text').value = 'Generate audio first to review clips here.';
      }

      // Restore contact photo cache
      (d.contact_photo_names || []).forEach(n => _contactPhotoCache.set(n, Date.now()));

      // Restore script image cache
      (d.image_names || []).forEach(n => _scriptImageCache.set(n, Date.now()));

      updatePreview();
      saveSettings();
      await audioReady;
      document.getElementById('loading-sub').textContent = `${clipCount} clip${clipCount !== 1 ? 's' : ''} loaded`;
      _hideLoadingOverlay();
      setStatus(`✅ Project "${name}" loaded — ${clipCount} clips`);
    } catch(e) {
      _hideLoadingOverlay();
      _currentProject = '';
      document.getElementById('project-select').value = '';
      document.getElementById('project-label').textContent = 'Untitled';
      setStatus('Load error: ' + e.message);
    }
  }

  // ── Delete project — inline confirm ────────────────────────────────────────────
  async function doDeleteProject() {
    const name = _currentProject || document.getElementById('project-select').value;
    if (!name) { setStatus('No project selected.'); return; }
    document.getElementById('delete-confirm-label').textContent = `Delete project "${name}"?`;
    showConfirm('delete-confirm-row');
  }

  async function doDeleteProjectConfirm() {
    const name = _currentProject || document.getElementById('project-select').value;
    hideConfirm('delete-confirm-row');
    await fetch(`/api/projects/${encodeURIComponent(name)}`, { method: 'DELETE' });
    _currentProject = '';
    document.getElementById('project-label').textContent = 'Untitled';
    document.getElementById('project-select').value = '';
    _clearAllContent();
    await loadProjectList();
    setStatus(`Project "${name}" deleted.`);
  }

  // ── Init ───────────────────────────────────────────────────────────────────────
  if (IS_DEMO) {
    document.getElementById('demo-banner').style.display = 'flex';
    document.getElementById('header-user-section').style.display = 'none';
    document.getElementById('header-demo-section').style.display = 'flex';
    // Hide ElevenLabs card entirely in demo
    const elCard = document.querySelector('#el-content')?.closest('.app-card');
    if (elCard) elCard.style.display = 'none';
    // Lock script textarea
    const scriptEl = document.getElementById('script-input');
    if (scriptEl) {
      scriptEl.readOnly = true;
      scriptEl.style.opacity = '0.6';
      scriptEl.style.cursor = 'default';
      scriptEl.style.userSelect = 'none';
    }
    // Pre-fill demo script
    if (scriptEl && !scriptEl.value.trim()) {
      scriptEl.value = `sarah\u{1F495}
1: natasha> i can't believe mason asked jessica to prom
2: alex> sarah i'm so sorry..
1: natasha> i've been dropping hints for weeks luke
2: alex> his loss honestly
1: natasha> now i have no date\u0020
1: natasha> and prom is in 3 days!
rizz
alex
2: alex> You could always go with me you know?
1: natasha> luke you're gay remember?
2: alex> so?
2: alex> we'd have the most fun together
1: natasha> that's actually perfect
1: natasha> my gay bestie as my prom date!`;
    }
  }

  loadSettings();
  if (IS_DEMO) {
    // Force dark mode
    if (!isAppDark) toggleDarkMode();
    // Force badge number to 67
    const badgeEl = document.getElementById('unread-badge');
    if (badgeEl) { badgeEl.value = 67; badgeEl.dispatchEvent(new Event('input')); }
    // Open gameplay toggle by default
    const gpSwitch = document.getElementById('switch-gameplay');
    if (gpSwitch && !gpSwitch.classList.contains('on')) {
      gpSwitch.classList.add('on');
      toggleGameplay();
    }
  }
  loadMe();
  loadContactPhotoCache().then(() => updatePreview());
  if (!IS_DEMO) {
    loadElevenProfiles();
    loadMusicList();
    loadGameplayList();
    loadProjectList();
  }
