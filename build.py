#!/usr/bin/env python3
"""Build static/index.html as a single self-contained file.

Inlines style.css and app.js into the HTML template. Uses plain
str.replace (NOT re.sub) so backslash escapes in the JS/CSS are preserved.
Run:  python3 build.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

TEMPLATE = """<!DOCTYPE html>
<html lang="id" data-theme="light">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>DFTIKTOK — TikTok Downloader</title>
<meta name="description" content="DFTIKTOK — download video TikTok HD tanpa watermark, musik MP3 & carousel foto." />
<meta name="theme-color" content="#ffffff" />
<meta name="color-scheme" content="light dark" />
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
<link rel="manifest" href="/manifest.json" />
<style>
@@CSS@@
</style>
</head>
<body>

<header class="topbar">
  <div class="brand">
    <span class="brand-mark"></span>
    <span class="brand-name">DFTIKTOK</span>
    <span class="brand-sub">downloader</span>
  </div>
  <nav class="nav">
    <button type="button" id="install-btn" class="nav-btn install-btn" hidden>Pasang</button>
    <button type="button" id="lang-toggle" class="nav-btn lang-btn" title="Bahasa / Language">EN</button>
    <button type="button" id="settings-toggle" class="nav-btn" title="Pengaturan" aria-label="Pengaturan">
      <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
    </button>
    <button type="button" id="theme-toggle" class="nav-btn" title="Ganti tema">
      <svg class="ic-moon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
      <svg class="ic-sun" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
      <span class="ic-auto">A</span>
    </button>
    <a href="/docs" target="_blank">API Docs</a>
    <a href="/redoc" target="_blank">Redoc</a>
    <a href="https://github.com" target="_blank" class="nav-git" aria-label="GitHub">
      <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor"><path d="M12 .5C5.7.5.5 5.7.5 12c0 5.1 3.3 9.4 7.9 10.9.6.1.8-.2.8-.5v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.7 1.3 3.4 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.4-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.2 1.2a11 11 0 0 1 5.8 0C17.3 4.9 18.3 5.2 18.3 5.2c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.6.8.5 4.6-1.5 7.9-5.8 7.9-10.9C23.5 5.7 18.3.5 12 .5z"/></svg>
    </a>
  </nav>
</header>

<div id="settings-panel" class="settings-panel" hidden></div>

<main>
  <section class="hero">
    <span class="eyebrow">100% tanpa watermark · langsung dari server sendiri</span>
    <h1>Unduh video <span class="u">TikTok</span><br />tanpa watermark.</h1>
    <p class="sub">Video HD &middot; Musik MP3 &middot; Carousel foto &mdash; cepat, bersih, tanpa aplikasi.</p>

    <form id="form" class="input-wrap" autocomplete="off" onsubmit="event.preventDefault(); if (typeof handleSubmit === 'function') handleSubmit(event); return false;">
      <div class="input-box">
        <input id="url" type="text" placeholder="Tempel link TikTok di sini…" spellcheck="false" />
        <button type="button" id="clear" class="btn-clear" hidden aria-label="Bersihkan">×</button>
        <button type="submit" id="go" class="btn-go">
          <span class="btn-label">Ambil</span>
        </button>
      </div>
      <button type="button" id="paste" class="btn-paste">Tempel</button>
    </form>
    <p class="hint">bisa lebih dari satu — pisahkan dengan baris baru · tekan <kbd>/</kbd> untuk fokus</p>

    <div class="stats-strip" id="stats-strip" hidden></div>
  </section>

  <section id="status" class="status" hidden></section>

  <section id="result" class="result" hidden></section>

  <section id="history" class="history" hidden>
    <h2>Riwayat</h2>
    <div class="history-list" id="history-list"></div>
    <button type="button" id="history-clear" class="btn-ghost">bersihkan riwayat</button>
  </section>

  <section class="explore" id="explore">
    <h2>Jelajahi</h2>
    <p class="how-sub" id="explore-sub">Cari video TikTok berdasarkan kata kunci atau hashtag.</p>
    <form id="search-form" class="search-wrap" autocomplete="off">
      <input id="search-input" type="text" placeholder="Cari video, hashtag…" spellcheck="false" />
      <button type="submit" id="search-btn" class="btn-go">Cari</button>
    </form>
    <div id="search-status" class="status" hidden></div>
  </section>

  <section class="how">
    <h2>Untuk developer</h2>
    <p class="how-sub">Ambil hasil lewat REST API — dokumentasi interaktif di <a href="/docs" target="_blank">/docs</a>.</p>
    <div class="code-block">
      <div class="code-head"><span>bash</span><button type="button" class="copy" data-copy="curl &quot;https://dftiktok.example.com/api/parse?url=&lt;tiktok_url&gt;&quot;">copy</button></div>
      <pre><code>curl "https://dftiktok.example.com/api/parse?url=&lt;tiktok_url&gt;"</code></pre>
    </div>
  </section>
</main>

<footer>
  <span>DFTIKTOK &middot; api di <code>/docs</code> &amp; <code>/redoc</code></span>
  <div id="userinfo" class="userinfo"></div>
</footer>

<div id="toast" class="toast" hidden></div>
<div id="dl-progress" class="dl-progress" hidden>
  <div class="dl-box">
    <div class="dl-label"><span id="dl-label">Mengunduh…</span> <span id="dl-text">0%</span></div>
    <div class="dl-track"><div id="dl-bar" class="dl-fill"></div></div>
  </div>
</div>
<button id="backtop" class="backtop" title="Ke atas" aria-label="Ke atas">↑</button>

<script>
@@JS@@
</script>
</body>
</html>
"""


def main():
    css = open(os.path.join(HERE, "static", "style.css"), encoding="utf-8").read()
    js = open(os.path.join(HERE, "static", "app.js"), encoding="utf-8").read()

    # Safety: neither should contain a tag that would terminate inlining.
    assert "</style>" not in css.lower(), "style.css contains </style>"
    assert "</script>" not in js.lower(), "app.js contains </script>"

    html = TEMPLATE.replace("@@CSS@@", css).replace("@@JS@@", js)

    out = os.path.join(HERE, "static", "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    # Verify the JS regex survives intact (regression check for the re.sub bug).
    assert "split(/\\n+/)" in html, "JS newline regex was corrupted!"
    print("built", out, "->", len(html), "bytes")


if __name__ == "__main__":
    main()
