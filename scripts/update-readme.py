import feedparser
from datetime import datetime

FEEDURL = "https://www.havocspage.net/rss.xml"
MAXENTRIES = 5

STARTMARKER = "<!-- Latest News - Start -->"
ENDMARKER = "<!-- Latest News - End -->"

def fetchFeedEntries(feedUrl, maxEntries=5):
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
    newsPosts = fetchFeedEntries(FEEDURL, MAXENTRIES)
    newsSection = f"{STARTMARKER}\n{newsPosts}\n{ENDMARKER}"

    toolsSection = """\
## 🧰 Tools & Technologies I Use

### 💻 Languages, Frameworks & Libraries
<p>
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/c/c-original.svg" width="32" height="32" alt="C" title="C" aria-label="C">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/cplusplus/cplusplus-original.svg" width="32" height="32" alt="C++" title="C++" aria-label="C++">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/csharp/csharp-original.svg" width="32" height="32" alt="C#" title="C#" aria-label="C#">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/dotnetcore/dotnetcore-original.svg" width="32" height="32" alt=".NET Core" title=".NET Core" aria-label=".NET Core">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/blazor/blazor-original.svg" width="32" height="32" alt="Blazor" title="Blazor" aria-label="Blazor">
    <img src="https://raw.githubusercontent.com/MudBlazor/MudBlazor/5509f5175c9df0f97069b6014b9dd41276ded219/content/MudBlazor.svg" width="32" height="32" alt="MudBlazor" title="MudBlazor" aria-label="MudBlazor">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/html5/html5-original.svg" width="32" height="32" alt="HTML5" title="HTML5" aria-label="HTML5">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/css3/css3-original.svg" width="32" height="32" alt="CSS3" title="CSS3" aria-label="CSS3">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/javascript/javascript-original.svg" width="32" height="32" alt="JavaScript" title="JavaScript" aria-label="JavaScript">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/typescript/typescript-original.svg" width="32" height="32" alt="TypeScript" title="TypeScript" aria-label="TypeScript">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/angular/angular-original.svg" width="32" height="32" alt="Angular" title="Angular" aria-label="Angular">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nodejs/nodejs-original.svg" width="32" height="32" alt="NodeJS" title="NodeJS" aria-label="NodeJS">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/express/express-original.svg" width="32" height="32" alt="Express" title="Express" aria-label="Express">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/sdl/sdl-original.svg" width="32" height="32" alt="SDL" title="SDL" aria-label="SDL">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/php/php-original.svg" width="32" height="32" alt="PHP" title="PHP" aria-label="PHP">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" width="32" height="32" alt="Python" title="Python" aria-label="Python">
</p>

### ☁️ Cloud, DevOps & Backend
<p>
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/azure/azure-original.svg" width="32" height="32" alt="Azure" title="Azure" aria-label="Azure">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/git/git-original.svg" width="32" height="32" alt="Git" title="Git" aria-label="Git">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/mysql/mysql-original.svg" width="32" height="32" alt="MySQL" title="MySQL" aria-label="MySQL">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/mariadb/mariadb-original.svg" width="32" height="32" alt="MariaDB" title="MariaDB" aria-label="MariaDB">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/microsoftsqlserver/microsoftsqlserver-original.svg" width="32" height="32" alt="MS SQL Server" title="MS SQL Server" aria-label="MS SQL Server">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/apache/apache-original.svg" width="32" height="32" alt="Apache" title="Apache" aria-label="Apache">

</p>

### 🎨 Frontend Styling
<p>
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/tailwindcss/tailwindcss-original.svg" width="32" height="32" alt="Tailwind CSS" title="Tailwind CSS" aria-label="Tailwind CSS">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/bootstrap/bootstrap-original.svg" width="32" height="32" alt="Bootstrap" title="Bootstrap" aria-label="Bootstrap">
</p>

### 🧰 IDEs & Development Tools
<p>
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/visualstudio/visualstudio-original.svg" width="32" height="32" alt="Visual Studio" title="Visual Studio" aria-label="Visual Studio">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vscode/vscode-original.svg" width="32" height="32" alt="Visual Studio Code" title="Visual Studio Code" aria-label="Visual Studio Code">
    <img src="https://raw.githubusercontent.com/eranif/codelite/bac35a37c42ff75f7ebfc9c9b9889ca9e5723eed/svgs/dark-theme/codelite-logo.svg" width="32" height="32" alt="CodeLite" title="CodeLite" aria-label="CodeLite">
    <img src="https://cdn.simpleicons.org/cplusplusbuilder/e62431" width="32" height="32" alt="C++ Builder" title="C++ Builder" aria-label="C++ Builder">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/cmake/cmake-original.svg" width="32" height="32" alt="CMake" title="CMake" aria-label="CMake">
    <img src="https://cdn.simpleicons.org/notepadplusplus/90e59a" width="32" height="32" alt="Notepad++" title="Notepad++" aria-label="Notepad++">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/pycharm/pycharm-original.svg" width="32" height="32" alt="PyCharm" title="PyCharm" aria-label="PyCharm">
</p>

### 🔧 Utilities & Testing
<p>
    <img src="https://cdn.simpleicons.org/phpmyadmin/6c78af" width="32" height="32" alt="phpMyAdmin" title="phpMyAdmin" aria-label="phpMyAdmin">
    <img src="https://raw.githubusercontent.com/danmar/cppcheck/f28aeaee431f4d1ebb5cc75abd80e3c943fe486f/gui/cppcheck-gui.svg" width="32" height="32" alt="Cppcheck" title="Cppcheck" aria-label="Cppcheck">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/postman/postman-original.svg" width="32" height="32" alt="Postman" title="Postman" aria-label="Postman">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/photoshop/photoshop-original.svg" width="32" height="32" alt="Photoshop" title="Photoshop" aria-label="Photoshop">
    <img src="https://avatars.githubusercontent.com/u/11067286?s=200&v=4" width="32" height="32" alt="Paint.NET" title="Paint.NET" aria-label="Paint.NET">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/premierepro/premierepro-original.svg" width="32" height="32" alt="Premiere Pro" title="Premiere Pro" aria-label="Premiere Pro">
</p>
"""

    readmeContent = f"""\
# Hi 🤘

My name is **René _"Havoc"_ Nicolaus**. I'm a Senior Software Engineer / Indie Game Developer.

## 📂 Latest Projects
- [Portals](https://havocspage.net/projects.html#portals): A custom game engine inspired by Doom, currently in development and intended for a future game project
- [havIDE](https://havocspage.net/projects.html#havIDE): My own integrated development environment (IDE) built specifically for managing and working on C++ projects

{toolsSection}

## 📰 Latest News

{newsSection}

---

<a href="https://github.com/Havoc7891/Havoc7891/actions"><img src="https://github.com/Havoc7891/Havoc7891/workflows/Update%20README/badge.svg" alt="Update README" title="Update README" aria-label="Update README" align="right"></a>
"""

    with open("updated-readme.md", "w", encoding="utf-8") as file:
        file.write(readmeContent)

if __name__ == "__main__":
    generateReadme()
