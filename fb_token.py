"""Turn a short-lived Graph API Explorer token into PERMANENT Page tokens.

Reads FB_APP_ID, FB_APP_SECRET, FB_SHORT_TOKEN from .env, then:
  short user token -> 60-day user token -> page tokens (never expire)
Writes them to .env as FB_PAGE_TOKENS=<page_id>:<token>,... and clears
FB_SHORT_TOKEN. Prints only page names, never the tokens.
"""
import os, re, sys
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(HERE, ".env")
G = "https://graph.facebook.com/v21.0"

lines = open(ENV, encoding="utf-8-sig").read().splitlines()
env = {l.split("=", 1)[0].strip(): l.split("=", 1)[1].strip().strip('"')
       for l in lines if "=" in l and not l.lstrip().startswith("#")}
app_id, secret, short = env.get("FB_APP_ID"), env.get("FB_APP_SECRET"), env.get("FB_SHORT_TOKEN")
missing = [k for k, v in (("FB_APP_ID", app_id), ("FB_APP_SECRET", secret), ("FB_SHORT_TOKEN", short)) if not v]
if missing:
    sys.exit("Missing in .env: " + ", ".join(missing))

r = requests.get(f"{G}/oauth/access_token", timeout=30, params={
    "grant_type": "fb_exchange_token", "client_id": app_id,
    "client_secret": secret, "fb_exchange_token": short}).json()
if "access_token" not in r:
    sys.exit("Exchange failed: " + r.get("error", {}).get("message", str(r))[:200])
long_user = r["access_token"]

pages = requests.get(f"{G}/me/accounts", timeout=30, params={
    "fields": "id,name,access_token", "limit": 100, "access_token": long_user}).json()
if "error" in pages:
    sys.exit("Could not list pages: " + pages["error"].get("message", "")[:200])
data = pages.get("data", [])
if not data:
    sys.exit("No Pages found. Did you tick your Pages in the Facebook pop-up?")

value = ",".join(f"{p['id']}:{p['access_token']}" for p in data)
names = ",".join(f"{p['id']}:{p['name']}" for p in data)
out, seen = [], set()
for l in lines:
    k = l.split("=", 1)[0].strip()
    if k == "FB_SHORT_TOKEN":
        l = "FB_SHORT_TOKEN="
    elif k == "FB_PAGE_TOKENS":
        l = f"FB_PAGE_TOKENS={value}"
    elif k == "FB_PAGE_NAMES":
        l = f"FB_PAGE_NAMES={names}"
    seen.add(k)
    out.append(l)
if "FB_PAGE_TOKENS" not in seen:
    out.append(f"FB_PAGE_TOKENS={value}")
if "FB_PAGE_NAMES" not in seen:
    out.append(f"FB_PAGE_NAMES={names}")
open(ENV, "w", encoding="utf-8").write("\n".join(out) + "\n")

print(f"OK: permanent tokens saved for {len(data)} page(s):")
for p in data:
    print("  -", p["name"])
