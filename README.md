# DFTIKTOK — TikTok Downloader (self-hosted)

Unduh **video TikTok tanpa watermark (HD)**, **musik (MP3)**, dan **carousel foto** — plus **stream** langsung. Tanpa aplikasi, tanpa pihak ketiga (tidak pakai tikwm/snaptik/dll).

## Fitur
- 🎬 Video — tanpa watermark + multi-kualitas HD (1080p/720p/540p, H.264/H.265)
- 🎵 Musik / original sound — MP3
- 🖼️ Carousel / slideshow foto — unduh per foto **atau semua sekaligus (.zip)**
- 📺 Stream langsung di browser (anti-CORS, anti-hotlink, dukung HTTP Range/seek)
- 📁 Nama file otomatis bermakna (judul lagu, kualitas HD) + bisa di-override (`filename=...`)
- 🔍 **Jelajahi** — cari video/hashtag via scraper headless (Playwright + Chromium)
- 🌗 Tema terang/gelap/auto · 🌐 Bahasa ID/EN · 📲 PWA (install)
- 🧩 REST API lengkap + dokumentasi interaktif di **`/docs`** (Swagger) & **`/redoc`**
- 📊 Statistik runtime (`/api/stats`) + riwayat unduhan (localStorage)

## Cara pakai (lokal)
```bash
pip install -r requirements.txt
playwright install chromium     # untuk fitur Jelajahi
uvicorn main:app --host 0.0.0.0 --port 8000
# buka http://localhost:8000
```

## Deploy ke cloud

### Railway (paling gampang)
1. Push repo ini ke GitHub.
2. Di [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo** → pilih repo.
3. Railway otomatis mendeteksi `railway.json` → build pakai `Dockerfile`.
4. Selesai — buka URL yang diberikan. `Dockerfile` sudah include Chromium (untuk Jelajahi).

### Render
1. Push ke GitHub → [render.com](https://render.com) → **New → Web Service** → pilih repo.
2. Render membaca `render.yaml` otomatis (atau pilih "Docker" + `./Dockerfile`).
3. Deploy.

### Fly.io
```bash
flyctl launch   # baca fly.toml
flyctl deploy
```

### VPS / Docker manual
```bash
docker build -t dftiktok .
docker run -p 8000:8000 dftiktok
```

## Environment variables (opsional)
Lihat `.env.example` — `DFTIKTOK_API_KEY`, `DFTIKTOK_RATE_LIMIT`, `DFTIKTOK_FEED_ENDPOINT`.

## REST API

| Method | Endpoint | Keterangan |
|--------|----------|------------|
| GET | `/api/parse?url=<tiktok_url>` | Resolve link → metadata + stream/download URL |
| GET | `/api/info/{video_id}` | Parse dari ID video saja |
| GET | `/api/stream?token=&kind=&idx=&download=&filename=` | Stream / download media |
| GET | `/api/download?url=&kind=&idx=&filename=` | One-shot parse + download |
| GET | `/api/stats` | Statistik runtime (parse/unduhan/stream/uptime) |
| GET | `/health` | Health check |

`kind` untuk `/api/stream` & `/api/download`:
- `video` + `idx=-1` → no-watermark (default)
- `video` + `idx=0..n` → HD qualities (`formats[]`)
- `video` + `idx=-2` → versi ber-watermark resmi
- `music` → MP3
- `image` + `idx=n` → foto ke-n
- `zip` → semua foto carousel dalam satu `.zip`
- (khusus `/api/download`) `hd` → otomatis pilih resolusi tertinggi

`filename` (opsional) di semua endpoint unduhan → override nama file.

### Contoh
```bash
# parse
curl "http://localhost:8000/api/parse?url=https://www.tiktok.com/@user/video/1234567890123456789"

# download no-watermark sekali jalan
curl -L -o video.mp4 \
  "http://localhost:8000/api/download?url=<tiktok_url>&kind=video"

# download MP3
curl -L -o audio.mp3 \
  "http://localhost:8000/api/download?url=<tiktok_url>&kind=music"
```

## Format URL yang didukung
`tiktok.com/@user/video/ID`, `.../photo/ID`, `vt.tiktok.com/xxx`, `vm.tiktok.com/xxx`,
`m.tiktok.com/...`, `www.tiktok.com/t/xxx`, dan ID angka langsung.

## Catatan
- Link media TikTok **ditandatangani & kedaluwarsa (~1 jam)**. Aplikasi menyimpan sesi di memori (~45 menit), meng-*proxy* media dengan cookie + Referer yang benar, dan **auto-refresh** link yang kedaluwarsa.
- **Fitur Jelajahi** memakai scraper headless. TikTok mendeteksi **IP datacenter** (termasuk Railway/Render/VPS) dan bisa menampilkan CAPTCHA — maka fitur Jelajahi paling stabil bila di-deploy di **IP residensial** (PC/rumah). Downloader/parse/stream **tidak terpengaruh** dan tetap jalan normal.
- Gunakan untuk konten yang memang boleh diunduh / milik Anda sendiri.
