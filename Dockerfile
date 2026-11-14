# UND — All In One · container image (Railway / Docker)
#
# Railway: this file at the repo root is picked up automatically
# (or via railway.json → build.dockerfilePath).
#
# Manual build:  docker build -t und-bot .
# Manual run:    docker run -d --env-file bot/.env -v "$PWD/bot/db:/app/db" und-bot
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=UTC

# ffmpeg = voice/music helpers
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY bot/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY bot/ ./

# Runtime folders. The code opens SQLite files under db/ and JSON stores under
# jsondb/ on first use; without these the container crashes with
# "unable to open database file".
# Mount Railway volumes on /app/db, /app/jsondb (and /app/clients) to keep
# data across deploys.
RUN mkdir -p db jsondb clients logs data lang

EXPOSE 8000
# Keep the container alive: if the bot process ever exits (gateway closed
# cleanly, fatal error, …) it is started again after 5 seconds instead of
# leaving the deployment marked as "Crashed".
CMD ["sh", "-c", "while true; do python UND.py; echo '[supervisor] bot exited — restarting in 5s'; sleep 5; done"]
