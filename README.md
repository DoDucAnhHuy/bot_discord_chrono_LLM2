# 🐉 Discord Boss Tracker Bot

Track Lineage 2M boss respawn timers with slash commands and automatic alerts.

---

## 📁 Project Structure

```
discord-boss-tracker/
├── main.py                   # Entrypoint
├── config.py                 # Env-based configuration
├── requirements.txt
├── .env.example              # Copy → .env and fill in
├── seed_data.json            # Example boss master data
├── seed_firestore.py         # One-time seed script
│
├── database/
│   └── firestore.py          # All Firestore read/write helpers
│
├── models/
│   ├── boss.py               # Boss dataclass
│   └── kill.py               # KillRecord dataclass
│
├── services/
│   ├── boss_service.py       # Boss lookup + in-memory cache + fuzzy search
│   ├── time_service.py       # Datetime parsing, formatting, calculations
│   └── alert_service.py      # Background respawn alert loop
│
└── commands/
    ├── kill.py               # /kill slash command
    └── list.py               # /list slash command (paginated)
```

---

## 🚀 Setup Guide

> Security note: `firebase_credentials.json` is sensitive and should never be committed.
> This project ignores both `.env` and `firebase_credentials.json` via `.gitignore`.

### 1 · Create a Discord Bot

1. Go to [https://discord.com/developers/applications](https://discord.com/developers/applications)
2. Click **New Application** → give it a name
3. Go to **Bot** tab → click **Add Bot**
4. Under **Token** click **Reset Token** and copy it
5. Enable **"applications.commands"** scope + **"bot"** scope in OAuth2
6. Under **Bot** tab, enable:
   - `Send Messages`
   - `Embed Links`
7. Under **OAuth2 → URL Generator**, select scopes:
   `bot` + `applications.commands`
   Permissions: `Send Messages`, `Embed Links`
8. Use the generated URL to invite the bot to your server

---

### 2 · Set Up Firebase

1. Go to [https://console.firebase.google.com](https://console.firebase.google.com)
2. Create a new project (or use an existing one)
3. Click **Build → Firestore Database → Create Database**
   - Choose **Start in production mode**
   - Select a region closest to you (e.g. `asia-southeast1` for Vietnam)
4. Go to **Project Settings → Service Accounts**
5. Click **Generate new private key** → download the JSON file
6. Rename the downloaded file to `firebase_credentials.json` and place it in the project root

#### Firestore Security Rules (Firestore → Rules tab)

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if false; // Only the service account can access
    }
  }
}
```

---

### 3 · Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_guild_id_here          # Right-click your server → Copy Server ID
ALERT_CHANNEL_ID=your_channel_id     # Right-click #alerts channel → Copy Channel ID
FIREBASE_CREDENTIALS_PATH=firebase_credentials.json
FIREBASE_CREDENTIALS_B64=            # Optional: base64 of firebase_credentials.json
```

> **Tip:** To get IDs, enable Developer Mode in Discord settings (Advanced → Developer Mode), then right-click any server/channel.

---

### 4 · Install Dependencies

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

### 5 · Seed Boss Data

```bash
python seed_firestore.py
```

This populates the `dimboss` collection with 8 classic L2 bosses. Edit `seed_data.json` to add your own bosses first.

---

### 6 · Run the Bot

```bash
python main.py
```

You should see:
```
Logged in as BossTracker#1234 (ID: ...)
Commands synced to guild ... (instant)
Alert loop started (interval: 60s, thresholds: [10, 5] min)
```

---

## 💬 Commands

### `/kill boss:<name> [time:<HH:mm|now>]`

Record a boss kill.

| Parameter | Required | Values |
|-----------|----------|--------|
| `boss`    | ✅       | Boss name or ID (fuzzy search supported) |
| `time`    | ❌       | `now` (default) or `HH:mm` in UTC+7 |

**Examples:**
```
/kill boss:Gahareth
/kill boss:Gahareth time:17:40
/kill boss:gahareth time:now
/kill boss:gaha time:17:40     ← fuzzy match works!
```

**Response:**
```
⚔️ GAHARETH KILLED

Time Killed  03/29/26 17:40 (UTC+7)
Next Spawn   01:10
Remain       7h30m
```

---

### `/list`

Show all bosses sorted by time until next spawn.

- 10 bosses per page
- Prev / Next pagination buttons
- Bosses without a recorded kill show "Unknown"

---

## 🔔 Alert System

The bot automatically sends alerts to the configured channel:

- **10 minutes** before a boss spawns → `⚠️ Respawn Alert! … Spawns in 10 minutes!`
- **5 minutes** before a boss spawns → `⚠️ Respawn Alert! … Spawns in 5 minutes!`

Alerts are deduplicated: each threshold fires only once per boss cycle.

---

## ➕ Adding a New Boss

Simply add a document to the `dimboss` Firestore collection:

```json
{
  "id": "queen_ant",
  "name": "Queen Ant",
  "cycle_minutes": 1440
}
```

The bot caches boss data for 5 minutes, so changes reflect automatically.

---

## 🗄️ Firestore Data Model

### Collection: `dimboss`

| Field | Type | Example |
|-------|------|---------|
| `id` | string | `"gahareth"` |
| `name` | string | `"Gahareth"` |
| `cycle_minutes` | number | `210` |

### Collection: `fact_kill`

| Field | Type | Example |
|-------|------|---------|
| `boss_id` | string | `"gahareth"` |
| `last_kill_time` | string (ISO UTC) | `"2026-03-29T10:40:00+00:00"` |
| `updated_by` | string | `"123456789"` (Discord user ID) |

> `next_spawn` and `remain` are **never stored** — always computed in real-time.

---

## ☁️ Deploy on Railway (Private GitHub Repo)

### 1 · Push code to GitHub (private)

1. Create a **private** repository on GitHub.
2. Push this project, but do **not** include `.env` or `firebase_credentials.json`.

### 2 · Deploy from GitHub in Railway

1. Open [https://railway.app](https://railway.app)
2. Click **New Project** → **Deploy from GitHub**
3. Select your private repo

### 3 · Add environment variables in Railway

Set these variables:

```env
DISCORD_TOKEN=...
GUILD_ID=...
ALERT_CHANNEL_ID=...
FIREBASE_CREDENTIALS_B64=...
```

Generate base64 locally:

```bash
python -c "import base64; print(base64.b64encode(open('firebase_credentials.json','rb').read()).decode())"
```

### 4 · Start command

In Railway service settings, set start command to:

```bash
python main.py
```

### 5 · Optional fallback (volume + file path)

If you prefer file-based credentials, upload `firebase_credentials.json` to a Railway volume and set:

```env
FIREBASE_CREDENTIALS_PATH=/path/in/volume/firebase_credentials.json
```

When `FIREBASE_CREDENTIALS_B64` is set, it takes precedence over `FIREBASE_CREDENTIALS_PATH`.
