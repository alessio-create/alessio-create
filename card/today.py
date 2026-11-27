# Draws the neofetch-style profile card (card/dark.svg, card/light.svg) with live GitHub stats.
# Needs GH_TOKEN: a classic token with `repo` + `read:user`, so private repos are counted.
# Runs daily from .github/workflows/card.yml. Locally: GH_TOKEN=$(gh auth token) py card/today.py
import base64, datetime, html, json, os, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
TOKEN = os.environ.get("GH_TOKEN")
if not TOKEN:
    print("GH_TOKEN missing: keeping the last card"); sys.exit(0)

def api(url, body=None):
    req = urllib.request.Request(
        url if url.startswith("http") else "https://api.github.com" + url,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-card"})
    with urllib.request.urlopen(req) as r:
        return r.status, (json.loads(r.read() or b"null"))

def gql(q):
    _, d = api("/graphql", {"query": q})
    if d.get("errors"): sys.exit(d["errors"])
    return d["data"]

# ---- stats ----
v = gql("""{ viewer { login createdAt
  repositories(ownerAffiliations: OWNER) { totalCount }
  pullRequests(states: MERGED) { totalCount } } }""")["viewer"]
login = v["login"]

contributions, year = 0, int(v["createdAt"][:4])
now = datetime.datetime.now(datetime.timezone.utc)
while year <= now.year:  # the contribution calendar is limited to one year per query
    d = gql(f'{{ viewer {{ contributionsCollection(from: "{year}-01-01T00:00:00Z", to: "{year}-12-31T23:59:59Z") '
            '{ contributionCalendar { totalContributions } } } }')
    contributions += d["viewer"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    year += 1

repos, page = [], 1
while True:
    _, batch = api(f"/user/repos?affiliation=owner&per_page=100&page={page}")
    repos += batch; page += 1
    if len(batch) < 100: break

MINE = {login, "Alessiodaleo"}  # both of my GitHub accounts; commits made with my personal email land on the second
BOTS = {"claude"}                 # commits Claude made for me: counted apart, and in lines of code
commits = bot_commits = added = deleted = 0
for r in repos:
    for _ in range(8):  # GitHub answers 202 while it computes the stats: retry
        status, stats = api(f"/repos/{r['full_name']}/stats/contributors")
        if status != 202: break
        time.sleep(4)
    if status == 202: print("skipped (stats still computing):", r["full_name"])  # next run catches it
    for s in stats or []:
        who = (s.get("author") or {}).get("login")
        if who in MINE | BOTS:
            if who in MINE: commits += s["total"]
            else: bot_commits += s["total"]
            added += sum(w["a"] for w in s["weeks"])
            deleted += sum(w["d"] for w in s["weeks"])

# ---- layout ----
W = 54  # characters in the info column
n = lambda x: f"{x:,}"

def row(key, value):
    dots = "." * max(1, W - len(key) - len(value) - 6)
    return [(". ", "dot"), (key, "key"), (": ", "dot"), (dots, "dot"), (" ", ""), (value, "val")]

def title(t, top=False):  # every line is W-1 characters wide
    lead = "" if top else "- "
    return [(lead, "dot"), (t, "head"), (" " + "─" * (W - 2 - len(lead) - len(t)), "dot")]

def stat(key, value, cls="num"):
    return [(". ", "dot"), (key, "key"), (": ", "dot"), (value, cls)]

blank = [(".", "dot")]
STATUS = "open for new builds"
PROMPT, CMD = "alessio@builder:~$ ", 'claude "build what\'s next"'  # CMD types itself, then erases
info = [
    title("github@" + login, top=True),
    row("OS", "Claude Code"),
    row("Uptime", "shipping since 2021"),
    row("Host", "Palermo, Italy"),
    row("Kernel", "performance marketer -> AI builder"),
    row("IDE", "Claude Code, Codex, Lovable"),
    blank,
    row("Languages.Programming", "English, Italian"),
    row("Languages.Agents", "skills, hooks, MCP"),
    row("Stack.Automation", "n8n, Make"),
    row("Stack.Ship", "Supabase, Vercel"),
    row("Hobbies", "building in public"),
    blank,
    title("Contact"),
    row("Website", "alessiodaleo.xyz"),
    row("LinkedIn", "alessiodaleo"),
    row("Instagram", "@alessiodaleo_ai"),
    row("Status", "  " + STATUS),  # the two spaces hold the pulsing dot, drawn as a circle
    blank,
    title("GitHub Stats"),
    stat("Repos", n(v["repositories"]["totalCount"])) + [(" | ", "dot")] + stat("PRs merged", n(v["pullRequests"]["totalCount"]))[1:],
    stat("Commits", n(commits)) + [(" | ", "dot")] + stat("by Claude", n(bot_commits))[1:],
    stat("Contributions", n(contributions)),
    stat("Lines of Code", n(added - deleted)) + [(" ( ", "dot"), (n(added) + "++", "add"), (", ", "dot"),
        (n(deleted) + "--", "del"), (" )", "dot")],
    blank,
    [("alessio@builder", "key"), (":", "dot"), ("~", "num"), ("$ ", "dot")],
]
STATUS_I = next(i for i, l in enumerate(info) if ("Status", "key") in l)
PROMPT_I = len(info) - 1

# art.json (coloured, from ascii_color.py) wins over art.txt (plain). Row = runs of [text, colour, is_eye].
J = HERE / "art.json"
art = json.loads(J.read_text()) if J.exists() else     [[[l, None, False]] for l in (HERE / "art.txt").read_text(encoding="utf-8").splitlines()]
ART_W = max(sum(len(r[0]) for r in row) for row in art)
FS, LH, CW = 16, 20, 9.6          # font size, line height, JetBrains Mono advance (0.6em)
ART_X, PAD = 28, 28
AFS = 11 if J.exists() else FS   # the coloured art uses a smaller font: more detail in the same space
ACW, ALH = AFS * .6, AFS * 1.2
INFO_X = ART_X + ART_W * ACW + 36
H = max(len(art) * ALH, len(info) * LH)
width = round(INFO_X + W * CW + PAD)
height = round(H + PAD * 2)
info_top = round(PAD + (H - len(info) * LH) / 2)   # both columns centred vertically
art_top = PAD + (H - len(art) * ALH) / 2

font = base64.b64encode((HERE / "mono.ttf").read_bytes()).decode()
THEMES = {
    "dark":  dict(bg="#0E0F13", art="#F6F2E7", dot="#5B616E", key="#5B9BF5", val="#F6F2E7", head="#F6F2E7",
                  num="#E8F04B", add="#7FD88F", dl="#E7302F"),
    "light": dict(bg="#F6F2E7", art="#0E0F13", dot="#9A968A", key="#0F5FCC", val="#0E0F13", head="#0E0F13",
                  num="#0A3E8C", add="#1E7A34", dl="#C4231F"),
}

def svg(t):
    c = THEMES[t]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
           f'font-family="JBMono, Consolas, Menlo, monospace" font-size="{FS}" role="img" aria-label="{login} profile card">',
           f"<style>@font-face{{font-family:JBMono;src:url(data:font/ttf;base64,{font}) format('truetype')}}text{{font-variant-ligatures:none}}"
           f".dot{{fill:{c['dot']}}}.key{{fill:{c['key']}}}.val{{fill:{c['val']}}}.head{{fill:{c['head']}}}"
           f".num{{fill:{c['num']}}}.add{{fill:{c['add']}}}.del{{fill:{c['dl']}}}"
           # Every 5s a ripple runs down the portrait: each row swings sideways as it passes.
           # The whole face also floats. Frame 0 is the still, whole face: viewers that freeze SVG images show it.
           f".a{{fill:{c['art']};fill-opacity:.9;animation:wave 5s ease-in-out infinite}}"
           f"@keyframes wave{{0%{{transform:none}}"
           f"5%{{transform:translateX({ACW * 2}px)}}10%{{transform:translateX(-{ACW * 1.5}px)}}"
           "15%,100%{transform:none}}"
           ".float{animation:float 4s ease-in-out infinite}@keyframes float{50%{transform:translateY(-5px)}}"
           # Status dot pulses. The prompt "types" CMD: a background-coloured cover and the cursor slide right
           # together one char per step, uncovering the text; hold, slide back (erase), every 8s.
           f".live{{fill:{c['add']};animation:pulse 2s ease-in-out infinite}}"
           "@keyframes pulse{50%{opacity:.25}}"
           f".cmd{{fill:{c['val']}}}.typer{{animation:move 8s infinite}}"
           f".cur{{fill:{c['key']};animation:blink 1s steps(1) infinite}}"
           f"@keyframes move{{0%{{transform:none;animation-timing-function:steps({len(CMD)},end)}}"
           f"20%,85%{{transform:translateX({len(CMD) * CW}px)}}85%{{animation-timing-function:steps(8,end)}}"
           "92%,100%{transform:none}}"
           "@keyframes blink{50%{opacity:0}}"
           ".eye{filter:url(#glow);animation:glow 2.4s ease-in-out infinite}@keyframes glow{50%{opacity:.5}}"
           "@media (prefers-reduced-motion:reduce){.a,.float,.live,.typer,.cur,.eye{animation:none}}</style>",
           '<defs><filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3" result="b"/>'
           '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>',
           f'<rect width="100%" height="100%" rx="14" fill="{c["bg"]}"/>']
    if J.exists():  # the coloured art is made for a dark screen: give it a dark disc in the light theme too
        out.append(f'<ellipse cx="{ART_X + ART_W * ACW / 2:.0f}" cy="{art_top + len(art) * ALH / 2 + 3:.0f}" '
                   f'rx="{ART_W * ACW / 2 + 10:.0f}" ry="{len(art) * ALH / 2 + 10:.0f}" fill="{THEMES["dark"]["bg"]}"/>')
    out.append('<g class="float">')
    for i, row in enumerate(art):
        y, col, plain, eyes = round(art_top + (i + 1) * ALH, 1), 0, "", []
        for text, colour, is_eye in row:
            if is_eye:  # drawn apart so it can glow; spaces keep the row aligned
                eyes.append(f'<text class="eye" x="{ART_X + col * ACW:.1f}" y="{y}" font-size="{AFS}" fill="{colour}">{html.escape(text)}</text>')
                plain += " " * len(text)
            else:
                plain += f'<tspan fill="{colour}">{html.escape(text)}</tspan>' if colour else html.escape(text)
            col += len(text)
        out.append(f'<g class="a" style="animation-delay:{300 + i * 70}ms">'
                   f'<text x="{ART_X}" y="{y}" font-size="{AFS}" xml:space="preserve">{plain or " "}</text>{"".join(eyes)}</g>')
    out.append("</g>")
    out.append(f'<text x="{INFO_X:.0f}" y="{info_top}" xml:space="preserve">')
    for line in info:
        segs = "".join(f'<tspan class="{cls}">{html.escape(s)}</tspan>' if cls else html.escape(s) for s, cls in line)
        out.append(f'<tspan x="{INFO_X:.0f}" dy="{LH}">{segs}</tspan>')
    out.append("</text>")
    base = lambda i: info_top + (i + 1) * LH                 # baseline of info row i
    dot_x = INFO_X + (W - 1 - len(STATUS) - 2 + 0.5) * CW    # first of the two spaces before STATUS
    cmd_x = INFO_X + len(PROMPT) * CW
    out += [f'<circle class="live" cx="{dot_x:.1f}" cy="{base(STATUS_I) - FS * .32:.1f}" r="{FS * .3:.1f}"/>',
            f'<text class="cmd" x="{cmd_x:.1f}" y="{base(PROMPT_I)}" xml:space="preserve">{html.escape(CMD)}</text>',
            f'<g class="typer"><rect x="{cmd_x:.1f}" y="{base(PROMPT_I) - LH + 2}" width="{(len(CMD) + 1) * CW:.1f}" '
            f'height="{LH}" fill="{c["bg"]}"/>',
            f'<rect class="cur" x="{cmd_x:.1f}" y="{base(PROMPT_I) - FS * .8:.1f}" width="{CW:.1f}" height="{FS:.0f}"/></g>',
            "</svg>"]
    return "\n".join(out)

for t in THEMES:
    (HERE / f"{t}.svg").write_text(svg(t), encoding="utf-8")
print(f"repos {len(repos)} commits {commits} claude {bot_commits} +{added} -{deleted} contributions {contributions}")
