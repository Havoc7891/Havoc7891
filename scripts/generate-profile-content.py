import argparse
import base64
import hashlib
import os
import re
import sys
import feedparser
import requests
from datetime import datetime, timezone
from collections import Counter
from html import escape
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

NEWSPAGEURL = "https://havoc.de/articles"
FEEDURL = "https://havoc.de/rss.xml"
FEEDMAXDATES = 5
FEEDTIMEZONE = ZoneInfo("Europe/Berlin")
USERNAME = "Havoc7891"
READMEPATH = "README.md"
DEFAULTOUTPUTPATH = "generated-profile-content.md"
REQUESTTIMEOUT = 20
NEWSHEADING = "## 📰 Latest News"
VIDEOSHEADING = "## 📹 Latest Videos"
LANGUAGESHEADING = "## 📊 Top Languages Across My Public GitHub Repositories"
TOOLSHEADING = "## 🧰 Tools & Technologies I Use"
MINLANGUAGEPERCENT = 0.1 # Group all languages below this percentage under "Other"
GITHUBLANGUAGECOLORS = {
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#7355dd",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#663399",
    "Java": "#b07219",
    "PHP": "#4f5d95",
    "SQL": "#e38c00",
    "Python": "#3572a5",
    "CMake": "#da3434",
    "PowerShell": "#012456",
    "Other": "#ededed",
}
LEGENDICONSFOLDER = "assets/legend-icons"
TOPLANGUAGESSVGPATH = "top-languages.svg"
YOUTUBECHANNELID = "UCaGa30jV6OWFpjBWY3r4GWQ"
YOUTUBEMAXENTRIES = 6
YOUTUBEVIDEOIDPATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")

class DynamicContentError(RuntimeError):
    pass

def fetchResponse(url: str, sourceName: str, **kwargs):
    try:
        response = requests.get(url, timeout=REQUESTTIMEOUT, **kwargs)
    except requests.RequestException as ex:
        raise DynamicContentError(f"{sourceName} request failed: {ex}") from ex

    if not response.ok:
        raise DynamicContentError(f"{sourceName} returned HTTP {response.status_code}.")

    return response

def fetchJson(url: str, sourceName: str, **kwargs):
    response = fetchResponse(url, sourceName, **kwargs)

    try:
        return response.json()
    except ValueError as ex:
        raise DynamicContentError(f"{sourceName} returned malformed JSON.") from ex

def extractReadmeSection(startHeading: str, endHeading: str, sectionName: str) -> str:
    try:
        with open(READMEPATH, "r", encoding="utf-8") as file:
            readme = file.read()
    except FileNotFoundError as ex:
        raise DynamicContentError(f"Cannot preserve {sectionName}: {READMEPATH} does not exist.") from ex

    start = readme.find(startHeading)
    if start == -1:
        raise DynamicContentError(f"Cannot preserve {sectionName}: heading '{startHeading}' was not found.")

    end = readme.find(endHeading, start + len(startHeading))
    if end == -1:
        raise DynamicContentError(f"Cannot preserve {sectionName}: next heading '{endHeading}' was not found.")

    return readme[start:end].rstrip()

def buildSectionOrPreserve(sectionName: str, startHeading: str, endHeading: str, builder):
    try:
        return builder()
    except DynamicContentError as ex:
        print(f"Warning: preserving existing {sectionName}: {ex}", file=sys.stderr)
        return extractReadmeSection(startHeading, endHeading, sectionName)

def getAggregatedLanguages() -> dict:
    token = os.getenv("GH_TOKEN")
    if not token:
        raise DynamicContentError("GH_TOKEN is missing.")

    headers = {"Authorization": f"Bearer {token}"}
    reposUrl = f"https://api.github.com/users/{USERNAME}/repos"

    repos = []
    page = 1
    while True:
        data = fetchJson(
            reposUrl,
            f"GitHub repository page {page}",
            headers=headers,
            params={"page": page, "per_page": 100},
        )
        if not isinstance(data, list):
            raise DynamicContentError(f"GitHub repository page {page} returned malformed data.")
        if not data:
            break
        repos.extend(data)
        page += 1

    if not repos:
        raise DynamicContentError("GitHub returned no repositories.")

    langTotals = Counter()
    usableRepos = 0

    for repo in repos:
        if not isinstance(repo, dict):
            raise DynamicContentError("GitHub returned a malformed repository entry.")

        # Skip forked repositories
        if repo.get("fork"):
            continue

        usableRepos += 1
        langUrl = repo.get("languages_url")
        if not langUrl:
            continue

        langData = fetchJson(langUrl, f"GitHub language data for {repo.get('name', 'unknown repository')}", headers=headers)
        if not isinstance(langData, dict):
            raise DynamicContentError(f"GitHub language data for {repo.get('name', 'unknown repository')} returned malformed data.")
        langTotals.update(langData)

    if usableRepos == 0:
        raise DynamicContentError("GitHub returned no non-fork repositories.")

    totalBytes = sum(langTotals.values())
    if totalBytes == 0:
        raise DynamicContentError("GitHub returned zero language bytes.")

    return {
        lang: round((count / totalBytes) * 100, 2)
        for lang, count in langTotals.most_common()
    }

def generateTopLanguagesSvg(languages: dict):
    if not languages:
        svg = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="40" viewBox="0 0 400 40" role="img">
  <title>Top Languages</title>
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="14">
    No language data
  </text>
</svg>
"""
        with open(TOPLANGUAGESSVGPATH, "w", encoding="utf-8") as file:
            file.write(svg)
        return

    # Sort languages by percentage descending
    items = sorted(languages.items(), key=lambda x: x[1], reverse=True)

    # SVG layout
    width = 720
    height = 12
    barX = 0
    barY = 2
    barHeight = 8
    radius = barHeight / 2

    currentX = barX

    svgParts = []

    svgParts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
    )
    svgParts.append("<title>Top Languages</title>")

    # Clip path to get rounded ends for the whole stacked bar
    svgParts.append("<defs>")
    svgParts.append(
        f'<clipPath id="barClip">'
        f'<rect x="{barX}" y="{barY}" width="{width}" height="{barHeight}" '
        f'rx="{radius}" ry="{radius}" />'
        f'</clipPath>'
    )
    svgParts.append("</defs>")

    # Group for stacked segments, clipped to rounded rect
    svgParts.append(f'<g clip-path="url(#barClip)">')

    totalPct = sum(p for _, p in items) or 1.0

    for i, (lang, pct) in enumerate(items):
        if pct <= 0:
            continue

        segmentWidth = width * (pct / totalPct)

        # Ensure last segment ends exactly at bar width to avoid gaps from float rounding
        if i == len(items) - 1:
            segmentWidth = width - (currentX - barX)

        color = GITHUBLANGUAGECOLORS.get(lang, "#999999")

        svgParts.append(
            f'<rect x="{currentX:.2f}" y="{barY}" width="{segmentWidth:.2f}" '
            f'height="{barHeight}" fill="{color}" />'
        )

        currentX += segmentWidth

    svgParts.append("</g>")
    svgParts.append("</svg>")

    with open(TOPLANGUAGESSVGPATH, "w", encoding="utf-8") as file:
        file.write("\n".join(svgParts))

def generateLegendCircleSvg(color: str, filename: str):
    os.makedirs(LEGENDICONSFOLDER, exist_ok=True)

    # SVG template
    svgTemplate = f"""<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12">
<circle cx="6" cy="6" r="5" fill="{color}" />
</svg>
"""

    # Compute hash of the content
    newHash = hashlib.sha256(svgTemplate.encode("utf-8")).hexdigest()

    # If file exists, compare hash
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as file:
            existing = file.read()
        existingHash = hashlib.sha256(existing.encode("utf-8")).hexdigest()

        if existingHash == newHash:
            # Cache hit: no need to rewrite file
            return

    # Cache miss: write new file
    with open(filename, "w", encoding="utf-8") as file:
        file.write(svgTemplate)

def cleanupLegendIcons(currentLanguages: dict):
    if not os.path.isdir(LEGENDICONSFOLDER):
        return # Nothing to clean

    # Create the set of expected filenames
    expected = set()
    for lang in currentLanguages:
        safeName = lang.lower().replace("#", "sharp").replace("+", "plus")
        expected.add(f"legend-{safeName}.svg")

    # Walk through the folder and delete old ones
    for filename in os.listdir(LEGENDICONSFOLDER):
        if filename.endswith(".svg") and filename.startswith("legend-"):
            if filename not in expected:
                os.remove(os.path.join(LEGENDICONSFOLDER, filename))

def buildLanguagesSection(languages: dict):
    if not languages:
        raise DynamicContentError("No language stats are available.")

    os.makedirs(LEGENDICONSFOLDER, exist_ok=True)

    # Generate / update the SVG file for the stacked bar
    generateTopLanguagesSvg(languages)

    # Markdown section embedding the SVG
    lines = [
        LANGUAGESHEADING,
        "",
        f"![Top Languages]({TOPLANGUAGESSVGPATH})",
        "",
    ]

    # Generate / update legend
    for lang, pct in sorted(languages.items(), key=lambda x: x[1], reverse=True):
        color = GITHUBLANGUAGECOLORS.get(lang, "#999999")
        safeName = lang.lower().replace("#", "sharp").replace("+", "plus")
        iconFile = os.path.join(LEGENDICONSFOLDER, f"legend-{safeName}.svg")
        generateLegendCircleSvg(color, iconFile)
        webPath = iconFile.replace(os.sep, "/")
        lines.append(f"<img src=\"{webPath}\" width=\"12\" height=\"12\"> **{lang}** {pct:.1f}%")

    cleanupLegendIcons(languages)

    return "\n".join(lines)

def formatViewCount(value):
    if not isinstance(value, str) or not value.isdigit():
        raise DynamicContentError("YouTube RSS feed returned a malformed view count.")

    count = int(value)
    for minimum, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if count >= minimum:
            compact = f"{count / minimum:.1f}".removesuffix(".0")
            return f"{compact}{suffix}"

    return str(count)

def fetchLatestYouTubeVideos():
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={YOUTUBECHANNELID}"
    response = fetchResponse(url, "YouTube RSS feed")
    if not response.content or not response.content.strip():
        raise DynamicContentError("YouTube RSS feed returned an empty response.")

    feed = feedparser.parse(response.content)
    if feed.get("bozo"):
        raise DynamicContentError(f"YouTube RSS feed could not be parsed: {feed.get('bozo_exception')}")

    entries = feed.entries[:YOUTUBEMAXENTRIES] if hasattr(feed, "entries") else []
    if not entries:
        raise DynamicContentError("YouTube RSS feed returned no videos.")

    videos = []
    for entry in entries:
        videoId = entry.get("yt_videoid")
        title = entry.get("title")
        publishedParsed = entry.get("published_parsed")
        statistics = entry.get("media_statistics")
        viewCount = statistics.get("views") if isinstance(statistics, dict) else None
        if not title or not publishedParsed or not isinstance(videoId, str):
            raise DynamicContentError("YouTube RSS feed returned incomplete video data.")
        if not YOUTUBEVIDEOIDPATTERN.fullmatch(videoId):
            raise DynamicContentError("YouTube RSS feed returned an invalid video ID.")

        published = datetime(*publishedParsed[:6]).strftime("%B %d, %Y")

        videos.append({
            "title": title,
            "url": f"https://www.youtube.com/watch?v={videoId}",
            "thumb": f"https://i.ytimg.com/vi/{videoId}/maxresdefault.jpg",
            "published": published,
            "viewCount": formatViewCount(viewCount)
        })

    return videos

def buildVideosSection(videos):
    if not videos:
        raise DynamicContentError("No recent videos are available.")

    htmlParts = [VIDEOSHEADING, "\n\n", "<table>\n"]

    for index in range(0, len(videos), 2):
        htmlParts.append("  <tr>\n")

        for video in videos[index:index + 2]:
            label = f'{escape(video["title"], quote=True)} | {video["published"]}'
            htmlParts.append(
                "    <td align=\"center\" valign=\"top\">\n"
                f'      <a href="{video["url"]}">'
                f'<img src="{video["thumb"]}" width="400" '
                f'alt="{label}" title="{label}" aria-label="{label}">'
                "</a>\n"
                f'      <div align="right">◉ {video["viewCount"]} views</div>\n'
                "    </td>\n"
            )

        htmlParts.append("  </tr>\n")

    htmlParts.append("</table>")

    return "".join(htmlParts)

def formatFeedEntries(entries):
    if not entries:
        raise DynamicContentError("RSS feed returned no entries.")

    groups = []
    currentGroupKey = None

    for entryIndex, entry in enumerate(entries):
        publishedParsed = entry.get("published_parsed")
        if publishedParsed:
            published = datetime(*publishedParsed[:6], tzinfo=timezone.utc).astimezone(FEEDTIMEZONE)
            groupKey = published.strftime("%Y-%m-%d")
            publicationDate = published.strftime("%m/%d/%Y")
            publicationTime = published.strftime("%I:%M %p")
        else:
            groupKey = f"unknown-{entryIndex}"
            publicationDate = "Unknown Date"
            publicationTime = None

        if groupKey != currentGroupKey:
            if len(groups) >= FEEDMAXDATES:
                break

            groups.append({
                "date": publicationDate,
                "entries": [],
            })
            currentGroupKey = groupKey

        title = entry.get("title")
        link = entry.get("link")
        if not title or not link:
            raise DynamicContentError("RSS feed returned an entry without title or link.")

        groups[-1]["entries"].append({
            "title": title,
            "link": link,
            "time": publicationTime,
        })

    lines = []

    for group in groups:
        groupEntries = group["entries"]
        if len(groupEntries) == 1:
            entry = groupEntries[0]
            lines.append(f'- {group["date"]} - [{entry["title"]}]({entry["link"]})')
            continue

        lines.append(f'- {group["date"]}')
        for entry in groupEntries:
            lines.append(f'  - {entry["time"]} - [{entry["title"]}]({entry["link"]})')

    if lines:
        lines.append("")

    lines.append(f"[More news on havoc.de]({NEWSPAGEURL})")

    return "\n".join(lines)

def fetchFeedEntries():
    response = fetchResponse(FEEDURL, "RSS feed")
    if not response.content or not response.content.strip():
        raise DynamicContentError("RSS feed returned an empty response.")

    feed = feedparser.parse(response.content)
    if feed.get("bozo"):
        raise DynamicContentError(f"RSS feed could not be parsed: {feed.get('bozo_exception')}")

    if not hasattr(feed, "entries"):
        raise DynamicContentError("RSS feed returned malformed data.")

    return formatFeedEntries(feed.entries)

def buildNewsSection():
    return f"{NEWSHEADING}\n\n{fetchFeedEntries()}"

def buildLanguageStatsSection():
    languages = getAggregatedLanguages()

    mainLanguages = {k: v for k, v in languages.items() if v >= MINLANGUAGEPERCENT}
    otherTotal = sum(v for v in languages.values() if v < MINLANGUAGEPERCENT)

    if otherTotal > 0:
        mainLanguages["Other"] = round(otherTotal, 2)

    languages = mainLanguages

    return buildLanguagesSection(languages)

def buildCustomLogoBadge(name: str, color: str, logoPath: str) -> str:
    try:
        with open(logoPath, "rb") as file:
            encodedLogo = base64.b64encode(file.read()).decode("ascii")
    except OSError as ex:
        raise DynamicContentError(f"Cannot read badge logo {logoPath}: {ex}") from ex

    query = urlencode({
        "style": "for-the-badge",
        "logo": f"data:image/svg+xml;base64,{encodedLogo}",
    })
    return f"![{name}](https://img.shields.io/badge/{quote(name, safe='')}-{color.lower()}?{query})"

def generateReadme(outputPath: str):
    havRemoteBadge = buildCustomLogoBadge("havRemote", "c40000", "assets/logos/havRemote.svg")

    newsSection = buildSectionOrPreserve(
        "Latest News",
        NEWSHEADING,
        VIDEOSHEADING,
        buildNewsSection,
    )

    videosSection = buildSectionOrPreserve(
        "Latest Videos",
        VIDEOSHEADING,
        LANGUAGESHEADING,
        lambda: buildVideosSection(fetchLatestYouTubeVideos()),
    )

    languagesSection = buildSectionOrPreserve(
        "Top Languages",
        LANGUAGESHEADING,
        TOOLSHEADING,
        buildLanguageStatsSection,
    )

    toolsSection = f"""\
## 🧰 Tools & Technologies I Use

### 💻 Languages, Frameworks & Libraries

![C](https://img.shields.io/badge/C-555555?logo=c&logoColor=white&style=for-the-badge)
![C++](https://img.shields.io/badge/C++-f34b7d?logo=cplusplus&logoColor=white&style=for-the-badge)
![C#](https://img.shields.io/badge/C%23-7355dd?style=for-the-badge)
![.NET](https://img.shields.io/badge/.NET-512bd4?logo=dotnet&logoColor=white&style=for-the-badge)
![Blazor](https://img.shields.io/badge/Blazor-512bd4?logo=blazor&logoColor=white&style=for-the-badge)
![MudBlazor](https://img.shields.io/badge/MudBlazor-594ae2?style=for-the-badge)
![wxWidgets](https://img.shields.io/badge/wxWidgets-2222ff?style=for-the-badge)
![HTML5](https://img.shields.io/badge/HTML5-e34c26?logo=html5&logoColor=white&style=for-the-badge)
![CSS3](https://img.shields.io/badge/CSS3-663399?logo=css&logoColor=white&style=for-the-badge)
![JavaScript](https://img.shields.io/badge/JavaScript-f1e05a?logo=javascript&logoColor=black&style=for-the-badge)
![TypeScript](https://img.shields.io/badge/TypeScript-3178c6?logo=typescript&logoColor=white&style=for-the-badge)
![jQuery](https://img.shields.io/badge/jQuery-0769ad?logo=jquery&logoColor=white&style=for-the-badge)
![Angular](https://img.shields.io/badge/Angular-dd0031?logo=angular&logoColor=white&style=for-the-badge)
![RxJS](https://img.shields.io/badge/RxJS-b7178c?logo=reactivex&logoColor=white&style=for-the-badge)
![Node.js](https://img.shields.io/badge/Node.js-339933?logo=node.js&logoColor=white&style=for-the-badge)
![Express](https://img.shields.io/badge/Express-000000?logo=express&logoColor=white&style=for-the-badge)
![Sequelize](https://img.shields.io/badge/Sequelize-52b0e7?logo=sequelize&logoColor=white&style=for-the-badge)
![SDL](https://img.shields.io/badge/SDL-132a47?style=for-the-badge)
![OpenGL](https://img.shields.io/badge/OpenGL-5586a4?logo=opengl&logoColor=white&style=for-the-badge)
![PHP](https://img.shields.io/badge/PHP-4f5d95?logo=php&logoColor=white&style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3572a5?logo=python&logoColor=white&style=for-the-badge)

### ☁️ Cloud, DevOps & Backend

![Azure](https://img.shields.io/badge/Azure-0078d4?logo=microsoftazure&logoColor=white&style=for-the-badge)
![Azure DevOps](https://img.shields.io/badge/Azure_DevOps-4697e9?logo=azuredevops&logoColor=white&style=for-the-badge)
![Git](https://img.shields.io/badge/Git-f05032?logo=git&logoColor=white&style=for-the-badge)
![MySQL](https://img.shields.io/badge/MySQL-4479a1?logo=mysql&logoColor=white&style=for-the-badge)
![MariaDB](https://img.shields.io/badge/MariaDB-003545?logo=mariadb&logoColor=white&style=for-the-badge)
![Azure SQL](https://img.shields.io/badge/Azure_SQL-1572b9?logo=microsoftsqlserver&logoColor=white&style=for-the-badge)
![SQL Server](https://img.shields.io/badge/SQL_Server-cc2927?logo=microsoftsqlserver&logoColor=white&style=for-the-badge)
![Apache](https://img.shields.io/badge/Apache-ab0000?logo=apache&logoColor=white&style=for-the-badge)

### 🎨 Frontend Styling

![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-06b6d4?logo=tailwindcss&logoColor=white&style=for-the-badge)
![daisyUI](https://img.shields.io/badge/daisyUI-ffc63a?logo=daisyui&logoColor=black&style=for-the-badge)
![Bootstrap](https://img.shields.io/badge/Bootstrap-7952b3?logo=bootstrap&logoColor=white&style=for-the-badge)
![Angular Material](https://img.shields.io/badge/Angular_Material-004f4f?logo=angular&logoColor=white&style=for-the-badge)

### 🧰 IDEs & Development Tools

![Visual Studio](https://img.shields.io/badge/Visual_Studio-5c2d91?logo=visualstudio&logoColor=white&style=for-the-badge)
![VS Code](https://img.shields.io/badge/VS_Code-007acc?logo=visualstudiocode&logoColor=white&style=for-the-badge)
![Copilot Studio](https://img.shields.io/badge/Copilot_Studio-13b4d7?style=for-the-badge)
![CodeLite](https://img.shields.io/badge/CodeLite-3a4557?style=for-the-badge)
![C++ Builder](https://img.shields.io/badge/C++_Builder-e62431?logo=cplusplusbuilder&logoColor=white&style=for-the-badge)
![Lazygit](https://img.shields.io/badge/Lazygit-303030?style=for-the-badge)
![CMake](https://img.shields.io/badge/CMake-da3434?logo=cmake&logoColor=white&style=for-the-badge)
![Figma](https://img.shields.io/badge/Figma-f24e1e?logo=figma&logoColor=white&style=for-the-badge)
![PyCharm](https://img.shields.io/badge/PyCharm-d5ec64?logo=pycharm&logoColor=black&style=for-the-badge)

### 🔧 Utilities & Testing

![phpMyAdmin](https://img.shields.io/badge/phpMyAdmin-6c78af?logo=phpmyadmin&logoColor=white&style=for-the-badge)
![Cppcheck](https://img.shields.io/badge/Cppcheck-9898ff?style=for-the-badge)
![Dependencies](https://img.shields.io/badge/Dependencies-808080?style=for-the-badge)
![HxD](https://img.shields.io/badge/HxD-6ab675?style=for-the-badge)
![WinMerge](https://img.shields.io/badge/WinMerge-ffcc00?style=for-the-badge)
![Postman](https://img.shields.io/badge/Postman-ff6c37?logo=postman&logoColor=white&style=for-the-badge)
{havRemoteBadge}
![Bash](https://img.shields.io/badge/Bash-89e051?logo=gnubash&logoColor=black&style=for-the-badge)
![PowerShell](https://img.shields.io/badge/PowerShell-012456?logo=powershell&logoColor=white&style=for-the-badge)

### 🖼️ Creative Tools

![FL Studio](https://img.shields.io/badge/FL_Studio-e46729?style=for-the-badge)
![Audacity](https://img.shields.io/badge/Audacity-0000cc?logo=audacity&logoColor=white&style=for-the-badge)
![sfxr](https://img.shields.io/badge/sfxr-c0b090?style=for-the-badge)
![Photoshop](https://img.shields.io/badge/Photoshop-31a8ff?logo=adobephotoshop&logoColor=white&style=for-the-badge)
![Paint.NET](https://img.shields.io/badge/Paint.NET-173e8f?style=for-the-badge)
![Aseprite](https://img.shields.io/badge/Aseprite-7d929e?logo=aseprite&logoColor=white&style=for-the-badge)
![Premiere Pro](https://img.shields.io/badge/Premiere_Pro-9999ff?logo=adobepremierepro&logoColor=white&style=for-the-badge)
![Clipchamp](https://img.shields.io/badge/Clipchamp-6d1dd2?style=for-the-badge)
![OBS Studio](https://img.shields.io/badge/OBS_Studio-191819?logo=obsstudio&logoColor=white&style=for-the-badge)

### ⚙️ Operating Systems

![Linux](https://img.shields.io/badge/Linux-fcc624?logo=linux&logoColor=black&style=for-the-badge)
![Windows](https://img.shields.io/badge/Windows-0078d6?logo=windows&logoColor=white&style=for-the-badge)
"""

    readmeContent = f"""\
# Hi 🤘

My name is **René "Havoc" Nicolaus**. I'm a Senior Software Engineer and Indie Game Developer.

## 🔖 Featured Projects
- **[hav Task List](https://havoc.de/project/havTaskList)**: A VS Code extension that scans workspace files for TODO-style task tags and shows them in a dedicated tree view
- **[hav Commit Guard](https://havoc.de/project/havCommitGuard)**: A VS Code commit guard that scans staged Git changes for TODOs, debug leftovers, merge conflict markers, and custom regex matches before you commit
- **[havPreviewHandler](https://havoc.de/project/havPreviewHandler)**: A shell extension DLL for File Explorer on Windows 11 that provides animated image previews and representative static thumbnails for GIF, WebP, and PNG files (including APNG content in PNG containers), plus still-frame video preview / thumbnail support for MP4 and WMV files
- **[Portals](https://havoc.de/project/portals)**: A Doom-inspired custom game engine, currently in development for a future game project
- **[havIDE](https://havoc.de/project/havIDE)**: An integrated development environment (IDE) for C++ projects, currently in development

{newsSection}

{videosSection}

{languagesSection}

{toolsSection}

---

<a href="https://github.com/Havoc7891/Havoc7891/actions/workflows/profile-content.yml"><img src="https://github.com/Havoc7891/Havoc7891/actions/workflows/profile-content.yml/badge.svg" alt="Update Profile Content" title="Update Profile Content" aria-label="Update Profile Content" align="right"></a>
"""

    outputDirectory = os.path.dirname(os.path.abspath(outputPath))
    os.makedirs(outputDirectory, exist_ok=True)

    with open(outputPath, "w", encoding="utf-8") as file:
        file.write(readmeContent)

def parseArgs():
    parser = argparse.ArgumentParser(description="Generate profile README content and related assets.")
    parser.add_argument(
        "--output",
        default=DEFAULTOUTPUTPATH,
        help=f"Path for the generated profile README candidate. Defaults to {DEFAULTOUTPUTPATH}.",
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parseArgs()

    try:
        generateReadme(args.output)
    except DynamicContentError as ex:
        print(f"Profile content generation failed: {ex}", file=sys.stderr)
        sys.exit(1)
