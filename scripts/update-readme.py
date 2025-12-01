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
    "CMake": "#064F8C",
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
<p>
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/c/c-original.svg" width="32" height="32" alt="C" title="C" aria-label="C">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/cplusplus/cplusplus-original.svg" width="32" height="32" alt="C++" title="C++" aria-label="C++">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/csharp/csharp-original.svg" width="32" height="32" alt="C#" title="C#" aria-label="C#">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/dot-net/dot-net-original.svg" width="32" height="32" alt=".NET" title=".NET" aria-label=".NET">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/dotnetcore/dotnetcore-original.svg" width="32" height="32" alt=".NET Core" title=".NET Core" aria-label=".NET Core">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/blazor/blazor-original.svg" width="32" height="32" alt="Blazor" title="Blazor" aria-label="Blazor">
    <img src="icons/MudBlazor.svg" width="32" height="32" alt="MudBlazor" title="MudBlazor" aria-label="MudBlazor">
    <img src="icons/wxWidgets.svg" width="32" height="32" alt="wxWidgets" title="wxWidgets" aria-label="wxWidgets">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/html5/html5-original.svg" width="32" height="32" alt="HTML5" title="HTML5" aria-label="HTML5">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/css3/css3-original.svg" width="32" height="32" alt="CSS3" title="CSS3" aria-label="CSS3">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/javascript/javascript-original.svg" width="32" height="32" alt="JavaScript" title="JavaScript" aria-label="JavaScript">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/typescript/typescript-original.svg" width="32" height="32" alt="TypeScript" title="TypeScript" aria-label="TypeScript">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/jquery/jquery-original.svg" width="32" height="32" alt="JQuery" title="JQuery" aria-label="JQuery">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/angular/angular-original.svg" width="32" height="32" alt="Angular" title="Angular" aria-label="Angular">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/rxjs/rxjs-original.svg" width="32" height="32" alt="RxJS" title="RxJS" aria-label="RxJS">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nodejs/nodejs-original.svg" width="32" height="32" alt="NodeJS" title="NodeJS" aria-label="NodeJS">
    <img src="https://cdn.simpleicons.org/express/384752" width="32" height="32" alt="Express" title="Express" aria-label="Express">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/sequelize/sequelize-original.svg" width="32" height="32" alt="Sequelize" title="Sequelize" aria-label="Sequelize">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/sdl/sdl-original.svg" width="32" height="32" alt="SDL" title="SDL" aria-label="SDL">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/opengl/opengl-original.svg" width="32" height="32" alt="OpenGL" title="OpenGL" aria-label="OpenGL">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/php/php-original.svg" width="32" height="32" alt="PHP" title="PHP" aria-label="PHP">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" width="32" height="32" alt="Python" title="Python" aria-label="Python">
</p>

### ☁️ Cloud, DevOps & Backend
<p>
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/azure/azure-original.svg" width="32" height="32" alt="Azure" title="Azure" aria-label="Azure">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/azuredevops/azuredevops-original.svg" width="32" height="32" alt="Azure DevOps" title="Azure DevOps" aria-label="Azure DevOps">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/git/git-original.svg" width="32" height="32" alt="Git" title="Git" aria-label="Git">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/mysql/mysql-original.svg" width="32" height="32" alt="MySQL" title="MySQL" aria-label="MySQL">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/mariadb/mariadb-original.svg" width="32" height="32" alt="MariaDB" title="MariaDB" aria-label="MariaDB">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/azuresqldatabase/azuresqldatabase-original.svg" width="32" height="32" alt="Azure SQL Database" title="Azure SQL Database" aria-label="Azure SQL Database">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/microsoftsqlserver/microsoftsqlserver-original.svg" width="32" height="32" alt="MS SQL Server" title="MS SQL Server" aria-label="MS SQL Server">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/apache/apache-original.svg" width="32" height="32" alt="Apache" title="Apache" aria-label="Apache">

</p>

### 🎨 Frontend Styling
<p>
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/tailwindcss/tailwindcss-original.svg" width="32" height="32" alt="Tailwind CSS" title="Tailwind CSS" aria-label="Tailwind CSS">
    <img src="icons/daisyUI.svg" width="32" height="32" alt="daisyUI" title="daisyUI" aria-label="daisyUI">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/bootstrap/bootstrap-original.svg" width="32" height="32" alt="Bootstrap" title="Bootstrap" aria-label="Bootstrap">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/angularmaterial/angularmaterial-original.svg" width="32" height="32" alt="Angular Material" title="Angular Material" aria-label="Angular Material">
</p>

### 🧰 IDEs & Development Tools
<p>
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/visualstudio/visualstudio-original.svg" width="32" height="32" alt="Visual Studio" title="Visual Studio" aria-label="Visual Studio">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vscode/vscode-original.svg" width="32" height="32" alt="Visual Studio Code" title="Visual Studio Code" aria-label="Visual Studio Code">
    <img src="icons/CopilotStudio.svg" width="32" height="32" alt="Microsoft Copilot Studio" title="Microsoft Copilot Studio" aria-label="Microsoft Copilot Studio">
    <img src="icons/CodeLite.svg" width="32" height="32" alt="CodeLite" title="CodeLite" aria-label="CodeLite">
    <img src="https://cdn.simpleicons.org/cplusplusbuilder/e62431" width="32" height="32" alt="C++ Builder" title="C++ Builder" aria-label="C++ Builder">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/cmake/cmake-original.svg" width="32" height="32" alt="CMake" title="CMake" aria-label="CMake">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/figma/figma-original.svg" width="32" height="32" alt="Figma" title="Figma" aria-label="Figma">
    <img src="https://cdn.simpleicons.org/notepadplusplus/90e59a" width="32" height="32" alt="Notepad++" title="Notepad++" aria-label="Notepad++">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/pycharm/pycharm-original.svg" width="32" height="32" alt="PyCharm" title="PyCharm" aria-label="PyCharm">
</p>

### 🔧 Utilities & Testing
<p>
    <img src="https://cdn.simpleicons.org/phpmyadmin/6c78af" width="32" height="32" alt="phpMyAdmin" title="phpMyAdmin" aria-label="phpMyAdmin">
    <img src="icons/Cppcheck.svg" width="32" height="32" alt="Cppcheck" title="Cppcheck" aria-label="Cppcheck">
    <img src="icons/HxD.png" width="32" height="32" alt="HxD" title="HxD" aria-label="HxD">
    <img src="icons/WinMerge.png" width="32" height="32" alt="WinMerge" title="WinMerge" aria-label="WinMerge">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/postman/postman-original.svg" width="32" height="32" alt="Postman" title="Postman" aria-label="Postman">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/photoshop/photoshop-original.svg" width="32" height="32" alt="Photoshop" title="Photoshop" aria-label="Photoshop">
    <img src="icons/Paint.NET.png" width="32" height="32" alt="Paint.NET" title="Paint.NET" aria-label="Paint.NET">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/premierepro/premierepro-original.svg" width="32" height="32" alt="Premiere Pro" title="Premiere Pro" aria-label="Premiere Pro">
    <img src="icons/Clipchamp.svg" width="32" height="32" alt="Microsoft Clipchamp" title="Microsoft Clipchamp" aria-label="Microsoft Clipchamp">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/filezilla/filezilla-original.svg" width="32" height="32" alt="FileZilla" title="FileZilla" aria-label="FileZilla">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/bash/bash-original.svg" width="32" height="32" alt="Bash" title="Bash" aria-label="Bash">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/powershell/powershell-original.svg" width="32" height="32" alt="PowerShell" title="PowerShell" aria-label="PowerShell">
</p>

### ⚙️ Operating Systems
<p>
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/linux/linux-original.svg" width="32" height="32" alt="Linux" title="Linux" aria-label="Linux">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/windows11/windows11-original.svg" width="32" height="32" alt="Windows" title="Windows" aria-label="Windows">
</p>
"""

    readmeContent = f"""\
# Hi 🤘

My name is **René _"Havoc"_ Nicolaus**. I'm a Senior Software Engineer / Indie Game Developer.

## 📂 Latest Projects
- [Portals](https://havoc.de/projects.html#portals) - A custom game engine inspired by Doom, currently in development and intended for a future game project
- [havIDE](https://havoc.de/projects.html#havIDE) - An integrated development environment (IDE), currently in development, designed specifically for managing and working on C++ projects

## 📰 Latest News

{newsSection}

## 📹 Latest Videos

{videosSection}

{languagesSection}

{toolsSection}

## 📝 Attributions & Legal Notice

Some icons and logos included in this repository are the property of their respective owners. They are used here **for identification and reference purposes only** under their respective open licenses or trademark policies. No affiliation or endorsement is implied.

See [icons/ATTRIBUTIONS.md](icons/ATTRIBUTIONS.md) for full attribution and license details.

---

<a href="https://github.com/Havoc7891/Havoc7891/actions"><img src="https://github.com/Havoc7891/Havoc7891/workflows/Update%20README/badge.svg" alt="Update README" title="Update README" aria-label="Update README" align="right"></a>
"""

    with open("updated-readme.md", "w", encoding="utf-8") as file:
        file.write(readmeContent)

if __name__ == "__main__":
    generateReadme()
