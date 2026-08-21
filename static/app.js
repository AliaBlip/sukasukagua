/* DFTIKTOK — frontend logic */

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const form = $("#form");
const urlInput = $("#url");
const goBtn = $("#go");
const statusEl = $("#status");
const resultEl = $("#result");
const toastEl = $("#toast");

let _results = [];  // parsed results for share / export

/* ---------------- i18n ---------------- */
let LANG = "id";
const I18N = {
  id: {
    eyebrow: "100% tanpa watermark · langsung dari server sendiri",
    hero: 'Unduh video <span class="u">TikTok</span><br>tanpa watermark.',
    sub: "Video HD · Musik MP3 · Carousel foto — cepat, bersih, tanpa aplikasi.",
    placeholder: "Tempel link TikTok di sini…",
    go: "Ambil",
    paste: "Tempel",
    hint: "bisa lebih dari satu — pisahkan dengan baris baru · tekan <kbd>/</kbd> untuk fokus",
    history_h2: "Riwayat",
    history_clear: "bersihkan riwayat",
    how_h2: "Untuk developer",
    how_sub: 'Ambil hasil lewat REST API — dokumentasi interaktif di <a href="/docs" target="_blank">/docs</a>.',
    footer: 'DFTIKTOK · api di <code>/docs</code> &amp; <code>/redoc</code>',
    dl_label: "Mengunduh…",
    download: "Unduh",
    zip: "Unduh semua foto (.zip)",
    photo: "Foto ",
    video_nowm: "Video (no watermark)",
    video_wm: "Versi watermark",
    cover: "Unduh cover",
    mp3: "Unduh MP3",
    share: "Bagikan",
    export: "Export JSON",
    open_tt: "Buka di TikTok",
    copy_caption: "Salin caption",
    read_more: "Baca selengkapnya",
    read_less: "Sembunyikan",
    no_desc: "(tanpa deskripsi)",
    q_default: "Default (no watermark)",
    err_empty: "masukkan link TikTok dulu.",
    err_no_url: "link TikTok tidak ditemukan di teks.",
    err_parse: "gagal memproses link.",
    err_net: "jaringan tidak tersedia",
    copied_caption: "caption tersalin ✓",
    copy_fail: "tidak dapat menyalin",
    downloaded: "terunduh ✓",
    dl_fail: "unduhan gagal — coba link langsung",
    clipboard_block: "clipboard diblokir browser — tempel manual (Ctrl+V).",
    install: "Pasang",
    copy_page_link: "Salin link halaman",
    dl_all_hd: "Unduh semua HD",
    dl_all_results: "Unduh semua hasil",
    grid: "Grid",
    single: "Tunggal",
    settings: "Pengaturan",
    default_quality: "Kualitas default",
    q_best: "Tertinggi (HD)",
    queue_done: "antrean unduhan selesai ✓",
    link_copied: "link tersalin ✓",
    explore_h2: "Jelajahi",
    explore_sub: "Cari video TikTok berdasarkan kata kunci atau hashtag.",
    search_ph: "Cari video, hashtag…",
    search_btn: "Cari",
    search_not_configured: "Scraper pencarian belum siap. Jalankan `playwright install chromium` di server, lalu coba lagi.",
    search_empty: "Tidak ada hasil.",
    search_err: "Gagal memuat hasil pencarian.",
  },
  en: {
    eyebrow: "100% no watermark · served from your own server",
    hero: 'Download <span class="u">TikTok</span><br>videos without watermark.',
    sub: "HD video · MP3 music · Photo carousel — fast, clean, no app needed.",
    placeholder: "Paste a TikTok link here…",
    go: "Fetch",
    paste: "Paste",
    hint: "multiple supported — separate with new lines · press <kbd>/</kbd> to focus",
    history_h2: "History",
    history_clear: "clear history",
    how_h2: "For developers",
    how_sub: 'Fetch results via the REST API — interactive docs at <a href="/docs" target="_blank">/docs</a>.',
    footer: 'DFTIKTOK · api at <code>/docs</code> &amp; <code>/redoc</code>',
    dl_label: "Downloading…",
    download: "Download",
    zip: "Download all photos (.zip)",
    photo: "Photo ",
    video_nowm: "Video (no watermark)",
    video_wm: "Watermarked version",
    cover: "Download cover",
    mp3: "Download MP3",
    share: "Share",
    export: "Export JSON",
    open_tt: "Open on TikTok",
    copy_caption: "Copy caption",
    read_more: "Read more",
    read_less: "Hide",
    no_desc: "(no description)",
    q_default: "Default (no watermark)",
    err_empty: "paste a TikTok link first.",
    err_no_url: "no TikTok link found in the text.",
    err_parse: "failed to process link.",
    err_net: "network unavailable",
    copied_caption: "caption copied ✓",
    copy_fail: "could not copy",
    downloaded: "downloaded ✓",
    dl_fail: "download failed — try the direct link",
    clipboard_block: "clipboard blocked by browser — paste manually (Ctrl+V).",
    install: "Install",
    copy_page_link: "Copy page link",
    dl_all_hd: "Download all HD",
    dl_all_results: "Download all results",
    grid: "Grid",
    single: "Single",
    settings: "Settings",
    default_quality: "Default quality",
    q_best: "Highest (HD)",
    queue_done: "download queue done ✓",
    link_copied: "link copied ✓",
    explore_h2: "Explore",
    explore_sub: "Search TikTok videos by keyword or hashtag.",
    search_ph: "Search videos, hashtags…",
    search_btn: "Search",
    search_not_configured: "Search scraper isn't ready. Run `playwright install chromium` on the server, then try again.",
    search_empty: "No results.",
    search_err: "Failed to load search results.",
  },
};

function t(key) {
  return (I18N[LANG] && I18N[LANG][key]) || I18N.id[key] || key;
}

function applyI18n() {
  const el = (s) => document.querySelector(s);
  const setText = (sel, key) => { const n = el(sel); if (n) n.textContent = t(key); };
  const setHtml = (sel, key) => { const n = el(sel); if (n) n.innerHTML = t(key); };
  setText(".eyebrow", "eyebrow");
  setHtml(".hero h1", "hero");
  setText(".hero .sub", "sub");
  const u = el("#url"); if (u) u.placeholder = t("placeholder");
  setText("#paste", "paste");
  setHtml(".hint", "hint");
  setText(".history h2", "history_h2");
  setText("#history-clear", "history_clear");
  setText(".how h2", "how_h2");
  setHtml(".how-sub", "how_sub");
  setHtml("footer > span", "footer");
  setText("#dl-label", "dl_label");
  setText("#install-btn", "install");
  setText(".explore h2", "explore_h2");
  setText("#explore-sub", "explore_sub");
  const si = el("#search-input"); if (si) si.placeholder = t("search_ph");
  setText("#search-btn", "search_btn");
  const g = el("#go .btn-label"); if (g && !goBtn.disabled) g.textContent = t("go");
}

function setLang(lang) {
  LANG = lang;
  try { localStorage.setItem("dftiktok_lang", lang); } catch {}
  const btn = $("#lang-toggle");
  if (btn) btn.textContent = lang === "id" ? "EN" : "ID";
  document.documentElement.setAttribute("lang", lang);
  applyI18n();
  buildSettingsPanel();
}

function initLang() {
  let saved = null;
  try { saved = localStorage.getItem("dftiktok_lang"); } catch {}
  if (saved === "id" || saved === "en") { setLang(saved); return; }
  const browser = (navigator.language || "id").toLowerCase();
  setLang(browser.startsWith("en") ? "en" : "id");
}

const ICONS = {
  dl: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12m0 0l-5-5m5 5l5-5M4 21h16"/></svg>',
  zip: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 3v5h5M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-5z"/><path d="M10 12h.01M12 12v4M10 16h4"/></svg>',
  music: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
  img: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>',
  play: '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>',
  copy: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  eye: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
  heart: '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 21s-7.5-4.6-10-9.2C.4 8.5 2.4 5 6 5c2.2 0 3.6 1.2 6 3.6C14.4 6.2 15.8 5 18 5c3.6 0 5.6 3.5 4 6.8C19.5 16.4 12 21 12 21z"/></svg>',
  comment: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
  share: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/></svg>',
  ext: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3"/></svg>',
  json: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 1-2 2 2 2 0 0 1 2 2v5a2 2 0 0 0 2 2h1M16 3h1a2 2 0 0 1 2 2v5a2 2 0 0 0 2 2 2 2 0 0 0-2 2v5a2 2 0 0 1-2 2h-1"/></svg>',
  cover: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>',
};

function fmt(n) {
  if (n === null || n === undefined) return "0";
  n = Number(n) || 0;
  if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, "") + "B";
  if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + "K";
  return String(n);
}

function fmtBytes(b) {
  if (b === null || b === undefined || !b) return "";
  if (b >= 1024 * 1024 * 1024) return (b / 1024 / 1024 / 1024).toFixed(1) + " GB";
  if (b >= 1024 * 1024) return (b / 1024 / 1024).toFixed(1) + " MB";
  if (b >= 1024) return Math.round(b / 1024) + " KB";
  return b + " B";
}

function toast(msg) {
  toastEl.textContent = msg;
  toastEl.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (toastEl.hidden = true), 2200);
}

function buzz(ms) {
  try { if (navigator.vibrate) navigator.vibrate(ms || 40); } catch {}
}

function showStatus(msg, type) {
  statusEl.hidden = false;
  statusEl.className = "status " + (type || "info");
  statusEl.textContent = msg;
}
function hideStatus() { statusEl.hidden = true; }

function setLoading(on) {
  goBtn.disabled = on;
  goBtn.querySelector(".btn-label").textContent = on ? "…" : t("go");
}

/* ---------------- card builders ---------------- */

function buildMedia(d) {
  const wrap = document.createElement("div");
  if (d.type === "image" && d.images && d.images.length) {
    const stage = document.createElement("div");
    stage.className = "img-stage";
    const img = document.createElement("img");
    let cur = 0, dots = null;
    const updateDots = () => {
      if (dots) dots.querySelectorAll("span").forEach((s, i) => s.classList.toggle("active", i === cur));
    };
    const set = () => { img.src = d.images[cur].stream; updateDots(); };
    img.alt = d.desc || "photo";
    stage.appendChild(img);
    if (d.images.length > 1) {
      const prev = document.createElement("button");
      prev.className = "nav-arrow prev"; prev.type = "button"; prev.innerHTML = "‹";
      prev.onclick = () => { cur = (cur - 1 + d.images.length) % d.images.length; set(); };
      const next = document.createElement("button");
      next.className = "nav-arrow next"; next.type = "button"; next.innerHTML = "›";
      next.onclick = () => { cur = (cur + 1) % d.images.length; set(); };
      stage.appendChild(prev); stage.appendChild(next);
      dots = document.createElement("div");
      dots.className = "dots";
      d.images.forEach((_, i) => {
        const sp = document.createElement("span");
        sp.onclick = () => { cur = i; set(); };
        dots.appendChild(sp);
      });
      stage.appendChild(dots);

      // touch swipe (mobile)
      let touchX = null;
      stage.addEventListener("touchstart", (e) => {
        touchX = e.touches[0].clientX;
      }, { passive: true });
      stage.addEventListener("touchend", (e) => {
        if (touchX === null) return;
        const dx = e.changedTouches[0].clientX - touchX;
        if (Math.abs(dx) > 40) {
          cur = dx < 0
            ? (cur + 1) % d.images.length
            : (cur - 1 + d.images.length) % d.images.length;
          set();
        }
        touchX = null;
      }, { passive: true });
    }
    wrap.appendChild(stage);
    set();

    // grid / single view toggle
    if (d.images.length > 1) {
      const viewToggle = document.createElement("button");
      viewToggle.type = "button";
      viewToggle.className = "view-toggle";
      viewToggle.textContent = t("grid");
      let grid = null;
      viewToggle.onclick = () => {
        if (grid) {
          grid.remove();
          grid = null;
          stage.hidden = false;
          wrap.style.width = "";
          viewToggle.textContent = t("grid");
        } else {
          grid = document.createElement("div");
          grid.className = "grid-gallery";
          d.images.forEach((im, i) => {
            const cell = document.createElement("div");
            cell.className = "grid-cell";
            const imgs = document.createElement("img");
            imgs.src = im.stream;
            imgs.alt = t("photo") + (i + 1);
            imgs.loading = "lazy";
            const dlBtn = document.createElement("button");
            dlBtn.type = "button";
            dlBtn.className = "grid-dl";
            dlBtn.innerHTML = ICONS.dl;
            dlBtn.title = t("download") + " " + (i + 1);
            dlBtn.onclick = (e) => {
              e.stopPropagation();
              const u = im.download || im.stream;
              const p = startDownload(u);
              if (p === null) window.location = u;
            };
            cell.appendChild(imgs);
            cell.appendChild(dlBtn);
            grid.appendChild(cell);
          });
          wrap.appendChild(grid);
          stage.hidden = true;
          wrap.style.width = "100%";
          viewToggle.textContent = t("single");
        }
      };
      wrap.appendChild(viewToggle);
    }
  } else if (d.video && d.video.no_watermark_stream) {
    const v = document.createElement("video");
    v.controls = true;
    v.playsInline = true;
    v.preload = "metadata";
    v.controlsList = "nodownload"; // hide native "download" option
    v.disablePictureInPicture = true;
    v.poster = d.cover || "";
    v.src = d.video.no_watermark_stream;
    wrap.appendChild(v);

    // live quality switcher (no reload)
    const fmts = (d.video.formats || []).filter((f) => f.stream);
    if (fmts.length) {
      const opts = [{ label: t("q_default"), url: d.video.no_watermark_stream }]
        .concat(fmts.map((f) => ({ label: f.label, url: f.stream })));
      const qbar = document.createElement("div");
      qbar.className = "qbar";
      const sel = document.createElement("select");
      opts.forEach((o, i) => {
        const opt = document.createElement("option");
        opt.value = String(i);
        opt.textContent = o.label;
        sel.appendChild(opt);
      });
      // preselect saved default quality (player switcher index = format index + 1)
      const pi = pickQualityIndex(fmts, getQualityPref());
      if (pi >= 0 && opts[pi + 1]) {
        sel.value = String(pi + 1);
        if (opts[pi + 1].url) v.src = opts[pi + 1].url;
      }
      sel.onchange = () => {
        const o = opts[Number(sel.value)];
        const pos = v.currentTime;
        const wasPlaying = !v.paused && !v.ended;
        v.src = o.url;
        v.load();
        v.addEventListener("loadedmetadata", () => {
          try { v.currentTime = pos; } catch (e) {}
          if (wasPlaying) v.play().catch(() => {});
        }, { once: true });
      };
      qbar.appendChild(sel);
      wrap.appendChild(qbar);
    }
  } else {
    const box = document.createElement("div");
    box.className = "audio-box";
    box.innerHTML = '<div class="disc">' + ICONS.music + "</div>";
    if (d.music && d.music.stream) {
      const viz = document.createElement("canvas");
      viz.className = "viz";
      viz.width = 280;
      viz.height = 44;
      box.appendChild(viz);
      const a = document.createElement("audio");
      a.controls = true;
      a.preload = "none";
      a.src = d.music.stream;
      setupVisualizer(a, viz);
      box.appendChild(a);
    }
    wrap.appendChild(box);
  }
  return wrap;
}

function buildInfo(d) {
  const info = document.createElement("div");
  info.className = "info";
  const a = d.author || {};

  // author row
  const ar = document.createElement("div");
  ar.className = "author-row";
  const av = document.createElement("img");
  av.className = "avatar";
  av.alt = "";
  av.src = a.avatar || "";
  av.onerror = () => (av.style.visibility = "hidden");
  const am = document.createElement("div");
  am.className = "author-meta";
  const nick = document.createElement("div");
  nick.className = "nick";
  nick.textContent = a.nickname || "Unknown";
  const handle = document.createElement("div");
  handle.className = "handle";
  handle.textContent = a.unique_id ? "@" + a.unique_id : "";
  am.appendChild(nick); am.appendChild(handle);
  ar.appendChild(av); ar.appendChild(am);
  if (a.verified) {
    const vf = document.createElement("span");
    vf.className = "verified";
    vf.textContent = "✓";
    vf.title = "Verified";
    ar.appendChild(vf);
  }
  info.appendChild(ar);

  // desc (collapsible when long)
  const desc = document.createElement("p");
  desc.className = "desc";
  const fullDesc = d.desc || t("no_desc");
  const MAX = 160;
  if (fullDesc.length > MAX) {
    desc.textContent = fullDesc.slice(0, MAX) + "…";
    info.appendChild(desc);
    const more = document.createElement("button");
    more.type = "button";
    more.className = "desc-more";
    more.textContent = t("read_more");
    let open = false;
    more.onclick = () => {
      open = !open;
      desc.textContent = open ? fullDesc : fullDesc.slice(0, MAX) + "…";
      more.textContent = open ? t("read_less") : t("read_more");
    };
    info.appendChild(more);
  } else {
    desc.textContent = fullDesc;
    info.appendChild(desc);
  }

  // stats
  const s = d.stats || {};
  const stats = document.createElement("div");
  stats.className = "stats";
  [
    ["heart", fmt(s.digg)],
    ["comment", fmt(s.comment)],
    ["share", fmt(s.share)],
    ["eye", fmt(s.play)],
  ].forEach(([ic, val]) => {
    const sp = document.createElement("span");
    sp.className = "stat";
    sp.innerHTML = ICONS[ic] + val;
    stats.appendChild(sp);
  });
  info.appendChild(stats);

  info.appendChild(document.createElement("hr"));

  // actions
  info.appendChild(buildActions(d));

  // meta line
  const ml = document.createElement("div");
  ml.className = "meta-line";
  const badge = document.createElement("span");
  badge.className = "type-badge";
  badge.textContent = d.type === "image" ? "Carousel" : "Video";
  const mt = document.createElement("span");
  mt.className = "meta-text";
  mt.textContent = "id " + (d.id || "—") + (d.duration ? " · " + d.duration + "s" : "");
  ml.appendChild(badge); ml.appendChild(mt);

  // salin caption (full text, even when collapsed)
  if (fullDesc && fullDesc !== t("no_desc")) {
    const capBtn = document.createElement("button");
    capBtn.type = "button";
    capBtn.className = "copy-caption";
    capBtn.innerHTML = ICONS.copy + t("copy_caption");
    capBtn.onclick = () => {
      copyText(fullDesc).then(
        () => toast(t("copied_caption")),
        () => toast(t("copy_fail"))
      );
    };
    ml.appendChild(capBtn);
  }
  info.appendChild(ml);

  return info;
}

/* Robust clipboard copy with legacy fallback (works without secure context /
   clipboard permission, e.g. inside sandboxed iframes). */
function copyText(text) {
  return new Promise((resolve, reject) => {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(resolve, () =>
        legacyCopy(text, resolve, reject)
      );
    } else {
      legacyCopy(text, resolve, reject);
    }
  });
}

function legacyCopy(text, resolve, reject) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  ta.style.top = "0";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  ta.setSelectionRange(0, text.length);
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch (e) {
    ok = false;
  }
  document.body.removeChild(ta);
  if (ok) resolve();
  else reject(new Error("copy gagal"));
}

/* ---------------- download with progress ---------------- */

function startDownload(url) {
  const prog = $("#dl-progress");
  const bar = $("#dl-bar");
  const txt = $("#dl-text");
  if (!prog || !bar || !txt) return null; // no overlay → caller falls back to direct link

  prog.hidden = false;
  bar.style.width = "0%";
  txt.textContent = "0%";

  return fetch(url)
    .then((res) => {
      if (!res.ok) throw new Error("HTTP " + res.status);
      const total = Number(res.headers.get("content-length")) || 0;
      const cd = res.headers.get("content-disposition") || "";
      const m = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd);
      const fname = m ? decodeURIComponent(m[1]) : "dftiktok_" + Date.now();
      const reader = res.body.getReader();
      const chunks = [];
      let received = 0;
      return new Promise((resolve, reject) => {
        const pump = () => {
          reader.read().then(({ done, value }) => {
            if (done) { resolve({ blob: new Blob(chunks), fname }); return; }
            chunks.push(value);
            received += value.length;
            const pct = total ? Math.round((received / total) * 100) : 0;
            bar.style.width = (total ? pct : 100) + "%";
            txt.textContent = (total ? pct + "%" : fmtBytes(received));
            pump();
          }).catch(reject);
        };
        pump();
      });
    })
    .then(({ blob, fname }) => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = fname;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(a.href), 5000);
      buzz(60);
      toast(t("downloaded"));
      return true;
    })
    .catch(() => { toast(t("dl_fail")); return false; })
    .finally(() => setTimeout(() => { prog.hidden = true; }, 700));
}

function dlAnchor(url, html, className) {
  const a = document.createElement("a");
  a.className = className || "btn";
  a.href = url;
  a.innerHTML = html;
  a.addEventListener("click", (e) => {
    e.preventDefault();
    const p = startDownload(url);
    if (p === null) window.location = url;
  });
  return a;
}

/* ---------------- download queue + quality preference ---------------- */

async function queueDownloads(urls) {
  urls = (urls || []).filter(Boolean);
  if (!urls.length) return;
  for (let i = 0; i < urls.length; i++) {
    const p = startDownload(urls[i]);
    if (p === null) {
      window.open(urls[i], "_blank");
      await new Promise((r) => setTimeout(r, 700));
    } else {
      await p;
    }
  }
  toast(t("queue_done"));
}

function getQualityPref() {
  try { return localStorage.getItem("dftiktok_quality") || "default"; } catch { return "default"; }
}

// formats are sorted best-first. Returns index into formats, or -1 for "default".
function pickQualityIndex(formats, pref) {
  if (!formats || !formats.length) return -1;
  if (pref === "best") return 0;
  const h = parseInt(pref, 10);
  if (!h) return -1; // default / no-watermark
  for (let i = 0; i < formats.length; i++) {
    if ((formats[i].height || 0) >= h) return i;
  }
  return formats.length - 1; // fall back to lowest available
}

/* ---------------- real audio visualizer (Web Audio API) ---------------- */

function setupVisualizer(audioEl, canvas) {
  let ctx = null, analyser = null, raf = null, data = null;

  function ensure() {
    if (ctx) return !!analyser;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return false;
    try {
      ctx = new AC();
      const src = ctx.createMediaElementSource(audioEl);
      analyser = ctx.createAnalyser();
      analyser.fftSize = 128;
      analyser.smoothingTimeConstant = 0.8;
      src.connect(analyser);
      analyser.connect(ctx.destination);
      data = new Uint8Array(analyser.frequencyBinCount);
      return true;
    } catch (e) {
      return false;
    }
  }

  function stop() {
    if (raf) { cancelAnimationFrame(raf); raf = null; }
  }

  function draw() {
    if (!analyser || !canvas) return;
    analyser.getByteFrequencyData(data);
    const g = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    g.clearRect(0, 0, W, H);
    const bars = 36;
    const bw = W / bars;
    const usable = Math.floor(data.length * 0.7); // ignore the very top frequencies
    let color = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
    if (!color) color = "#0d9e6d";
    g.fillStyle = color;
    for (let i = 0; i < bars; i++) {
      const idx = Math.floor((i / bars) * usable);
      const v = data[idx] / 255;
      const bh = Math.max(2, v * H);
      const x = i * bw + bw * 0.22;
      g.fillRect(x, H - bh, bw * 0.56, bh);
    }
    raf = requestAnimationFrame(draw);
  }

  // our media is same-origin (proxied through /api/stream), so this works;
  // crossOrigin is set defensively in case an absolute URL is ever used.
  audioEl.crossOrigin = "anonymous";
  audioEl.addEventListener("play", () => {
    if (!ensure()) { if (canvas) canvas.hidden = true; return; }
    if (ctx.state === "suspended") ctx.resume();
    if (canvas) canvas.hidden = false;
    if (!raf) draw();
  });
  audioEl.addEventListener("pause", stop);
  audioEl.addEventListener("ended", stop);
}

function buildActions(d) {
  const box = document.createElement("div");
  box.className = "actions";
  const h = document.createElement("h4");
  h.textContent = t("download");
  box.appendChild(h);

  if (d.type === "image") {
    if (d.zip_download) {
      box.appendChild(dlAnchor(d.zip_download, ICONS.zip + " " + t("zip"), "btn accent"));
    }
    const cnt = document.createElement("span");
    cnt.className = "stat";
    cnt.style.justifyContent = "center";
    cnt.textContent = d.images.length + " foto";
    box.appendChild(cnt);
    d.images.forEach((im, i) => {
      box.appendChild(dlAnchor(im.download || im.stream, ICONS.img + " " + t("photo") + (i + 1)));
    });
  } else {
    const v = d.video || {};
    if (v.no_watermark_download) {
      box.appendChild(dlAnchor(v.no_watermark_download, ICONS.dl + " " + t("video_nowm"), "btn primary"));
    }
    if (v.formats && v.formats.length) {
      const qrow = document.createElement("div");
      qrow.className = "quality-row";
      const sel = document.createElement("select");
      v.formats.forEach((f, i) => {
        const o = document.createElement("option");
        o.value = i;
        const sz = fmtBytes(f.size_estimate);
        o.textContent = "HD " + f.label + (sz ? " · ~" + sz : "");
        sel.appendChild(o);
      });
      qrow.appendChild(sel);
      const dl = dlAnchor(v.formats[0].download, t("download"), "btn");
      dl.style.width = "auto";
      sel.onchange = () => { dl.href = v.formats[sel.value].download; };
      // preselect saved default quality
      const pi = pickQualityIndex(v.formats, getQualityPref());
      if (pi >= 0) { sel.value = String(pi); dl.href = v.formats[pi].download; }
      qrow.appendChild(dl);
      box.appendChild(qrow);
    }
    if (v.watermark_stream) {
      box.appendChild(dlAnchor(v.watermark_stream + "&download=1", ICONS.dl + " " + t("video_wm")));
    }
    if (d.cover_download) {
      box.appendChild(dlAnchor(d.cover_download, ICONS.cover + " " + t("cover")));
    }
    // download all HD variants at once
    const hdAllUrls = [v.no_watermark_download]
      .concat((v.formats || []).map((f) => f.download))
      .filter(Boolean);
    if (hdAllUrls.length > 1) {
      const hdAll = document.createElement("button");
      hdAll.type = "button";
      hdAll.className = "btn";
      hdAll.innerHTML = ICONS.dl + " " + t("dl_all_hd");
      hdAll.onclick = () => queueDownloads(hdAllUrls);
      box.appendChild(hdAll);
    }
  }

  if (d.music && d.music.stream) {
    // inline player (more reliable than a new tab)
    const ap = document.createElement("div");
    ap.className = "audio-inline";
    const head = document.createElement("div");
    head.className = "audio-head";
    const at = document.createElement("div");
    at.className = "audio-title";
    at.textContent = (d.music.title || "Audio") + (d.music.author ? " · " + d.music.author : "");
    const viz = document.createElement("canvas");
    viz.className = "viz";
    viz.width = 280;
    viz.height = 40;
    head.appendChild(at);
    head.appendChild(viz);
    ap.appendChild(head);
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "none";
    audio.src = d.music.stream;
    setupVisualizer(audio, viz);
    ap.appendChild(audio);
    box.appendChild(ap);

    if (d.music.download) {
      box.appendChild(dlAnchor(d.music.download, ICONS.dl + " " + t("mp3")));
    }
  }

  // secondary actions: share / export / open
  const row2 = document.createElement("div");
  row2.className = "share-row";
  const shareBtn = document.createElement("button");
  shareBtn.type = "button";
  shareBtn.className = "btn mini";
  shareBtn.innerHTML = ICONS.share + " " + t("share");
  shareBtn.onclick = () => shareData(d);
  row2.appendChild(shareBtn);
  const exportBtn = document.createElement("button");
  exportBtn.type = "button";
  exportBtn.className = "btn mini";
  exportBtn.innerHTML = ICONS.json + " " + t("export");
  exportBtn.onclick = () => exportJson(d);
  row2.appendChild(exportBtn);
  box.appendChild(row2);

  const row3 = document.createElement("div");
  row3.className = "share-row";
  const copyLink = document.createElement("button");
  copyLink.type = "button";
  copyLink.className = "btn mini";
  copyLink.innerHTML = ICONS.copy + " " + t("copy_page_link");
  copyLink.onclick = () => {
    const deep = location.origin + "/?url=" + encodeURIComponent(d.url);
    copyText(deep).then(
      () => toast(t("link_copied")),
      () => toast(t("copy_fail"))
    );
  };
  row3.appendChild(copyLink);
  const openBtn = document.createElement("a");
  openBtn.className = "btn mini";
  openBtn.href = d.url;
  openBtn.target = "_blank";
  openBtn.rel = "noopener";
  openBtn.innerHTML = ICONS.ext + " " + t("open_tt");
  row3.appendChild(openBtn);
  box.appendChild(row3);

  if (d.author && d.author.unique_id) {
    const lm = document.createElement("div");
    lm.className = "link-mini";
    const p = document.createElement("a");
    p.href = "https://www.tiktok.com/@" + d.author.unique_id;
    p.target = "_blank";
    p.rel = "noopener";
    p.textContent = "@" + d.author.unique_id + " → profil";
    lm.appendChild(p);
    box.appendChild(lm);
  }

  return box;
}

function shareData(d) {
  const text = (d.desc || "DFTIKTOK") + " — " + d.url;
  if (navigator.share) {
    navigator.share({ title: "DFTIKTOK", text: text, url: d.url }).catch(() => {});
  } else {
    copyText(d.url).then(
      () => toast("link tersalin ✓"),
      () => toast(t("copy_fail"))
    );
  }
}

function exportJson(d) {
  const data = JSON.stringify(d, null, 2);
  const blob = new Blob([data], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "dftiktok_" + (d.id || "result") + ".json";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
  toast("JSON ✓");
}

function buildCard(d) {
  const card = document.createElement("div");
  card.className = "card";
  const preview = document.createElement("div");
  preview.className = "preview";
  preview.appendChild(buildMedia(d));
  card.appendChild(preview);
  card.appendChild(buildInfo(d));
  return card;
}

/* ---------------- history ---------------- */

const HIST_KEY = "dftiktok_history";

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HIST_KEY)) || []; } catch { return []; }
}
function saveHistory(list) {
  try { localStorage.setItem(HIST_KEY, JSON.stringify(list.slice(0, 24))); } catch {}
}

function pushHistory(d) {
  const list = loadHistory().filter((x) => x.url !== d.url);
  list.unshift({
    url: d.url,
    title: d.desc || ((d.author || {}).nickname || ""),
    author: (d.author || {}).unique_id || "",
    thumb: d.cover || (d.images && d.images[0] && d.images[0].url) || "",
    type: d.type,
    ts: Date.now(),
  });
  saveHistory(list);
  renderHistory();
}

function renderHistory() {
  const wrap = $("#history");
  const holder = $("#history-list");
  if (!wrap || !holder) return;
  const list = loadHistory();
  if (!list.length) { wrap.hidden = true; return; }
  wrap.hidden = false;
  holder.innerHTML = "";
  list.forEach((it) => {
    const el = document.createElement("div");
    el.className = "hist-item";
    const th = document.createElement("img");
    th.className = "hist-thumb";
    th.alt = "";
    th.src = it.thumb || "";
    th.onerror = () => { th.style.visibility = "hidden"; };
    const meta = document.createElement("div");
    meta.className = "hist-meta";
    const t = document.createElement("div");
    t.className = "hist-title";
    t.textContent = it.title || it.url;
    const s = document.createElement("div");
    s.className = "hist-sub";
    s.textContent = "@" + it.author;
    meta.appendChild(t); meta.appendChild(s);
    const ty = document.createElement("span");
    ty.className = "hist-type";
    ty.textContent = it.type;
    el.appendChild(th); el.appendChild(meta); el.appendChild(ty);
    el.onclick = () => {
      urlInput.value = it.url;
      urlInput.scrollIntoView({ behavior: "smooth" });
      handleSubmit(new Event("submit"));
    };
    holder.appendChild(el);
  });
}

$("#history-clear").addEventListener("click", () => {
  localStorage.removeItem(HIST_KEY);
  renderHistory();
});

/* ---------------- stats ---------------- */

async function loadStats() {
  try {
    const r = await fetch("/api/stats");
    if (!r.ok) return;
    const s = await r.json();
    const strip = $("#stats-strip");
    if (!strip) return;
    strip.hidden = false;
    const mins = Math.floor(s.uptime_seconds / 60);
    const uptime = mins >= 60 ? Math.floor(mins / 60) + "j" : mins + "m";
    strip.innerHTML =
      `<span class="pill"><span class="live"></span> online ${uptime}</span>` +
      `<span class="pill"><b>${s.parses}</b> parse</span>` +
      `<span class="pill"><b>${s.downloads}</b> unduhan</span>` +
      `<span class="pill"><b>${s.streams}</b> stream</span>`;
  } catch {}
}

/* ---------------- flow ---------------- */

let _busy = false;

// Extract TikTok URLs from pasted text — accepts full share messages like
// "Check out this video: https://vt.tiktok.com/xxx #fyp" and grabs the link.
function extractUrls(raw) {
  const found = [];
  const re = /https?:\/\/[^\s"'<>]+/g;
  let m;
  while ((m = re.exec(raw)) !== null) {
    found.push(m[0].replace(/[.,;:'")\]}>]+$/, ""));
  }
  if (found.length) return [...new Set(found)];
  // no URL detected — fall back to plain line-splitting
  return raw.split(/\n+/).map((u) => u.trim()).filter(Boolean);
}

async function processUrls(urls) {
  hideStatus();
  resultEl.hidden = true;
  resultEl.innerHTML = "";
  _results = [];
  setLoading(true);
  _busy = true;

  let okCount = 0;
  let failCount = 0;
  for (let i = 0; i < urls.length; i++) {
    const url = urls[i];
    if (urls.length > 1) {
      setLoading(true);
      goBtn.querySelector(".btn-label").textContent = (i + 1) + "/" + urls.length;
    }
    try {
      const res = await fetch("/api/parse?url=" + encodeURIComponent(url));
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.detail || t("err_parse"));
      resultEl.appendChild(buildCard(data));
      pushHistory(data);
      _results.push(data);
      okCount++;
    } catch (err) {
      const card = document.createElement("div");
      card.className = "status err";
      card.textContent = "✖ " + url.slice(0, 60) + " — " + (err.message || t("err_net"));
      resultEl.appendChild(card);
      failCount++;
    }
  }

  // summary line for multi-link / failures
  if (urls.length > 1 || failCount) {
    const sum = document.createElement("div");
    sum.className = "summary";
    const bits = [];
    if (okCount) bits.push("✓ " + okCount + " berhasil");
    if (failCount) bits.push("✗ " + failCount + " gagal");
    sum.textContent = bits.join("  ·  ");
    resultEl.insertBefore(sum, resultEl.firstChild);
  }

  // batch download bar (when more than one result succeeded)
  if (okCount > 1) {
    const bar = document.createElement("div");
    bar.className = "batch-bar";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn primary";
    btn.innerHTML = ICONS.dl + " " + t("dl_all_results") + " (" + okCount + ")";
    btn.onclick = () => {
      const dlUrls = [];
      _results.forEach((r) => {
        const v = r.video || {};
        if (v.no_watermark_download) dlUrls.push(v.no_watermark_download);
        else if (r.music && r.music.download) dlUrls.push(r.music.download);
        else if (r.images && r.images.length) dlUrls.push(r.images[0].download || r.images[0].stream);
      });
      queueDownloads(dlUrls);
    };
    bar.appendChild(btn);
    resultEl.insertBefore(bar, resultEl.firstChild);
  }

  resultEl.hidden = false;
  if (okCount || failCount) {
    resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  setLoading(false);
  goBtn.querySelector(".btn-label").textContent = t("go");
  _busy = false;
}

async function handleSubmit(e) {
  if (e && e.preventDefault) e.preventDefault();
  if (_busy) return;
  const raw = urlInput.value.trim();
  if (!raw) { showStatus(t("err_empty"), "err"); return; }

  const urls = extractUrls(raw);
  if (!urls.length) { showStatus(t("err_no_url"), "err"); return; }
  await processUrls(urls);
}

/* ---------------- search / feed (optional provider) ---------------- */

async function runSearch(q) {
  q = (q || "").trim();
  if (!q) return;
  const statusEl = $("#search-status");
  const btn = $("#search-btn");
  if (!btn) return;
  btn.disabled = true;
  if (statusEl) statusEl.hidden = true;
  try {
    const res = await fetch("/api/feed?q=" + encodeURIComponent(q));
    const data = await res.json();
    if (!data.configured) {
      statusEl.hidden = false;
      statusEl.className = "status info";
      statusEl.textContent = t("search_not_configured");
      return;
    }
    if (!data.ok) {
      statusEl.hidden = false;
      statusEl.className = "status err";
      statusEl.textContent = data.detail || t("search_err");
      return;
    }
    if (!data.items || !data.items.length) {
      statusEl.hidden = false;
      statusEl.className = "status info";
      statusEl.textContent = t("search_empty");
      return;
    }
    await processUrls(data.items);
  } catch (e) {
    statusEl.hidden = false;
    statusEl.className = "status err";
    statusEl.textContent = t("search_err");
  } finally {
    btn.disabled = false;
  }
}

$("#paste").addEventListener("click", async () => {
  try {
    urlInput.value = (await navigator.clipboard.readText()).trim();
    urlInput.focus();
  } catch {
    showStatus(t("clipboard_block"), "err");
  }
});

// generic "copy" buttons (code blocks)
$$(".copy").forEach((b) => {
  b.addEventListener("click", () => {
    copyText(b.getAttribute("data-copy")).then(
      () => toast("tersalin ✓"),
      () => toast(t("copy_fail"))
    );
  });
});

/* ---------------- user info (ip / region / battery) ---------------- */

async function loadBattery() {
  try {
    if (navigator.getBattery) {
      const b = await navigator.getBattery();
      const pct = Math.round(b.level * 100) + "%";
      if (b.charging) return pct + " · isi daya";
      return pct;
    }
  } catch {}
  return null;
}

async function loadUserInfo() {
  const el = $("#userinfo");
  if (!el) return;
  const parts = [];
  try {
    const r = await fetch("/api/whoami");
    if (r.ok) {
      const d = await r.json();
      if (d.ip) parts.push("ip " + d.ip);
      if (d.country) {
        const loc = [d.city, d.region, d.country].filter(Boolean).join(", ");
        if (loc) parts.push((d.flag ? d.flag + " " : "") + loc);
      }
      if (d.isp) parts.push(d.isp);
    }
  } catch {}
  const bat = await loadBattery();
  if (bat) parts.push("🔋 " + bat);
  if (parts.length) el.textContent = parts.join("  ·  ");
}

const q = new URLSearchParams(location.search).get("url");
if (q && urlInput) urlInput.value = q;

/* ---------------- theme (3-mode: light / dark / auto) ---------------- */

let THEME_MODE = "auto";
const mqDark = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

function resolveTheme(mode) {
  if (mode === "auto") return (mqDark && mqDark.matches) ? "dark" : "light";
  return mode;
}

function applyTheme(mode) {
  THEME_MODE = mode;
  document.documentElement.setAttribute("data-theme", resolveTheme(mode));
  document.documentElement.setAttribute("data-theme-mode", mode);
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", resolveTheme(mode) === "dark" ? "#0e1013" : "#ffffff");
  try { localStorage.setItem("dftiktok_theme", mode); } catch {}
}

function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem("dftiktok_theme"); } catch {}
  applyTheme(saved === "light" || saved === "dark" || saved === "auto" ? saved : "auto");
  if (mqDark && mqDark.addEventListener) {
    mqDark.addEventListener("change", () => {
      if (THEME_MODE === "auto") applyTheme("auto");
    });
  }
}

/* ---------------- keyboard shortcuts ---------------- */

function setupKeyboard() {
  document.addEventListener("keydown", (e) => {
    const tag = (e.target && e.target.tagName ? e.target.tagName : "").toLowerCase();
    const typing = tag === "input" || tag === "textarea";
    if (e.key === "/" && !typing) {
      e.preventDefault();
      urlInput.focus();
    } else if (e.key === "Escape" && typing && e.target === urlInput) {
      urlInput.value = "";
      urlInput.blur();
    }
  });
}

function setupBackTop() {
  const btn = $("#backtop");
  if (!btn) return;
  const onScroll = () => {
    btn.classList.toggle("show", window.scrollY > 500);
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  btn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

function setupClearBtn() {
  const clearBtn = $("#clear");
  if (!clearBtn) return;
  const sync = () => { clearBtn.hidden = !urlInput.value; };
  urlInput.addEventListener("input", sync);
  clearBtn.addEventListener("click", () => {
    urlInput.value = "";
    sync();
    urlInput.focus();
    buzz(30);
  });
  sync();
}

/* ---------------- settings panel (default quality) ---------------- */

function buildSettingsPanel() {
  const panel = $("#settings-panel");
  if (!panel) return;
  panel.innerHTML = "";
  const item = document.createElement("div");
  item.className = "settings-item";
  const lbl = document.createElement("span");
  lbl.className = "settings-label";
  lbl.textContent = t("default_quality");
  const sel = document.createElement("select");
  const opts = [
    ["default", t("q_default")],
    ["best", t("q_best")],
    ["1080", "1080p"],
    ["720", "720p"],
    ["540", "540p"],
  ];
  opts.forEach(([v, l]) => {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = l;
    sel.appendChild(o);
  });
  sel.value = getQualityPref();
  sel.onchange = () => {
    try { localStorage.setItem("dftiktok_quality", sel.value); } catch {}
    toast("✓");
  };
  item.appendChild(lbl);
  item.appendChild(sel);
  panel.appendChild(item);
}

function setupSettings() {
  const toggle = $("#settings-toggle");
  const panel = $("#settings-panel");
  if (!toggle || !panel) return;
  buildSettingsPanel();
  toggle.addEventListener("click", () => {
    panel.hidden = !panel.hidden;
  });
  document.addEventListener("click", (e) => {
    if (panel.hidden) return;
    if (!panel.contains(e.target) && !toggle.contains(e.target)) panel.hidden = true;
  });
}

/* ---------------- install prompt (PWA) ---------------- */

function setupSearch() {
  const sform = $("#search-form");
  if (!sform) return;
  sform.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = $("#search-input").value;
    runSearch(q);
  });
}

function setupInstall() {
  let deferredPrompt = null;
  const btn = $("#install-btn");
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    if (btn) btn.hidden = false;
  });
  window.addEventListener("appinstalled", () => {
    if (btn) btn.hidden = true;
  });
  if (btn) {
    btn.addEventListener("click", async () => {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      await deferredPrompt.userChoice;
      deferredPrompt = null;
      btn.hidden = true;
    });
  }
}

function init() {
  if (!form || !urlInput || !goBtn) return;
  initLang();
  initTheme();
  setupKeyboard();
  setupBackTop();
  setupClearBtn();
  setupSettings();
  setupInstall();
  setupSearch();
  loadStats();
  renderHistory();
  loadUserInfo();
  const themeBtn = $("#theme-toggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const order = ["light", "dark", "auto"];
      const cur = document.documentElement.getAttribute("data-theme-mode") || "auto";
      applyTheme(order[(order.indexOf(cur) + 1) % order.length]);
    });
  }
  const langBtn = $("#lang-toggle");
  if (langBtn) {
    langBtn.addEventListener("click", () => {
      setLang(LANG === "id" ? "en" : "id");
    });
  }
  // auto-parse when a ?url= deep-link is present
  if (urlInput.value.trim()) {
    setTimeout(() => handleSubmit(new Event("submit")), 300);
  }
  // auto-focus input on desktop only (avoids popping keyboard on mobile)
  if (window.innerWidth > 720 && !urlInput.value) urlInput.focus();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
