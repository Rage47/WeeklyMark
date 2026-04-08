#!/usr/bin/env python3
"""obs_weekly.py — **single‑file** tool that can run either in CLI mode (the original
behaviour) *or* with a small PyQt6 GUI.

You can now do one of the following:

```bash
# ⚙ classic CLI
python obs_weekly.py -h            # see options
python obs_weekly.py ~/Vault --summarize

# 🖼 GUI (explicit flag)
python obs_weekly.py --gui

# 🖼 GUI (implicit — no args, DISPLAY available)
python obs_weekly.py
```

All code from your original *collector.py*, *renderer.py*, *summarize.py* and
*obs_weekly/__main__.py* is kept **unchanged** — it is just consolidated here.
The only additions are the GUI class and a small wrapper that decides which
entry‑point to launch.
"""

from __future__ import annotations

###############################################################################
# ─────────────────────────────────────────────────────────────────────────────#
#  Standard library imports                                                   #
# ─────────────────────────────────────────────────────────────────────────────#
###############################################################################

from pathlib import Path
from datetime import date, datetime, timedelta
import sys
import os
import re
import argparse
import inspect
import traceback

###############################################################################
#  Third‑party dependencies                                                   #
###############################################################################

# Everything below was already used in your original code.
import frontmatter
from jinja2 import Template
import requests
import toml

# PyQt6 is optional; if missing we degrade gracefully and fall back to CLI.
try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QApplication,
        QWidget,
        QLabel,
        QLineEdit,
        QCheckBox,
        QPushButton,
        QFileDialog,
        QSpinBox,
        QTextEdit,
        QHBoxLayout,
        QVBoxLayout,
        QMessageBox,
    )
except ModuleNotFoundError:  # pragma: no cover
    QApplication = None  # type: ignore

###############################################################################
#  Regexes (unchanged)                                                        #
###############################################################################

TASK_RE = re.compile(
    r"""^\s*                # any leading whitespace
        [-*+]               # markdown bullet
        \s+                 # at least one space
        (?:\[[xX ]\]\s+)?   # OPTIONAL checkbox [ ], [x], [X]
        .+                  # the text itself
    """,
    re.VERBOSE,
)
TAG_RE = re.compile(r"(?<!\w)#([\w/-]+)")  # #tag or #foo/bar

###############################################################################
#  Helper: tiny date parser                                                   #
###############################################################################

_COMMON_FMTS = (
    "%Y-%m-%d",          # 2025-06-07
    "%Y/%m/%d",          # 2025/06/07
    "%d-%m-%Y",          # 07-06-2025
    "%d/%m/%Y",          # 07/06/2025
    "%Y%m%d",            # 20250607
)

def _parse_date(raw) -> date | None:  # noqa: ANN001
    if isinstance(raw, date):
        return raw if isinstance(raw, date) and not isinstance(raw, datetime) else raw.date()
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        pass
    for fmt in _COMMON_FMTS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None

###############################################################################
#  Core worker functions (verbatim copies)                                    #
###############################################################################

# -- collector.py ------------------------------------------------------------

def collect_tasks(vault_path: str | Path, *, days_back: int = 7):
    vault = Path(vault_path).expanduser().resolve()
    today = date.today()
    since = today - timedelta(days=days_back)
    week: dict[str, list[dict]] = {d: [] for d in
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}
    md_files = list(vault.rglob("*.md"))
    for md_path in md_files:
        try:
            post = frontmatter.load(md_path)
        except Exception:
            continue
        raw_date = post.metadata.get("date") or post.metadata.get("created") or post.metadata.get("modified")
        note_date = _parse_date(raw_date)
        if note_date is None or not (since <= note_date <= today):
            continue
        tasks = [ln.rstrip() for ln in post.content.splitlines() if TASK_RE.match(ln)]
        front_tags = post.metadata.get("tags", [])
        if isinstance(front_tags, str):
            front_tags = [front_tags]
        body_tags = TAG_RE.findall(post.content)
        tags = sorted(set(front_tags) | set(body_tags))
        week[note_date.strftime("%A")].append({
            "file": md_path.relative_to(vault).as_posix(),
            "date": note_date,
            "tasks": tasks,
            "tags": tags,
        })
    return week

# -- renderer.py -------------------------------------------------------------

def _week_range():
    today = date.today()
    mon = today - timedelta(days=today.weekday())
    sun = mon + timedelta(days=6)
    return mon, sun

_TEMPLATE = Template("""\

## Highlights

_Total notes:_ **{{ notes }}**  
_Finished tasks:_ **{{ done_tasks }}**  
_Open tasks:_ **{{ open_tasks }}**

{% for weekday, notes in week.items() if notes %}
### {{ weekday }}
{% for n in notes %}
#### {{ n.file }} ({{ n.date }})

{% for t in n.tasks %}
{{ t }}
{% endfor %}
{% if n.tags %}
Tags: {{ n.tags | join(', ') }}
{% endif %}

{% endfor %}
{% endfor -%}
""")

def render_markdown(week):  # noqa: ANN001
    mon, sun = _week_range()
    note_count = sum(len(v) for v in week.values())
    total_tasks = sum(len(n["tasks"]) for v in week.values() for n in v)
    done_tasks = sum(1 for v in week.values() for n in v for t in n["tasks"] if "[x]" in t.lower())
    open_tasks = total_tasks - done_tasks
    return _TEMPLATE.render(start=mon, end=sun, notes=note_count, done_tasks=done_tasks, open_tasks=open_tasks, week=week)

# -- summarize.py ------------------------------------------------------------

GUMROAD_VERIFY_URL = "https://api.gumroad.com/v2/licenses/verify"
PRODUCT_ID = "IDSEv2EnJP2gfWNDavjlow=="

class GumroadHTTPError(RuntimeError):
    pass
class InvalidLicenseError(RuntimeError):
    pass

def verify_license(license_key: str):
    data = {"product_id": PRODUCT_ID, "license_key": license_key}
    try:
        resp = requests.post(GUMROAD_VERIFY_URL, data=data, timeout=5)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise GumroadHTTPError(f"Gumroad HTTP error: {exc}") from exc
    payload = resp.json()
    if not payload.get("success"):
        raise InvalidLicenseError(payload.get("message", "Invalid licence key"))

# Optional: you can `pip install openai` to enable summaries.
try:
    import openai
except ModuleNotFoundError:  # pragma: no cover
    openai = None  # type: ignore

def summarize_tasks(week_dict, openai_api_key, licence_key):
    if openai is None:
        raise RuntimeError("openai package not installed.")
    # verify_license(licence_key)
    if not openai_api_key:
        raise ValueError("OpenAI API key missing.")
    openai.api_key = openai_api_key
    all_tasks: list[str] = []
    all_tags: set[str] = set()
    for notes in week_dict.values():
        for note in notes:
            all_tasks.extend(note["tasks"])
            all_tags.update(note["tags"])
    if not all_tasks and not all_tags:
        return "No tasks or tags found for the last 7 days."
    tasks_text = "\n".join(f"- {t}" for t in all_tasks)
    tags_text = ", ".join(sorted(all_tags))
    prompt = (
        "Summarize the following weekly tasks and tags in about 200 words.\n\n"
        f"Tasks:\n{tasks_text}\n\nTags: {tags_text}\n"
    )
    rsp = openai.chat.completions.create(
        model="gpt-4.1-mini-2025-04-14",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes and reviews weekly notes."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return rsp.choices[0].message.content.strip()

###############################################################################
#  PyQt6 GUI                                                                  #
###############################################################################

if QApplication is not None:

    class MainWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("obs-weekly GUI")
            self._build()

        # ------------------------------------------------------------------ #
        # UI
        # ------------------------------------------------------------------ #

        def _build(self):
            self.vault_edit = QLineEdit()
            vault_btn = QPushButton("Browse…", clicked=self._pick_vault)
            self.output_edit = QLineEdit()
            out_btn = QPushButton("Browse…", clicked=self._pick_output)
            self.days_spin = QSpinBox(minimum=1, maximum=365, value=7)
            self.summarize_chk = QCheckBox("Add GPT summary")
            self.openai_edit = QLineEdit(placeholderText="OpenAI API key")
            self.openai_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.licence_edit = QLineEdit(placeholderText="Gumroad licence key (required)")
            self.licence_edit.setEchoMode(QLineEdit.EchoMode.Password)
            gen_btn = QPushButton("Generate Report", clicked=self._generate)
            quit_btn = QPushButton("Quit", clicked=self.close)
            self.log = QTextEdit(readOnly=True, minimumHeight=150)
            form = QVBoxLayout(self)

            def row(label, widget, *extras):
                box = QHBoxLayout()
                box.addWidget(QLabel(label))
                box.addWidget(widget, 1)
                for w in extras:
                    box.addWidget(w)
                form.addLayout(box)

            row("Vault path:", self.vault_edit, vault_btn)
            row("Output path:", self.output_edit, out_btn)
            row("Days back:", self.days_spin)
            form.addWidget(self.summarize_chk)
            form.addWidget(self.openai_edit)
            form.addWidget(self.licence_edit)
            btn_box = QHBoxLayout()
            btn_box.addWidget(gen_btn)
            btn_box.addWidget(quit_btn)
            form.addLayout(btn_box)
            form.addWidget(QLabel("Log:"))
            form.addWidget(self.log)

        # ------------------------------------------------------------------ #
        # Helpers
        # ------------------------------------------------------------------ #

        def _pick_vault(self):
            dir_ = QFileDialog.getExistingDirectory(self, "Select vault or folder")
            if dir_:
                self.vault_edit.setText(dir_)

        def _pick_output(self):
            file_, _ = QFileDialog.getSaveFileName(self, "Choose output file", "Weekly Report.md", "Markdown (*.md)")
            if file_:
                self.output_edit.setText(file_)

        def _log(self, msg: str):
            self.log.append(msg)

        def _err(self, msg: str):
            QMessageBox.critical(self, "Error", msg)
            self._log(f"✖ {msg}")

        def _generate(self):
            vault = Path(self.vault_edit.text()).expanduser()
            if not vault.is_dir():
                self._err("Vault path is invalid.")
                return
            out_txt = self.output_edit.text().strip()
            output = Path(out_txt).expanduser() if out_txt else None
            days_back = self.days_spin.value()
            summarize = self.summarize_chk.isChecked()
            openai_key = self.openai_edit.text().strip()
            licence_key = self.licence_edit.text().strip()
            if not licence_key:
                self._err("Gumroad licence key required.")
                return
            try:
                self._log(f"Scanning {vault} (last {days_back} days)…")
                week = collect_tasks(str(vault), days_back=days_back)
                md = render_markdown(week)
                if summarize:
                    try:
                        md = "\n\n## Weekly Summary\n" + summarize_tasks(week, openai_key, licence_key) + "\n" + md
                    except Exception as exc:
                        self._log(f"⚠ Summary failed: {exc}")
                if output is None or output.is_dir():
                    today = date.today(); mon = today - timedelta(days=today.weekday()); sun = mon + timedelta(days=6)
                    output = vault / f"Weekly Report; {mon:%d} to {sun:%d} {sun:%B} {sun:%Y}.md"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(md, encoding="utf-8")
                self._log(f"✓ Report written → {output}")
                QMessageBox.information(self, "Done", str(output))
            except Exception as exc:
                self._err(str(exc))

    def _launch_gui():  # pragma: no cover
        app = QApplication(sys.argv)
        win = MainWindow()
        win.resize(640, 420)
        win.show()
        sys.exit(app.exec())
else:
    def _launch_gui():  # type: ignore  # pragma: no cover
        print("✖ PyQt6 not installed — install with `pip install PyQt6` or run CLI mode.")
        sys.exit(1)

###############################################################################
#  CLI wrapper (kept minimal)                                                 #
###############################################################################

def _run_cli(argv: list[str]):
    parser = argparse.ArgumentParser(prog="obs-weekly", description="Generate a weekly Markdown report (with optional GPT summary).")
    parser.add_argument("vault_path", nargs="?", help="Path to your Markdown vault (defaults to CWD if it already contains *.md files)")
    parser.add_argument("-o", "--output", dest="output_path", help="Output file OR directory (default: vault/Weekly-<range>.md)")
    parser.add_argument("--summarize", action="store_true", help="Add a ~200-word AI summary (requires premium licence)")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back (default 7)")
    parser.add_argument("--gui", action="store_true", help="Launch the GUI instead of CLI")
    args = parser.parse_args(argv)
    if args.gui:
        _launch_gui()
        return
    # Existing CLI main() logic from your monolith -----------------------
    vault = Path(args.vault_path).expanduser().resolve() if args.vault_path else Path.cwd()
    if not vault.is_dir():
        sys.exit(f"✖ Vault path not found: {vault}")
    if args.output_path:
        out = Path(args.output_path).expanduser().resolve()
        if out.is_dir():
            today = date.today(); mon = today - timedelta(days=today.weekday()); sun = mon + timedelta(days=6)
            out = out / f"Weekly Report; {mon:%d} to {sun:%d} {sun:%B} {sun:%Y}.md"
    else:
        today = date.today(); mon = today - timedelta(days=today.weekday()); sun = mon + timedelta(days=6)
        out = vault / f"Weekly Report; {mon:%d} to {sun:%d} {sun:%B} {sun:%Y}.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    licence_key = input("Gumroad licence key (required): ").strip()
    #if not licence_key:
        #sys.exit("✖ Licence key required.")

    week = collect_tasks(str(vault), days_back=args.days)
    md = render_markdown(week)
    if args.summarize:
        openai_key = os.getenv("OPENAI_API_KEY") or input("OpenAI API key: ").strip()
        try:
            #md = "\n\n## Weekly Summary\n" + summarize_tasks(week, openai_key, licence_key) + "\n" + md
            md = "\n\n## Weekly Summary\n" + summarize_tasks(week, openai_key, licence_key) + "\n" + md
        except Exception as exc:
            print(f"⚠ Summary failed: {exc}")
    out.write_text(md, encoding="utf-8")
    print(f"✓ Weekly report written → {out}")

###############################################################################
#  Entry‑point                                                                #
###############################################################################

if __name__ == "__main__":
    if len(sys.argv) == 1 and os.environ.get("DISPLAY"):
        # No arguments → try GUI if possible
        _launch_gui()
    else:
        _run_cli(sys.argv[1:])
