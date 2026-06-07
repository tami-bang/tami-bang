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

BOOT_LOGS = [
    "공고 데이터를 모아 나에게 맞는 기회를 찾는 중",
    "작은 자동화를 끝까지 실행 가능한 시스템으로 바꾸는 중",
    "코드, 기록, 포트폴리오를 한 흐름으로 연결하는 중",
    "문제를 보면 먼저 파이프라인을 상상하는 중",
]

ASCII_FALLBACK = [
    "        .-''''-.        ",
    "      .'  tami  '.      ",
    "     /  data  ai  \\     ",
    "    |  backend sec |    ",
    "    |   build log  |    ",
    "     \\  portfolio /     ",
    "      '.________.'      ",
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
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "tami-bang-profile-neofetch"},
    )
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


def make_ascii_avatar(avatar_url, width=36):
    if not avatar_url or Image is None:
        return ASCII_FALLBACK

    try:
        image_bytes = request_bytes(avatar_url)
        image = Image.open(BytesIO(image_bytes)).convert("L")
    except Exception:
        return ASCII_FALLBACK

    image = crop_square(image)
    chars = "@%#*+=-:. "
    height = max(13, int(width * 0.52))
    image = image.resize((width, height))

    rows = []
    for y in range(image.height):
        row = []
        for x in range(image.width):
            pixel = image.getpixel((x, y))
            row.append(chars[pixel * (len(chars) - 1) // 255])
        rows.append("".join(row).rstrip())
    return rows


def crop_square(image):
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def format_number(value):
    if value is None:
        return "집계중"
    return f"{value:,}"


def today_boot_log():
    index = date.today().toordinal() % len(BOOT_LOGS)
    return BOOT_LOGS[index]


def collect_profile_data():
    user = safe_json(f"{API_ROOT}/users/{USER}", {})
    avatar_url = user.get("avatar_url") or f"https://github.com/{USER}.png?size=420"
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
        "mood": "조용히 집요하게, 끝까지 만드는 타입",
        "boot": today_boot_log(),
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
        (f"{data['user']}@TamiOS", "title"),
        ("-" * 36, "muted"),
        ("OS", "TamiOS / profile edition"),
        ("Host", data["host"]),
        ("Name", data["name"]),
        ("Role", data["role"]),
        ("Age", data["age"]),
        ("Mood", data["mood"]),
        ("Boot Log", data["boot"]),
        ("Repos", format_number(data["repos"])),
        ("Commits", format_number(data["commits"])),
        ("Stars", format_number(data["stars"])),
        ("Followers", format_number(data["followers"])),
        ("Code Lines", format_number(data["lines"])),
        ("Main Quest", "데이터를 모아 의사결정 가능한 리포트로 만들기"),
        ("Projects", data["projects"]),
        ("Stack", data["stack"]),
        ("Portfolio", data["portfolio"]),
        ("Email", data["email"]),
        ("Updated", data["updated"]),
    ]


def svg_text(text, x, y, fill, size=15, weight="400"):
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" '
        "font-family=\"'Pretendard', 'Apple SD Gothic Neo', 'Malgun Gothic', Consolas, Menlo, monospace\" "
        f'font-weight="{weight}">{escape(text)}</text>'
    )


def wrap_value(label, value, max_len=42):
    if len(value) <= max_len:
        return [(label, value)]
    wrapped = textwrap.wrap(value, max_len)
    return [(label, wrapped[0])] + [("", part) for part in wrapped[1:]]


def render_svg(data, theme):
    if theme == "dark":
        bg = "#0f1117"
        panel = "#171a21"
        border = "#343844"
        text = "#e6edf3"
        muted = "#9aa4b2"
        accent = "#ff8fb3"
        key = "#a7f3d0"
        avatar = "#ffd166"
        shadow = "#050608"
        chip_bg = "#242936"
    else:
        bg = "#fff8fb"
        panel = "#ffffff"
        border = "#ead7df"
        text = "#24212a"
        muted = "#766b75"
        accent = "#d6336c"
        key = "#087f5b"
        avatar = "#7c3aed"
        shadow = "#efdde5"
        chip_bg = "#fff0f5"

    width = 960
    height = 560
    parts = [
        f'<svg width="100%" height="auto" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" rx="24" fill="{bg}"/>',
        f'<rect x="30" y="32" width="{width - 60}" height="{height - 66}" rx="22" fill="{shadow}" opacity="0.42"/>',
        f'<rect x="22" y="24" width="{width - 60}" height="{height - 66}" rx="22" fill="{panel}" stroke="{border}" stroke-width="1.5"/>',
        f'<circle cx="55" cy="54" r="7" fill="#ff5f56"/><circle cx="78" cy="54" r="7" fill="#ffbd2e"/><circle cx="101" cy="54" r="7" fill="#27c93f"/>',
        svg_text("tami-os --profile --cute-but-practical", 128, 60, muted, 13),
        f'<rect x="42" y="82" width="286" height="390" rx="18" fill="{chip_bg}" stroke="{border}"/>',
        svg_text("profile.photo --ascii", 66, 112, accent, 15, "700"),
    ]

    y = 146
    for line in data["avatar"]:
        parts.append(svg_text(line, 62, y, avatar, 14, "700"))
        y += 18

    x = 370
    y = 102
    for item in build_terminal_lines(data):
        if len(item) == 2 and item[1] in {"title", "muted"}:
            value, style = item
            fill = accent if style == "title" else muted
            parts.append(svg_text(value, x, y, fill, 17, "800" if style == "title" else "400"))
            y += 24
            continue

        label, value = item
        for sub_label, sub_value in wrap_value(label, str(value)):
            if sub_label:
                parts.append(svg_text(f"{sub_label:>10}", x, y, key, 14, "800"))
                parts.append(svg_text(":", x + 96, y, muted, 14))
                parts.append(svg_text(sub_value, x + 112, y, text, 14))
            else:
                parts.append(svg_text(sub_value, x + 112, y, text, 14))
            y += 22

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
