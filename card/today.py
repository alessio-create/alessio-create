# Draws the profile card (card/card.svg): a CRT terminal with live GitHub stats, my ASCII shadow, binary rain.
# The look lives in crt.py; the portrait and titles come from static.py (run locally).
# Needs GH_TOKEN: a classic token with `repo` + `read:user`, so private repos are counted.
# Runs daily from .github/workflows/card.yml. Locally: GH_TOKEN=$(gh auth token) py card/today.py
import base64, datetime, html, json, os, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from crt import BG, CSS, DEFS, DIM, G, G2, PALE, PANEL, RED, bar, pixel, rain
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
PROMPT, CMD, ANSWER = "alessio@builder:~$ ", "human --verify", "> yes. probably."  # CMD types itself, ANSWER shows, both erase
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

ST = json.loads((HERE / "static.json").read_text())          # made by static.py
FS, LH, CW = 16, 20, 9.6                                      # font size, line height, JetBrains Mono advance (0.6em)
FW, FH = ST["fig"]
PX, PY, PAD = 470, 28, 22                                     # terminal panel: left edge, top, inner padding
PW = round(W * CW + PAD * 2)
INFO_X, BAR_Y = PX + PAD, PY + 24 + ST["title"]["size"][1] * 4 + 12
info_top = BAR_Y + 26
height = round(info_top + (len(info) + 1) * LH + 18 + PY)     # +1 row: the answer under the prompt
width = PX + PW + 28
FX, FY = 6, height - FH                                       # the figure stands on the bottom edge
EX, EY = FX + ST["eye"][0], FY + ST["eye"][1]
b64 = lambda f: base64.b64encode((HERE / f).read_bytes()).decode()
font = b64("mono.ttf")
C = dict(dot=DIM, key=G2, val=PALE, head=G, num=G, add=G, dl=RED,
         s0="#0B2014", s1="#123321", s2="#1C4A30", s3="#2C6A45", rim=G2)   # shadow tones dark -> light, rim

css = (f"@font-face{{font-family:JBMono;src:url(data:font/ttf;base64,{font}) format('truetype')}}text{{font-variant-ligatures:none}}"
       + "".join(f".{k}{{fill:{c}}}" for k, c in C.items() if k != "dl") + f".del{{fill:{RED}}}" + CSS
       # red eye pulses; status dot pulses; the prompt types CMD (a panel-coloured cover + cursor slide right together),
       # the answer appears, both erase: every 8s
       + ".eye{animation:pulse 2.2s ease-in-out infinite}.live{animation:pulse 2s ease-in-out infinite}@keyframes pulse{50%{opacity:.4}}"
       + f".typer{{animation:move 8s infinite}}.cur{{animation:blink 1s steps(1) infinite}}@keyframes blink{{50%{{opacity:0}}}}"
       + f"@keyframes move{{0%{{transform:none;animation-timing-function:steps({len(CMD)},end)}}"
       + f"20%,85%{{transform:translateX({len(CMD) * CW}px)}}85%{{animation-timing-function:steps(8,end)}}92%,100%{{transform:none}}}}"
       + ".ans{animation:ans 8s infinite}@keyframes ans{0%,22%{opacity:0}23%,85%{opacity:1}86%,100%{opacity:0}}"
       + "@media (prefers-reduced-motion:reduce){.eye,.live,.typer,.cur,.ans{animation:none}}")

def shadow_svg():  # my silhouette in ASCII (rows of [text, tone] from static.py)
    sh, out = ST["shadow"], []
    for i, row in enumerate(sh["rows"]):
        spans = "".join(f'<tspan class="{c}">{html.escape(t)}</tspan>' if c else t for t, c in row)
        out.append(f'<text x="{FX}" y="{FY + (i + 1) * sh["lh"]}" font-size="{sh["fs"]}" xml:space="preserve">{spans}</text>')
    return "".join(out)

base = lambda i: info_top + (i + 1) * LH                       # baseline of info row i
dot_x = INFO_X + (W - 1 - len(STATUS) - 2 + 0.5) * CW          # first of the two spaces before STATUS
cmd_x = INFO_X + len(PROMPT) * CW
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
       f'font-family="JBMono, Consolas, Menlo, monospace" font-size="{FS}" role="img" aria-label="{login} profile card">',
       f"<style>{css}</style>", DEFS,
       f'<rect width="100%" height="100%" rx="14" fill="{BG}"/><g class="flick">',
       f'<g opacity=".6">{rain(8, PX, height, seed=1)}</g>',
       f'<image href="data:image/png;base64,{b64("halo.png")}" x="{FX}" y="{FY}" width="{FW}" height="{FH}"/>',
       shadow_svg(),
       f'<circle class="eye" cx="{EX}" cy="{EY}" r="8" fill="{RED}" filter="url(#glow)"/><circle cx="{EX}" cy="{EY}" r="3" fill="#FFC2B8"/>',
       f'<rect x="{PX}" y="{PY}" width="{PW}" height="{height - 2 * PY}" rx="6" fill="{PANEL}" stroke="{DIM}"/>',
       pixel(ST["title"], INFO_X, PY + 20), bar(INFO_X, BAR_Y, PW - 2 * PAD),
       f'<text x="{INFO_X:.0f}" y="{info_top}" xml:space="preserve">']
for line in info:
    segs = "".join(f'<tspan class="{cls}">{html.escape(s)}</tspan>' if cls else html.escape(s) for s, cls in line)
    out.append(f'<tspan x="{INFO_X:.0f}" dy="{LH}">{segs}</tspan>')
out += ["</text>",
        f'<circle class="live" cx="{dot_x:.1f}" cy="{base(STATUS_I) - FS * .32:.1f}" r="{FS * .3:.1f}" fill="{G}"/>',
        f'<text x="{cmd_x:.1f}" y="{base(PROMPT_I)}" fill="{PALE}" xml:space="preserve">{html.escape(CMD)}</text>',
        f'<text class="ans" x="{INFO_X}" y="{base(PROMPT_I + 1)}" fill="{RED}" xml:space="preserve">{html.escape(ANSWER)}</text>',
        f'<g class="typer"><rect x="{cmd_x:.1f}" y="{base(PROMPT_I) - LH + 2}" width="{(len(CMD) + 1) * CW:.1f}" height="{LH + 4}" fill="{PANEL}"/>',
        f'<rect class="cur" x="{cmd_x:.1f}" y="{base(PROMPT_I) - FS * .8:.1f}" width="{CW:.1f}" height="{FS:.0f}" fill="{G}"/></g>',
        f'</g><rect width="100%" height="100%" rx="14" fill="url(#sl)"/></svg>']
(HERE / "card.svg").write_text("\n".join(out), encoding="utf-8")
print(f"repos {len(repos)} commits {commits} claude {bot_commits} +{added} -{deleted} contributions {contributions}")
