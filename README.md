# Book Nishita™

A tiny, fun two-page site for scheduling (pointless but delightful) appointments with Nishita, an Actuarial Analyst at Deloitte who works day and night.

## Pages

1. **Login** (`public/index.html`): choose Prateek, Ritika, Yuvraj or Nishita from a dropdown.
2. **Calendar** (`public/calendar.html`):
   - **Prateek / Ritika / Yuvraj** get a pop-up saying Nishita can give them only **15 minutes**, so don't hope for much. They pick a free slot in the 7-day view and choose a reason from 18 presets (chai, roast, ice cream emergency…) or enter a **custom reason**.
   - **Nishita** blocks slots with absurd actuarial events (or her own excuse), or blocks a whole day at once. Blocked slots can't be booked by the others. She can also decline bookings.

## Run it

Requires Python 3.9+ (standard library only, nothing to install).

```powershell
cd fun_web
python server.py
```

Open <http://127.0.0.1:8000>. Everyone who uses the same server shares the same calendar; data is saved in `data.json`.

| Env var     | Default          | Purpose                                      |
|-------------|------------------|----------------------------------------------|
| `HOST`      | `127.0.0.1`      | Bind address (use `0.0.0.0` to share on LAN) |
| `PORT`      | `8000`           | Port                                         |
| `DATA_FILE` | `./data.json`    | Where blocks and bookings are stored         |

## Deploy (Render, free)

1. Push this folder to a GitHub repository (the folder is already a git repo with `render.yaml`).
2. On <https://render.com>: **New +** → **Blueprint** → select the repo → **Apply**. (Or **New Web Service** with runtime Python, build command `python --version`, start command `python server.py`, env var `HOST=0.0.0.0`.)
3. Share the generated `https://book-nishita.onrender.com` URL (the exact name may differ).

Render supplies `PORT` automatically. Caveats of the free plan: the service sleeps after ~15 minutes idle (first visit takes ~30 s to wake) and its disk is ephemeral, so blocks and bookings reset on restart or redeploy.

## Email notifications

Nishita gets an email whenever Prateek, Ritika or Yuvraj books a slot (who, when, reason, note). Sending uses plain SMTP and is configured with environment variables, so no credentials live in the code. It is off until `SMTP_HOST` and `NOTIFY_EMAIL` are set, and an email failure never blocks a booking.

| Env var         | Example                    | Purpose                                         |
|-----------------|----------------------------|-------------------------------------------------|
| `NOTIFY_EMAIL`  | Nishita's address          | Who receives the notifications                  |
| `SMTP_HOST`     | `smtp-relay.brevo.com`     | SMTP server                                     |
| `SMTP_PORT`     | `587` (default) / `2525`   | `465` uses SSL, anything else uses STARTTLS     |
| `SMTP_USER`     |                            | SMTP login                                      |
| `SMTP_PASSWORD` |                            | SMTP password / app password / API key          |
| `MAIL_FROM`     | a verified sender address  | From address (defaults to `SMTP_USER`)          |

Local example (PowerShell, Gmail with an [app password](https://myaccount.google.com/apppasswords)):

```powershell
$env:NOTIFY_EMAIL="nishita@example.com"; $env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_USER="you@gmail.com"; $env:SMTP_PASSWORD="<app password>"
python server.py
```

On Render's free plan, outbound SMTP ports 25, 465 and 587 are blocked, so use a provider that supports port **2525** (Brevo, Mailgun, SendGrid) and verify your sender address with it. Enter the values in the Render dashboard (**Environment**); `render.yaml` lists them with `sync: false` so they are never committed.

## Tests

```powershell
cd fun_web
python -m unittest -v
```

## Notes

- This is a fun site: login is by name only (no passwords), so anyone who picks "Nishita" can block her calendar.
- Slots are hourly, 6 AM – 12 midnight, for the next 7 days. The last cell of each day (12 AM – 6 AM) is permanently "Booked by Deloitte", can't be changed, and counts toward the Busy-o-Meter.
