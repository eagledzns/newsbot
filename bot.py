"""Viral news scout -> Telegram.

Collects Bangladeshi news from RSS, groups the same story across outlets,
scores each story on coverage, Google News prominence, Google Trends search
volume, YouTube view velocity, optional Facebook engagement, momentum and
freshness, then posts the best new ones to a Telegram chat.

Usage:
    python bot.py --once        # one scan (for GitHub Actions / cron)
    python bot.py --loop 20     # scan every 20 minutes (run on your PC)
    python bot.py --dry-run     # print the ranking, post nothing
"""
import argparse, hashlib, html, json, math, os, re, sys, time
from calendar import timegm
from concurrent.futures import ThreadPoolExecutor

import feedparser
import requests

import config as C

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "state.json")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9,bn;q=0.8"}
NOW = time.time()
JUNK = re.compile("|".join(C.JUNK_TITLES), re.I)
FB_ERR = {}


def load_env():
    path = os.path.join(HERE, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- text utils
STOP = set("""এবং ও এর এই সেই তার তাদের একটি এক থেকে করে করা করতে হয় হয়েছে হবে
হচ্ছে জন্য নিয়ে দিয়ে বলে বললেন না নেই আর কি কী কে যে সঙ্গে সাথে পর আগে মধ্যে
উপর ওপর বিষয়ে প্রতি গেল গেছে আজ the a an of in on to for and is are with by at
from as after over says said new""".split())
SUFFIXES = sorted(["দের", "েরা", "ের", "কে", "তে", "য়ের", "য়", "রা", "টি", "টা", "গুলো",
                   "সহ", "র", "ে", "'s", "s"], key=len, reverse=True)


def stem(tok):
    for s in SUFFIXES:
        if tok.endswith(s) and len(tok) - len(s) >= 2:
            return tok[: -len(s)]
    return tok


def tokens(text):
    text = re.sub(r"<[^>]+>", " ", text or "").lower()
    raw = re.findall(r"[\wঀ-৿']+", text)
    return {stem(t) for t in raw if len(t) > 1 and t not in STOP and not t.isdigit()}


def overlap(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / min(len(a), len(b)) if inter >= 2 else 0.0


def clean_title(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t or ""))
    return re.sub(r"\s+", " ", t).strip()


def ts(entry):
    p = entry.get("published_parsed") or entry.get("updated_parsed")
    return timegm(p) if p else NOW


def fetch(url, **kw):
    r = requests.get(url, headers=UA, timeout=25, **kw)
    r.raise_for_status()
    return r


# ---------------------------------------------------------------- collectors
def get_feed(name, url):
    try:
        f = feedparser.parse(fetch(url).content)
    except Exception as e:
        log(f"[skip] {name}: {e}")
        return []
    out = []
    via_gn = "news.google.com" in url
    for e in f.entries:
        title = clean_title(e.get("title"))
        t = ts(e)
        if not title or NOW - t > C.MAX_AGE_HOURS * 3600:
            continue
        it = {"source": name, "title": title, "link": e.get("link", ""), "ts": t}
        if via_gn:  # "Headline - Outlet" -> keep headline, record outlet
            m = re.match(r"(.*)\s[-–|]\s([^-–|]+)$", title)
            if m:
                it["title"] = m.group(1).strip()
                if name == "Google News":
                    o = m.group(2).strip()
                    it["outlet"] = C.OUTLET_ALIASES.get(o, o)
        if len(tokens(it["title"])) < 3 or JUNK.search(it["title"]):  # ePaper, bulletins...
            continue
        out.append(it)
    return out


def get_homepage(src, cache):
    """Sites without RSS: read article links off the homepage, then each
    article's title/date (cached in state so each page is fetched once)."""
    try:
        page = fetch(src["homepage"]).text
    except Exception as e:
        log(f"[skip] {src['name']}: {e}")
        return []
    base = src["homepage"].rstrip("/")
    paths = list(dict.fromkeys(re.findall(r'href="(%s[^"#?]+)"' % re.escape(src["pattern"]), page)))
    out, fetched = [], 0
    for p in paths[:30]:
        url = base + p
        meta = cache.get(url)
        if meta is None and fetched < 15:
            fetched += 1
            try:
                h = fetch(url).text
                title = re.search(r'og:title" content="([^"]+)', h)
                desc = re.search(r'og:description" content="([^"]+)', h)
                pub = re.search(r'(?:"datePublished":"|published_time" content=")([^"]+)', h)
                t = (timegm(time.strptime(pub.group(1)[:19], "%Y-%m-%dT%H:%M:%S"))
                     if pub else NOW)
                meta = cache[url] = {"title": clean_title(title.group(1)) if title else "",
                                     "desc": clean_title(desc.group(1))[:200] if desc else "",
                                     "ts": t}
            except Exception:
                continue
        if meta and meta["title"] and NOW - meta["ts"] <= C.MAX_AGE_HOURS * 3600:
            # description helps match English explainer headlines to Bangla news
            out.append({"source": src["name"], "title": meta["title"], "link": url,
                        "ts": meta["ts"], "extra": meta["desc"]})
    return out


def get_source(src, cache=None):
    if src.get("homepage"):
        return get_homepage(src, cache if cache is not None else {})
    if src.get("rss"):
        return get_feed(src["name"], src["rss"])
    lang = src.get("lang", "bn")
    ed = "hl=bn&gl=BD&ceid=BD:bn" if lang == "bn" else "hl=en-US&gl=US&ceid=US:en"
    return get_feed(src["name"],
                    f"https://news.google.com/rss/search?q=site:{src['site']}+when:1d&{ed}")


def get_google_news():
    return [it for url in C.GOOGLE_NEWS_FEEDS for it in get_feed("Google News", url)]


TIER = {s["name"]: s["tier"] for s in C.SOURCES + C.SOCIAL_PAGES}


def outlet(a):
    return a.get("outlet") or a["source"]


def tier_w(name):
    return C.TIER_WEIGHT[TIER.get(name, "OTHER")]


def parse_traffic(s):
    m = re.match(r"([\d,.]+)\s*([KkMm]?)", s or "")
    if not m:
        return 0
    n = float(m.group(1).replace(",", ""))
    return int(n * {"k": 1e3, "m": 1e6}.get(m.group(2).lower(), 1))


def get_trends():
    """Google Trends: Bangladesh plus GLOBAL_TRENDS_GEOS countries."""
    out = []
    for geo in ["BD"] + list(C.GLOBAL_TRENDS_GEOS):
        url = re.sub(r"geo=\w+", f"geo={geo}", C.GOOGLE_TRENDS_FEED)
        try:
            f = feedparser.parse(fetch(url).content)
        except Exception as e:
            log(f"[skip] trends {geo}: {e}")
            continue
        for e in f.entries:
            news_titles = e.get("ht_news_item_title", "")
            out.append({"term": e.get("title", "").strip(), "geo": geo,
                        "traffic": parse_traffic(e.get("ht_approx_traffic")),
                        "toks": tokens(e.get("title", "")) | tokens(news_titles),
                        "url": e.get("ht_news_item_url", ""),
                        "news_title": clean_title(news_titles),
                        "news_source": e.get("ht_news_item_source", "")})
    return out


def get_youtube():
    vids = []
    for h, cid in C.YOUTUBE_CHANNELS.items():
        try:
            f = feedparser.parse(fetch(
                f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}").content)
        except Exception as e:
            log(f"[skip] youtube {h}: {e}")
            continue
        for e in f.entries:
            t = ts(e)
            age_h = max((NOW - t) / 3600, 0.5)
            if age_h > C.MAX_AGE_HOURS:
                continue
            if JUNK.search(e.get("title", "")):
                continue
            views = int((e.get("media_statistics") or {}).get("views", 0) or 0)
            vids.append({"source": f"YouTube · {h}", "kind": "yt",
                         "title": clean_title(e.get("title")),
                         "link": e.get("link", ""), "ts": t, "views": views,
                         "vph": views / age_h})
    return vids


def parse_count(s):
    m = re.match(r"([\d.]+)\s*([KkMm]?)", (s or "").strip())
    return int(float(m.group(1)) * {"k": 1e3, "m": 1e6}.get(m.group(2).lower(), 1)) if m else 0


def get_telegram(name, channel):
    """Public Telegram channel web preview (t.me/s/...) incl. view counts."""
    try:
        page = fetch(f"https://t.me/s/{channel}").text
    except Exception as e:
        log(f"[skip] telegram {channel}: {e}")
        return []
    out = []
    for block in page.split("tgme_widget_message_wrap")[1:]:
        txt = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', block, re.S)
        tm = re.search(r'<time datetime="([^"]+)"', block)
        post = re.search(r'data-post="([^"]+)"', block)
        if not (txt and tm and post):
            continue
        t = time.mktime(time.strptime(tm.group(1)[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
        age_h = max((NOW - t) / 3600, 0.5)
        if age_h > C.MAX_AGE_HOURS:
            continue
        body = clean_title(txt.group(1).replace("<br/>", "\n").replace("<br>", "\n"))
        views = parse_count((re.search(r'tgme_widget_message_views">([^<]+)', block) or [None, ""])[1])
        out.append({"source": name, "kind": "tg", "title": body[:160],
                    "link": f"https://t.me/{post.group(1)}", "ts": t, "vph": views / age_h})
    return out


def get_facebook_page(name, page_id, token, edge="posts"):
    """Official Graph API. Works for pages you manage; other pages need
    Meta's (free) 'Page Public Content Access' approval on your app."""
    base = "message,created_time,permalink_url,shares"
    # richest field set first; fall back if a permission (e.g. comments) is missing
    for fields in (base + ",reactions.summary(total_count).limit(0),comments.summary(total_count).limit(0)",
                   base + ",reactions.summary(total_count).limit(0)",
                   base):
        try:
            r = requests.get(f"https://graph.facebook.com/v21.0/{page_id}/{edge}", timeout=25,
                             params={"fields": fields, "limit": 20, "access_token": token}).json()
        except Exception as e:
            log(f"[skip] facebook {name}: {e}")
            return []
        if r.get("error", {}).get("code") != 10:
            break
    if "error" in r:
        FB_ERR["code"] = r["error"].get("code")
        FB_ERR["msg"] = r["error"].get("message", "")[:120]
        if edge != "posts" or FB_ERR["code"] not in (10, 190):   # logged once by get_social
            log(f"[skip] facebook {name}: {FB_ERR['msg']}")
        return []
    posts = []
    for p in r.get("data", []):
        eng = (p.get("reactions", {}).get("summary", {}).get("total_count", 0)
               + p.get("comments", {}).get("summary", {}).get("total_count", 0)
               + 2 * (p.get("shares") or {}).get("count", 0))
        t = time.mktime(time.strptime(p["created_time"][:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
        posts.append((p, eng, t))
    engs = sorted(e for _, e, _ in posts)
    median = engs[len(engs) // 2] if engs else 0        # this Page's usual engagement
    out = []
    for p, eng, t in posts:
        msg = clean_title(p.get("message", ""))
        age_h = max((NOW - t) / 3600, 0.5)
        if not msg or age_h > C.MAX_AGE_HOURS:
            continue
        out.append({"source": name, "kind": "fb", "title": msg[:160], "eng": eng,
                    "page_median": median, "age_h": age_h,
                    "link": p.get("permalink_url", ""), "ts": t, "vph": eng / age_h})
    return out


def get_own_posts():
    """Your own Facebook Pages (see OWN_PAGES) via permanent page tokens in
    FB_PAGE_TOKENS="<page_id>:<token>,...". Used to flag stories you've
    already covered, not to score them."""
    tokens_by_id = dict(p.split(":", 1) for p in
                        os.environ.get("FB_PAGE_TOKENS", "").split(",") if ":" in p)
    out = []
    for name, pid in C.OWN_PAGES.items():
        tok = tokens_by_id.get(pid)
        if tok:
            for p in get_facebook_page(name, pid, tok, edge="published_posts"):
                p["own"] = True
                out.append(p)
            out += get_own_instagram(name, pid, tok)
    return out


def get_own_instagram(name, page_id, token):
    """Recent posts of the Instagram professional account linked to your Page."""
    g = "https://graph.facebook.com/v21.0"
    try:
        ig = requests.get(f"{g}/{page_id}", timeout=20, params={
            "fields": "instagram_business_account", "access_token": token}).json()
        ig_id = (ig.get("instagram_business_account") or {}).get("id")
        if not ig_id:
            return []
        r = requests.get(f"{g}/{ig_id}/media", timeout=20, params={
            "fields": "caption,timestamp,permalink,like_count,comments_count",
            "limit": 20, "access_token": token}).json()
    except Exception as e:
        log(f"[skip] instagram {name}: {e}")
        return []
    out = []
    for m in r.get("data", []):
        cap = clean_title(m.get("caption", ""))
        t = time.mktime(time.strptime(m["timestamp"][:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
        age_h = max((NOW - t) / 3600, 0.5)
        if not cap or age_h > C.MAX_AGE_HOURS:
            continue
        eng = m.get("like_count", 0) + m.get("comments_count", 0)
        out.append({"source": f"{name} (Instagram)", "kind": "ig", "own": True,
                    "title": cap[:160], "eng": eng, "link": m.get("permalink", ""),
                    "ts": t, "vph": eng / age_h})
    return out


def get_social():
    # any of our tokens works once Meta grants Page Public Content Access
    token = next((p.split(":", 1)[1] for p in os.environ.get("FB_PAGE_TOKENS", "").split(",")
                  if ":" in p), None) or os.environ.get("FB_PAGE_TOKEN")
    items, fb_blocked, fb_pages = [], False, 0
    for s in C.SOCIAL_PAGES:
        if s.get("tg"):
            items += get_telegram(s["name"], s["tg"])
        if s.get("fb") and token and not fb_blocked:
            got = get_facebook_page(s["name"], s["fb"], token)
            fb_pages += bool(got)
            items += got
            if not got and FB_ERR.get("code") in (10, 190):   # no approval yet / bad token
                fb_blocked = True
    n_fb = sum(1 for s in C.SOCIAL_PAGES if s.get("fb"))
    if fb_blocked and FB_ERR.get("code") == 190:
        log(f"[facebook] token problem, skipped {n_fb} media Pages: {FB_ERR.get('msg', '')[:80]}")
    elif fb_blocked:
        log(f"[facebook] {n_fb} media Pages waiting for Meta's Page Public Content Access approval")
    elif token:
        log(f"[facebook] read {fb_pages}/{n_fb} media Pages")
    return items


def fb_engagement(url, token):
    try:
        r = requests.get("https://graph.facebook.com/v21.0/",
                         params={"id": url, "fields": "engagement", "access_token": token},
                         timeout=20).json()
        e = r.get("engagement") or {}
        return sum(int(e.get(k, 0) or 0) for k in
                   ("reaction_count", "comment_count", "share_count", "comment_plugin_count"))
    except Exception:
        return 0


# ---------------------------------------------------------------- clustering
def cluster(articles, thresh=0.5):
    clusters = []
    for a in sorted(articles, key=lambda x: x["ts"]):
        a["toks"] = tokens(a["title"] + " " + a.get("extra", ""))
        best, best_s = None, 0.0
        for c in clusters:
            s = overlap(a["toks"], c["toks"])
            if s > best_s:
                best, best_s = c, s
        if best and best_s >= thresh:
            best["items"].append(a)
            best["toks"] |= a["toks"]
        else:
            clusters.append({"items": [a], "toks": set(a["toks"])})
    return clusters


def story_key(c):
    lead = max(c["items"], key=lambda a: len(a["toks"]))
    return hashlib.md5(" ".join(sorted(lead["toks"])).encode()).hexdigest()[:12]


# ---------------------------------------------------------------- scoring
def score(c, trends, videos, prev_cov):
    news = [a for a in c["items"] if a.get("kind") != "yt"]   # articles + FB/TG page posts
    outlets = {outlet(a) for a in news if a["source"] != "Google News" or a.get("outlet")}
    in_gnews = any(a["source"] == "Google News" for a in news)
    cov = len(outlets)
    wcov = sum(tier_w(o) for o in outlets)
    links = {a["link"] for a in c["items"]}

    alltext = " ".join(a["title"].lower() for a in news)
    matched = [t for t in trends
               if t["url"] in links or overlap(t["toks"], c["toks"]) >= 0.5
               or (len(t["term"]) > 3 and t["term"].lower() in alltext)]
    trend = max(matched, key=lambda t: t["traffic"], default=None)
    countries = sorted({t["geo"] for t in matched})
    def rate(kind):
        return sum(v["vph"] for v in videos if v["kind"] == kind and
                   (v in c["items"] or overlap(v["toks"], c["toks"]) >= 0.5))
    yt_vph, tg_vph, fb_eph = rate("yt"), rate("tg"), rate("fb")
    text = " ".join(a["title"].lower() for a in c["items"])
    kw = any(k.lower() in text for k in C.VIRAL_KEYWORDS)

    parts = {
        "coverage": C.W_COVERAGE * math.log2(1 + wcov),
        "gnews": C.W_GNEWS if in_gnews else 0,
        "trend": C.W_TREND * math.log10(max(trend["traffic"], 10)) if trend else 0,
        "countries": min(C.TREND_COUNTRIES_CAP, C.W_TREND_COUNTRIES * max(0, len(countries) - 1)),
        "youtube": C.W_YT * math.log10(1 + yt_vph),
        "telegram": C.W_TG * math.log10(1 + tg_vph),
        "fb_pages": C.W_FB_PAGES * math.log10(1 + fb_eph),
        "growth": min(C.GROWTH_CAP, C.W_GROWTH * max(0, cov - prev_cov.get(story_key(c), cov))),
        "keyword": C.W_KEYWORD if kw else 0,
        "fb": 0.0,
    }
    tiers = {TIER.get(o) for o in outlets}
    n_int = sum(1 for o in outlets if TIER.get(o) == "INT")
    n_bd = sum(1 for o in outlets if TIER.get(o) in ("S", "A", "B"))
    # international = mostly covered by world outlets / trending outside BD
    intl = (n_int > 0 and n_int >= n_bd) or (n_bd == 0 and any(g != "BD" for g in countries))
    c.update(cov=cov, tiers="/".join(t for t in ("S", "A", "B", "INT") if t in tiers),
             intl=intl, countries=countries,
             in_gnews=in_gnews, trend=trend, yt_vph=yt_vph, tg_vph=tg_vph, fb_eph=fb_eph,
             parts=parts,
             fresh=0.5 ** (max(0, NOW - max(a["ts"] for a in c["items"])) / 3600 / C.HALF_LIFE_H))
    finalize(c)


def finalize(c):
    raw = sum(c["parts"].values()) * c["fresh"]
    c["score"] = round(10 * (1 - math.exp(-raw / C.SCALE)), 2)


# ---------------------------------------------------------------- telegram
def pick_link(c):
    # prefer a direct link from the highest-tier outlet
    news = [a for a in c["items"] if not a.get("kind")] or c["items"]
    news.sort(key=lambda a: ("news.google.com" in a["link"], -tier_w(outlet(a)), len(a["link"])))
    return news[0]


def fmt_num(n):
    return f"{n/1e6:.1f}M" if n >= 1e6 else f"{n/1e3:.1f}K" if n >= 1e3 else str(int(n))


def render(c):
    lead = pick_link(c)
    e = html.escape
    sig = [f"📰 {c['cov']} outlets" + (f" (tier {c['tiers']})" if c["tiers"] else "")]
    if c["in_gnews"]:
        sig.append("🔝 Google News")
    if c["trend"]:
        where = ", ".join(c["countries"])
        sig.append(f"📈 Trending “{e(c['trend']['term'])}” {fmt_num(c['trend']['traffic'])}+ searches"
                   f" ({where})")
    if c["yt_vph"] >= 1:
        sig.append(f"▶️ {fmt_num(c['yt_vph'])} YouTube views/hr")
    if c["tg_vph"] >= 1:
        sig.append(f"✈️ {fmt_num(c['tg_vph'])} Telegram views/hr")
    if c["fb_eph"] >= 1:
        sig.append(f"💬 {fmt_num(c['fb_eph'])} FB page engagements/hr")
    for p in c.get("own", [])[:2]:
        sig.append(f"✅ Already on {e(p['source'])} ({fmt_num(p.get('eng', 0))} engagements)")
    if c.get("fb_eng"):
        sig.append(f"👍 {fmt_num(c['fb_eng'])} FB engagements")
    seen, others = {lead.get("outlet") or lead["source"]}, []
    for a in sorted(c["items"], key=lambda a: "news.google.com" in a["link"]):
        name = a.get("outlet") or a["source"]
        if name not in seen and len(others) < 4:
            seen.add(name)
            others.append(a)
    more = "\n".join(f"• <a href=\"{e(a['link'])}\">{e(a.get('outlet') or a['source'])}</a>"
                     for a in others)
    lane = "🌍 International" if c.get("intl") else "🇧🇩 Bangladesh"
    return (f"🔥 <b>Viral score: {c['score']:.2f}/10</b> · {lane}\n\n"
            f"<b>{e(lead['title'])}</b>\n\n" + " · ".join(sig) + "\n\n"
            f"{e(lead['link'])}" + (f"\n\nAlso covered by:\n{more}" if more else ""))


# ---------------------------------------------------------------- viral topics
# Things people are buzzing about that newspapers haven't (fully) covered yet:
# trending searches, Wikipedia spikes and fast-rising videos.
WIKI_SKIP = re.compile(r"^(Deaths_in|List_of|Main_Page|প্রধান_পাতা|\d{4}$|\d{4}_in_)|:|"
                       r"porn|xxx|sex|যৌন|xvideos|onlyfans", re.I)


def squash(raw):
    return round(10 * (1 - math.exp(-raw / C.SCALE)), 2)


def wiki_top(project, day):
    u = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{project}/all-access/"
         f"{day:%Y/%m/%d}")
    r = requests.get(u, timeout=25, headers={"User-Agent": "ViralNewsScout/1.0 (news trend bot)"})
    r.raise_for_status()
    return {a["article"]: a["views"] for a in r.json()["items"][0]["articles"]}


def get_wiki_spikes(state):
    """Pages whose daily Wikipedia readership jumped. Computed once a day."""
    import datetime as dt
    cache = state.get("wiki", {})
    yesterday = dt.date.today() - dt.timedelta(days=1)
    if cache.get("date") == str(yesterday):
        return cache["items"]
    items, ok, day = [], False, yesterday
    for proj, lang, min_views in (("bn.wikipedia", "bn", C.WIKI_MIN_VIEWS_BN),
                                  ("en.wikipedia", "en", C.WIKI_MIN_VIEWS_EN)):
        today = None
        for d in (yesterday, yesterday - dt.timedelta(days=1)):   # yesterday may not be published yet
            try:
                today, before, day = wiki_top(proj, d), wiki_top(proj, d - dt.timedelta(days=1)), d
                break
            except Exception:
                continue
        if today is None:
            log(f"[skip] wikipedia {lang}: no recent data yet")
            continue
        ok = ok or day == yesterday
        floor = min(before.values()) if before else 1
        for art, views in list(today.items())[:200]:
            if views < min_views or WIKI_SKIP.search(art):
                continue
            ratio = views / before.get(art, floor)
            if ratio >= C.WIKI_MIN_SPIKE:
                items.append({"title": art.replace("_", " "), "views": views,
                              "ratio": round(min(ratio, 10), 1), "lang": lang,
                              "link": f"https://{lang}.wikipedia.org/wiki/{art}"})
    if ok:   # cache only once yesterday's data is out; otherwise retry next scan
        state["wiki"] = {"date": str(yesterday), "items": items}
    return items


def find_viral_topics(trends, videos, clusters, state):
    covered = [c for c in clusters if c["cov"] >= 2]

    def is_covered(toks, text=""):
        return any(overlap(toks, c["toks"]) >= 0.5 or
                   (len(text) > 3 and text.lower() in " ".join(a["title"].lower() for a in c["items"]))
                   for c in covered)

    topics = []
    # 1) trending searches with little/no news coverage yet
    by_term = {}
    for t in trends:
        term = t["term"].strip()
        if not term or C.TREND_SKIP and re.search(C.TREND_SKIP, term, re.I):
            continue
        g = by_term.setdefault(term.lower(), {**t, "geos": set(), "traffic": 0})
        g["geos"].add(t["geo"])
        g["traffic"] = max(g["traffic"], t["traffic"])
    for g in by_term.values():
        if is_covered(g["toks"], g["term"]):
            continue
        raw = 2 * math.log10(max(g["traffic"], 10)) + 0.8 * (len(g["geos"]) - 1)
        topics.append({"kind": "trend", "title": g["term"], "score": squash(raw),
                       "toks": tokens(g["term"]) | tokens(g.get("news_title", "")),
                       "geos": sorted(g["geos"]), "traffic": g["traffic"],
                       "link": g.get("url", ""), "news_title": g.get("news_title", ""),
                       "news_source": g.get("news_source", "")})
    # 2) Wikipedia readership spikes
    for w in get_wiki_spikes(state):
        toks = tokens(w["title"])
        if is_covered(toks):
            continue
        if w["lang"] == "en":   # global page: needs a regional signal to be relevant
            regional = any(t["geo"] not in ("US", "GB") and overlap(toks, t["toks"]) >= 0.5
                           for t in trends) or any(
                overlap(toks, c["toks"]) >= 0.5 and
                any(TIER.get(outlet(a)) in ("S", "A", "B") for a in c["items"])
                for c in clusters)
            if not regional:
                continue
        raw = 1.5 * math.log10(w["views"]) + 1.5 * math.log2(w["ratio"])
        topics.append({"kind": "wiki", "title": w["title"], "score": squash(raw),
                       "toks": toks, **{k: w[k] for k in ("views", "ratio", "lang", "link")}})
    # 3) fast-rising videos not tied to a covered story
    for v in videos:
        if v["kind"] != "yt" or v["vph"] < C.VIRAL_VIDEO_MIN_VPH or is_covered(v["toks"]):
            continue
        topics.append({"kind": "video", "title": v["title"], "score": squash(2 * math.log10(v["vph"])),
                       "toks": v["toks"], "vph": v["vph"], "views": v.get("views", 0),
                       "link": v["link"], "source": v["source"]})
    # 4) Facebook posts from media Pages doing far better than that Page's usual
    for v in videos:
        if v["kind"] != "fb" or v.get("own") or v.get("age_h", 99) > C.FB_VIRAL_MAX_AGE:
            continue
        ratio = v["eng"] / max(v.get("page_median", 0), 1)
        if v["eng"] < C.FB_VIRAL_MIN_ENG or ratio < C.FB_VIRAL_MULT:
            continue
        raw = 1.5 * math.log10(v["eng"]) + 2 * math.log2(min(ratio, 16))
        topics.append({"kind": "fb", "title": v["title"], "score": squash(raw),
                       "toks": v["toks"], "eng": v["eng"], "ratio": round(ratio, 1),
                       "age_h": v["age_h"], "link": v["link"], "source": v["source"]})
    topics.sort(key=lambda t: t["score"], reverse=True)
    return topics


def topic_key(t):
    return "vt:" + hashlib.md5(t["title"].lower().encode()).hexdigest()[:12]


def render_topic(t):
    e = html.escape
    head = {"trend": "📈 Trending search", "wiki": "📚 Wikipedia spike",
            "video": "▶️ Viral video", "fb": "📘 Viral Facebook post"}[t["kind"]]
    lines = [f"🔥 <b>Viral score: {t['score']:.2f}/10</b> · 🔥 Viral Topic · {head}", "",
             f"<b>{e(t['title'])}</b>", ""]
    if t["kind"] == "trend":
        lines.append(f"🔎 {fmt_num(t['traffic'])}+ searches · trending in {', '.join(t['geos'])}")
        if t["news_title"]:
            lines.append(f"📰 Related: {e(t['news_title'])}"
                         + (f" ({e(t['news_source'])})" if t["news_source"] else ""))
    elif t["kind"] == "wiki":
        lines.append(f"👀 {fmt_num(t['views'])} reads yesterday on "
                     f"{'Bangla' if t['lang'] == 'bn' else 'English'} Wikipedia · ↑{t['ratio']}× vs day before")
    elif t["kind"] == "fb":
        lines.append(f"📘 {e(t['source'])} · {fmt_num(t['eng'])} reactions+comments+shares "
                     f"in {t['age_h']:.0f}h · {t['ratio']}× this Page's usual")
    else:
        lines.append(f"▶️ {fmt_num(t['vph'])} views/hr · {fmt_num(t['views'])} total · {e(t['source'])}")
    if t["kind"] != "fb":
        lines.append("💡 Little or no news coverage yet: chance to cover it first")
    if t.get("link"):
        lines += ["", e(t["link"])]
    return "\n".join(lines)


def send(text, chat=None):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), chat or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (or use --dry-run).")
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=25, json={
        "chat_id": chat, "text": text, "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": False, "prefer_large_media": True}})
    if not r.ok:
        log("[telegram]", r.status_code, r.text[:300])
    return r.ok


# ---------------------------------------------------------------- main
def load_state():
    try:
        return json.load(open(STATE_FILE, encoding="utf-8"))
    except Exception:
        return {}


def save_state(s):
    json.dump(s, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def run(dry=False, top=15):
    global NOW
    NOW = time.time()
    state = load_state()
    posted = {k: v for k, v in state.get("posted", {}).items()
              if NOW - v["at"] < C.REPOST_GAP_HOURS * 3600}

    with ThreadPoolExecutor(8) as ex:
        page_cache = state.setdefault("page_cache", {})
        news_jobs = [ex.submit(get_source, s, page_cache) for s in C.SOURCES]
        gn_job, tr_job = ex.submit(get_google_news), ex.submit(get_trends)
        yt_job, so_job = ex.submit(get_youtube), ex.submit(get_social)
        own_job = ex.submit(get_own_posts)
        articles = [a for j in news_jobs for a in j.result()] + gn_job.result()
        trends, social = tr_job.result(), so_job.result()
        videos = yt_job.result() + social
        own = own_job.result()
    for v in videos + own:
        v["toks"] = tokens(v["title"])
    n = lambda k: sum(1 for v in videos if v["kind"] == k)
    log(f"collected {len(articles)} articles, {len(trends)} trends, {n('yt')} YouTube videos, "
        f"{n('tg')} Telegram posts, {n('fb')} Facebook page posts, {len(own)} own-page posts")

    # page posts always join clustering (they are "outlets" too); videos only when hot
    hot = [v for v in videos if v["kind"] != "yt" or v["vph"] >= 200]
    clusters = cluster(articles + hot)
    prev_cov = state.get("coverage", {})
    for c in clusters:
        score(c, trends, videos, prev_cov)
        c["own"] = [p for p in own if overlap(p["toks"], c["toks"]) >= 0.5]
    clusters.sort(key=lambda c: c["score"], reverse=True)

    fb_id, fb_secret = os.environ.get("FB_APP_ID"), os.environ.get("FB_APP_SECRET")
    if fb_id and fb_secret:
        tok = f"{fb_id}|{fb_secret}"
        for c in clusters[: C.FB_CHECK_TOP_N]:
            c["fb_eng"] = sum(fb_engagement(a["link"], tok) for a in c["items"][:4]
                              if "news.google.com" not in a["link"])
            c["parts"]["fb"] = C.W_FB * math.log10(1 + c["fb_eng"])
            finalize(c)
        clusters.sort(key=lambda c: c["score"], reverse=True)

    def already(c):
        if story_key(c) in posted:
            return True
        # topic-level dedup: skip near-same angles of a story already posted
        return any(overlap(c["toks"], set(p["toks"])) >= C.DEDUP_OVERLAP for p in posted.values())

    for lane_intl in (False, True):
        lane = [c for c in clusters if c["intl"] == lane_intl]
        log(f"--- {'International' if lane_intl else 'Bangladesh'} top ---")
        for i, c in enumerate(lane[:top], 1):
            p = {k: round(v, 1) for k, v in c["parts"].items() if v}
            log(f"{i:2}. {c['score']:5.2f} {'(posted) ' if already(c) else ''}"
                f"{pick_link(c)['title'][:70]}  {p}")

    sent = {False: 0, True: 0}
    limit = {False: (C.MAX_POSTS_PER_RUN, C.MIN_SCORE),
             True: (C.INTL_MAX_POSTS_PER_RUN, C.INTL_MIN_SCORE)}
    for c in clusters:
        cap, floor = limit[c["intl"]]
        if sent[c["intl"]] >= cap or c["score"] < floor or already(c):
            continue
        if dry:
            print(render(c), "\n" + "-" * 60)
        elif not send(render(c)):
            continue
        posted[story_key(c)] = {"at": NOW, "toks": sorted(c["toks"]), "score": c["score"]}
        sent[c["intl"]] += 1
    log(f"{'would post' if dry else 'posted'} {sent[False]} Bangladesh + {sent[True]} international")

    # viral topics lane
    topics = find_viral_topics(trends, videos, clusters, state)
    log("--- Viral topics top ---")
    for i, t in enumerate(topics[:10], 1):
        log(f"{i:2}. {t['score']:5.2f} [{t['kind']}] {t['title'][:70]}")
    vsent = 0
    for t in topics:
        if vsent >= C.VIRAL_MAX_POSTS_PER_RUN or t["score"] < C.VIRAL_MIN_SCORE:
            break
        if topic_key(t) in posted or any(overlap(t["toks"], set(p["toks"])) >= 0.6
                                         for p in posted.values()):
            continue
        if dry:
            print(render_topic(t), "\n" + "-" * 60)
        elif not send(render_topic(t)):
            continue
        posted[topic_key(t)] = {"at": NOW, "toks": sorted(t["toks"]), "score": t["score"]}
        vsent += 1
    log(f"{'would post' if dry else 'posted'} {vsent} viral topics")

    # 🇺🇸 US video ideas (separate Telegram chat)
    try:
        import us_scout
        us_scout.run(sys.modules[__name__], state, trends, get_wiki_spikes(state), dry)
    except Exception as e:
        log(f"[us] error: {e}")

    state["coverage"] = {story_key(c): c["cov"] for c in clusters if c["cov"] > 1}
    state["page_cache"] = {u: m for u, m in page_cache.items()      # keep 3 days
                           if NOW - m["ts"] < 3 * 86400}
    if not dry:
        state["posted"] = posted
    save_state(state)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", type=int, metavar="MINUTES")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.loop:
        while True:
            try:
                run(a.dry_run)
            except Exception as e:
                log("[error]", e)
            time.sleep(a.loop * 60)
    else:
        run(a.dry_run)
