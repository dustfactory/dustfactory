"""Contribution grid with the meonji cat walking across and tidying up the cells.
Usage: GITHUB_TOKEN=... python cat_grid.py <user> <outdir>   (or --demo <outdir>)"""
import json, os, sys, random, urllib.request

CAT_D = open(os.path.join(os.path.dirname(__file__), "cat_path.txt")).read().strip()
# symbol bbox in its own coords (path is translated by 414.0039,381.4531 in the source svg)
CAT_TX, CAT_TY = 414.00390625, 381.453125
BX0, BY0, BW, BH = 236.5, 371.0, 783.5, 586.6

THEMES = {
    "light": dict(bg="none", fg="#111111", levels=["#ebebe8", "#c8c8c4", "#9a9a96", "#5c5c5a", "#111111"]),
    "dark": dict(bg="none", fg="#f0f0f0", levels=["#121720", "#34383e", "#626569", "#a3a5a8", "#f0f0f0"]),
}
LV = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

def fetch(user, token):
    q = 'query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{weeks{contributionDays{contributionLevel weekday}}}}}}'
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"u": user}}).encode(),
        headers={"Authorization": "bearer " + token, "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [[(dd["weekday"], LV[dd["contributionLevel"]]) for dd in w["contributionDays"]] for w in weeks]

def demo():
    random.seed(1)
    return [[(d, random.choice([0, 0, 0, 1, 2, 3, 4])) for d in range(7)] for _ in range(53)]

def build(weeks, theme):
    t = THEMES[theme]
    C, G = 12, 3                      # cell size, gap
    PX, TOP = 8, 30                   # padding, lane for the cat above the grid
    n = len(weeks)
    W = PX * 2 + n * (C + G) - G
    H = TOP + 7 * (C + G) - G + 10
    DUR = 24.0                        # seconds per loop
    WALK = 0.80                       # fraction of loop spent walking; rest = pause then reset
    catw = 26.0
    sc = catw / BW
    cath = BH * sc
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    css = [".c{shape-rendering:geometricPrecision}",
           f"@keyframes walk{{0%{{transform:translateX({PX - catw - 4:.1f}px)}}{WALK*100:.1f}%{{transform:translateX({W - PX + 4:.1f}px)}}100%{{transform:translateX({W - PX + 4:.1f}px)}}}}",
           "@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-2.5px)}}",
           f"#cat{{animation:walk {DUR}s linear infinite}}#bob{{animation:bob .36s ease-in-out infinite}}"]
    cells = []
    for i, w in enumerate(weeks):
        x = PX + i * (C + G)
        # time (fraction) when the cat's front reaches this column
        travel = (x + C / 2 - (PX - catw - 4) - catw * 0.6) / ((W - PX + 4) - (PX - catw - 4))
        p = max(0.0, min(WALK, travel * WALK)) * 100
        p2 = min(p + 1.2, 99.0)
        css.append(f"@keyframes k{i}{{0%,{p:.2f}%{{opacity:1;transform:scale(1)}}{p2:.2f}%,97%{{opacity:0;transform:scale(.3)}}100%{{opacity:1;transform:scale(1)}}}}"
                   f".w{i}{{animation:k{i} {DUR}s linear infinite;transform-box:fill-box;transform-origin:center}}")
        for wd, lv in w:
            y = TOP + wd * (C + G)
            base = f'<rect x="{x}" y="{y}" width="{C}" height="{C}" rx="2.5" fill="{t["levels"][0]}"/>'
            cells.append(base)
            if lv:
                cells.append(f'<rect class="w{i}" x="{x}" y="{y}" width="{C}" height="{C}" rx="2.5" fill="{t["levels"][lv]}"/>')
    out.append("<style>" + "".join(css) + "@media (prefers-reduced-motion:reduce){#cat,#bob,[class^=w]{animation:none}}</style>")
    out += cells
    cy = TOP - 3 - cath
    out.append(f'<g id="cat"><g transform="translate(0,{cy:.2f})"><g id="bob">'
               f'<path fill="{t["fg"]}" transform="scale({sc:.5f}) translate({-BX0 + CAT_TX:.3f},{-BY0 + CAT_TY:.3f})" d="{CAT_D}"/>'
               f'</g></g></g>')
    out.append("</svg>")
    return "\n".join(out)

if __name__ == "__main__":
    if sys.argv[1] == "--demo":
        weeks, outdir = demo(), sys.argv[2]
    else:
        weeks, outdir = fetch(sys.argv[1], os.environ["GITHUB_TOKEN"]), sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    for th in THEMES:
        open(os.path.join(outdir, f"cat-{th}.svg"), "w").write(build(weeks, th))
