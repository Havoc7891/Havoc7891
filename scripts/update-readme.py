import hashlib
import os
import feedparser
import requests
from datetime import datetime
from collections import Counter

FEEDURL = "https://havoc.de/rss.xml"
FEEDMAXENTRIES = 5
USERNAME = "Havoc7891"
MINLANGUAGEPERCENT = 0.1 # Group all languages below this percentage under "Other"
GITHUBLANGUAGECOLORS = {
    "C": "#555555",
    "C++": "#F34B7D",
    "C#": "#178600",
    "JavaScript": "#F1E05A",
    "TypeScript": "#3178C6",
    "HTML": "#E34C26",
    "CSS": "#563D7C",
    "Java": "#B07219",
    "PHP": "#4F5D95",
    "SQL": "#E38C00",
    "Python": "#3572A5",
    "CMake": "#DA3434",
    "PowerShell": "#012456",
    "Other": "#EDEDED",
}
LEGENDICONSFOLDER = "legend-icons"
YOUTUBECHANNELID = "UCaGa30jV6OWFpjBWY3r4GWQ"
YOUTUBEMAXENTRIES = 6

def getAggregatedLanguages(username: str) -> dict:
    token = os.getenv("GH_TOKEN")
    if not token:
        return {}

    headers = {"Authorization": f"Bearer {token}"}
    reposUrl = f"https://api.github.com/users/{username}/repos"

    repos = []
    page = 1
    while True:
        resp = requests.get(reposUrl, headers=headers, params={"page": page, "per_page": 100})
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        repos.extend(data)
        page += 1

    langTotals = Counter()

    for repo in repos:
        # Skip forked repositories
        if repo.get("fork"):
            continue

        langUrl = repo.get("languages_url")
        if not langUrl:
            continue

        langResp = requests.get(langUrl, headers=headers)
        if langResp.status_code == 200:
            langTotals.update(langResp.json())

    totalBytes = sum(langTotals.values())
    if totalBytes == 0:
        return {}

    return {
        lang: round((count / totalBytes) * 100, 2)
        for lang, count in langTotals.most_common()
    }

def generateTopLanguagesSvg(languages: dict, colorMap: dict, filename: str):
    if not languages:
        svg = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="40" viewBox="0 0 400 40" role="img">
  <title>Top Languages</title>
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="14">
    No language data
  </text>
</svg>
"""
        with open(filename, "w", encoding="utf-8") as file:
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

        color = colorMap.get(lang, "#999999")

        svgParts.append(
            f'<rect x="{currentX:.2f}" y="{barY}" width="{segmentWidth:.2f}" '
            f'height="{barHeight}" fill="{color}" />'
        )

        currentX += segmentWidth

    svgParts.append("</g>")
    svgParts.append("</svg>")

    with open(filename, "w", encoding="utf-8") as file:
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

def cleanupLegendIcons(currentLanguages: dict, directory: str):
    if not os.path.isdir(directory):
        return # Nothing to clean

    # Create the set of expected filenames
    expected = set()
    for lang in currentLanguages:
        safeName = lang.lower().replace("#", "sharp").replace("+", "plus")
        expected.add(f"legend-{safeName}.svg")

    # Walk through the folder and delete old ones
    for filename in os.listdir(directory):
        if filename.endswith(".svg") and filename.startswith("legend-"):
            if filename not in expected:
                os.remove(os.path.join(directory, filename))

def buildLanguagesSection(languages: dict, colorMap: dict):
    if not languages:
        return "## 📊 Top Languages Across My Public GitHub Repositories\nCould not fetch language stats."

    os.makedirs(LEGENDICONSFOLDER, exist_ok=True)

    # Generate / update the SVG file for the stacked bar
    generateTopLanguagesSvg(languages, colorMap, "top-languages.svg")

    # Markdown section embedding the SVG
    lines = [
        "## 📊 Top Languages Across My Public GitHub Repositories",
        "",
        "![Top Languages](top-languages.svg)",
        "",
    ]

    # Generate / update legend
    for lang, pct in sorted(languages.items(), key=lambda x: x[1], reverse=True):
        color = colorMap.get(lang, "#999999")
        safeName = lang.lower().replace("#", "sharp").replace("+", "plus")
        iconFile = os.path.join(LEGENDICONSFOLDER, f"legend-{safeName}.svg")
        generateLegendCircleSvg(color, iconFile)
        webPath = iconFile.replace(os.sep, "/")
        lines.append(f"<img src=\"{webPath}\" width=\"12\" height=\"12\"> **{lang}** {pct:.1f}%")

    cleanupLegendIcons(languages, LEGENDICONSFOLDER)

    return "\n".join(lines)

def getUploadsPlaylistId(channelId, apiKey):
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "contentDetails",
        "id": channelId,
        "key": apiKey
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    try:
        return data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    except (KeyError, IndexError):
        return None

def fetchLatestYouTubeVideos(channelId, maxEntries):
    apiKey = os.getenv("YOUTUBE_API_KEY")
    if not apiKey:
        return []

    uploadsPlaylistId = getUploadsPlaylistId(channelId, apiKey)
    if not uploadsPlaylistId:
        return []

    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet",
        "playlistId": uploadsPlaylistId,
        "maxResults": maxEntries,
        "key": apiKey
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    videos = []
    for item in data.get("items", []):
        snippet = item["snippet"]
        videoId = snippet["resourceId"]["videoId"]

        videos.append({
            "title": snippet["title"],
            "url": f"https://www.youtube.com/watch?v={videoId}",
            "thumb": f"https://img.youtube.com/vi/{videoId}/maxresdefault.jpg",
            "published": datetime.strptime(snippet["publishedAt"], "%Y-%m-%dT%H:%M:%SZ").strftime("%B %d, %Y")
        })

    return videos

def buildVideosSection(videos):
    if not videos:
        return "No recent videos found."

    htmlParts = []
    htmlParts.append("<div>\n")

    for video in videos:
        htmlParts.append(
            f'    <a href="{video["url"]}">'
            f'<img src="{video["thumb"]}" width="400" '
            f'alt="{video["title"]} | {video["published"]}" '
            f'title="{video["title"]} | {video["published"]}" '
            f'aria-label="{video["title"]} | {video["published"]}">'
            f'</a>\n'
        )

    htmlParts.append("</div>")
    return "".join(htmlParts)

def fetchFeedEntries(feedUrl, maxEntries):
    feed = feedparser.parse(feedUrl)
    entries = feed.entries[:maxEntries]
    lines = []
    for entry in entries:
        title = entry.title
        link = entry.link
        publicationDate = "Unknown Date"
        if hasattr(entry, "published_parsed"):
            publicationDate = datetime(*entry.published_parsed[:6]).strftime("%m/%d/%Y")
        lines.append(f"- {publicationDate} - [{title}]({link})")
    return "\n".join(lines)

def generateReadme():
    newsSection = fetchFeedEntries(FEEDURL, FEEDMAXENTRIES)

    videos = fetchLatestYouTubeVideos(YOUTUBECHANNELID, YOUTUBEMAXENTRIES)
    videosSection = buildVideosSection(videos)

    languages = getAggregatedLanguages(USERNAME)

    mainLanguages = {k: v for k, v in languages.items() if v >= MINLANGUAGEPERCENT}
    otherTotal = sum(v for v in languages.values() if v < MINLANGUAGEPERCENT)

    if otherTotal > 0:
        mainLanguages["Other"] = round(otherTotal, 2)

    languages = mainLanguages

    languagesSection = buildLanguagesSection(languages, GITHUBLANGUAGECOLORS)

    toolsSection = """\
## 🧰 Tools & Technologies I Use

### 💻 Languages, Frameworks & Libraries

![C](https://img.shields.io/badge/C-5F86AA?logo=c&logoColor=white&style=for-the-badge)
![C++](https://img.shields.io/badge/C++-00599C?logo=cplusplus&logoColor=white&style=for-the-badge)
![C#](https://img.shields.io/badge/C%23-239120?logo=csharp&logoColor=white&style=for-the-badge)
![.NET](https://img.shields.io/badge/.NET-512BD4?logo=dotnet&logoColor=white&style=for-the-badge)
![Blazor](https://img.shields.io/badge/Blazor-512BD4?logo=blazor&logoColor=white&style=for-the-badge)
![MudBlazor](https://img.shields.io/badge/MudBlazor-594AE2?style=for-the-badge)
![wxWidgets](https://img.shields.io/badge/wxWidgets-2222FF?style=for-the-badge)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white&style=for-the-badge)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?logo=css&logoColor=white&style=for-the-badge)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black&style=for-the-badge)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white&style=for-the-badge)
![jQuery](https://img.shields.io/badge/jQuery-0769AD?logo=jquery&logoColor=white&style=for-the-badge)
![Angular](https://img.shields.io/badge/Angular-DD0031?logo=angular&logoColor=white&style=for-the-badge)
![RxJS](https://img.shields.io/badge/RxJS-B7178C?logo=reactivex&logoColor=white&style=for-the-badge)
![Node.js](https://img.shields.io/badge/Node.js-339933?logo=node.js&logoColor=white&style=for-the-badge)
![Express](https://img.shields.io/badge/Express-000000?logo=express&logoColor=white&style=for-the-badge)
![Sequelize](https://img.shields.io/badge/Sequelize-52B0E7?logo=sequelize&logoColor=white&style=for-the-badge)
![SDL](https://img.shields.io/badge/SDL-132A47?style=for-the-badge)
![OpenGL](https://img.shields.io/badge/OpenGL-5586A4?logo=opengl&logoColor=white&style=for-the-badge)
![PHP](https://img.shields.io/badge/PHP-777BB4?logo=php&logoColor=white&style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white&style=for-the-badge)

### ☁️ Cloud, DevOps & Backend

![Azure](https://img.shields.io/badge/Azure-0078D4?logo=microsoftazure&logoColor=white&style=for-the-badge)
![Azure DevOps](https://img.shields.io/badge/Azure_DevOps-0078D7?logo=azuredevops&logoColor=white&style=for-the-badge)
![Git](https://img.shields.io/badge/Git-F05032?logo=git&logoColor=white&style=for-the-badge)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?logo=mysql&logoColor=white&style=for-the-badge)
![MariaDB](https://img.shields.io/badge/MariaDB-003545?logo=mariadb&logoColor=white&style=for-the-badge)
![Azure SQL](https://img.shields.io/badge/Azure_SQL-1572B9?logo=microsoftsqlserver&logoColor=white&style=for-the-badge)
![SQL Server](https://img.shields.io/badge/SQL_Server-CC2927?logo=microsoftsqlserver&logoColor=white&style=for-the-badge)
![Apache](https://img.shields.io/badge/Apache-AB0000?logo=apache&logoColor=white&style=for-the-badge)

### 🎨 Frontend Styling

![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-06B6D4?logo=tailwindcss&logoColor=white&style=for-the-badge)
![daisyUI](https://img.shields.io/badge/daisyUI-FFC63A?logo=daisyui&logoColor=black&style=for-the-badge)
![Bootstrap](https://img.shields.io/badge/Bootstrap-7952B3?logo=bootstrap&logoColor=white&style=for-the-badge)
![Angular Material](https://img.shields.io/badge/Angular_Material-004F4F?logo=angular&logoColor=white&style=for-the-badge)

### 🧰 IDEs & Development Tools

![Visual Studio](https://img.shields.io/badge/Visual_Studio-5C2D91?logo=visualstudio&logoColor=white&style=for-the-badge)
![VS Code](https://img.shields.io/badge/VS_Code-007ACC?logo=visualstudiocode&logoColor=white&style=for-the-badge)
![Copilot Studio](https://img.shields.io/badge/Copilot_Studio-13B4D7?style=for-the-badge)
![CodeLite](https://img.shields.io/badge/CodeLite-A05A2C?style=for-the-badge)
![C++ Builder](https://img.shields.io/badge/C++_Builder-E62431?logo=cplusplusbuilder&logoColor=white&style=for-the-badge)
![Lazygit](https://img.shields.io/badge/Lazygit-303030?style=for-the-badge)
![CMake](https://img.shields.io/badge/CMake-064F8C?logo=cmake&logoColor=white&style=for-the-badge)
![Figma](https://img.shields.io/badge/Figma-F24E1E?logo=figma&logoColor=white&style=for-the-badge)
![PyCharm](https://img.shields.io/badge/PyCharm-D5EC64?logo=pycharm&logoColor=black&style=for-the-badge)

### 🔧 Utilities & Testing

![phpMyAdmin](https://img.shields.io/badge/phpMyAdmin-6C78AF?logo=phpmyadmin&logoColor=white&style=for-the-badge)
![Cppcheck](https://img.shields.io/badge/Cppcheck-9898FF?style=for-the-badge)
![Dependencies](https://img.shields.io/badge/Dependencies-808080?style=for-the-badge)
![HxD](https://img.shields.io/badge/HxD-6AB675?style=for-the-badge)
![WinMerge](https://img.shields.io/badge/WinMerge-FFCC00?style=for-the-badge)
![Postman](https://img.shields.io/badge/Postman-FF6C37?logo=postman&logoColor=white&style=for-the-badge)
![FileZilla](https://img.shields.io/badge/FileZilla-BF0000?logo=filezilla&logoColor=white&style=for-the-badge)
![Bash](https://img.shields.io/badge/Bash-4EAA25?logo=gnubash&logoColor=white&style=for-the-badge)
![PowerShell](https://img.shields.io/badge/PowerShell-5391FE?logo=powershell&logoColor=white&style=for-the-badge)

### 🖼️ Creative Tools

![FL Studio](https://img.shields.io/badge/FL_Studio-E46729?style=for-the-badge)
![Audacity](https://img.shields.io/badge/Audacity-0000CC?logo=audacity&logoColor=white&style=for-the-badge)
![sfxr](https://img.shields.io/badge/sfxr-C0B090?style=for-the-badge)
![Photoshop](https://img.shields.io/badge/Photoshop-31A8FF?logo=adobephotoshop&logoColor=white&style=for-the-badge)
![Paint.NET](https://img.shields.io/badge/Paint.NET-173E8F?style=for-the-badge)
![Premiere Pro](https://img.shields.io/badge/Premiere_Pro-9999FF?logo=adobepremierepro&logoColor=white&style=for-the-badge)
![Clipchamp](https://img.shields.io/badge/Clipchamp-6D1DD2?style=for-the-badge)
![OBS Studio](https://img.shields.io/badge/OBS_Studio-191819?logo=obsstudio&logoColor=white&style=for-the-badge)

### ⚙️ Operating Systems

![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black&style=for-the-badge)
![Windows](https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=white&style=for-the-badge)
"""

    readmeContent = f"""\
# Hi 🤘

My name is **René "Havoc" Nicolaus**. I'm a Senior Software Engineer / Indie Game Developer.

## 🔖 Featured Projects
- [havPreviewHandler](https://havoc.de/project/havPreviewHandler) - A shell extension DLL for File Explorer on Windows 11 that provides animated image previews and representative static thumbnails for GIF, WebP, and PNG files (including APNG content in PNG containers), plus still-frame preview / thumbnail support for MP4 files
- [Portals](https://havoc.de/project/portals) - A Doom-inspired custom game engine, currently in development for a future game project
- [havIDE](https://havoc.de/project/havIDE) - An integrated development environment (IDE) for C++ projects, currently in development

## 📰 Latest News

{newsSection}

## 📹 Latest Videos

{videosSection}

{languagesSection}

{toolsSection}

---

<a href="https://github.com/Havoc7891/Havoc7891/actions"><img src="https://github.com/Havoc7891/Havoc7891/workflows/Update%20README/badge.svg" alt="Update README" title="Update README" aria-label="Update README" align="right"></a>
"""

    with open("updated-readme.md", "w", encoding="utf-8") as file:
        file.write(readmeContent)

if __name__ == "__main__":
    generateReadme()
