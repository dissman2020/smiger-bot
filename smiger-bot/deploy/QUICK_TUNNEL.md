# Quick Tunnel Usage

Use this mode when you want webhook access immediately without setting up Railway/Render.

## Prerequisites

- Docker Desktop is running.
- `cloudflared` installed:

```powershell
winget install --id Cloudflare.cloudflared -e
```

## Start

From repo root (`smiger-bot`):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_quick_tunnel.ps1
```

The script will:

- Start Docker services.
- Start backend/frontend Cloudflare Quick Tunnels.
- Update `.env`:
  - `TELEGRAM_ENABLED=true`
  - `TELEGRAM_MODE=webhook`
  - `TELEGRAM_WEBHOOK_BASE_URL=<backend tunnel url>`
- Recreate backend and register Telegram webhook.
- Rebuild frontend with `NEXT_PUBLIC_API_URL=<backend tunnel url>`.

## Stop

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop_quick_tunnel.ps1
```

Stop tunnels and containers:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop_quick_tunnel.ps1 -StopCompose
```

## Important Notes

- Quick Tunnel domains are temporary and will change.
- Run `start_quick_tunnel.ps1` again whenever domain changes.
- For a stable production domain, use a named Cloudflare Tunnel or deploy to Railway/Render.
