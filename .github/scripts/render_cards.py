"""Render hand-drawn style dashboard cards (light + dark SVG) from profile data JSON.
Text is converted to vector paths from an OFL handwriting font, so cards look the same everywhere.
Usage: python render_cards.py <data.json> <icons_dir> <font.ttf> <outdir>"""
import json, os, sys, math, random, zlib
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

THEMES = {
    "light": dict(card="#ffffff", line="#2a2a2a", soft="#d9d9d4", fg="#111111", mut="#6f6f6c", faint="#f1f1ee",
                  shades=["#111111", "#555555", "#858585", "#aaaaaa", "#cbcbcb", "#e2e2e2"]),
    "dark": dict(card="#0d1117", line="#c9cbce", soft="#30353d", fg="#f0f0f0", mut="#9a9ea4", faint="#161b22",
                 shades=["#f0f0f0", "#c4c6c9", "#9a9da1", "#73767b", "#50535a", "#383b42"]),
}
MON = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"]

class Hand:
    def __init__(self, path):
        f = TTFont(path)
        self.gs = f.getGlyphSet(); self.cmap = f.getBestCmap(); self.upm = f["head"].unitsPerEm
        self.hmtx = f["hmtx"]; self.cache = {}
    def glyph(self, ch):
        if ch not in self.cache:
            name = self.cmap.get(ord(ch)) or self.cmap.get(ord("?"))
            pen = SVGPathPen(self.gs, ntos=lambda v: ("%.1f" % v).rstrip("0").rstrip("."))
            self.gs[name].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0)))
            self.cache[ch] = (pen.getCommands(), self.hmtx[name][0])
        return self.cache[ch]
    def width(self, s, size):
        return sum(self.glyph(c)[1] for c in s) * size / self.upm
    def text(self, s, x, y, size, fill, anchor="start", spacing=0.0):
        w = self.width(s, size) + spacing * size * max(len(s) - 1, 0)
        if anchor == "middle": x -= w / 2
        elif anchor == "end": x -= w
        k = size / self.upm; out = []; cx = 0.0
        for c in s:
            d, adv = self.glyph(c)
            if d.strip():
                out.append(f'<path transform="translate({x + cx * k:.1f},{y:.1f}) scale({k:.4f})" d="{d}"/>')
            cx += adv + spacing * self.upm
        return f'<g fill="{fill}">{"".join(out)}</g>'

def rng_for(key):
    return random.Random(zlib.crc32(key.encode()))

def smooth(pts, closed=False):
    """Catmull-Rom -> cubic bezier path."""
    n = len(pts)
    if n < 2: return ""
    P = pts + pts[:3] if closed else [pts[0]] + pts + [pts[-1]]
    d = [f"M{P[1][0]:.1f} {P[1][1]:.1f}"]
    rng_ = range(1, n + 1) if closed else range(1, n)
    for i in rng_:
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}")
    return "".join(d)

def rline(r, x1, y1, x2, y2, color, w=1.4, passes=2, amp=1.0):
    out = []
    L = math.hypot(x2 - x1, y2 - y1) or 1
    nx, ny = -(y2 - y1) / L, (x2 - x1) / L
    for p in range(passes):
        j = lambda: r.uniform(-amp, amp) * (0.6 if p == 0 else 1.0)
        a = (x1 + j(), y1 + j()); b = (x2 + j(), y2 + j())
        bow = r.uniform(-1, 1) * min(L * 0.01, 1.8) * amp
        c = ((a[0] + b[0]) / 2 + nx * bow, (a[1] + b[1]) / 2 + ny * bow)
        out.append(f'<path d="M{a[0]:.1f} {a[1]:.1f} Q{c[0]:.1f} {c[1]:.1f} {b[0]:.1f} {b[1]:.1f}" '
                   f'fill="none" stroke="{color}" stroke-width="{w if p == 0 else w * 0.6:.2f}" stroke-linecap="round" opacity="{1 if p == 0 else .55}"/>')
    return "".join(out)

def rrect_pts(r, x, y, w, h, rad, amp):
    pts = []
    corners = [(x + w - rad, y + rad, -90), (x + w - rad, y + h - rad, 0), (x + rad, y + h - rad, 90), (x + rad, y + rad, 180)]
    for cx, cy, a0 in corners:
        rr = rad * r.uniform(0.94, 1.06)
        for k in range(3):
            a = math.radians(a0 + k * 45)
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        # points along the following edge
        a1 = math.radians(a0 + 90)
        ex, ey = cx + rad * math.cos(a1), cy + rad * math.sin(a1)
        pts.append((ex, ey))
    # subdivide long edges with jitter
    res = []
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        res.append((p[0] + r.uniform(-amp, amp) * .15, p[1] + r.uniform(-amp, amp) * .15))
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        n = int(L // 90) if L > 30 else 0
        for s in range(1, n + 1):
            t = s / (n + 1)
            res.append((p[0] + (q[0] - p[0]) * t + r.uniform(-amp, amp), p[1] + (q[1] - p[1]) * t + r.uniform(-amp, amp)))
    return res

def rrect(r, x, y, w, h, color, fill="none", rad=12, sw=1.6, amp=1.1):
    a = smooth(rrect_pts(r, x, y, w, h, rad, amp), closed=True)
    b = smooth(rrect_pts(r, x + .6, y + .4, w - .8, h - .6, rad, amp), closed=True)
    return (f'<path d="{a}" fill="{fill}" stroke="{color}" stroke-width="{sw}" stroke-linejoin="round"/>'
            f'<path d="{b}" fill="none" stroke="{color}" stroke-width="{sw * .55:.2f}" opacity=".5"/>')

def rbar(r, x, y, w, h, fill):
    if h < 1: return ""
    j = lambda: r.uniform(-.7, .7)
    pts = [(x + j(), y + h), (x + j(), y + j() + 1.5), (x + w * .5, y + j()), (x + w + j(), y + 1.5 + j()), (x + w + j(), y + h)]
    d = "M" + " L".join(f"{p[0]:.1f} {p[1]:.1f}" for p in pts) + "Z"
    return f'<path d="{d}" fill="{fill}" stroke="{fill}" stroke-width="1.2" stroke-linejoin="round"/>'

def icon(icons, name, t, x, y, size=20):
    raw = open(os.path.join(icons, f"{name}-light.svg"), encoding="utf-8").read()
    inner = raw[raw.index(">") + 1: raw.rindex("</svg>")].replace("#111111", t["fg"])
    return f'<g transform="translate({x},{y}) scale({size / 24:.4f})" fill="none">{inner}</g>'

def svg(w, h, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'

# ---------- doodles ----------
def d_ears(r, t, x, y):
    """two small cat ears peeking over a card edge at (x,y) = baseline left."""
    out = []
    for dx in (0, 30):
        p = [(x + dx, y + 2), (x + dx + 5 + r.uniform(-1, 1), y - 15 + r.uniform(-1, 1)), (x + dx + 20, y + 2)]
        d = f"M{p[0][0]:.1f} {p[0][1]:.1f} Q{p[1][0] - 1:.1f} {p[1][1] + 4:.1f} {p[1][0]:.1f} {p[1][1]:.1f} Q{p[1][0] + 4:.1f} {p[1][1] + 4:.1f} {p[2][0]:.1f} {p[2][1]:.1f}Z"
        out.append(f'<path d="{d}" fill="{t["card"]}" stroke="{t["line"]}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>')
    return "".join(out)

def d_scribble(r, t, x, y, w):
    pts = []
    for i in range(7):
        pts.append((x + w * i / 6, y + (2.2 if i % 2 else -0.4) + r.uniform(-.6, .6)))
    return f'<path d="{smooth(pts)}" fill="none" stroke="{t["fg"]}" stroke-width="1.8" stroke-linecap="round"/>'

def d_arrow(r, t, x1, y1, x2, y2):
    cx, cy = (x1 + x2) / 2 + 18, (y1 + y2) / 2 - 10
    ang = math.atan2(y2 - cy, x2 - cx)
    h1 = (x2 - 8 * math.cos(ang - .5), y2 - 8 * math.sin(ang - .5))
    h2 = (x2 - 8 * math.cos(ang + .5), y2 - 8 * math.sin(ang + .5))
    return (f'<path d="M{x1:.1f} {y1:.1f} Q{cx:.1f} {cy:.1f} {x2:.1f} {y2:.1f} M{h1[0]:.1f} {h1[1]:.1f} L{x2:.1f} {y2:.1f} L{h2[0]:.1f} {h2[1]:.1f}" '
            f'fill="none" stroke="{t["fg"]}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>')

def d_sparkle(r, t, x, y, s=7):
    d = f"M{x} {y - s} Q{x + 1} {y - 1} {x + s} {y} Q{x + 1} {y + 1} {x} {y + s} Q{x - 1} {y + 1} {x - s} {y} Q{x - 1} {y - 1} {x} {y - s}Z"
    return f'<path d="{d}" fill="none" stroke="{t["fg"]}" stroke-width="1.3" stroke-linejoin="round"/>'

def d_puff(r, t, x, y):
    out = []
    for i in range(9):
        a = i / 9 * math.tau
        rr = 9 + r.uniform(-2, 2)
        out.append((x + math.cos(a) * rr, y + math.sin(a) * rr * .8))
    s = f'<path d="{smooth(out, closed=True)}" fill="none" stroke="{t["fg"]}" stroke-width="1.4"/>'
    for k in range(7):
        a = k / 7 * math.tau + 0.3
        s += f'<path d="M{x + 13 * math.cos(a):.1f} {y + 11 * math.sin(a):.1f} l{4 * math.cos(a):.1f} {4 * math.sin(a):.1f}" stroke="{t["fg"]}" stroke-width="1.3" stroke-linecap="round"/>'
    s += f'<circle cx="{x - 3:.1f}" cy="{y - 1:.1f}" r="1.2" fill="{t["fg"]}"/><circle cx="{x + 3:.1f}" cy="{y - 1:.1f}" r="1.2" fill="{t["fg"]}"/>'
    return s

def d_paw(r, t, x, y):
    s = f'<ellipse cx="{x}" cy="{y + 4}" rx="5" ry="4" fill="{t["mut"]}"/>'
    for dx, dy in ((-6, -3), (-2, -7), (3, -7), (7, -3)):
        s += f'<ellipse cx="{x + dx}" cy="{y + dy}" rx="1.9" ry="2.3" fill="{t["mut"]}"/>'
    return s

# ---------- cards ----------
W = 830

def stats(d, t, H_):
    r = rng_for("stats")
    H = 236
    b = [rrect(r, 3, 18, W - 6, H - 22, t["line"], t["card"])]
    b.append(d_ears(r, t, W - 92, 20))
    items = [("기여", d["contributions_year"], "지난 12개월"), ("활동한 날", d["active_days"], "일"),
             ("연속 기록", d["current_streak"], f"최고 {d['longest_streak']}일"), ("저장소", d["public_repos"], f"별 {d['stars']}개")]
    colw = (W - 56) / 4
    for i, (lab, val, sub) in enumerate(items):
        x = 30 + i * colw
        if i: b.append(rline(r, x - 14, 52, x - 14, 136, t["soft"], 1.2, 1, .8))
        b.append(H_.text(lab, x, 66, 19, t["mut"]))
        b.append(H_.text(f"{val:,}", x, 120, 54, t["fg"]))
        if i == 0: b.append(d_scribble(r, t, x, 128, H_.width(f"{val:,}", 54)))
        b.append(H_.text(sub, x, 150, 16, t["mut"]))
    wk = d["weeks"]; mx = max(wk) or 1
    x0, x1, yb, hh = 30, W - 30, 206, 40
    step = (x1 - x0) / max(len(wk) - 1, 1)
    pts = [(x0 + i * step, yb - v / mx * hh + r.uniform(-.4, .4)) for i, v in enumerate(wk)]
    b.append(rline(r, x0, yb, x1, yb, t["soft"], 1.2, 2, .8))
    b.append(f'<path d="{smooth(pts)}L{x1} {yb}L{x0} {yb}Z" fill="{t["faint"]}"/>')
    b.append(f'<path d="{smooth(pts)}" fill="none" stroke="{t["fg"]}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>')
    lx, ly = pts[-1]
    b.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3.4" fill="{t["fg"]}"/>')
    b.append(H_.text("1년 전", x0, yb + 22, 15, t["mut"]))
    b.append(H_.text("이번 주", x1, yb + 22, 15, t["mut"], "end"))
    return svg(W, H + 10, "".join(b))

def charts(d, t, H_):
    """activity (left) + languages (right) in one image so edges align with full-width cards."""
    r = rng_for("charts")
    H = 286; gap = 16; cw = (W - 6 - gap) / 2
    b = [rrect(r, 3, 4, cw, H - 8, t["line"], t["card"]), rrect(r, 3 + cw + gap, 4, cw, H - 8, t["line"], t["card"])]
    # activity
    ms = d["months"]; mx = max(m["count"] for m in ms) or 1
    b.append(H_.text("월별 활동", 28, 44, 22, t["fg"]))
    x0, yb, ch = 28, 232, 140
    bw = (cw - 50) / len(ms)
    b.append(rline(r, x0, yb, x0 + bw * len(ms), yb, t["line"], 1.4))
    for i, m in enumerate(ms):
        h = m["count"] / mx * ch; x = x0 + i * bw + bw * .17; w = bw * .66
        last = i == len(ms) - 1
        if m["count"]: b.append(rbar(r, x, yb - max(h, 2), w, max(h, 2), t["fg"] if last else t["shades"][2]))
        mi = int(m["month"][5:]) - 1
        if i % 2 == 1 or last:
            b.append(H_.text(MON[mi], x + w / 2, yb + 24, 15, t["fg"] if last else t["mut"], "middle"))
        if last:
            b.append(H_.text(str(m["count"]), x + w / 2, yb - h - 10, 18, t["fg"], "middle"))
            b.append(d_arrow(r, t, x - 58, yb - h + 6, x - 8, yb - h + 22))
            b.append(H_.text("이번 달", x - 64, yb - h + 2, 15, t["mut"], "end"))
    # languages
    ox = 3 + cw + gap
    ls = d["languages"]
    b.append(H_.text("언어", ox + 26, 44, 22, t["fg"]))
    b.append(d_sparkle(r, t, ox + cw - 34, 36))
    bx0, bx1, by = ox + 26, ox + cw - 26, 70
    x = bx0
    for i, l in enumerate(ls):
        w = (bx1 - bx0) * l["pct"] / 100
        b.append(rbar(r, x + .8, by, max(w - 2.5, 1.2), 16, t["shades"][min(i, 5)]))
        x += w
    for i, l in enumerate(ls):
        col, row = i % 2, i // 2
        lx = bx0 + col * (bx1 - bx0) / 2; ly = 136 + row * 44
        b.append(rbar(r, lx, ly - 13, 12, 12, t["shades"][min(i, 5)]))
        b.append(H_.text(l["name"], lx + 20, ly, 19, t["fg"]))
        b.append(H_.text(f"{l['pct']:.0f}%" if l["pct"] >= 10 else f"{l['pct']:.1f}%", lx + (bx1 - bx0) / 2 - 18, ly, 17, t["mut"], "end"))
    return svg(W, H, "".join(b))

PROJECTS = {
    "meonji-jump": ("먼지 달려", "고양이가 먼지를 뛰어넘는 게임", "game-controller", "플레이"),
    "MEONJI-Brand": ("MEONJI-Brand", "브랜드 에셋과 로고 제작 규격", "layers", "브랜드"),
    "agent-harness": ("agent-harness", "코딩 에이전트와 일하는 규칙", "wrench", "도구"),
}

def project(p, t, icons, H_):
    r = rng_for("p-" + p["name"])
    Wp, H = 266, 168
    title, desc, ic, tag = PROJECTS[p["name"]]
    b = [rrect(r, 3, 4, Wp - 6, H - 8, t["line"], t["card"]), icon(icons, ic, t, 24, 24, 22),
         H_.text(tag, Wp - 24, 42, 17, t["mut"], "end"),
         H_.text(title, 24, 92, 27, t["fg"]),
         H_.text(desc, 24, 118, 17, t["mut"]),
         rline(r, 24, 132, Wp - 24, 132, t["soft"], 1.2, 1, .8),
         H_.text(p["language"] or "-", 24, 154, 16, t["mut"]),
         H_.text(p["pushed"][5:].replace("-", ".") + " 업데이트", Wp - 24, 154, 16, t["mut"], "end")]
    if p["name"] == "meonji-jump":
        b.append(d_puff(r, t, Wp - 44, 82))
    return svg(Wp, H, "".join(b))

def journal(d, t, icons, H_):
    r = rng_for("journal")
    js = d["journal"][:3]
    H = 84 + 40 * max(len(js), 1)
    b = [rrect(r, 3, 4, W - 6, H - 8, t["line"], t["card"]), H_.text("일지", 28, 44, 22, t["fg"]),
         icon(icons, "notebook", t, W - 50, 24, 20), d_paw(r, t, W - 84, 36)]
    for i, j in enumerate(js):
        y = 88 + i * 40
        b.append(H_.text(j["date"][5:].replace("-", "."), 28, y, 18, t["mut"]))
        b.append(H_.text(j["title"], 96, y, 20, t["fg"]))
        if i < len(js) - 1: b.append(rline(r, 28, y + 15, W - 28, y + 15, t["soft"], 1, 1, .8))
    return svg(W, H, "".join(b))

STACK = [("앱", ["Flutter", "Dart", "Swift"]), ("웹 · 도구", ["TypeScript", "JavaScript", "Python"]), ("백엔드", ["Supabase"])]

def stack(t, icons, H_):
    r = rng_for("stack")
    H = 196
    b = [rrect(r, 3, 4, W - 6, H - 8, t["line"], t["card"]), H_.text("쓰는 기술", 28, 44, 22, t["fg"]),
         icon(icons, "layers", t, W - 50, 24, 20)]
    for i, (lab, items) in enumerate(STACK):
        y = 88 + i * 38
        b.append(H_.text(lab, 28, y + 6, 18, t["mut"]))
        x = 150
        for it in items:
            w = H_.width(it, 19) + 28
            b.append(rrect(r, x, y - 14, w, 28, t["line"], "none", rad=13, sw=1.2, amp=.6))
            b.append(H_.text(it, x + w / 2, y + 6, 19, t["fg"], "middle"))
            x += w + 10
    return svg(W, H, "".join(b))

def main(data, icons, font, out):
    d = json.load(open(data, encoding="utf-8"))
    H_ = Hand(font)
    os.makedirs(out, exist_ok=True)
    for th, t in THEMES.items():
        files = {"stats": stats(d, t, H_), "charts": charts(d, t, H_), "journal": journal(d, t, icons, H_), "stack": stack(t, icons, H_)}
        for p in d["featured"]:
            if p["name"] in PROJECTS:
                files["project-" + p["name"].lower()] = project(p, t, icons, H_)
        for k, v in files.items():
            open(os.path.join(out, f"{k}-{th}.svg"), "w", encoding="utf-8").write(v)

if __name__ == "__main__":
    main(*sys.argv[1:5])
