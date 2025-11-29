import os
import feedparser
import requests
from datetime import datetime
from collections import Counter

FEEDURL = "https://havoc.de/rss.xml"
MAXENTRIES = 5
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

def getAggregatedLanguages(username: str) -> dict:
    token = os.getenv("GITHUB_TOKEN")
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

def getDarkModeSafeColor(colorHex: str) -> str:
    return (
        f"color-mix(in srgb, {colorHex} 85%, white 15%)"
    )

def buildLanguageSection(languages: dict, colorMap: dict):
    if not languages:
        return """## 📊 Top Languages Across My Public GitHub Repositories\nCould not fetch language stats."""

    # Sort languages by percentage descending
    languages = dict(sorted(languages.items(), key=lambda x: x[1], reverse=True))

    # Wrapper - Start
    html = [
        """## 📊 Top Languages Across My Public GitHub Repositories\n""",
        """<div style="width: 100%; max-width: 700px; margin: 15px 0;">""",
    ]

    # Stacked Bar - Start
    html.append(
        f"""    <style>
        .stack-bar-bg {{
            background-color: #D1D9E0;
        }}
        @media (prefers-color-scheme: light) {{
            .stack-bar-bg {{
                background-color: #D1D9E0;
            }}
        }}
        @media (prefers-color-scheme: dark) {{
            .stack-bar-bg {{
                background-color: #3D444D;
            }}
        }}
    </style>
    <div class="stack-bar-bg" style="display: flex; height: 8px; border-radius: 7px; overflow: hidden; gap: 2px;">"""
    )

    for i, (lang, pct) in enumerate(languages.items()):
        baseColor = colorMap.get(lang, "#999999")
        effectiveColor = getDarkModeSafeColor(baseColor)

        # Rounded left on first, rounded right on last
        border = ""
        if i == 0:
            border = " border-radius: 7px 0 0 7px;"
        elif i == len(languages) - 1:
            border = " border-radius: 0 7px 7px 0;"

        html.append(
            f"""        <div style="background: {effectiveColor}; width: {pct}%;{border}"></div>"""
        )

    html.append("    </div>") # Stacked Bar - End

    # Legend - Start
    html.append(
        """    <div style="margin-top: 8px; display: flex; flex-wrap: wrap; gap: 10px; font-size: 12px;">"""
    )

    for lang, pct in languages.items():
        baseColor = colorMap.get(lang, "#999999")
        effectiveColor = getDarkModeSafeColor(baseColor)

        html.append(
            f"""        <span style="display: inline-flex; align-items: center; gap: 6px;">
            <span style="background-color: {effectiveColor}; width: 10px; height: 10px; border-radius: 50%;"></span>
            {lang}
            <span style="color: #9198A1">{pct:.1f}%</span>
        </span>"""
        )

    html.append("    </div>") # Legend - End
    html.append("</div>") # Wrapper - End

    return "\n".join(html)

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
    newsSection = fetchFeedEntries(FEEDURL, MAXENTRIES)

    languages = getAggregatedLanguages(USERNAME)

    mainLanguages = {k: v for k, v in languages.items() if v >= MINLANGUAGEPERCENT}
    otherTotal = sum(v for v in languages.values() if v < MINLANGUAGEPERCENT)

    if otherTotal > 0:
        mainLanguages["Other"] = round(otherTotal, 2)

    languages = mainLanguages

    languagesSection = buildLanguageSection(languages, GITHUBLANGUAGECOLORS)

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
