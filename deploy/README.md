# Deploying UND

Three supported paths. The bot needs a **long-running process** (Discord gateway
connection), so serverless / sleeping web services do not work.

## 1 · VPS / Oracle Cloud Always Free (recommended, truly free 24/7)

```bash
git clone <your-repo> /opt/und-src      # or upload the project
cd /opt/und-src
sudo bash deploy/install.sh
```

The installer:

* installs `python3-venv`, `ffmpeg` (music), `rsync`
* creates the `und` system user
* copies `bot/` to `/opt/und/bot` and builds `/opt/und/bot/.venv`
* installs `deploy/und-bot.service` → `/etc/systemd/system/und-bot.service`
* enables it so it starts on boot and restarts on crash (`Restart=always`)

Then:

```bash
sudo nano /opt/und/bot/.env            # TOKEN=..., OWNER_IDS=...
sudo systemctl restart und-bot
journalctl -u und-bot -f               # live logs
```

Oracle users: everything the bot needs is **outbound** (Discord gateway +
Cloudflare Tunnel), so you do not have to open any inbound port.

## 2 · Bot panel (Pterodactyl / ACLClouds / Waifly / cogithost)

Upload the **`bot/` folder** as the server root and set the start command to:

```bash
bash start.sh
```

`start.sh` installs `requirements.txt` and then runs `python3 UND.py`. Keep the
`.env` file in the same folder. These plans are small (≈300 MB RAM, ≈500 MB–1 GB
disk) — if the bot gets killed for memory, move to Oracle or a paid tier.

## 3 · Docker

```bash
docker build -f deploy/Dockerfile -t und-bot .
docker run -d --name und -p 8000:8000 \
  -v "$PWD/bot/.env:/app/.env:ro" \
  -v "$PWD/bot/db:/app/db" -v "$PWD/bot/jsondb:/app/jsondb" und-bot
```

Mount `.env` as a file instead of using `--env-file`: the bot reads it with
`python-dotenv`, and `--env-file` would keep the quotes around values.

Mount `db/` and `jsondb/` or you lose every setting on restart.

## Dashboard → Vercel

1. Import the repo in Vercel, set **Root Directory = `dashboard`**.
2. Add the variables from `dashboard/.env.production.example`.
3. In Discord → OAuth2 → Redirects add
   `https://<your-app>.vercel.app/api/auth/callback/discord`.

## Exposing the bot API to Vercel (Cloudflare Tunnel, free)

The dashboard is serverless and the bot lives on your VPS, so the API needs a
public HTTPS URL. The bot already ships the tunnel (`utils/tunnel.py`,
`pycloudflared` — the binary downloads itself on first run):

1. <https://one.dash.cloudflare.com> → Networks → Tunnels → Create a tunnel →
   **Cloudflared**, name it `und-api`.
2. Copy the token from the install command (`cloudflared tunnel run --token …`).
3. Published application route: subdomain `api`, your domain, service
   `http://localhost:8000`.
4. In `bot/.env`:

```env
API_ENABLED="true"
API_PORT="8000"
TUNNEL_ENABLED="true"
CF_TUNNEL_TOKEN="<token from step 2>"
CF_TUNNEL_URL="https://api.yourdomain.com"
```

5. Restart the bot. The console prints the live URL.
6. On Vercel set `NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1` and the
   same `NEXT_PUBLIC_DASHBOARD_API_KEY` as `DASHBOARD_API_KEY` in `bot/.env`.

Without the tunnel you can still run the dashboard locally
(`http://localhost:3000` talking to `http://localhost:8000/api/v1`).

## 4 · Railway (always-on, 24/7)

The repo root ships `Dockerfile` + `railway.json`, so Railway builds a real
Docker image (no Railpack guessing, no `pip install` on every restart).

1. <https://railway.app> → **New Project → Deploy from GitHub repo** →
   `DISCORD-BOTh`, branch `main`.
2. **Settings → Build**: Builder `Dockerfile`, Dockerfile Path `Dockerfile`
   (taken from `railway.json`, only check it once).
3. **Variables** (never commit these):

   ```env
   TOKEN=...
   OWNER_IDS=...
   BRAND_NAME=UND
   LAVALINK_HOST=...
   LAVALINK_PORT=80
   LAVALINK_SECURE=false
   LAVALINK_PASSWORD=...
   EMOJI_SYNC=true
   API_ENABLED=false
   TUNNEL_ENABLED=false
   ```

4. **Volumes** — without them every setting/database is wiped on redeploy:
   mount `/app/db`, `/app/jsondb` (and `/app/clients` if you use `/client`).
5. **Replicas = 1** — two replicas mean two gateway connections and every
   command running twice.
6. **Public Networking**: off. The bot needs no inbound port while
   `API_ENABLED=false`.

Deploy logs should end with:

```
Loaded & Online!
Logged in as: <your bot>#0000
EmojiSync: Sync complete: N already matching
Music: Lavalink node connected.
```
