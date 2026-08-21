"""
DFTIKTOK — Self-hosted TikTok Downloader API + Web UI
=====================================================
Download TikTok videos (with/without watermark, HD), music (MP3) and
photo carousels, and stream them directly — no third-party service used.

Everything is parsed from TikTok's own public web pages
(`__UNIVERSAL_DATA_FOR_REHYDRATION__` / `SIGI_STATE`), so the media URLs are
the official signed CDN links.

Features
--------
* Video  -> no-watermark play stream + multiple HD qualities (bitrateInfo)
* Music  -> original sound / song as MP3
* Photo  -> carousel images (one by one or all)
* Stream -> proxied through this server so CORS / hotlink blocks never bite
* REST   -> fully documented, interactive docs at /docs (Swagger) & /redoc
"""

from __future__ import annotations

import html as html_lib
import io
import json
import os
import re
import threading
import time
import unicodedata
import uuid
import zipfile
from typing import Any, Dict, List, Optional
from urllib.parse import quote, unquote, urlparse

import requests
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

# --------------------------------------------------------------------------- #
#  Configuration
# --------------------------------------------------------------------------- #

APP_NAME = "DFTIKTOK"
APP_VERSION = "1.0.0"

# Realistic browser headers — TikTok serves full media data to normal browsers
# and only degrades for clearly-bot requests.
DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": DESKTOP_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "upgrade-insecure-requests": "1",
}
REFERER = "https://www.tiktok.com/"
TIMEOUT = 25
CACHE_TTL = 45 * 60  # signed CDN links expire (~1h); cache shorter than that

# Optional API key — set env DFTIKTOK_API_KEY to require `X-API-Key` header on
# parse/download endpoints. Empty = open access.
API_KEY = os.environ.get("DFTIKTOK_API_KEY", "").strip()

# Optional feed/search provider. Empty = use the BUILT-IN scraper (scraper.py).
# When set, /api/feed proxies queries to this endpoint instead (query appended as ?q=...).
FEED_ENDPOINT = os.environ.get("DFTIKTOK_FEED_ENDPOINT", "").strip()

# In-memory rate limiter (per client IP), configurable via env.
RATE_LIMIT = int(os.environ.get("DFTIKTOK_RATE_LIMIT", "60"))  # requests/window
RATE_WINDOW = 60  # seconds
_RATE: Dict[str, List[float]] = {}
_RATE_LOCK = threading.Lock()

# In-memory store of parsed sessions: token -> {cookies, media, meta, original_url, created}
_SESSIONS: Dict[str, Dict[str, Any]] = {}

# Lightweight runtime counters for the public stats endpoint.
STATS: Dict[str, Any] = {
    "started_at": time.time(),
    "parses": 0,
    "downloads": 0,
    "streams": 0,
}

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "**DFTIKTOK** — self-contained TikTok downloader.\n\n"
        "Paste any TikTok link and get back structured media data "
        "(video, HD qualities, music MP3, photo carousel) plus proxied "
        "**stream** and **download** endpoints.\n\n"
        "### Quick start\n"
        "1. `GET /api/parse?url=<tiktok_url>` to resolve a link.\n"
        "2. Use the returned `stream` URLs to play/download media "
        "(they already handle cookies, Referer and CORS).\n\n"
        "Supported URL shapes: `tiktok.com/@user/video/ID`, "
        "`.../photo/ID`, `vt.tiktok.com/...`, `vm.tiktok.com/...`, "
        "`m.tiktok.com/...`, `www.tiktok.com/t/...` and bare numeric IDs."
    ),
    contact={"name": "DFTIKTOK"},
    license_info={"name": "MIT"},
    docs_url=None,      # custom themed /docs below
    redoc_url=None,     # custom themed /redoc below
    openapi_tags=[
        {"name": "parse", "description": "Resolve a TikTok URL into media data."},
        {"name": "media", "description": "Stream & download the actual media files."},
        {"name": "meta", "description": "Service health & info."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "Content-Range", "Accept-Ranges"],
)


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _cleanup_expired() -> None:
    """Drop sessions older than CACHE_TTL."""
    now = time.time()
    for token in [t for t, s in _SESSIONS.items() if now - s["created"] > CACHE_TTL]:
        _SESSIONS.pop(token, None)


def _normalize_url(url: str) -> str:
    """Turn whatever the user pasted into a canonical tiktok.com URL."""
    url = (url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL kosong. Masukkan link TikTok.")
    if url.isdigit():
        return f"https://www.tiktok.com/@/video/{url}"
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    host = urlparse(url).netloc.lower()
    if "tiktok" not in host:
        raise HTTPException(
            status_code=400,
            detail="Bukan link TikTok yang valid. Contoh: https://www.tiktok.com/@user/video/123456789",
        )
    return url


def _video_id(url: str) -> Optional[str]:
    m = re.search(r"/(?:video|photo|t)/(\d{10,})", url)
    if m:
        return m.group(1)
    m = re.search(r"(\d{15,})", url)
    return m.group(1) if m else None


def _extract_json(html: str) -> Optional[Dict[str, Any]]:
    """Pull the embedded item JSON out of the page.

    TikTok embeds the video data in two possible script tags. We try both.
    """
    for sid in ("__UNIVERSAL_DATA_FOR_REHYDRATION__", "SIGI_STATE"):
        m = re.search(
            rf'<script[^>]*id=["\']?{re.escape(sid)}["\']?[^>]*>(.*?)</script>',
            html,
            re.S,
        )
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
    # Some old pages assign a global var instead of a script tag.
    m = re.search(
        r"__UNIVERSAL_DATA_FOR_REHYDRATION__\s*=\s*(\{.*?\})\s*;?\s*</script>",
        html,
        re.S,
    )
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return None


def _first(items: Optional[List[str]]) -> Optional[str]:
    if items:
        return items[0]
    return None


def _url_list(val: Any) -> Optional[str]:
    """A media URL can be a plain string or {UrlList:[...]} / {urlList:[...]}."""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        for key in ("UrlList", "urlList"):
            if isinstance(val.get(key), list) and val[key]:
                return val[key][0]
        return None
    return None


def _build_item_struct(data: Dict[str, Any], url: str) -> Dict[str, Any]:
    """Locate itemStruct inside the embedded JSON, across schema generations."""
    scope = data.get("__DEFAULT_SCOPE__", data) or {}

    # 1) Current schema: webapp.video-detail.itemInfo.itemStruct
    vd = scope.get("webapp.video-detail") or {}
    item_info = vd.get("itemInfo") or {}
    if isinstance(item_info, dict) and item_info.get("itemStruct"):
        return item_info["itemStruct"]
    if isinstance(vd, dict) and vd.get("itemStruct"):
        return vd["itemStruct"]

    # 2) Older schema: SIGI_STATE.ItemModule.<id>
    item_module = scope.get("ItemModule") or data.get("ItemModule") or {}
    vid = _video_id(url)
    if vid and isinstance(item_module, dict) and item_module.get(vid):
        return item_module[vid]
    if isinstance(item_module, dict) and item_module:
        # only one item -> return it
        vals = [v for v in item_module.values() if isinstance(v, dict) and v.get("id")]
        if len(vals) == 1:
            return vals[0]

    return {}


def _quality_label(w: Optional[int], h: Optional[int], gear: Optional[str]) -> str:
    height = h or 0
    if height >= 2160:
        base = "4K"
    elif height >= 1080:
        base = "1080p"
    elif height >= 720:
        base = "720p"
    elif height >= 540:
        base = "540p"
    elif height >= 360:
        base = "360p"
    else:
        base = gear or "SD"
    dims = f"{w}x{h}" if (w and h) else ""
    return (base + (f" ({dims})" if dims else "")).strip()


# --------------------------------------------------------------------------- #
#  Fetch + parse
# --------------------------------------------------------------------------- #

def fetch_and_parse(url: str) -> Dict[str, Any]:
    """Fetch the TikTok page and extract every media asset.

    Returns a dict suitable for the API response (media URLs + metadata).
    The caller is responsible for stashing `cookies` into the session cache.
    """
    _cleanup_expired()

    url = _normalize_url(url)
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        resp = session.get(url, allow_redirects=True, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Gagal mengakses TikTok: {exc}")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"TikTok mengembalikan status {resp.status_code}.",
        )

    final_url = resp.url
    cookies = session.cookies.get_dict()
    html = resp.text

    data = _extract_json(html)
    if not data:
        raise HTTPException(
            status_code=502,
            detail="Tidak dapat membaca data dari halaman TikTok (mungkin diblokir / captcha). Coba lagi.",
        )

    item = _build_item_struct(data, final_url)
    if not item:
        scope = data.get("__DEFAULT_SCOPE__", data) or {}
        vd = scope.get("webapp.video-detail") or {}
        code = vd.get("statusCode") or vd.get("status_code")
        if code == 10204 or (code and code not in (0, None)):
            raise HTTPException(
                status_code=404,
                detail="Video tidak ditemukan / bersifat privat / telah dihapus.",
            )
        raise HTTPException(
            status_code=404,
            detail="Konten tidak ditemukan atau tidak dapat diakses (mungkin private/dihapus).",
        )

    return _extract_media(item, final_url, cookies)


def _extract_media(item: Dict[str, Any], final_url: str, cookies: Dict[str, str]) -> Dict[str, Any]:
    vid = item.get("id") or _video_id(final_url)
    author = item.get("author") or {}
    music = item.get("music") or {}
    stats = item.get("stats") or {}
    video = item.get("video") or {}
    image_post = item.get("imagePost") or {}

    # --- determine media type -------------------------------------------------
    images: List[Dict[str, Any]] = []
    for img in image_post.get("images") or []:
        u = _url_list((img.get("imageURL") or {}).get("urlList")) or _url_list(
            img.get("imageURL")
        )
        if u:
            images.append(
                {
                    "url": u,
                    "width": img.get("imageWidth"),
                    "height": img.get("imageHeight"),
                }
            )
    media_type = "image" if images else "video"

    # --- video -----------------------------------------------------------------
    nowm_url = _url_list(video.get("playAddr")) or _url_list(
        video.get("PlayAddrStruct")
    )
    watermark_url = _url_list(video.get("downloadAddr"))

    formats: List[Dict[str, Any]] = []
    seen = set()
    for bi in video.get("bitrateInfo") or []:
        pa = bi.get("PlayAddr") if isinstance(bi.get("PlayAddr"), dict) else {}
        u = _url_list(pa) or _url_list(bi.get("playAddr"))
        if not u or u in seen:
            continue
        seen.add(u)
        w = bi.get("Width") or pa.get("Width")
        h = bi.get("Height") or pa.get("Height")
        formats.append(
            {
                "url": u,
                "label": _quality_label(w, h, bi.get("GearName")),
                "width": w,
                "height": h,
                "bitrate": bi.get("Bitrate"),
                "codec": bi.get("CodecType"),
                "fps": bi.get("BitrateFPS"),
            }
        )
    # sort formats best-first (highest resolution/bitrate)
    formats.sort(key=lambda f: (f.get("height") or 0, f.get("bitrate") or 0), reverse=True)

    # rough file-size estimate per format (bitrate × duration)
    dur = video.get("duration") or item.get("duration") or 0
    for f in formats:
        f["size_estimate"] = round((f.get("bitrate") or 0) * dur / 8) if (f.get("bitrate") and dur) else None
    # fallback: if no playAddr but formats exist, treat best format as no-watermark
    if not nowm_url and formats:
        nowm_url = formats[0]["url"]

    # --- music ------------------------------------------------------------------
    music_url = _url_list(music.get("playUrl"))
    # photo posts sometimes stash the audio under music.playUrl too — same field.

    cover = _url_list(video.get("cover")) or _url_list(video.get("originCover"))
    if not cover and image_post:
        cover = _url_list(image_post.get("cover"))
    if not cover and images:
        cover = images[0]["url"]

    def _author_field(key: str) -> Optional[str]:
        val = author.get(key)
        if isinstance(val, list):  # avatar is a urlList
            return _first(val)
        return val

    result: Dict[str, Any] = {
        "ok": True,
        "type": media_type,
        "id": vid,
        "desc": (item.get("desc") or "").strip(),
        "url": final_url,
        "duration": video.get("duration") or item.get("duration"),
        "create_time": item.get("createTime"),
        "cover": cover,
        "author": {
            "id": author.get("id"),
            "unique_id": author.get("uniqueId"),
            "nickname": author.get("nickname"),
            "signature": author.get("signature"),
            "avatar": _author_field("avatarLarger")
            or _author_field("avatarMedium")
            or _author_field("avatarThumb")
            or _author_field("avatar"),
            "verified": author.get("verified"),
        },
        "stats": {
            "digg": stats.get("diggCount"),
            "share": stats.get("shareCount"),
            "comment": stats.get("commentCount"),
            "play": stats.get("playCount"),
            "collect": stats.get("collectCount"),
        },
    }

    if media_type == "image":
        result["images"] = images
        result["music"] = {
            "title": music.get("title"),
            "author": music.get("authorName"),
            "url": music_url,
        } if music_url else None
    else:
        result["video"] = {
            "no_watermark": nowm_url,
            "watermark": watermark_url,
            "formats": formats,
        }
        result["music"] = {
            "title": music.get("title"),
            "author": music.get("authorName"),
            "url": music_url,
            "duration": music.get("duration"),
        } if music_url else None

    result["_cookies"] = cookies
    result["_source_url"] = _normalize_url(final_url)
    return result


# --------------------------------------------------------------------------- #
#  Session cache
# --------------------------------------------------------------------------- #

def _store(parsed: Dict[str, Any]) -> str:
    token = uuid.uuid4().hex
    _SESSIONS[token] = {
        "cookies": parsed.pop("_cookies", {}),
        "source_url": parsed.pop("_source_url", ""),
        "media": parsed,
        "created": time.time(),
    }
    return token


def _get_session(token: str) -> Dict[str, Any]:
    _cleanup_expired()
    entry = _SESSIONS.get(token)
    if not entry:
        raise HTTPException(status_code=410, detail="Sesi kedaluwarsa — parse ulang link.")
    return entry


def _refresh_entry(entry: Dict[str, Any]) -> bool:
    """Re-parse the original URL to renew expired signed CDN links.

    Returns True if the session media was successfully refreshed.
    """
    src = entry.get("source_url")
    if not src:
        return False
    try:
        parsed = fetch_and_parse(src)
    except HTTPException:
        return False
    entry["cookies"] = parsed.pop("_cookies", {})
    entry["source_url"] = parsed.pop("_source_url", src)
    entry["media"] = parsed
    entry["created"] = time.time()
    return True


def _media_url_for(entry: Dict[str, Any], kind: str, idx: int) -> str:
    media = entry["media"]
    if kind == "music":
        url = (media.get("music") or {}).get("url")
        if url:
            return url
    elif kind == "video":
        v = media.get("video") or {}
        if idx == -1:
            url = v.get("no_watermark")
        elif idx == -2:
            url = v.get("watermark")
        elif 0 <= idx < len(v.get("formats", [])):
            url = v["formats"][idx]["url"]
        else:
            url = None
        if url:
            return url
    elif kind == "image":
        imgs = media.get("images") or []
        if 0 <= idx < len(imgs):
            return imgs[idx]["url"]
    elif kind == "cover":
        url = media.get("cover")
        if url:
            return url
    raise HTTPException(status_code=404, detail=f"Media '{kind}' (idx={idx}) tidak tersedia.")


def _slug(text: str, maxlen: int = 60) -> str:
    """Turn arbitrary text (title/desc) into a clean, filename-safe slug.

    Keeps letters/numbers (incl. non-Latin), drops emoji & symbols,
    collapses whitespace to hyphens.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    text = re.sub(r"-+", "-", text)
    return text[:maxlen].rstrip("-").lower()


def _suggested_filename(entry: Dict[str, Any], kind: str, idx: int, override: Optional[str] = None) -> str:
    """Build a meaningful download filename.

    - video no-watermark : dftiktok_{slug}.mp4
    - video HD quality   : dftiktok.hd-{quality}_{slug}.mp4
    - video watermark    : dftiktok.wm_{slug}.mp4
    - music              : {artist} - {title}.mp3   (judul lagu / original sound)
    - image              : dftiktok_{slug}_{n}.jpg

    `override` (the `filename` query param) always wins when provided.
    """
    if override:
        return override
    media = entry["media"]
    author = (media.get("author") or {}).get("unique_id") or "tiktok"
    vid = media.get("id") or "video"
    slug = _slug(media.get("desc")) or f"{author}-{vid}"
    music = media.get("music") or {}

    if kind == "video":
        v = media.get("video") or {}
        if idx == -1:
            return f"dftiktok_{slug}.mp4"
        if idx == -2:
            return f"dftiktok.wm_{slug}.mp4"
        quality = "hd"
        if 0 <= idx < len(v.get("formats", [])):
            label = v["formats"][idx].get("label") or "hd"
            quality = label.split(" ")[0].lower()  # "1080p", "720p", ...
        return f"dftiktok.hd-{quality}_{slug}.mp4"
    if kind == "music":
        title = _slug(music.get("title")) or "audio"
        artist = _slug(music.get("author")) or author
        return f"{artist} - {title}.mp3"
    if kind == "cover":
        return f"dftiktok_cover_{slug}.jpg"
    return f"dftiktok_{slug}_{idx + 1}.jpg"


# --------------------------------------------------------------------------- #
#  Routes — meta
# --------------------------------------------------------------------------- #

@app.get("/", include_in_schema=False)
def index() -> HTMLResponse:
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(
            f.read(),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )


_FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="14" fill="#0e1013"/>'
    '<path d="M40 14c.7 5.2 3.8 8.5 9 9v6c-3.3 0-6.4-1-9-2.8V40c0 8.5-5.9 14.8-14.4 14.8S11.2 48.5 11.2 40s5.9-14.8 14.4-14.8c.7 0 1.6.05 2.4.15v6.4c-.7-.2-1.6-.35-2.4-.35-4.7 0-8.2 3.6-8.2 8.6s3.5 8.6 8.2 8.6 8.2-3.6 8.2-8.6V14h6.2z" fill="#0d9e6d"/>'
    "</svg>"
)


@app.get("/favicon.svg", include_in_schema=False)
def favicon() -> Response:
    return Response(content=_FAVICON_SVG, media_type="image/svg+xml")


# --------------------------------------------------------------------------- #
#  Custom themed /docs (Swagger UI) & /redoc
# --------------------------------------------------------------------------- #

_DOCS_CSS = """
<style>
:root { --accent:#0d9e6d; --ink:#0e1013; --line:#e8eaf0; --soft:#f6f7f9; }
* { box-sizing:border-box; }
body { margin:0; background:#fafbfc; color:#1a1d23; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif; }
a { color:var(--accent); }
/* topbar */
.swagger-ui .topbar { background:#fff; border-bottom:1px solid var(--line); padding:12px 24px; }
.swagger-ui .topbar .wrapper { max-width:1180px; margin:0 auto; }
.swagger-ui .topbar .topbar-wrapper { display:flex; align-items:center; gap:10px; }
.swagger-ui .topbar a { display:flex; align-items:center; gap:9px; text-decoration:none; }
.swagger-ui .topbar .link::before {
  content:""; width:11px; height:11px; border-radius:3px; background:var(--ink);
  box-shadow:inset 4px 4px 0 var(--accent); display:inline-block;
}
.swagger-ui .topbar .link { color:var(--ink); font-weight:800; font-size:16px; letter-spacing:.3px; }
.swagger-ui .topbar .link span:last-child { display:none; } /* hide "swagger" word */
/* info block */
.swagger-ui .info { margin:26px 0 8px; }
.swagger-ui .info .title { color:var(--ink); font-weight:800; font-size:30px; }
.swagger-ui .info .title small { background:var(--accent); color:#fff; border-radius:999px; padding:2px 8px; font-size:11px; vertical-align:middle; }
.swagger-ui .info p, .swagger-ui .info li, .swagger-ui .info a { color:#3a3f48; }
/* scheme container */
.swagger-ui .scheme-container { background:#fff; box-shadow:none; padding:0; margin:0; }
.swagger-ui .schemes-server-container { display:none; }
/* operation blocks */
.swagger-ui .opblock-tag { color:var(--ink); font-weight:700; font-size:16px; border-bottom:1px solid var(--line); }
.swagger-ui .opblock-tag small { color:#868c98; }
.swagger-ui .opblock { border-radius:10px; box-shadow:none; border:1px solid var(--line); margin:0 0 10px; }
.swagger-ui .opblock .opblock-summary { border-color:var(--line); padding:10px 14px; }
.swagger-ui .opblock .opblock-summary-method { border-radius:6px; font-size:12px; }
.swagger-ui .opblock .opblock-summary-path { color:var(--ink); font-weight:600; font-family:ui-monospace,Menlo,Consolas,monospace; }
.swagger-ui .opblock .opblock-summary-description { color:#868c98; }
.swagger-ui .opblock.opblock-get { border-left:3px solid #4f8cff; background:#fff; }
.swagger-ui .opblock.opblock-post { border-left:3px solid #3ecf8e; background:#fff; }
.swagger-ui .opblock.opblock-put { border-left:3px solid #f5a623; background:#fff; }
.swagger-ui .opblock.opblock-delete { border-left:3px solid #ff5c6c; background:#fff; }
.swagger-ui .opblock .opblock-summary-method { background:#fff; color:#1a1d23; border:1px solid var(--line); }
.swagger-ui .opblock.opblock-get .opblock-summary-method { background:#eef4ff; color:#4f8cff; }
.swagger-ui .opblock.opblock-post .opblock-summary-method { background:#e7f6f0; color:#0d9e6d; }
.swagger-ui .opblock.opblock-put .opblock-summary-method { background:#fef6e7; color:#c07d10; }
.swagger-ui .opblock.opblock-delete .opblock-summary-method { background:#fff0f1; color:#c03447; }
/* description text inside ops */
.swagger-ui .opblock-description-wrapper p, .swagger-ui .opblock-external-docs-wrapper p, .swagger-ui .opblock-title_normal p { color:#3a3f48; }
.swagger-ui .markdown code, .swagger-ui .renderedMarkdown code { color:var(--accent); background:var(--soft); }
/* params / models */
.swagger-ui table thead tr td, .swagger-ui table thead tr th { color:#3a3f48; border-bottom:1px solid var(--line); }
.swagger-ui .parameter__name, .swagger-ui .parameter__type { font-family:ui-monospace,Menlo,Consolas,monospace; }
.swagger-ui .model-box { background:#fff; border-radius:10px; }
.swagger-ui .model-title { color:var(--ink); }
/* buttons */
.swagger-ui .btn { border-radius:8px; font-weight:600; }
.swagger-ui .btn.authorize { color:var(--accent); border-color:var(--accent); background:none; }
.swagger-ui .btn.authorize svg { fill:var(--accent); }
.swagger-ui .btn.execute { background:var(--ink); border-color:var(--ink); color:#fff; }
.swagger-ui .btn.execute:hover { background:#1c2026; }
.swagger-ui .btn.cancel { color:#c03447; border-color:#ffd6da; }
.swagger-ui .try-out__btn { color:var(--accent); border-color:var(--accent); }
.swagger-ui .response-col_status { color:var(--ink); }
/* inputs */
.swagger-ui input, .swagger-ui select, .swagger-ui textarea { border-radius:8px; border:1px solid var(--line); color:var(--ink); }
.swagger-ui input:focus, .swagger-ui select:focus, .swagger-ui textarea:focus { border-color:var(--accent); box-shadow:0 0 0 3px rgba(13,158,109,.12); }
/* models section */
.swagger-ui section.models { border:1px solid var(--line); border-radius:12px; }
.swagger-ui section.models h4 { color:var(--ink); }
.swagger-ui .model-toggle::after { background:transparent; }
.swagger-ui .model { color:var(--ink); }
/* footer link back */
.swagger-ui .info .base-url { font-size:13px; }
.swagger-ui .wrapper { padding:0 24px; }
</style>
"""

_DOCS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>DFTIKTOK — API Documentation</title>
<meta name="description" content="DFTIKTOK REST API reference" />
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
{0}
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
<script>
window.addEventListener('load', function () {{
  window.ui = SwaggerUIBundle({{
    url: '/openapi.json',
    dom_id: '#swagger-ui',
    deepLinking: true,
    displayRequestDuration: true,
    defaultModelsExpandDepth: -1,
    docExpansion: 'list',
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
    layout: 'BaseLayout'
  }});
}});
</script>
</body>
</html>
""".format(_DOCS_CSS)


_REDOC_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>DFTIKTOK — API Reference</title>
<meta name="description" content="DFTIKTOK REST API reference (ReDoc)" />
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
<style>
  body { margin: 0; background: #fff; }
  .brand { position: fixed; top: 14px; left: 24px; z-index: 10;
    display: flex; align-items: center; gap: 9px; text-decoration: none;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  .brand .mark { width: 11px; height: 11px; border-radius: 3px; background: #0e1013;
    box-shadow: inset 4px 4px 0 #0d9e6d; }
  .brand .name { color: #0e1013; font-weight: 800; font-size: 16px; letter-spacing: .3px; }
</style>
</head>
<body>
<a class="brand" href="/">
  <span class="mark"></span>
  <span class="name">DFTIKTOK</span>
</a>
<div id="redoc"></div>
<script src="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js"></script>
<script>
Redoc.init('/openapi.json', {{
  scrollYOffset: 60,
  hideDownloadButton: true,
  expandResponses: '200',
  disableSearch: false,
  theme: {{
    colors: {{
      primary: {{ main: '#0d9e6d' }},
      text: {{ primary: '#0e1013', secondary: '#3a3f48' }},
      http: {{ get: '#4f8cff', post: '#0d9e6d', put: '#c07d10', delete: '#c03447' }},
      border: {{ dark: '#e8eaf0', light: '#e8eaf0' }},
    }},
    typography: {{
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      headings: {{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', fontWeight: '700' }},
      code: {{ fontFamily: 'ui-monospace, Menlo, Consolas, monospace', backgroundColor: '#f6f7f9' }},
    }},
    sidebar: {{ backgroundColor: '#fafbfc', textColor: '#3a3f48', activeTextColor: '#0d9e6d' }},
    rightPanel: {{ backgroundColor: '#0e1013', textColor: '#d8dee9' }},
    menu: {{ backgroundColor: '#fafbfc' }},
  }}
}}, document.getElementById('redoc'));
</script>
</body>
</html>
"""


@app.get("/docs", include_in_schema=False)
def docs_page() -> HTMLResponse:
    return HTMLResponse(_DOCS_HTML)


@app.get("/redoc", include_in_schema=False)
def redoc_page() -> HTMLResponse:
    return HTMLResponse(_REDOC_HTML)


@app.get("/manifest.json", include_in_schema=False)
def manifest() -> JSONResponse:
    return JSONResponse(
        {
            "name": "DFTIKTOK — TikTok Downloader",
            "short_name": "DFTIKTOK",
            "description": "Download video TikTok HD tanpa watermark, musik MP3 & carousel foto.",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#0d9e6d",
            "icons": [
                {
                    "src": "/favicon.svg",
                    "sizes": "any",
                    "type": "image/svg+xml",
                    "purpose": "any",
                }
            ],
        }
    )


@app.get("/health", tags=["meta"], summary="Health check")
def health() -> Dict[str, Any]:
    """Liveness probe. Returns service name, version and uptime-ish info."""
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "active_sessions": len(_SESSIONS),
    }


@app.get("/api/stats", tags=["meta"], summary="Runtime usage stats")
def api_stats() -> Dict[str, Any]:
    """Live counters: total parses, downloads, streams and uptime.

    Useful to show a small "usage" strip in a UI or for monitoring.
    """
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "uptime_seconds": int(time.time() - STATS["started_at"]),
        "parses": STATS["parses"],
        "downloads": STATS["downloads"],
        "streams": STATS["streams"],
        "active_sessions": len(_SESSIONS),
    }


def _client_ip(req: Request) -> Optional[str]:
    """Best-effort client IP from proxy headers, falling back to the socket."""
    xff = req.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    real = req.headers.get("x-real-ip")
    if real:
        return real.strip()
    return req.client.host if req.client else None


def _require_api_key(req: Request) -> None:
    """Reject requests missing a valid X-API-Key when DFTIKTOK_API_KEY is set."""
    if not API_KEY:
        return
    provided = req.headers.get("x-api-key", "")
    if provided != API_KEY:
        raise HTTPException(
            status_code=401, detail="API key tidak valid (kirim header X-API-Key)."
        )


def _rate_limit(req: Request) -> None:
    """Simple sliding-window rate limit keyed by client IP."""
    ip = _client_ip(req) or "unknown"
    now = time.time()
    with _RATE_LOCK:
        times = [t for t in _RATE.get(ip, []) if now - t < RATE_WINDOW]
        if len(times) >= RATE_LIMIT:
            raise HTTPException(
                status_code=429, detail="Terlalu banyak permintaan. Coba lagi beberapa saat."
            )
        times.append(now)
        _RATE[ip] = times


@app.get("/api/whoami", tags=["meta"], summary="Client IP & region info")
def api_whoami(req: Request) -> Dict[str, Any]:
    """Return the caller's IP and (best-effort) geo/ISP info.

    Geo lookup uses a free no-key service (`ipwho.is`) with a short timeout;
    if it is unreachable the endpoint still returns the IP alone.
    """
    ip = _client_ip(req)
    out: Dict[str, Any] = {"ip": ip}
    if not ip:
        return out

    # Skip lookups for private / loopback ranges (they will never resolve).
    if ip.startswith(("10.", "192.168.", "127.", "172.16.", "172.17.", "172.18.",
                      "172.19.", "172.2", "172.30.", "172.31.", "0.", "169.254.")):
        out["note"] = "private/loopback — no geo lookup"
        return out

    try:
        r = requests.get(
            f"https://ipwho.is/{ip}",
            headers={"User-Agent": DESKTOP_UA},
            timeout=4,
        )
        if r.status_code == 200:
            d = r.json()
            if d.get("success", True) is not False:
                conn = d.get("connection") or {}
                flag = (d.get("flag") or {}).get("emoji")
                out.update(
                    {
                        "country": d.get("country"),
                        "country_code": d.get("country_code"),
                        "region": d.get("region"),
                        "city": d.get("city"),
                        "postal": d.get("postal"),
                        "flag": flag,
                        "isp": conn.get("isp"),
                        "org": conn.get("org"),
                        "latitude": d.get("latitude"),
                        "longitude": d.get("longitude"),
                        "timezone": (d.get("timezone") or {}).get("id"),
                    }
                )
    except requests.RequestException:
        pass

    return out


@app.get("/api/feed", tags=["meta"], summary="Search TikTok (built-in scraper or external provider)")
def api_feed(
    q: str = Query("", description="Keyword / hashtag to search."),
    req: Request = None,
) -> JSONResponse:
    """Search TikTok videos by keyword or hashtag.

    Two modes:

    - **Built-in scraper** (default): a headless-browser scraper
      (`scraper.py`) that opens TikTok's own search page and extracts the
      rendered video URLs. Requires `playwright` + Chromium to be installed,
      and works reliably from a residential IP (datacenter IPs are usually
      CAPTCHA'd by TikTok).
    - **External provider**: if `DFTIKTOK_FEED_ENDPOINT` is set, queries are
      proxied to that endpoint (which may return a list of URLs, or objects
      with a `url` / `id` field).

    The UI parses each returned URL normally (same as pasting links).
    """
    _rate_limit(req)

    # --- external provider mode -------------------------------------------
    if FEED_ENDPOINT:
        try:
            sep = "&" if "?" in FEED_ENDPOINT else "?"
            r = requests.get(
                f"{FEED_ENDPOINT}{sep}q={quote(q)}",
                headers={"User-Agent": DESKTOP_UA, "Accept": "application/json"},
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            raw = r.json()
        except Exception as exc:
            return JSONResponse({"ok": False, "configured": True, "detail": f"Provider error: {exc}"})

        if isinstance(raw, dict):
            raw = raw.get("items") or raw.get("data") or raw.get("results") or raw.get("videos") or []
        if not isinstance(raw, list):
            return JSONResponse({"ok": False, "configured": True, "detail": "Format provider tidak dikenali."})

        items: List[str] = []
        for it in raw:
            u = None
            if isinstance(it, str):
                u = it
            elif isinstance(it, dict):
                u = it.get("url") or it.get("web_url")
                if not u and it.get("id"):
                    u = f"https://www.tiktok.com/@/video/{it['id']}"
            if u and "tiktok" in u:
                items.append(u)
        return JSONResponse({"ok": True, "configured": True, "count": len(items), "items": items})

    # --- built-in scraper mode --------------------------------------------
    try:
        import scraper as _scraper
    except ImportError:
        return JSONResponse(
            {"ok": False, "configured": True, "detail": "Modul scraper tidak ditemukan."}
        )

    if not _scraper.available():
        return JSONResponse(
            {
                "ok": False,
                "configured": True,
                "detail": (
                    "Scraper belum diinstal. Jalankan: pip install playwright && "
                    "playwright install chromium"
                ),
            }
        )

    try:
        items = _scraper.search_tiktok(q, max_results=12)
    except _scraper.ScraperError as exc:
        return JSONResponse({"ok": False, "configured": True, "detail": str(exc)})

    if not items:
        return JSONResponse(
            {
                "ok": False,
                "configured": True,
                "detail": (
                    "Tidak ada hasil — kemungkinan besar TikTok menampilkan CAPTCHA "
                    "karena IP server (datacenter/headless) terdeteksi. "
                    "Self-host di IP residensial agar pencarian berfungsi."
                ),
            }
        )
    return JSONResponse({"ok": True, "configured": True, "count": len(items), "items": items})


# --------------------------------------------------------------------------- #
#  Routes — parse
# --------------------------------------------------------------------------- #

@app.get("/api/parse", tags=["parse"], summary="Resolve a TikTok URL into media data")
def api_parse(
    url: str = Query(..., description="TikTok URL (video, photo, atau short link)."),
    req: Request = None,
) -> JSONResponse:
    """Parse any TikTok link and return structured, downloadable media.

    Returns metadata plus ready-to-use `stream` URLs for every asset:

    - **video**: `no_watermark` (HD tanpa watermark), `formats[]` (multi-kualitas)
      dan `watermark` (versi ber-watermark resmi).
    - **music**: original sound / lagu sebagai MP3.
    - **images**: daftar foto untuk postingan carousel/slideshow.

    The returned `stream` URLs are proxied through this server, so you can use
    them directly in `<video>`/`<audio>`/`<img>` tags or as download links —
    no CORS or hotlink problems.
    """
    _require_api_key(req)
    _rate_limit(req)
    parsed = fetch_and_parse(url)
    token = _store(parsed)
    STATS["parses"] += 1

    out = dict(parsed)
    out.pop("_cookies", None)
    out.pop("_source_url", None)
    out["token"] = token
    out["expires_in"] = CACHE_TTL

    def stream(kind: str, idx: int = 0) -> str:
        return f"/api/stream?token={token}&kind={kind}&idx={idx}"

    # attach stream endpoints
    if out.get("type") == "image":
        for i, img in enumerate(out.get("images", [])):
            img["stream"] = stream("image", i)
            img["download"] = f"/api/download?url={quote(out['url'])}&kind=image&idx={i}"
        if len(out.get("images", [])) > 1:
            out["zip_download"] = f"/api/download?url={quote(out['url'])}&kind=zip"
        if out.get("music"):
            out["music"]["stream"] = stream("music")
            out["music"]["download"] = stream("music") + "&download=1"
    else:
        v = out.setdefault("video", {})
        if v.get("no_watermark"):
            v["no_watermark_stream"] = stream("video", -1)
            v["no_watermark_download"] = stream("video", -1) + "&download=1"
        if v.get("watermark"):
            v["watermark_stream"] = stream("video", -2)
        for i, f in enumerate(v.get("formats", [])):
            f["stream"] = stream("video", i)
            f["download"] = stream("video", i) + "&download=1"
        if out.get("music"):
            out["music"]["stream"] = stream("music")
            out["music"]["download"] = stream("music") + "&download=1"

    # cover/thumbnail
    if out.get("cover"):
        out["cover_stream"] = stream("cover")
        out["cover_download"] = stream("cover") + "&download=1"

    return JSONResponse(out)


@app.get("/api/info/{video_id}", tags=["parse"], summary="Alias: parse by bare video ID")
def api_info(video_id: str) -> JSONResponse:
    """Same as `/api/parse` but accepts a bare numeric TikTok video ID."""
    return api_parse(url=f"https://www.tiktok.com/@/video/{video_id}")


def _zip_images(entry: Dict[str, Any], filename: Optional[str] = None) -> Response:
    """Download all carousel photos and pack them into an in-memory ZIP."""
    media = entry["media"]
    images = media.get("images") or []
    if not images:
        raise HTTPException(status_code=404, detail="Tidak ada foto untuk di-zip.")

    headers = {"User-Agent": DESKTOP_UA, "Referer": REFERER, "Accept": "*/*"}
    if entry["cookies"]:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in entry["cookies"].items())

    buf = io.BytesIO()
    added = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, img in enumerate(images, 1):
            try:
                r = requests.get(img["url"], headers=headers, timeout=TIMEOUT)
                if r.status_code == 200 and r.content:
                    zf.writestr(f"foto_{i:02d}.jpg", r.content)
                    added += 1
            except requests.RequestException:
                continue
    if added == 0:
        raise HTTPException(status_code=502, detail="Gagal mengunduh foto untuk zip.")

    buf.seek(0)
    data = buf.getvalue()
    fname = filename or f"dftiktok_{media.get('id') or 'carousel'}.zip"
    resp = Response(content=data, media_type="application/zip")
    resp.headers["Content-Disposition"] = f'attachment; filename="{fname}"'
    STATS["downloads"] += 1
    return resp


# --------------------------------------------------------------------------- #
#  Routes — stream / download
# --------------------------------------------------------------------------- #

def _proxy(token: str, kind: str, idx: int, download: bool, req: Request, filename: Optional[str] = None) -> StreamingResponse:
    entry = _get_session(token)
    if download:
        STATS["downloads"] += 1
    else:
        STATS["streams"] += 1

    headers = {
        "User-Agent": DESKTOP_UA,
        "Referer": REFERER,
        "Accept": "*/*",
    }
    if entry["cookies"]:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in entry["cookies"].items())

    # Forward Range so HTML5 <video> seeking works.
    range_header = req.headers.get("range")
    if range_header:
        headers["Range"] = range_header

    # Fetch with one transparent retry: if the signed CDN link has expired
    # (403/404), re-parse the source URL and try again once.
    upstream = None
    for attempt in range(2):
        url = _media_url_for(entry, kind, idx)
        try:
            upstream = requests.get(url, headers=headers, stream=True, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Gagal mengunduh media: {exc}")
        if upstream.status_code not in (403, 404):
            break
        if attempt == 0 and _refresh_entry(entry):
            try:
                upstream.close()
            except Exception:
                pass
            continue
        break

    if upstream.status_code in (403, 404):
        raise HTTPException(
            status_code=upstream.status_code,
            detail="Media sudah kedaluwarsa / tidak dapat diakses. Parse ulang link.",
        )

    def gen():
        try:
            for chunk in upstream.iter_content(chunk_size=1024 * 128):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    resp = StreamingResponse(gen(), status_code=upstream.status_code)
    for k in (
        "Content-Length",
        "Content-Range",
        "Accept-Ranges",
        "ETag",
        "Last-Modified",
        "Cache-Control",
    ):
        if upstream.headers.get(k):
            resp.headers[k] = upstream.headers[k]

    # Force a correct MIME type per media kind (TikTok's CDN sometimes
    # labels audio as video/mp4, which breaks <audio> playback).
    forced_ctype = {
        "music": "audio/mpeg",
        "video": "video/mp4",
        "image": "image/jpeg",
        "cover": "image/jpeg",
    }.get(kind)
    resp.headers["Content-Type"] = forced_ctype or upstream.headers.get(
        "Content-Type", "application/octet-stream"
    )
    resp.headers["Accept-Ranges"] = "bytes"

    if download:
        fname = _suggested_filename(entry, kind, idx, override=filename)
        resp.headers["Content-Disposition"] = f'attachment; filename="{fname}"'

    return resp


@app.get("/api/stream", tags=["media"], summary="Stream or download a media asset")
def api_stream(
    token: str = Query(..., description="Session token from /api/parse."),
    kind: str = Query(
        ...,
        description="Media type: `video` (use idx=-1 no-watermark, idx>=0 HD formats, idx=-2 watermark), `music`, or `image`.",
    ),
    idx: int = Query(0, description="Index for `video` formats or `image` list."),
    download: int = Query(
        0,
        ge=0,
        le=1,
        description="Set `1` to force a file download (Content-Disposition: attachment).",
    ),
    filename: Optional[str] = Query(
        None,
        description="Optional custom filename (overrides the auto-generated name).",
    ),
    req: Request = None,
) -> StreamingResponse:
    """Proxy the requested media through DFTIKTOK.

    Handles **cookies**, **Referer**, **CORS** and **HTTP Range** transparently,
    so the result can be dropped straight into an `<img>`, `<video>` or
    `<audio>` tag, or used as a plain download link.

    `kind` values:
    - `video` + `idx=-1`  → video tanpa watermark (default quality)
    - `video` + `idx=-2`  → video resmi ber-watermark
    - `video` + `idx=0..n`→ HD qualities from `formats[]`
    - `music`             → audio MP3 (original sound / lagu)
    - `image` + `idx=n`   → foto ke-n dari carousel
    """
    return _proxy(token, kind, idx, bool(download), req, filename)


@app.get("/api/download", tags=["media"], summary="One-shot: parse + download")
def api_download(
    url: str = Query(..., description="TikTok URL."),
    kind: str = Query(
        "video",
        description="`video` (no-watermark), `hd` (best HD), `watermark`, `music`, `image`, `cover` (thumbnail), or `zip` (all carousel photos).",
    ),
    idx: int = Query(0, description="Image index when kind=image."),
    filename: Optional[str] = Query(
        None,
        description="Optional custom filename (overrides the auto-generated name).",
    ),
    req: Request = None,
) -> StreamingResponse:
    """Convenience endpoint: parse a URL and immediately download the media.

    Equivalent to calling `/api/parse` then `/api/stream?download=1`.
    """
    _require_api_key(req)
    _rate_limit(req)
    parsed = fetch_and_parse(url)
    token = _store(parsed)
    mapping = {
        "video": ("video", -1),
        "watermark": ("video", -2),
        "music": ("music", 0),
        "image": ("image", idx),
        "cover": ("cover", 0),
    }
    if kind == "hd":
        formats = (parsed.get("video") or {}).get("formats") or []
        if not formats:
            return _proxy(token, "video", -1, True, req, filename)
        # pick highest-resolution format
        best = max(formats, key=lambda f: (f.get("height") or 0, f.get("bitrate") or 0))
        best_idx = formats.index(best)
        return _proxy(token, "video", best_idx, True, req, filename)
    if kind == "zip":
        return _zip_images(_get_session(token), filename)
    if kind not in mapping:
        raise HTTPException(status_code=400, detail="kind harus video|hd|watermark|music|image|cover|zip")
    k, i = mapping[kind]
    return _proxy(token, k, i, True, req, filename)


# --------------------------------------------------------------------------- #
#  Static assets (served after routes so / and /docs still work)
# --------------------------------------------------------------------------- #

app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
