"""Sources, weights and thresholds. Edit this file to tune the bot."""

# ---- Tier weights: an outlet's "vote" when it covers a story ---------------
TIER_WEIGHT = {"S": 1.5, "A": 1.0, "B": 0.7, "INT": 1.0, "OTHER": 0.5}

# ---- Sources (your Headlines list) ----------------------------------------
# "rss": direct feed. "site": no usable feed (or it blocks bots), so the bot
# reads that site's last-24h articles through Google News search instead.
# "lang": "bn" or "en" (which Google News edition to search).
SOURCES = [
    # S tier
    {"name": "The Business Standard", "tier": "S", "rss": "https://www.tbsnews.net/top-news/rss.xml"},
    {"name": "Ittefaq",               "tier": "S", "rss": "https://www.ittefaq.com.bd/feed/"},
    {"name": "The Daily Star",        "tier": "S", "rss": "https://www.thedailystar.net/frontpage/rss.xml"},
    {"name": "Prothom Alo",           "tier": "S", "rss": "https://www.prothomalo.com/feed/"},
    {"name": "Daily Waadaa",          "tier": "S", "rss": "https://dailywaadaa.com/feed"},
    {"name": "Nutshell Today",        "tier": "S", "homepage": "https://www.nutshelltoday.com",
                                                   "pattern": "/article/"},
    {"name": "DBC News",              "tier": "S", "site": "dbcnews.tv"},
    {"name": "Independent TV",        "tier": "S", "site": "itvbd.com"},
    # A tier
    {"name": "Jugantor",              "tier": "A", "site": "jugantor.com"},
    {"name": "Kaler Kantho",          "tier": "A", "site": "kalerkantho.com"},
    {"name": "Samakal",               "tier": "A", "site": "samakal.com"},
    {"name": "Dhaka Tribune",         "tier": "A", "rss": "https://www.dhakatribune.com/feed/"},
    {"name": "Jamuna TV",             "tier": "A", "site": "jamuna.tv"},
    {"name": "Maasranga News",        "tier": "A", "rss": "https://www.maasranga.tv/feed"},
    {"name": "Science Bee",           "tier": "A", "rss": "https://sciencebee.com.bd/feed"},
    # B tier
    {"name": "Daily Inqilab",         "tier": "B", "rss": "https://www.dailyinqilab.com/rss/rss.xml"},
    {"name": "Manab Zamin",           "tier": "B", "site": "mzamin.com"},
    {"name": "The Daily Campus",      "tier": "B", "site": "thedailycampus.com"},
    # International
    {"name": "Al Jazeera",            "tier": "INT", "rss": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "BBC",                   "tier": "INT", "rss": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "BBC Bangla",            "tier": "INT", "rss": "https://feeds.bbci.co.uk/bengali/rss.xml"},
    {"name": "Anadolu Ajansı",        "tier": "INT", "rss": "https://www.aa.com.tr/en/rss/default?cat=guncel"},
    {"name": "Roya News",             "tier": "INT", "site": "en.royanews.tv", "lang": "en"},
    {"name": "Middle East Eye",       "tier": "INT", "rss": "https://www.middleeasteye.net/rss"},
    {"name": "Middle East Monitor",   "tier": "INT", "rss": "https://www.middleeastmonitor.com/feed/"},
    {"name": "NDTV",                  "tier": "INT", "rss": "https://feeds.feedburner.com/ndtvnews-world-news"},
    {"name": "Daily Mail",            "tier": "INT", "rss": "https://www.dailymail.co.uk/news/index.rss"},
    {"name": "TRT World",             "tier": "INT", "site": "trtworld.com", "lang": "en"},
]

# Google News outlet names (as they appear in its feeds) -> your source names,
# so Google News mentions count toward the right tier.
OUTLET_ALIASES = {
    "প্রথম আলো": "Prothom Alo", "দৈনিক ইত্তেফাক": "Ittefaq", "ইত্তেফাক": "Ittefaq",
    "কালের কণ্ঠ": "Kaler Kantho", "যুগান্তর": "Jugantor", "সমকাল": "Samakal",
    "মানবজমিন": "Manab Zamin", "ইনকিলাব": "Daily Inqilab", "যমুনা টিভি": "Jamuna TV",
    "The Daily Star": "The Daily Star", "The Business Standard": "The Business Standard",
    "Dhaka Tribune": "Dhaka Tribune", "itvbd": "Independent TV", "Jamuna Television": "Jamuna TV",
    "BBC": "BBC", "BBC News বাংলা": "BBC Bangla", "Al Jazeera": "Al Jazeera", "NDTV": "NDTV",
    "Daily Mail": "Daily Mail", "TRT World": "TRT World", "Middle East Eye": "Middle East Eye",
}

# Google News "top stories" = editorial/algorithm prominence signal
GOOGLE_NEWS_FEEDS = [
    "https://news.google.com/rss?hl=bn&gl=BD&ceid=BD:bn",
    "https://news.google.com/rss?hl=en-BD&gl=BD&ceid=BD:en",
    # world top stories = global prominence for international news
    "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en",
]

# Google Trends in other countries: a story trending in several countries is
# globally viral. Search volume + number of countries both boost the score.
GLOBAL_TRENDS_GEOS = ["US", "GB", "IN", "PK", "AE", "SA", "TR"]
W_TREND_COUNTRIES = 0.6    # bonus per extra country trending it (capped)
TREND_COUNTRIES_CAP = 2.0

# Google Trends trending searches in Bangladesh (approx search volume = demand)
GOOGLE_TRENDS_FEED = "https://trends.google.com/trending/rss?geo=BD"

# YouTube channels: their public RSS feed includes VIEW COUNTS (free, no key).
YOUTUBE_CHANNELS = {
    "Jamuna TV":       "UCN6sm8iHiPd0cnoUardDAnw",
    "Independent TV":  "UCATUkaOHwO9EP_W87zCiPbA",
    "DBC News":        "UCUvXoiDEKI8VZJrr58g4VAw",
    "Maasranga TV":    "UCJGnNvYgPpUhd7ImU9diBSQ",
    "Somoy TV":        "UCxHoBXkY88Tb8z1Ssj6CWsQ",
    "Ekattor TV":      "UCtqvtAVmad5zywaziN6CbfA",
    "Channel 24":      "UCHLqIOMPk20w-6cFgkA90jw",
    "Prothom Alo":     "UChxZgRBNYXWul3c1eGQKO3A",
    "The Daily Star":  "UC5-BAboL0IOByHnlVShQRQA",
    # international
    "Al Jazeera":      "UCNye-wNBqNL5ZzHSJj3l8Bg",
    "BBC News":        "UC16niRr50-MSBwiO3YDb3RA",
    "TRT World":       "UC7fWeaHhqgM4Ry-RMpM2YYw",
    "Middle East Eye": "UCR0fZh5SBxxMNYdg0VzRFkg",
    "NDTV":            "UCZFMm1mMw0F81Z37aaEzTUA",
    "Anadolu":         "UCph-M7aQqpi1fW0BQwn7XUA",
}

# ---- Byte-sized media (Facebook-first pages) ------------------------------
# "fb": the page's Facebook username or numeric page ID, as in
#       facebook.com/<this>. CHECK each one by opening the page; these are guesses.
#       Read through the official Graph API (needs FB_PAGE_TOKEN, see README).
# "tg": public Telegram channel username (read free from t.me/s/<this>, with views).
# A page post counts as an outlet covering the story (at its tier) AND adds
# its engagement/views per hour to the score.
SOCIAL_PAGES = [
    {"name": "Cablgram",            "tier": "S", "fb": "610927672898119"},   # verified (from cablgram.com)
    {"name": "Bongo Wiki",          "tier": "S", "fb": "bongowiki"},
    {"name": "BengaliVerse",        "tier": "S", "fb": "bengaliverse"},
    {"name": "Nutshell Today",      "tier": "S", "fb": "1253091327888427"},  # verified (from nutshelltoday.com)
    {"name": "Science Bee",         "tier": "A", "fb": "sciencebee", "tg": "sciencebee"},
    {"name": "Sozoo Today",         "tier": "A", "fb": "sozootoday"},
    {"name": "Insights Today",      "tier": "A", "fb": "insightstoday"},
    {"name": "The Noiseless News",  "tier": "B", "fb": "thenoiselessnews"},
    {"name": "Blinkworthy",         "tier": "B", "fb": "blinkworthy"},
    {"name": "Get the Fame",        "tier": "B", "fb": "getthefame"},
]
# Your OWN Pages (read with permanent tokens from FB_PAGE_TOKENS, made by
# fb_token.py). Alerts get "✅ Already on <Page>" when you've covered a story.
OWN_PAGES = {
    "Tizzar":                      "713854771821351",
    "Tidbid Today":                "590221930839985",
    "The Breakdown Media Network": "899049026630545",
}

W_TG       = 1.0   # x log10(1 + Telegram views per hour)
W_FB_PAGES = 1.5   # x log10(1 + FB page reactions+comments+2*shares per hour)

# ---- Optional: Facebook engagement (free) ---------------------------------
# Set FB_APP_ID and FB_APP_SECRET env vars (free app at developers.facebook.com)
# and the bot adds reactions+comments+shares of each top story's article URL.
FB_CHECK_TOP_N = 15

# ---- Scoring weights ------------------------------------------------------
W_COVERAGE   = 2.0   # x log2(1 + tier-weighted outlets covering the story)
W_GNEWS      = 1.5   # story is in Google News top stories
W_TREND      = 1.0   # x log10(Google Trends search volume)
W_YT         = 1.0   # x log10(1 + YouTube views per hour)
W_FB         = 1.2   # x log10(1 + Facebook engagement)
W_GROWTH     = 1.0   # per extra outlet since last run (momentum), capped
GROWTH_CAP   = 3.0
W_KEYWORD    = 1.0   # "engageable" topic bonus (see VIRAL_KEYWORDS)
HALF_LIFE_H  = 5.0   # freshness: score halves every N hours since last update
SCALE        = 8.0   # 0-10 squashing; higher = harder to reach 10

# ---- Posting rules --------------------------------------------------------
MIN_SCORE         = 5.5   # only post stories scoring at least this (0-10)
MAX_POSTS_PER_RUN = 3     # Bangladesh stories per run (runs every 5 min)
# International lane: world stories get their own slots so local news
# can't crowd them out.
INTL_MIN_SCORE         = 5.5
INTL_MAX_POSTS_PER_RUN = 3
MAX_AGE_HOURS     = 24
REPOST_GAP_HOURS  = 48    # don't post the same story again within this window
DEDUP_OVERLAP     = 0.35  # lower = stricter "same topic" filter (0.3-0.6)

# Headlines to ignore (bulletins, roundups, live streams). Regex, case-insensitive.
JUNK_TITLES = [
    r"daily news brief", r"morning update", r"evening update", r"news ?(update|bulletin)",
    r"^live\b", r"\blive stream", r"headlines? (at|of) ", r"top \d+ news", r"ইপেপার",
    r"সংবাদ শিরোনাম", r"শিরোনাম", r"বুলেটিন", r"লাইভ",
]

VIRAL_KEYWORDS = [
    "ভাইরাল", "চাঞ্চল্য", "হত্যা", "খুন", "গ্রেপ্তার", "আটক", "ধর্ষণ", "দুর্ঘটনা",
    "নিহত", "মৃত্যু", "আগুন", "বিস্ফোরণ", "সংঘর্ষ", "হামলা", "অভিনেত্রী", "অভিনেতা",
    "নায়িকা", "নায়ক", "তারকা", "বিয়ে", "তালাক", "সাকিব", "তামিম", "মুশফিক",
    "ক্রিকেট", "ফুটবল", "মেসি", "রোনালদো", "হাসিনা", "তারেক", "নির্বাচন", "ভিডিও",
    "রেকর্ড", "গাজা", "ইসরায়েল", "ফিলিস্তিন",
    "viral", "killed", "arrest", "celebrity", "record", "shocking", "fire", "clash",
    "gaza", "israel", "trump",
]
