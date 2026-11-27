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
    blank,
    title("GitHub Stats"),
    stat("Repos", n(v["repositories"]["totalCount"])) + [(" | ", "dot")] + stat("PRs merged", n(v["pullRequests"]["totalCount"]))[1:],
    stat("Commits", n(commits)) + [(" | ", "dot")] + stat("by Claude", n(bot_commits))[1:],
    stat("Contributions", n(contributions)),
    stat("Lines of Code", n(added - deleted)) + [(" ( ", "dot"), (n(added) + "++", "add"), (", ", "dot"),
        (n(deleted) + "--", "del"), (" )", "dot")],
]

art = (HERE / "art.txt").read_text(encoding="utf-8").splitlines()
FS, LH, CW = 16, 20, 9.6          # font size, line height, JetBrains Mono advance (0.6em)
ART_X, PAD = 28, 28
INFO_X = ART_X + max(map(len, art)) * CW + 36
rows = max(len(art), len(info))
width = round(INFO_X + W * CW + PAD)
height = rows * LH + PAD * 2
info_top = PAD + (rows - len(info)) // 2 * LH   # center the info column against the art

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
           # A light runs down the portrait every 5s; a few rows glitch sideways now and then.
           # Frame 0 is the whole face (no hidden start): viewers that freeze SVG images still show it.
           f".a{{fill:{c['art']};fill-opacity:.9;animation:wave 5s ease-out infinite}}"
           ".g{animation:wave 5s ease-out infinite,glitch 7s steps(1) infinite}"
           f"@keyframes wave{{0%{{fill:{c['key']};fill-opacity:1}}10%,100%{{fill:{c['art']};fill-opacity:.9}}}}"
           f"@keyframes glitch{{0%{{transform:translateX({CW}px);fill:{c['num']}}}1.5%{{transform:translateX(-{CW}px)}}"
           "3%,100%{transform:none}}"
           "@media (prefers-reduced-motion:reduce){.a{animation:none}}</style>",
           f'<rect width="100%" height="100%" rx="14" fill="{c["bg"]}"/>']
    GLITCH = {6: 3100, 13: 4600, 20: 5800}  # row -> delay (ms) of its sideways jump
    for i, l in enumerate(art):
        wave = f"{300 + i * 60}ms"
        cls, delay = ("a g", f"{wave},{GLITCH[i]}ms") if i in GLITCH else ("a", wave)
        out.append(f'<text class="{cls}" x="{ART_X}" y="{PAD + (i + 1) * LH}" xml:space="preserve" '
                   f'style="animation-delay:{delay}">{html.escape(l) or " "}</text>')
    out.append(f'<text x="{INFO_X:.0f}" y="{info_top}" xml:space="preserve">')
    for line in info:
        segs = "".join(f'<tspan class="{cls}">{html.escape(s)}</tspan>' if cls else html.escape(s) for s, cls in line)
        out.append(f'<tspan x="{INFO_X:.0f}" dy="{LH}">{segs}</tspan>')
    out.append("</text></svg>")
    return "\n".join(out)

for t in THEMES:
    (HERE / f"{t}.svg").write_text(svg(t), encoding="utf-8")
print(f"repos {len(repos)} commits {commits} claude {bot_commits} +{added} -{deleted} contributions {contributions}")
