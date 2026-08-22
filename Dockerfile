# DFTIKTOK — production image
# Base image already ships Chromium + all its system dependencies,
# so the built-in search scraper (scraper.py) works out of the box.
FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy

WORKDIR /app

# Install Python dependencies first (better layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app.
COPY . .

# uvicorn binds 0.0.0.0 on the port provided by the platform ($PORT).
# Railway/Render/Fly inject a PORT env var; fall back to 8000 locally.
# --proxy-headers + --forwarded-allow-ips let us see the real client IP
# (needed for /api/whoami and the per-IP rate limiter) behind the proxy.
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=\"*\""]
