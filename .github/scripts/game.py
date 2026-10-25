#!/usr/bin/env python3
"""Profile README games: tic-tac-toe and chess.

Input comes only from environment variables (ISSUE_TITLE, ISSUE_USER).
Writes the reply comment to $COMMENT_FILE and prints changed=true/false
to $GITHUB_OUTPUT. Never executes visitor input.
"""
import json, os, random, re, sys, time, urllib.parse
from pathlib import Path

import chess
import chess.svg

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".github/games/state.json"
README = ROOT / "README.md"
ASSETS = ROOT / "assets/games"
REPO = os.environ.get("GITHUB_REPOSITORY", "meonji-mon/meonji-mon")
RATE_LIMIT = 20          # moves per user per hour
WINDOW = 3600
TTT_RE = re.compile(r"^ttt\|([abc][123])$")
CHESS_RE = re.compile(r"^chess\|([a-h][1-8][a-h][1-8][qrbn]?)$")
USER_RE = re.compile(r"^[A-Za-z0-9-]{1,39}$")
LINES = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
VALS = {chess.PAWN:100, chess.KNIGHT:320, chess.BISHOP:330, chess.ROOK:500, chess.QUEEN:900, chess.KING:0}

def new_state():
    return {"ttt": {"board": [""]*9, "log": [], "tally": {"x": 0, "o": 0, "draw": 0}},
            "chess": {"fen": chess.STARTING_FEN, "last": None, "log": [], "tally": {"white": 0, "black": 0, "draw": 0}},
            "rate": {}}

def load():
    return json.loads(STATE.read_text()) if STATE.exists() else new_state()

def issue_link(title, body="이 이슈를 그대로 제출하면 수가 둬져요. 제목은 바꾸지 마세요."):
    q = urllib.parse.urlencode({"title": title, "body": body}, quote_via=urllib.parse.quote)
    return f"https://github.com/{REPO}/issues/new?{q}"

# ---------- tic-tac-toe ----------
def cell_index(c):  # a1 = top-left; letter = column, digit = row
    return (int(c[1]) - 1) * 3 + "abc".index(c[0])

def cell_name(i):
    return "abc"[i % 3] + str(i // 3 + 1)

def winner(b):
    for a, c, d in LINES:
        if b[a] and b[a] == b[c] == b[d]:
            return b[a]
    return "draw" if all(b) else None

def minimax(b, turn):
    w = winner(b)
    if w == "o": return 1, None
    if w == "x": return -1, None
    if w == "draw": return 0, None
    best = None
    for i in range(9):
        if b[i]: continue
        b[i] = turn
        s, _ = minimax(b, "x" if turn == "o" else "o")
        b[i] = ""
        if best is None or (turn == "o" and s > best[0]) or (turn == "x" and s < best[0]):
            best = (s, i)
    return best

def ttt_bot(b, rng):
    empty = [i for i in range(9) if not b[i]]
    if rng.random() < 0.15:
        return rng.choice(empty)
    return minimax(b, "o")[1]

def ttt_svg(b, win_line=None):
    s = 300; c = s / 3
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s} {s}" width="{s}" height="{s}">',
           f'<rect width="{s}" height="{s}" rx="14" fill="#f2f2f2" stroke="#8a8a8a" stroke-width="2"/>']
    for k in (1, 2):
        out.append(f'<line x1="{c*k}" y1="18" x2="{c*k}" y2="{s-18}" stroke="#8a8a8a" stroke-width="3" stroke-linecap="round"/>')
        out.append(f'<line x1="18" y1="{c*k}" x2="{s-18}" y2="{c*k}" stroke="#8a8a8a" stroke-width="3" stroke-linecap="round"/>')
    for i, v in enumerate(b):
        cx = (i % 3) * c + c / 2; cy = (i // 3) * c + c / 2; r = 28
        if v == "x":
            out.append(f'<path d="M{cx-r} {cy-r}L{cx+r} {cy+r}M{cx+r} {cy-r}L{cx-r} {cy+r}" stroke="#111" stroke-width="10" stroke-linecap="round"/>')
        elif v == "o":
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{r+2}" fill="none" stroke="#111" stroke-width="10"/>')
        else:
            out.append(f'<text x="{cx}" y="{cy+6}" text-anchor="middle" font-family="ui-monospace,Menlo,monospace" font-size="16" fill="#b0b0b0">{cell_name(i)}</text>')
    if win_line:
        a, d = win_line[0], win_line[2]
        p = lambda i: ((i % 3) * c + c / 2, (i // 3) * c + c / 2)
        (x1, y1), (x2, y2) = p(a), p(d)
        out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#111" stroke-opacity=".35" stroke-width="16" stroke-linecap="round"/>')
    out.append("</svg>")
    return "\n".join(out)

def play_ttt(st, cell, user, rng):
    g = st["ttt"]; b = g["board"]; i = cell_index(cell)
    if b[i]:
        return False, f"`{cell}` 칸은 이미 채워져 있어요. 빈 칸을 골라 주세요."
    b[i] = "x"; g["log"].append(f"@{user} X {cell}")
    w = winner(b); msg = f"X를 `{cell}`에 두었어요."
    if not w:
        j = ttt_bot(b, rng); b[j] = "o"; g["log"].append(f"먼지 O {cell_name(j)}")
        msg += f" 먼지는 O를 `{cell_name(j)}`에 두었어요."
        w = winner(b)
    line = next((l for l in LINES if b[l[0]] and b[l[0]] == b[l[1]] == b[l[2]]), None)
    if w:
        g["tally"][w] += 1
        msg += {"x": " 이겼어요, 축하해요.", "o": " 이번 판은 먼지가 이겼어요.", "draw": " 무승부예요."}[w]
        msg += " 새 판을 시작했어요."
        g["board"] = [""] * 9; g["log"] = g["log"][-6:] + ["새 판"]
    g["log"] = g["log"][-8:]
    return True, msg

# ---------- chess ----------
def evaluate(bd):
    if bd.is_checkmate():
        return -99999 if bd.turn == chess.WHITE else 99999
    if bd.is_game_over():
        return 0
    s = 0
    for sq, p in bd.piece_map().items():
        v = VALS[p.piece_type]
        if p.piece_type in (chess.PAWN, chess.KNIGHT, chess.BISHOP):
            f, r = chess.square_file(sq), chess.square_rank(sq)
            v += int(10 - 3 * (abs(3.5 - f) + abs(3.5 - r)))  # center bonus
        s += v if p.color == chess.WHITE else -v
    return s

def search(bd, depth, alpha, beta):
    if depth == 0 or bd.is_game_over():
        return evaluate(bd)
    moves = sorted(bd.legal_moves, key=lambda m: not bd.is_capture(m))
    if bd.turn == chess.WHITE:
        v = -10**9
        for m in moves:
            bd.push(m); v = max(v, search(bd, depth - 1, alpha, beta)); bd.pop()
            alpha = max(alpha, v)
            if alpha >= beta: break
        return v
    v = 10**9
    for m in moves:
        bd.push(m); v = min(v, search(bd, depth - 1, alpha, beta)); bd.pop()
        beta = min(beta, v)
        if alpha >= beta: break
    return v

def chess_bot(bd, rng):
    scored = []
    for m in bd.legal_moves:
        bd.push(m); scored.append((search(bd, 2, -10**9, 10**9) + rng.randint(0, 15), m.uci())); bd.pop()
    scored.sort()
    return chess.Move.from_uci(scored[0][1])

COLORS = {"square light": "#e6e6e6", "square dark": "#9a9a9a", "margin": "#2b2b2b", "coord": "#e6e6e6",
          "square light lastmove": "#c9c9c9", "square dark lastmove": "#7a7a7a", "inner border": "#2b2b2b"}

def chess_svg(bd, last):
    mv = chess.Move.from_uci(last) if last else None
    chk = bd.king(bd.turn) if bd.is_check() else None
    return chess.svg.board(bd, lastmove=mv, check=chk, size=360, colors=COLORS)

def result_text(bd):
    if bd.is_checkmate(): return "체크메이트"
    if bd.is_stalemate(): return "스테일메이트"
    if bd.is_insufficient_material(): return "기물 부족"
    return "무승부 규칙"

def play_chess(st, uci, user, rng):
    g = st["chess"]; bd = chess.Board(g["fen"])
    if bd.turn != chess.WHITE:
        return False, "지금은 흰색 차례가 아니에요. 잠시 후 다시 시도해 주세요."
    mv = chess.Move.from_uci(uci)
    if mv not in bd.legal_moves:
        return False, f"`{uci}`는 지금 둘 수 없는 수예요. README의 둘 수 있는 수 목록에서 골라 주세요."
    san = bd.san(mv); bd.push(mv); g["log"].append(f"@{user} {san}"); g["last"] = uci
    msg = f"흰색 `{san}` 두었어요."
    if not bd.is_game_over(claim_draw=True):
        r = chess_bot(bd, rng); rs = bd.san(r); bd.push(r); g["last"] = r.uci()
        g["log"].append(f"먼지 {rs}"); msg += f" 먼지는 `{rs}` 받아 뒀어요."
    if bd.is_game_over(claim_draw=True):
        out = bd.outcome(claim_draw=True)
        key = "draw" if out.winner is None else ("white" if out.winner else "black")
        g["tally"][key] += 1
        msg += f" {result_text(bd)}로 게임이 끝났어요({ {'white':'흰색 승','black':'먼지 승','draw':'무승부'}[key] }). 새 게임을 시작했어요."
        bd = chess.Board(); g["last"] = None; g["log"] = g["log"][-6:] + ["새 게임"]
    g["fen"] = bd.fen(); g["log"] = g["log"][-10:]
    return True, msg

# ---------- README ----------
def render(st):
    ASSETS.mkdir(parents=True, exist_ok=True)
    t = st["ttt"]; c = st["chess"]
    (ASSETS / "ttt.svg").write_text(ttt_svg(t["board"]))
    bd = chess.Board(c["fen"])
    (ASSETS / "chess.svg").write_text(chess_svg(bd, c["last"]))
    empty = [cell_name(i) for i in range(9) if not t["board"][i]]
    ttt_links = " ".join(f'<a href="{issue_link("ttt|" + e)}"><code>{e}</code></a>' for e in empty)
    moves = sorted(bd.legal_moves, key=lambda m: bd.san(m))
    chess_links = " ".join(f'<a href="{issue_link("chess|" + m.uci())}"><code>{bd.san(m)}</code></a>' for m in moves)
    tl = t["tally"]; cl = c["tally"]
    tlog = " · ".join(t["log"][-4:]) or "아직 둔 수가 없어요"
    clog = " · ".join(c["log"][-6:]) or "아직 둔 수가 없어요"
    block = f"""<!-- GAMES:START -->
<h4>게임</h4>
<p>칸이나 수를 누르면 이슈가 열려요. 그대로 제출하면 1분 안에 먼지가 받아 둡니다.</p>

<table align="center">
  <tr><th align="left">틱택토 <sub>당신 X · 먼지 O</sub></th></tr>
  <tr><td align="center"><img alt="틱택토 판" src="./assets/games/ttt.svg" width="240"></td></tr>
  <tr><td align="left">둘 칸 &nbsp;{ttt_links}</td></tr>
  <tr><td align="left"><sub>전적 당신 {tl['x']} · 먼지 {tl['o']} · 무 {tl['draw']} &nbsp;|&nbsp; 최근 {tlog}</sub></td></tr>
</table>

<br>

<table align="center">
  <tr><th align="left">체스 <sub>당신 흰색 · 먼지 검은색</sub></th></tr>
  <tr><td align="center"><img alt="체스 판" src="./assets/games/chess.svg" width="320"></td></tr>
  <tr><td align="left"><details><summary>둘 수 있는 수 {len(moves)}개 보기</summary><br>{chess_links}</details></td></tr>
  <tr><td align="left"><sub>전적 당신 {cl['white']} · 먼지 {cl['black']} · 무 {cl['draw']} &nbsp;|&nbsp; 최근 {clog}</sub></td></tr>
</table>
<!-- GAMES:END -->"""
    txt = README.read_text()
    txt = re.sub(r"<!-- GAMES:START -->.*?<!-- GAMES:END -->", lambda _: block, txt, flags=re.S)
    README.write_text(txt)

def rate_ok(st, user, now):
    r = st.setdefault("rate", {})
    for u in list(r):
        r[u] = [t for t in r[u] if now - t < WINDOW]
        if not r[u]: del r[u]
    if len(r.get(user, [])) >= RATE_LIMIT:
        return False
    r.setdefault(user, []).append(now)
    return True

def main():
    title = os.environ.get("ISSUE_TITLE", "").strip()
    user = os.environ.get("ISSUE_USER", "")
    now = int(os.environ.get("NOW", time.time()))
    rng = random.Random(os.environ.get("SEED") or None)
    st = load(); changed = False
    if os.environ.get("RESET") == "1":
        st = new_state(); changed = True; msg = "reset"
    elif not USER_RE.match(user):
        msg = "요청을 처리할 수 없어요."
    elif not (TTT_RE.match(title) or CHESS_RE.match(title)):
        msg = "제목 형식이 맞지 않아요. `ttt|b2` 또는 `chess|e2e4`처럼 README의 링크를 눌러 주세요."
    elif not rate_ok(st, user, now):
        msg = f"한 시간에 {RATE_LIMIT}수까지 둘 수 있어요. 조금 쉬었다가 다시 와 주세요."
    else:
        m = TTT_RE.match(title)
        changed, msg = play_ttt(st, m.group(1), user, rng) if m else play_chess(st, CHESS_RE.match(title).group(1), user, rng)
        if changed:
            msg += f"\n\n[프로필로 돌아가기](https://github.com/{REPO})"
    if changed:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1) + "\n")
        render(st)
    Path(os.environ.get("COMMENT_FILE", "/tmp/comment.md")).write_text(msg + "\n")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f: f.write(f"changed={'true' if changed else 'false'}\n")
    print(msg)

if __name__ == "__main__":
    main()
