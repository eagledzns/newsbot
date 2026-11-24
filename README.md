# Viral News Scout

An automated news-monitoring bot that detects high-virality stories across
Bangladeshi and international media and delivers ranked alerts to a Telegram
channel or group. Each alert carries a **Viral Score (0–10)** built from coverage,
audience demand, video views and social engagement.

It runs entirely on free, public data sources and free GitHub Actions, with no paid APIs.

---

## Features

- **Multi-source monitoring**: 25+ news outlets via RSS, Google News site search and
  website parsing, organised into weighted tiers (S / A / B / International).
- **Two editorial lanes**: 🇧🇩 Bangladesh and 🌍 International, each with its own
  posting quota so local and world news never crowd each other out.
- **Virality scoring** from independent signals:

  | Signal | Source | What it measures |
  |---|---|---|
  | Coverage | Tiered outlet list | How many outlets run the story, weighted by tier |
  | Prominence | Google News (Bangladesh + World) | Editorial / algorithmic placement |
  | Search demand | Google Trends (BD, US, UK, IN, PK, AE, SA, TR) | Search volume and number of countries trending |
  | Video views | Public YouTube feeds of major TV and news channels | Views per hour |
  | Social engagement | Meta Graph API (optional) | Reactions, comments, shares per hour |
  | Telegram reach | Public channel previews | Views per hour |
  | Momentum | Previous scan | New outlets picking the story up |
  | Freshness | Publish time | Exponential decay (5-hour half-life) |

- **Story clustering**: groups the same story across outlets and languages
  (Bangla and English), so each event is reported once.
- **Deduplication**: remembers posted stories for 48 hours and skips near-identical angles.
- **Coverage check (optional)**: flags stories your own Facebook Pages have
  already published, with that post's engagement.
- **Noise filtering**: ignores bulletins, live streams and roundup posts.

---

## Quick start (local)

Requirements: Python 3.10+ and a Telegram bot token from [@BotFather](https://t.me/BotFather).

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
python bot.py --dry-run     # preview the ranking; posts nothing
python bot.py --loop 5      # scan and post every 5 minutes
```

On Windows you can use the included scripts instead: `1-setup.bat`, `2-preview.bat`,
`3-start-bot.bat`.

**Finding the chat ID:** add the bot to your group, send a message there, then open
`https://api.telegram.org/bot<TOKEN>/getUpdates` and copy the `chat.id` value
(it starts with `-100`).

---

## Deploy on GitHub Actions (24/7, free)

The included workflow (`.github/workflows/newsbot.yml`) runs a scan every 5 minutes
and commits the bot's memory (`state.json`) back to the repository.

1. Fork or push this repository to GitHub.
2. Under **Settings → Secrets and variables → Actions**, add:
   - `TELEGRAM_BOT_TOKEN`: your bot token
   - `FB_PAGE_TOKENS` *(optional)*: Page tokens for the coverage check
3. Set your `TELEGRAM_CHAT_ID` in the workflow file.
4. Open the **Actions** tab and run **viral-news-bot** once to start it.

> Scheduled runs on GitHub are best-effort and can occasionally start a few minutes late.

---

## Optional: Facebook integration

The bot uses Meta's official **Graph API** only.

- **Pages you manage**: run `fb_token.py` to exchange a short-lived Graph API Explorer
  token for permanent Page tokens (needs `FB_APP_ID`, `FB_APP_SECRET`, `FB_SHORT_TOKEN`
  in `.env`). List the pages to watch in `OWN_PAGES` in `config.py`.
- **Third-party pages**: listed in `SOCIAL_PAGES`. These require Meta's
  *Page Public Content Access* feature (App Review with business verification).
  Until it is granted, they are skipped automatically.

---

## Configuration

All tuning lives in `config.py`:

| Setting | Purpose |
|---|---|
| `SOURCES`, `TIER_WEIGHT` | News outlets and how much each tier counts |
| `YOUTUBE_CHANNELS` | Channels used for the view-velocity signal |
| `GLOBAL_TRENDS_GEOS` | Countries checked on Google Trends |
| `MIN_SCORE`, `MAX_POSTS_PER_RUN` | Bangladesh lane threshold and quota |
| `INTL_MIN_SCORE`, `INTL_MAX_POSTS_PER_RUN` | International lane threshold and quota |
| `HALF_LIFE_H`, `W_*` | Freshness decay and signal weights |
| `VIRAL_KEYWORDS`, `JUNK_TITLES` | Topic boosts and headlines to ignore |

---

## Security

- Credentials are read from environment variables or GitHub encrypted secrets only.
- `.env` is excluded by `.gitignore` and must never be committed.
- Token helper scripts never print token values.

## License

For private and editorial use. News content belongs to its respective publishers;
the bot shares headlines and links only.
