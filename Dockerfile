# DFTIKTOK — production image
# Base image already ships Chromium + all its system dependencies,
# so the built-in search scraper (scraper.py) works out of the box.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Install Python dependencies first (better layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app.
COPY . .

# uvicorn binds 0.0.0.0:8000 — Railway/cloud proxies expose this port.
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
