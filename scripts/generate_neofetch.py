import json
import os
import textwrap
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from html import escape
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover - GitHub Actions installs Pillow.
    Image = None


USER = os.getenv("PROFILE_USER", "tami-bang")
NAME = os.getenv("PROFILE_NAME", "Tami Bang")
BIRTHDAY = os.getenv("PROFILE_BIRTHDAY", "")
PORTFOLIO_URL = "https://tami-bang.github.io/"
EMAIL = "vjihyunbangv@gmail.com"
API_ROOT = "https://api.github.com"
OUTPUT_DIR = Path("assets")

PROJECTS = [
    "JobKorea Job Radar",
    "GateGuard",
    "Health AI Search API",
]

STACK = [
    "Python",
    "FastAPI",
    "Selenium",
    "SQLite",
    "Pandas",
    "C",
    "Next.js",
]

ASCII_FALLBACK = [
    "      _________      ",
    "   .-'  TAMI   '-.   ",
    "  /   DATA  AI    \\  ",
    " |  BACKEND  SEC   | ",
    " |  BUILD SYSTEMS  | ",
    "  \\   PORTFOLIO   /  ",
    "   '-._________.-'   ",
]


def request_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "tami-bang-profile-neofetch",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def request_bytes(url):
    request = urllib.request.Request(url, headers={"User-Agent": "tami-bang-profile-neofetch"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def safe_json(url, default):
    try:
        return request_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return default


def fetch_all_repos():
    repos = []
    page = 1
    while page <= 5:
        url = f"{API_ROOT}/users/{USER}/repos?type=owner&sort=updated&per_page=100&page={page}"
        page_repos = safe_json(url, [])
        if not page_repos:
            break
        repos.extend([repo for repo in page_repos if not repo.get("fork")])
        page += 1
    return repos


def count_commits_and_lines(repos):
    commit_count = 0
    additions = 0
    deletions = 0

    for repo in repos[:30]:
        name = repo["name"]
        commits_url = f"{API_ROOT}/repos/{USER}/{name}/commits?author={USER}&per_page=100"
        commits = safe_json(commits_url, [])
        if not isinstance(commits, list):
            continue

        commit_count += len(commits)
        for commit in commits[:60]:
            detail_url = commit.get("url")
            if not detail_url:
                continue
            detail = safe_json(detail_url, {})
            stats = detail.get("stats", {})
            additions += int(stats.get("additions", 0) or 0)
            deletions += int(stats.get("deletions", 0) or 0)

    return commit_count, additions, deletions


def count_search_commits():
    url = f"{API_ROOT}/search/commits?q=author:{USER}"
    headers = {
        "Accept": "application/vnd.github.cloak-preview+json",
        "User-Agent": "tami-bang-profile-neofetch",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data.get("total_count")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None


def calculate_age():
    if not BIRTHDAY:
        return "비공개"

    try:
        born = datetime.strptime(BIRTHDAY, "%Y-%m-%d").date()
    except ValueError:
        return "비공개"

    today = date.today()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return f"{age}세"


def make_ascii_avatar(avatar_url, width=28):
    if not avatar_url or Image is None:
        return ASCII_FALLBACK

    try:
        image_bytes = request_bytes(avatar_url)
        image = Image.open(BytesIO(image_bytes)).convert("L")
    except Exception:
        return ASCII_FALLBACK

    chars = "@%#*+=-:. "
    aspect = image.height / image.width
    height = max(8, int(width * aspect * 0.48))
    image = image.resize((width, height))

    rows = []
    for y in range(image.height):
        row = []
        for x in range(image.width):
            pixel = image.getpixel((x, y))
            row.append(chars[pixel * (len(chars) - 1) // 255])
        rows.append("".join(row).rstrip())
    return rows


def format_number(value):
    if value is None:
        return "집계중"
    return f"{value:,}"


def collect_profile_data():
    user = safe_json(f"{API_ROOT}/users/{USER}", {})
    avatar_url = user.get("avatar_url") or f"https://github.com/{USER}.png?size=220"
    repos = fetch_all_repos()
    stars = sum(int(repo.get("stargazers_count", 0) or 0) for repo in repos)
    commit_count, additions, deletions = count_commits_and_lines(repos)
    search_commits = count_search_commits()

    if search_commits is not None:
        commit_count = max(commit_count, int(search_commits))

    return {
        "name": NAME,
        "user": USER,
        "age": calculate_age(),
        "host": "GitHub Profile README",
        "role": "AI · Backend · Security",
        "uptime": "문제를 시스템으로 바꾸는 중",
        "repos": len(repos) or user.get("public_repos", 0),
        "followers": user.get("followers", 0),
        "stars": stars,
        "commits": commit_count,
        "lines": additions + deletions,
        "portfolio": PORTFOLIO_URL,
        "email": EMAIL,
        "projects": " · ".join(PROJECTS),
        "stack": " · ".join(STACK),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "avatar": make_ascii_avatar(avatar_url),
    }


def build_terminal_lines(data):
    return [
        (f"{data['user']}@github", "accent"),
        ("-" * 31, "muted"),
        ("OS", "GitHub Profile / neofetch-kor"),
        ("Host", data["host"]),
        ("Name", data["name"]),
        ("Role", data["role"]),
        ("Age", data["age"]),
        ("Uptime", data["uptime"]),
        ("Repos", format_number(data["repos"])),
        ("Commits", format_number(data["commits"])),
        ("Stars", format_number(data["stars"])),
        ("Followers", format_number(data["followers"])),
        ("Code Lines", format_number(data["lines"])),
        ("Projects", data["projects"]),
        ("Stack", data["stack"]),
        ("Portfolio", data["portfolio"]),
        ("Email", data["email"]),
        ("Updated", data["updated"]),
    ]


def svg_text(text, x, y, fill, size=15, weight="400"):
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" '
        f'font-weight="{weight}" font-family="Consolas, Menlo, Monaco, monospace">'
        f"{escape(text)}</text>"
    )


def wrap_value(label, value, max_len=48):
    if len(value) <= max_len:
        return [(label, value)]
    wrapped = textwrap.wrap(value, max_len)
    return [(label, wrapped[0])] + [("", part) for part in wrapped[1:]]


def render_svg(data, theme):
    if theme == "dark":
        bg = "#0d1117"
        panel = "#161b22"
        border = "#30363d"
        text = "#c9d1d9"
        muted = "#8b949e"
        accent = "#58a6ff"
        key = "#7ee787"
        avatar = "#f778ba"
        shadow = "#010409"
    else:
        bg = "#f6f8fa"
        panel = "#ffffff"
        border = "#d0d7de"
        text = "#24292f"
        muted = "#57606a"
        accent = "#0969da"
        key = "#1a7f37"
        avatar = "#8250df"
        shadow = "#d8dee4"

    width = 900
    height = 500
    parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" rx="18" fill="{bg}"/>',
        f'<rect x="20" y="20" width="{width - 40}" height="{height - 40}" rx="16" fill="{shadow}" opacity="0.22"/>',
        f'<rect x="16" y="16" width="{width - 40}" height="{height - 40}" rx="16" fill="{panel}" stroke="{border}"/>',
        f'<circle cx="45" cy="43" r="7" fill="#ff5f56"/><circle cx="68" cy="43" r="7" fill="#ffbd2e"/><circle cx="91" cy="43" r="7" fill="#27c93f"/>',
        svg_text("tami-bang neofetch", 118, 49, muted, 13),
    ]

    y = 92
    for line in data["avatar"]:
        parts.append(svg_text(line, 52, y, avatar, 15, "700"))
        y += 18

    x = 370
    y = 90
    for item in build_terminal_lines(data):
        if len(item) == 2 and item[1] in {"accent", "muted"}:
            value, style = item
            fill = accent if style == "accent" else muted
            parts.append(svg_text(value, x, y, fill, 16, "700" if style == "accent" else "400"))
            y += 21
            continue

        label, value = item
        for sub_label, sub_value in wrap_value(label, str(value)):
            if sub_label:
                parts.append(svg_text(f"{sub_label:>10}", x, y, key, 14, "700"))
                parts.append(svg_text(":", x + 86, y, muted, 14))
                parts.append(svg_text(sub_value, x + 102, y, text, 14))
            else:
                parts.append(svg_text(sub_value, x + 102, y, text, 14))
            y += 21

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    data = collect_profile_data()

    for theme in ("light", "dark"):
        (OUTPUT_DIR / f"neofetch-{theme}.svg").write_text(
            render_svg(data, theme),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
