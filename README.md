# Viral News Scout (Telegram)

Finds the most viral and engaging news for Tidbid / Tizzar and posts it to your
Telegram group with a **Viral score (0–10)**. It's free and uses no paid APIs.

---

## How to run it (on your PC)

### Step 1: Make the Telegram bot (2 min)
1. In Telegram, search **@BotFather** → send `/newbot` → pick a name → copy the
   **token** it gives you (looks like `8123456789:AAH...`).
2. Add your new bot to your group (e.g. *No Sleep Curation*) and make it **admin**.

### Step 2: Get the group's chat ID
1. Send any message in the group (e.g. `hi`).
2. Open this in your browser (put your token in):
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `"chat":{"id":-100xxxxxxxxxx` and copy that number, including the minus sign.

### Step 3: Setup
Double-click **`1-setup.bat`**. It installs the requirements and opens `.env` in Notepad.
Paste your token and chat ID, then save:
```
TELEGRAM_BOT_TOKEN=8123456789:AAH...
TELEGRAM_CHAT_ID=-1001234567890
```

### Step 4: Preview, then start
- Double-click **`2-preview.bat`**. It shows the ranking and the posts it *would* send,
  without posting anything.
- Double-click **`3-start-bot.bat`**. The bot is live: it scans every 5 minutes and posts
  stories that score ≥ 6. Keep the window open; close it to stop.

> PC must stay on for this. To run 24/7 with your PC off, use the GitHub option below.

---

## Run 24/7 for free on GitHub (optional)
1. Make a **private** repo on github.com and upload this whole folder
   (but NOT the `.env` file).
2. Repo → **Settings → Secrets and variables → Actions → New repository secret**:
   add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (plus `FB_PAGE_TOKEN` if you have it).
3. **Actions** tab → enable → *viral-news-bot* → **Run workflow**.
   After that, it runs every 5 minutes automatically.

---

## Step 5 (optional): Facebook pages: Cablgram, Nutshell, Bongo Wiki…

Facebook doesn't let anyone read pages without a login, so the bot uses Meta's
**official Graph API**. It's free and needs one token:

1. Go to **developers.facebook.com** → *My Apps* → **Create App** → type *Business*.
2. Open **Graph API Explorer** (Tools menu) → pick your app → *Generate Access Token*.
3. Paste the token as `FB_PAGE_TOKEN=` in `.env`.

What works with that token:
- ✅ **Pages you manage** (e.g. Tidbid, Tizzar) work immediately.
- ⏳ **Other pages** (Cablgram, Bongo Wiki, BengaliVerse, Sozoo…) need Meta to approve
  the **"Page Public Content Access"** feature for your app (*App Review* →
  request it; needs business verification; free). Until then the bot just skips
  them and logs a message; nothing breaks.

Tokens from the Explorer expire in ~1–2 hours. For a long-lasting one, exchange it
for a *long-lived token* (60 days) with the Access Token Debugger
(developers.facebook.com/tools/debug/accesstoken → "Extend Access Token").

When a page post matches a story, it counts as that outlet covering it (at its
tier) **and** adds the post's reactions + comments + shares per hour to the score.

Facebook handles in `config.py → SOCIAL_PAGES`: Cablgram's and Nutshell's IDs are
verified. The others are guesses, so open each page and fix the handle if needed.

### Already working without Facebook
- **Nutshell Today** articles are read from **nutshelltoday.com** (S tier).
- **Science Bee** from its website and its public Telegram channel (with view counts).
- **Cablgram's website** only shows image cards with no headline text, so it needs the
  Facebook token above.

---

## How the score works

| Signal | Source (free) | Measures |
|---|---|---|
| Coverage | Your S/A/B/International list (RSS, Google News, websites, FB pages) | How many outlets run it; S = 1.5×, A = 1×, B = 0.7× |
| Google News | BD top stories | Prominence |
| Trend | Google Trends BD | Search volume |
| YouTube views | Jamuna, Independent, DBC, Maasranga, Somoy, Ekattor, Channel 24 | Views per hour |
| FB pages | Graph API (Step 5) | Engagement per hour |
| Telegram | Public channels | Views per hour |
| Momentum | vs. last scan | New outlets picking it up |
| Topic | Keyword list | Crime, celebs, cricket, Gaza… |
| Freshness | Article time | Score halves every 5 h |

## Tuning: edit `config.py`
- `MIN_SCORE = 5.0`: raise for fewer, bigger stories; lower for more.
- `MAX_POSTS_PER_RUN`, `HALF_LIFE_H`, `TIER_WEIGHT`, the `W_*` weights.
- Add or remove sources in `SOURCES`, `SOCIAL_PAGES`, `YOUTUBE_CHANNELS`.
