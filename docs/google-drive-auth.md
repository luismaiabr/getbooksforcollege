# Google Drive OAuth Authentication

## How it works

The book-gateway needs a Google Drive OAuth token (`token.json`) to access
Drive files. Because the Docker container runs headless on a remote VPS, the
OAuth "consent → redirect → capture code" loop requires a little extra wiring.

The script `scripts/generate_token.py` starts a tiny HTTP server on
`0.0.0.0:8080` inside the container. Google's consent screen redirects the
browser to `http://localhost:8080/` (the only redirect URI allowed for
"Desktop / Installed" OAuth clients). The script captures the authorization
code from that redirect and exchanges it for a token.

The token is persisted to the `oauth_token` Docker named volume at
`/app/token_store/token.json`, so it survives container rebuilds.

---

## Prerequisites

| Item | Details |
|------|---------|
| `credentials.json` | Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client ID (type **Desktop**). Place it in the project root (`services/book-gateway/credentials.json`). |
| Port 8080 free on the VPS | The container maps `8080:8080`. Make sure nothing else uses it. |
| Domain (optional) | `egoals.uptoken.cloud` pointing to the VPS (147.79.86.144). |

---

## Method 1 — VS Code Remote SSH port forwarding (current default)

If you're connected to the VPS via **VS Code Remote SSH**, VS Code can
auto-forward port 8080 so that `localhost:8080` on your laptop reaches the
container.

1. Open VS Code's **Ports** panel and forward port **8080** (if not already).
2. Run:
   ```bash
   cd services/book-gateway
   ./scripts/auth_google_drive.sh
   ```
3. Open the printed URL in your local browser, sign in, grant access.
4. The browser redirects to `localhost:8080` → VS Code forwards it → the
   script captures the code → done.

---

## Method 2 — SSH tunnel (no VS Code needed)

If you're connected to the VPS via a plain SSH terminal (no VS Code), create
a tunnel so `localhost:8080` on your machine reaches port 8080 on the VPS:

```bash
# On your local machine (laptop / desktop):
ssh -L 8080:localhost:8080 root@egoals.uptoken.cloud
```

Then, **in a separate terminal on the VPS** (or in that same SSH session):

```bash
cd /root/REMOTEDEVELOPMENT/eGOALS/services/book-gateway
./scripts/auth_google_drive.sh
```

Open the printed URL in your local browser. The redirect to
`localhost:8080` travels through the SSH tunnel to the container. Once the
script prints **✅ Authentication complete!**, close the tunnel.

---

## Method 3 — Direct access via domain / public IP (no tunnels, no VS Code)

This method avoids any port forwarding entirely. You access the OAuth
callback server directly through the VPS's public IP or domain.

### One-time setup in Google Cloud Console

1. Go to **APIs & Services → Credentials → your OAuth 2.0 Client ID**.
2. Change the application type from **Desktop** to **Web application** (or
   create a new Web-type client and download its `credentials.json`).
3. Under **Authorized redirect URIs** add:
   ```
   http://egoals.uptoken.cloud:8080/
   ```
   (and/or `http://147.79.86.144:8080/` if you want to use the raw IP).
4. Save and download the updated `credentials.json` into the project root.

### One-time code change

In `scripts/generate_token.py`, update the `redirect_uri` for headless mode
to use the domain instead of `localhost`:

```python
# Replace this line:
redirect_uri = f"http://localhost:{port}/"

# With:
redirect_host = os.getenv("OAUTH_REDIRECT_HOST", "localhost")
redirect_uri = f"http://{redirect_host}:{port}/"
```

In `docker-compose.yml`, set `OAUTH_REDIRECT_HOST` to the domain:

```yaml
environment:
  OAUTH_REDIRECT_HOST: "egoals.uptoken.cloud"
```

And change the port mapping so port 8080 is reachable from the public
interface (not just Tailscale):

```yaml
ports:
  - "0.0.0.0:8080:8080"   # OAuth callback — open to public
```

### Running the auth flow

```bash
cd /root/REMOTEDEVELOPMENT/eGOALS/services/book-gateway
./scripts/auth_google_drive.sh
```

Open the printed URL in **any** browser (phone, laptop, anywhere). Google
redirects to `http://egoals.uptoken.cloud:8080/` which hits the container
directly. No tunnels, no VS Code.

> **Security note:** port 8080 is only open for the few seconds the auth
> script is running. The HTTP server shuts down immediately after capturing
> the code. You can also firewall port 8080 and only open it during auth.

---

## Method 4 — Copy-paste the redirect URL (no server, no ports)

If you cannot open any ports or tunnels, use the manual copy-paste flow:

1. Run:
   ```bash
   docker exec -it bookgateway python scripts/generate_token.py --headless
   ```
2. Open the printed URL, sign in, grant access.
3. Google redirects to `http://localhost:8080/?code=...&scope=...`. The page
   won't load (no server listening locally) — **that's fine**.
4. Copy the **full URL** from the browser's address bar.
5. Kill the waiting script (`Ctrl+C`), then run the token exchange manually:
   ```bash
   docker exec -it bookgateway python3 -c "
   from google_auth_oauthlib.flow import InstalledAppFlow
   from pathlib import Path
   from urllib.parse import urlparse, parse_qs

   url = input('Paste the redirect URL: ')
   code = parse_qs(urlparse(url).query)['code'][0]

   flow = InstalledAppFlow.from_client_secrets_file('/app/credentials.json',
       ['https://www.googleapis.com/auth/drive'])
   flow.redirect_uri = 'http://localhost:8080/'
   flow.fetch_token(code=code)

   Path('/app/token_store/token.json').write_text(flow.credentials.to_json())
   print('Done — token saved.')
   "
   ```

---

## Verifying the token

After any method, confirm the token exists and the API works:

```bash
# Check the token file
docker exec bookgateway ls -la /app/token_store/token.json

# Quick API test
curl -s http://localhost:8003/health | python3 -m json.tool
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `PermissionError: Permission denied: '/app/token_store/token.json'` | Old token owned by `root` from a previous `docker cp` | `docker exec -u root bookgateway chown appuser:appuser /app/token_store/token.json` |
| `Error 400: invalid_request` | Redirect URI doesn't match what's registered in Google Cloud Console | For Desktop clients only `http://localhost` works. For Web clients, register the exact URI. |
| `OSError: Address already in use` on port 8080 | Previous auth script or process still bound | `docker exec -u root bookgateway pkill -f generate_token` then retry |
| Browser redirects but page doesn't load | Port 8080 not forwarded / not reachable | Use one of the methods above to make port 8080 reachable from your browser |
| Token expires / `RefreshError` | Refresh token revoked or expired (>6 months unused, or app in "Testing" mode in GCP) | Re-run the auth flow. Consider moving the GCP app to "Production" status. |
