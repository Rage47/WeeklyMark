
# WeeklyMark
### The bridge between your daily mess and your weekly review

WeeklyMark is a local-first, Python-powered engine that scans your Obsidian or Markdown vault to extract tasks, tags, and highlights. It generates a structured weekly report in seconds, removing the need to manually hunt through dozens of notes to organize your review.

<details>
<summary>💎 <b>THE ELITE ADD-ON: ChangePoints OS</b></summary>

<br>

**For the practitioners who need data, not just documentation.**

While WeeklyMark manages your personal workflow, ChangePoints OS provides the high-level data backbone for serious ESG leads and policy designers.

### 1. The ChangePoints Notion Vault
Stop guessing what drives sustainable behavior. The ChangePoints Notion Vault is a digitized, searchable database of 50 historically proven ESG policy interventions.
* **Rigorously Scored**: Every intervention, such as Rwanda’s plastic ban or London’s ULEZ, is scored by actual behavioral impact, anomaly, and adoption speed.
* **Fully Cited**: The database is backed by primary source data from organizations like the World Bank and IMF.
* **Ready to Deploy**: Features one-click duplication directly into your own Notion workspace.

### 2. The Gumroad Partner Offer
Launch partners are being sought in the ESG and Behavioral Science space to join the program.
* **70% Commission**: For the first 30 days, the standard affiliate split is bumped to 70% for partners.
* **Done-for-you Marketing**: Partners receive Bento Grid graphics and pre-written copy to simplify promotion.
* **Lifetime Access**: Launch partners receive the full OS and all future data updates for free.

Apply to be a [ChangePoints Partner here](https://alexrotar.gumroad.com/affiliates)

</details>

## The Problem
Using Obsidian as a "Second Brain" often turns the weekly review into a manual chore. Users must open every daily note to find specific tags, check open tasks, and synthesize a summary manually.

## The Solution
WeeklyMark automates the discovery phase of your review.
* **Automated Extraction**: Pulls every task and tag from notes modified within a specified timeframe, such as the last 7 days.
* **AI-Powered Synthesis**: Utilizes models like GPT-4o-mini to transform raw tasks and tags into a concise executive summary.
* **Dual-Mode Flexibility**: Offers a CLI for automated workflows and a PyQt6 GUI for a standard desktop experience.

![WeeklyMark Demo](https://public-files.gumroad.com/v65zlxxdshfvxm0zkpy2aozv3pc7)
### [Read the full launch announcement & feature walkthrough](https://www.funkaey.com/blog/WeeklyMark-finally-out)

---

## Features
* **Smart Date Parsing**: Supports multiple frontmatter date formats, including ISO and YYYY-MM-DD.
* **Regex-Powered Task Tracking**: Detects bullets, checkboxes, and nested tags without disrupting Markdown syntax.
* **Local-First**: Your vault stays on your machine; tasks are only sent to OpenAI if the summarize flag is enabled.
* **Custom Templates**: Reporting is fully customizable via Jinja2 templates.

---

## Installation and Usage

1. **Clone and Install**:
   ```bash
   git clone [https://github.com/Rage47/WeeklyMark.git](https://github.com/Rage47/WeeklyMark.git)
   pip install -r Requirements.txt
   ```
  

2. **Run the GUI (Desktop App)**:
   ```bash
   python __main__.py
   ```
  

3. **Generate a Report (CLI mode)**:
   ```bash
   python __main__.py ~/MyVault --summarize --output ./Weekly-Report.md
   ```
  

---

## Requirements
* **Python 3.9+**
* **PyQt6** (for GUI)
* **Jinja2** (for rendering)
* **python-frontmatter** (for parsing metadata)
* **openai** (for summaries)

---

## Why I Built This (And The "Lazy" Option)

I built WeeklyMark because I love Obsidian, but I absolutely hated my Sunday afternoon "Weekly Review" ritual. Digging through dozens of daily notes just to find scattered checkboxes and tags felt like a massive waste of time. I needed a local-first engine to do the heavy lifting so I could actually focus on planning my week.

I decided to open-source the core Python logic because I believe the Markdown and PKM (Personal Knowledge Management) community thrives on shared tools. You are completely free to clone this repo, tweak the Jinja templates, and run it locally forever.

**Want to skip the terminal?**
If you don't want to mess with `pip install`, Python virtual environments, or executing scripts every Sunday, I have compiled WeeklyMark into native, 1-click desktop applications for macOS and Windows. 

You can grab the plug-and-play desktop app (and support my late-night coding sessions) over on Gumroad:

### 👉 [Get the WeeklyMark Desktop App Here](https://link.funkaey.com/git)

## License
MIT License.

Developed by [Alex Rotar](https://changepoints.net). 
Building tools for the intersection of Behavioral Economics and ESG.
