"""Render brand-styled dashboard cards (light + dark SVG) from profile data JSON.
Usage: python render_cards.py <data.json> <icons_dir> <outdir>"""
import json, os, sys, math
from html import escape

THEMES = {
    "light": dict(card="#ffffff", line="#e2e2de", fg="#111111", mut="#77777a", faint="#efefec",
                  shades=["#111111", "#4a4a4a", "#7c7c7c", "#a6a6a6", "#cbcbcb", "#e4e4e4"]),
    "dark": dict(card="#0d1117", line="#2b3038", fg="#f0f0f0", mut="#8b9097", faint="#1a1f27",
                 shades=["#f0f0f0", "#c4c6c9", "#9a9da1", "#73767b", "#50535a", "#363940"]),
}
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

def icon(icons, name, t, x, y, size=18):
    raw = open(os.path.join(icons, f"{name}-light.svg"), encoding="utf-8").read()
    inner = raw[raw.index(">") + 1: raw.rindex("</svg>")].replace("#111111", t["fg"])
    s = size / 24
    return f'<g transform="translate({x},{y}) scale({s:.4f})" fill="none">{inner}</g>'

def frame(w, h, t, body, title=None, tx=24):
    head = ""
    if title:
        head = (f'<text x="{tx}" y="34" font-family="{MONO}" font-size="11" letter-spacing="1.6" fill="{t["mut"]}">{escape(title)}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="12" fill="{t["card"]}" stroke="{t["line"]}"/>'
            f'{head}{body}</svg>')

def fmt(n):
    return f"{n:,}"

def stats(d, t):
    W, H = 830, 206
    items = [("CONTRIBUTIONS", d["contributions_year"], "last 12 months"),
             ("ACTIVE DAYS", d["active_days"], "days with activity"),
             ("STREAK", d["current_streak"], f"best {d['longest_streak']}"),
             ("REPOSITORIES", d["public_repos"], f"{d['stars']} stars")]
    colw = (W - 48) / 4
    b = []
    for i, (lab, val, sub) in enumerate(items):
        x = 24 + i * colw
        if i:
            b.append(f'<line x1="{x-12:.1f}" y1="28" x2="{x-12:.1f}" y2="112" stroke="{t["line"]}"/>')
        b.append(f'<text x="{x:.1f}" y="40" font-family="{MONO}" font-size="11" letter-spacing="1.6" fill="{t["mut"]}">{lab}</text>')
        b.append(f'<text x="{x:.1f}" y="88" font-family="{SANS}" font-size="44" font-weight="700" letter-spacing="-1" fill="{t["fg"]}">{fmt(val)}</text>')
        b.append(f'<text x="{x:.1f}" y="108" font-family="{MONO}" font-size="11" fill="{t["mut"]}">{escape(sub)}</text>')
    # weekly sparkline across the bottom
    wk = d["weeks"]; mx = max(wk) or 1
    x0, x1, yb, hh = 24, W - 24, 176, 44
    step = (x1 - x0) / max(len(wk) - 1, 1)
    pts = [(x0 + i * step, yb - v / mx * hh) for i, v in enumerate(wk)]
    path = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    area = path + f" L{x1:.1f} {yb} L{x0} {yb} Z"
    b.append(f'<line x1="{x0}" y1="{yb}" x2="{x1}" y2="{yb}" stroke="{t["line"]}"/>')
    b.append(f'<path d="{area}" fill="{t["faint"]}"/>')
    b.append(f'<path d="{path}" fill="none" stroke="{t["fg"]}" stroke-width="1.6" stroke-linejoin="round"/>')
    lx, ly = pts[-1]
    b.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3.2" fill="{t["fg"]}"/>')
    b.append(f'<text x="{x0}" y="{yb+14}" font-family="{MONO}" font-size="9" fill="{t["mut"]}">52 WEEKS AGO</text><text x="{x1}" y="{yb+14}" text-anchor="end" font-family="{MONO}" font-size="9" fill="{t["mut"]}">THIS WEEK</text>')
    return frame(W, H, t, "".join(b))

def activity(d, t):
    W, H = 409, 250
    ms = d["months"]; mx = max(m["count"] for m in ms) or 1
    x0, yb, ch = 24, 206, 140
    bw = (W - 48) / len(ms)
    b = [f'<line x1="{x0}" y1="{yb}" x2="{W-24}" y2="{yb}" stroke="{t["line"]}"/>']
    for i, m in enumerate(ms):
        h = m["count"] / mx * ch
        x = x0 + i * bw + bw * 0.18
        w = bw * 0.64
        last = i == len(ms) - 1
        if m["count"]:
            b.append(f'<rect x="{x:.1f}" y="{yb-h:.1f}" width="{w:.1f}" height="{max(h,2):.1f}" rx="2.5" fill="{t["fg"] if last else t["shades"][2]}"/>')
        else:
            b.append(f'<rect x="{x:.1f}" y="{yb-2}" width="{w:.1f}" height="2" rx="1" fill="{t["line"]}"/>')
        mi = int(m["month"][5:]) - 1
        b.append(f'<text x="{x+w/2:.1f}" y="{yb+16}" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{t["mut"]}">{MON[mi][0] if not last else MON[mi]}</text>')
        if last:
            b.append(f'<text x="{x+w:.1f}" y="{yb-h-8:.1f}" text-anchor="end" font-family="{MONO}" font-size="11" font-weight="700" fill="{t["fg"]}">{m["count"]}</text>')
    return frame(W, H, t, "".join(b), "ACTIVITY / MONTH")

def languages(d, t):
    W, H = 409, 250
    ls = d["languages"]
    x0, x1, y = 24, W - 24, 58
    b = []
    x = x0
    for i, l in enumerate(ls):
        w = (x1 - x0) * l["pct"] / 100
        b.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w-2,1):.1f}" height="12" rx="2" fill="{t["shades"][min(i,5)]}"/>')
        x += w
    for i, l in enumerate(ls):
        col, row = i % 2, i // 2
        lx = x0 + col * (x1 - x0) / 2
        ly = 108 + row * 34
        b.append(f'<rect x="{lx}" y="{ly-9}" width="9" height="9" rx="2" fill="{t["shades"][min(i,5)]}"/>')
        b.append(f'<text x="{lx+18}" y="{ly}" font-family="{SANS}" font-size="13" fill="{t["fg"]}">{escape(l["name"])}</text>')
        b.append(f'<text x="{lx+(x1-x0)/2-16}" y="{ly}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{t["mut"]}">{l["pct"]:.1f}%</text>')
    return frame(W, H, t, "".join(b), "LANGUAGES / PUBLIC REPOS")

PROJECTS = {
    "meonji-jump": ("먼지 달려", "고양이가 먼지를 뛰어넘는 브라우저 게임", "game-controller", "PLAY"),
    "MEONJI-Brand": ("MEONJI-Brand", "브랜드 에셋과 로고 제작 규격", "layers", "BRAND"),
    "agent-harness": ("agent-harness", "코딩 에이전트와 일하는 규칙", "wrench", "TOOL"),
}

def project(p, t, icons):
    W, H = 268, 150
    title, desc, ic, tag = PROJECTS[p["name"]]
    b = [icon(icons, ic, t, 24, 24, 20),
         f'<text x="{W-24}" y="38" text-anchor="end" font-family="{MONO}" font-size="10" letter-spacing="1.4" fill="{t["mut"]}">{tag}</text>',
         f'<text x="24" y="80" font-family="{SANS}" font-size="18" font-weight="700" fill="{t["fg"]}">{escape(title)}</text>',
         f'<text x="24" y="102" font-family="{SANS}" font-size="12" fill="{t["mut"]}">{escape(desc)}</text>',
         f'<line x1="24" y1="118" x2="{W-24}" y2="118" stroke="{t["line"]}"/>',
         f'<text x="24" y="136" font-family="{MONO}" font-size="10" fill="{t["mut"]}">{escape(p["language"] or "-")}</text>',
         f'<text x="{W-24}" y="136" text-anchor="end" font-family="{MONO}" font-size="10" fill="{t["mut"]}">updated {p["pushed"][5:].replace("-", ".")}</text>']
    return frame(W, H, t, "".join(b))

def journal(d, t, icons):
    W = 830
    js = d["journal"][:3]
    H = 70 + 34 * max(len(js), 1) + 6
    b = [icon(icons, "notebook", t, W - 44, 20, 18)]
    for i, j in enumerate(js):
        y = 76 + i * 34
        b.append(f'<text x="24" y="{y}" font-family="{MONO}" font-size="12" fill="{t["mut"]}">{j["date"].replace("-", ".")}</text>')
        b.append(f'<text x="130" y="{y}" font-family="{SANS}" font-size="14" fill="{t["fg"]}">{escape(j["title"])}</text>')
        if i < len(js) - 1:
            b.append(f'<line x1="24" y1="{y+14}" x2="{W-24}" y2="{y+14}" stroke="{t["faint"]}"/>')
    return frame(W, H, t, "".join(b), "JOURNAL / LATEST")

STACK = [("APP", ["Flutter", "Dart", "Swift"]), ("WEB · TOOLS", ["TypeScript", "JavaScript", "Python"]), ("BACKEND", ["Supabase"])]

def stack(t, icons):
    W, H = 830, 150
    b = [icon(icons, "layers", t, W - 44, 20, 18)]
    for r, (lab, items) in enumerate(STACK):
        y = 66 + r * 30
        b.append(f'<text x="24" y="{y+4}" font-family="{MONO}" font-size="11" letter-spacing="1.2" fill="{t["mut"]}">{escape(lab)}</text>')
        x = 150
        for it in items:
            w = 16 + len(it) * 7.6
            b.append(f'<rect x="{x}" y="{y-12}" width="{w:.1f}" height="22" rx="11" fill="none" stroke="{t["line"]}"/>')
            b.append(f'<text x="{x+w/2:.1f}" y="{y+3}" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{t["fg"]}">{escape(it)}</text>')
            x += w + 8
    return frame(W, H, t, "".join(b), "STACK")

def main(data, icons, out):
    d = json.load(open(data, encoding="utf-8"))
    os.makedirs(out, exist_ok=True)
    for th, t in THEMES.items():
        files = {"stats": stats(d, t), "activity": activity(d, t), "languages": languages(d, t),
                 "journal": journal(d, t, icons), "stack": stack(t, icons)}
        for p in d["featured"]:
            if p["name"] in PROJECTS:
                files["project-" + p["name"].lower()] = project(p, t, icons)
        for k, v in files.items():
            open(os.path.join(out, f"{k}-{th}.svg"), "w", encoding="utf-8").write(v)

if __name__ == "__main__":
    main(*sys.argv[1:4])
