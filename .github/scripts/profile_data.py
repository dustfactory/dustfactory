"""Collect PUBLIC profile data for the dashboard cards.
Usage: GITHUB_TOKEN=... python profile_data.py <user> <out.json>"""
import json, os, re, sys, urllib.request, datetime as dt
from collections import Counter, OrderedDict

FEATURED = ["meonji-jump", "MEONJI-Brand", "agent-harness"]

def gql(q, v):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": v}).encode(),
        headers={"Authorization": "bearer " + os.environ["GITHUB_TOKEN"], "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=60))
    if "errors" in r: raise SystemExit(r["errors"])
    return r["data"]

Q = """query($u:String!){user(login:$u){
 repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false, orderBy:{field:PUSHED_AT,direction:DESC}){
  totalCount nodes{name description stargazerCount pushedAt url homepageUrl primaryLanguage{name}
   languages(first:10, orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}
 contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""

def main(user, out):
    u = gql(Q, {"u": user})["user"]
    repos = u["repositories"]["nodes"]
    days = [d for w in u["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    total = u["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    # streaks (today may still be 0 -> don't break current streak on it)
    cur = 0
    for i, d in enumerate(reversed(days)):
        if d["contributionCount"] > 0: cur += 1
        elif i == 0: continue
        else: break
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        longest = max(longest, run)
    months = OrderedDict()
    for d in days:
        months.setdefault(d["date"][:7], 0); months[d["date"][:7]] += d["contributionCount"]
    months = list(months.items())[-12:]
    weeks = [sum(x["contributionCount"] for x in w["contributionDays"]) for w in u["contributionsCollection"]["contributionCalendar"]["weeks"]]
    active_days = sum(1 for d in days if d["contributionCount"] > 0)
    lang = Counter()
    for r in repos:
        for e in r["languages"]["edges"]:
            lang[e["node"]["name"]] += e["size"]
    tot = sum(lang.values()) or 1
    top = lang.most_common(5)
    langs = [{"name": n, "pct": round(s * 100 / tot, 1)} for n, s in top]
    other = round(100 - sum(l["pct"] for l in langs), 1)
    if other > 0.05: langs.append({"name": "Other", "pct": other})
    byname = {r["name"]: r for r in repos}
    featured = []
    for n in FEATURED:
        r = byname.get(n)
        if r:
            featured.append({"name": n, "stars": r["stargazerCount"], "language": (r["primaryLanguage"] or {}).get("name"),
                             "pushed": r["pushedAt"][:10], "url": r["url"], "homepage": r["homepageUrl"]})
    journal = []
    jr = os.path.join(os.path.dirname(__file__), "..", "..", "journal", "README.md")
    if os.path.exists(jr):
        for m in re.finditer(r"^\|\s*\[(\d{4}-\d{2}-\d{2})\]\(([^)]+)\)\s*\|\s*(.+?)\s*\|\s*$", open(jr, encoding="utf-8").read(), re.M):
            journal.append({"date": m.group(1), "title": m.group(3)})
    journal.sort(key=lambda j: j["date"], reverse=True)
    data = {"generated": dt.date.today().isoformat(), "public_repos": u["repositories"]["totalCount"],
            "stars": sum(r["stargazerCount"] for r in repos), "contributions_year": total,
            "active_days": active_days, "current_streak": cur, "longest_streak": longest,
            "months": [{"month": k, "count": v} for k, v in months], "weeks": weeks,
            "languages": langs, "featured": featured, "journal": journal[:3]}
    json.dump(data, open(out, "w"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
