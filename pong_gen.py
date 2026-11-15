#!/usr/bin/env python3
"""
pong_gen.py - playable ASCII pong that lives inside a GitHub README.

GitHub's markdown renderer runs no JavaScript, so the game is a pre-rendered
state machine: every game state is its own .md file (an ASCII board in a code
block) and the three buttons - left / stay / right - are plain links to the
file for the next state. Same trick as Kuber Mehta's DoomMe, just smaller.

Usage (run from the root of your repo):
    python pong_gen.py

It writes ./pong/ plus ./pong/README_SNIPPET.md. Paste the snippet into your
README.md, commit everything, push. Done.

Why it stays small: the ball's path never depends on the player (a paddle hit
bounces exactly like a wall), so the ball is a fixed timeline. A game state is
only (tick, paddle position) - a few thousand tiny files, not tens of thousands.
"""
import os
import posixpath
import shutil
from collections import deque

# ============================== CONFIG ==============================
W = 28                     # playfield width   (+2 border  = 30 columns)
ROWS = 14                  # playfield height  (+2 border  = 16 lines)
PADDLE_W = 5               # smaller paddle = harder game
START_BALL = (3, 2, 1, 1)  # x, y, dx, dy (must start strictly inside the field)
WIN_BOUNCES = 5            # paddle hits needed to win; None = endless (no score)
OUT_DIR = "pong"           # output folder, relative to the repo root
HOME = "README.md"         # where the "quit" links go, relative to the repo root
BALL, PADDLE, MISS = "O", "=", "X"
# ====================================================================

ENDLESS = WIN_BOUNCES is None
PADDLE_ROW = ROWS - 1      # paddle sits on the last playfield row
FLOOR = PADDLE_ROW - 1     # lowest row the ball reaches (right above the paddle)
MAX_P = W - PADDLE_W       # rightmost paddle position
START_P = MAX_P // 2
FENCE = "`" * 3

assert OUT_DIR not in ("", ".", "/"), "OUT_DIR must be a subfolder"
assert 0 < START_BALL[0] < W - 1 and 0 < START_BALL[1] < FLOOR, "start ball must be inside the field"
assert abs(START_BALL[2]) == 1 and abs(START_BALL[3]) == 1, "dx and dy must be +1 or -1"


# --------------------------- ball timeline ---------------------------
def advance(ball):
    """One tick of ball physics: bounce off side walls, ceiling and paddle row."""
    x, y, dx, dy = ball
    if not 0 <= x + dx < W:
        dx = -dx
    if not 0 <= y + dy <= FLOOR:
        dy = -dy
    return (x + dx, y + dy, dx, dy)


def build_trajectory():
    """Precompute the ball's whole path. Returns (trajectory, bounce_counts, period)."""
    traj, bounces = [START_BALL], [0]
    if ENDLESS:
        while True:                      # a bounce is reversible, so the path loops
            nxt = advance(traj[-1])
            if nxt == START_BALL:
                break
            traj.append(nxt)
        return traj, [0] * len(traj), len(traj)
    count = 0
    while count < WIN_BOUNCES:
        traj.append(advance(traj[-1]))
        if traj[-1][1] == FLOOR:         # ball arrived at the paddle row
            count += 1
        bounces.append(count)
    return traj, bounces, None


TRAJ, BOUNCES, PERIOD = build_trajectory()
T_END = len(TRAJ) - 1                    # finite mode: tick of the winning hit
TW = len(str(len(TRAJ)))                 # zero-pad widths for file names
PW = len(str(MAX_P))


# ------------------------------ paths --------------------------------
def game_path(t, p):
    return f"{OUT_DIR}/g/{t:0{TW}d}/{p:0{PW}d}.md"


def over_path(t, p):
    return f"{OUT_DIR}/o/{t:0{TW}d}/{p:0{PW}d}.md"


WIN_PATH = f"{OUT_DIR}/win.md"
SNIPPET_PATH = f"{OUT_DIR}/README_SNIPPET.md"


def rel(src, dst):
    """Relative link from file src to file dst (both repo-root-relative, posix style)."""
    return posixpath.relpath(dst, posixpath.dirname(src) or ".")


# ----------------------------- rendering -----------------------------
def board(ball_xy, p, ball_char):
    grid = [[" "] * W for _ in range(ROWS)]
    for i in range(PADDLE_W):
        grid[PADDLE_ROW][p + i] = PADDLE
    if ball_xy is not None:
        bx, by = ball_xy
        grid[by][bx] = ball_char
    edge = "+" + "-" * W + "+"
    return "\n".join([edge] + ["|" + "".join(r) + "|" for r in grid] + [edge])


def game_page(t, p, dsts):
    src = game_path(t, p)
    bx, by, _, _ = TRAJ[t]
    score = "" if ENDLESS else f" &nbsp;·&nbsp; bounces {BOUNCES[t]}/{WIN_BOUNCES}"
    left, stay, right = (rel(src, d) for d in dsts)
    return (
        f"### 🏓 PONG{score}\n\n"
        f"{FENCE}text\n{board((bx, by), p, BALL)}\n{FENCE}\n\n"
        f"[◀ left]({left}) &nbsp;·&nbsp; [■ stay]({stay}) &nbsp;·&nbsp; [right ▶]({right})\n\n"
        f"<sub>[quit]({rel(src, HOME)})</sub>\n"
    )


def over_page(t, p):
    src = over_path(t, p)
    bx, _, _, _ = TRAJ[t]
    hits = "" if ENDLESS else f"\n\nbounces: **{BOUNCES[t] - 1}**/{WIN_BOUNCES}"
    return (
        "### 💥 GAME OVER\n\n"
        f"{FENCE}text\n{board((bx, PADDLE_ROW), p, MISS)}\n{FENCE}{hits}\n\n"
        f"[↻ play again]({rel(src, game_path(0, START_P))}) &nbsp;·&nbsp; "
        f"[quit]({rel(src, HOME)})\n"
    )


def win_page():
    return (
        "### 🏆 YOU WIN\n\n"
        f"All {WIN_BOUNCES} bounces returned.\n\n"
        f"[↻ play again]({rel(WIN_PATH, game_path(0, START_P))}) &nbsp;·&nbsp; "
        f"[quit]({rel(WIN_PATH, HOME)})\n"
    )


def snippet():
    bx, by, _, _ = TRAJ[0]
    return (
        "### 🏓 PONG &nbsp;·&nbsp; playable right here\n\n"
        f"{FENCE}text\n{board((bx, by), START_P, BALL)}\n{FENCE}\n\n"
        f"**[▶ PLAY]({rel(HOME, game_path(0, START_P))})**\n\n"
        "<sub>Move your paddle left or right, keep the ball in play. "
        "No JavaScript: every frame is a pre-rendered markdown page and the buttons are links.</sub>\n"
    )


# ------------------------- state exploration -------------------------
def explore():
    """BFS over (tick, paddle_x) from the start. Returns (edges, game-over screens)."""
    start = (0, START_P)
    seen, queue = {start}, deque([start])
    edges, overs = {}, set()
    while queue:
        t, p = queue.popleft()
        nt = (t + 1) % PERIOD if ENDLESS else t + 1
        bx, by, _, _ = TRAJ[nt]
        dsts = []
        for move in (-1, 0, 1):                       # left, stay, right
            np_ = min(max(p + move, 0), MAX_P)
            if by == FLOOR and not (np_ <= bx < np_ + PADDLE_W):
                overs.add((nt, np_))                  # ball reached the floor, paddle missed
                dsts.append(over_path(nt, np_))
            elif not ENDLESS and nt == T_END:
                dsts.append(WIN_PATH)                 # final bounce was a hit
            else:
                if (nt, np_) not in seen:
                    seen.add((nt, np_))
                    queue.append((nt, np_))
                dsts.append(game_path(nt, np_))
        edges[(t, p)] = dsts
    return edges, overs


def write(path, text):
    os.makedirs(posixpath.dirname(path), exist_ok=True)
    data = text.rstrip("\n") + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)
    return len(data.encode("utf-8"))


def main():
    for sub in ("g", "o"):                            # only wipe our own subfolders
        shutil.rmtree(f"{OUT_DIR}/{sub}", ignore_errors=True)
    edges, overs = explore()
    total = 0
    for (t, p), dsts in edges.items():
        total += write(game_path(t, p), game_page(t, p, dsts))
    for t, p in overs:
        total += write(over_path(t, p), over_page(t, p))
    if not ENDLESS:
        total += write(WIN_PATH, win_page())
    write(SNIPPET_PATH, snippet())
    mode = "endless" if ENDLESS else f"first to {WIN_BOUNCES} bounces"
    print(f"mode: {mode}")
    print(f"{len(edges)} game pages + {len(overs)} game-over pages, {total / 1e6:.2f} MB of markdown")
    print(f"next: paste {SNIPPET_PATH} into {HOME}, then commit and push {OUT_DIR}/")


if __name__ == "__main__":
    main()
