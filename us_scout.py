"""🇺🇸 US Viral lane: video topic ideas for a US-audience YouTube channel.

Finds what Americans are watching and searching right now:
  - YouTube videos from big US channels growing much faster than usual
  - Google Trends (US) searches
  - English Wikipedia readership spikes
Signals about the same topic are merged into one idea, scored 0-10 and sent
to a separate Telegram chat (TELEGRAM_US_CHAT_ID).
"""
import html, math, os, re, time
from concurrent.futures import ThreadPoolExecutor

import feedparser

import config as C


def _yt_channel(bot, name, cid):
    try:
        f = feedparser.parse(bot.fetch(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}").content)
    except Exception as e:
        bot.log(f"[skip] us youtube {name}: {e}")
        return []
    vids = []
    for e in f.entries:
        title = e.get("title", "")
        words = re.findall(r"[A-Za-z]{4,}", title)          # real words, not emoji/filler
        if bot.JUNK.search(title) or re.search(C.US_SKIP, title, re.I) \
                or len(words) < C.US_MIN_TITLE_WORDS:
            continue
        t = bot.ts(e)
        views = int((e.get("media_statistics") or {}).get("views", 0) or 0)
        vids.append({"title": bot.clean_title(e.get("title")), "link": e.get("link", ""),
                     "ts": t, "views": views, "age_h": max((bot.NOW - t) / 3600, 0.5)})
    if not vids:
        return []
    usual = sorted(v["views"] for v in vids)[len(vids) // 2] or 1     # channel's median views
    out = []
    for v in vids:
        if v["age_h"] > C.US_MAX_AGE_HOURS:
            continue
        v["vph"] = v["views"] / v["age_h"]
        v["ratio"] = v["views"] / usual                 # vs this channel's typical video
        v["speed"] = v["ratio"] / max(v["age_h"] / 24, 0.25)   # "usual videos per day" pace
        v["channel"] = name
        out.append(v)
    return out


def collect(bot, trends, wiki):
    with ThreadPoolExecutor(8) as ex:
        vids = [v for vs in ex.map(lambda kv: _yt_channel(bot, *kv), C.US_YOUTUBE_CHANNELS.items())
                for v in vs]
    signals = []
    for v in vids:
        if v["vph"] < C.US_MIN_VPH or v["speed"] < C.US_MIN_SPEED:
            continue
        raw = 1.4 * math.log10(v["vph"]) + 1.8 * math.log2(1 + min(v["speed"], 30))
        signals.append({"kind": "yt", "title": v["title"], "toks": bot.tokens(v["title"]),
                        "raw": raw, "link": v["link"], "data": v})
    us_terms = {}
    for t in trends:
        if t["geo"] != "US" or t["traffic"] < C.US_MIN_SEARCHES or re.search(C.TREND_SKIP, t["term"], re.I):
            continue
        us_terms.setdefault(t["term"].lower(), t)
    for t in us_terms.values():
        signals.append({"kind": "trend", "title": t["term"], "toks": t["toks"],
                        "raw": 2 * math.log10(t["traffic"]), "link": t.get("url", ""), "data": t})
    for w in wiki:
        if w["lang"] != "en":
            continue
        raw = 1.5 * math.log10(w["views"]) + 1.5 * math.log2(w["ratio"])
        signals.append({"kind": "wiki", "title": w["title"], "toks": bot.tokens(w["title"]),
                        "raw": raw, "link": w["link"], "data": w})
    log_counts = {k: sum(1 for s in signals if s["kind"] == k) for k in ("yt", "trend", "wiki")}
    bot.log(f"[us] {len(vids)} recent US videos · viral signals: {log_counts}")
    return merge(bot, signals)


def merge(bot, signals):
    """Group signals about the same topic; more independent signals = stronger idea."""
    ideas = []
    for s in sorted(signals, key=lambda s: s["raw"], reverse=True):
        for idea in ideas:
            if bot.overlap(s["toks"], idea["toks"]) >= 0.5:
                idea["signals"].append(s)
                idea["toks"] |= s["toks"]
                break
        else:
            ideas.append({"signals": [s], "toks": set(s["toks"])})
    for idea in ideas:
        kinds = {s["kind"] for s in idea["signals"]}
        raw = max(s["raw"] for s in idea["signals"]) + 1.2 * (len(kinds) - 1)
        idea["score"] = bot.squash(raw)
        lead = idea["signals"][0]
        idea["title"], idea["link"] = lead["title"], lead["link"]
    ideas.sort(key=lambda i: i["score"], reverse=True)
    return ideas


def render(bot, idea):
    e, f = html.escape, bot.fmt_num
    lines = [f"🇺🇸 <b>Video idea · Viral score {idea['score']:.2f}/10</b>", "",
             f"<b>{e(idea['title'])}</b>", ""]
    for s in idea["signals"][:4]:
        d = s["data"]
        if s["kind"] == "yt":
            lines.append(f"▶️ {f(d['views'])} views in {d['age_h']:.0f}h ({f(d['vph'])}/hr) · "
                         f"{d['ratio']:.1f}× {e(d['channel'])}'s usual video")
        elif s["kind"] == "trend":
            lines.append(f"📈 Google US: “{e(d['term'])}” {f(d['traffic'])}+ searches"
                         + (f" · {e(d['news_title'][:80])}" if d.get("news_title") else ""))
        else:
            lines.append(f"📚 Wikipedia: {f(d['views'])} reads yesterday · ↑{d['ratio']}×")
    n = len({s['kind'] for s in idea["signals"]})
    if n > 1:
        lines.append(f"✅ Confirmed by {n} independent signals")
    if idea.get("link"):
        lines += ["", e(idea["link"])]
    return "\n".join(lines)


def run(bot, state, trends, wiki, dry=False):
    chat = os.environ.get("TELEGRAM_US_CHAT_ID") or getattr(C, "US_CHAT_ID", "")
    if not chat and not dry:
        return
    ideas = collect(bot, trends, wiki)
    posted = {k: v for k, v in state.get("us_posted", {}).items()
              if bot.NOW - v["at"] < C.REPOST_GAP_HOURS * 3600}
    bot.log("--- 🇺🇸 US video ideas top ---")
    for i, idea in enumerate(ideas[:10], 1):
        kinds = "+".join(sorted({s["kind"] for s in idea["signals"]}))
        bot.log(f"{i:2}. {idea['score']:5.2f} [{kinds}] {idea['title'][:70]}")
    sent = 0
    for idea in ideas:
        if sent >= C.US_MAX_POSTS_PER_RUN or idea["score"] < C.US_MIN_SCORE:
            break
        key = "us:" + bot.hashlib.md5(idea["title"].lower().encode()).hexdigest()[:12]
        if key in posted or any(bot.overlap(idea["toks"], set(p["toks"])) >= 0.5 for p in posted.values()):
            continue
        text = render(bot, idea)
        if dry:
            print(text, "\n" + "-" * 60)
        elif not bot.send(text, chat):
            continue
        posted[key] = {"at": bot.NOW, "toks": sorted(idea["toks"]), "score": idea["score"]}
        sent += 1
    bot.log(f"{'would post' if dry else 'posted'} {sent} US video ideas")
    if not dry:
        state["us_posted"] = posted
