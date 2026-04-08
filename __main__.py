from __future__ import annotations

import argparse
import sys
import json
from datetime import date, timedelta
from pathlib import Path

from collector import collect_tasks
from renderer import render_markdown
from summarize import summarize_tasks

CONFIG_FILE = Path.home() / ".weeklymark_config.json"

def week_range_today() -> tuple[date, date]:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday

def default_output(vault: Path) -> Path:
    monday, sunday = week_range_today()
    fname = f"Weekly Report: {monday:%d} to {sunday:%d} {sunday:%B} {sunday:%Y}.md"
    return vault / fname

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(cfg: dict) -> None:
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=4)
    except Exception as exc:
        print(f"✖ Could not write config file: {exc}", file=sys.stderr)

def prompt_and_store(cfg: dict, key: str, label: str) -> str | None:
    value = input(f"{label} (leave blank to skip): ").strip()
    if value:
        cfg[key] = value
        save_config(cfg)
    return value or None

def detect_local_vault() -> Path | None:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    if any(base.glob("*.md")): return base
    cwd = Path.cwd()
    if any(cwd.glob("*.md")): return cwd
    return None

def cli_main() -> None:
    parser = argparse.ArgumentParser(prog="WeeklyMark", description="Generate a weekly Markdown report.")
    parser.add_argument("vault_path", nargs="?", help="Path to your Markdown vault")
    parser.add_argument("-o", "--output", dest="output_path", help="Output file OR directory")
    parser.add_argument("--summarize", action="store_true", help="Add a GPT summary")
    args = parser.parse_args()

    # Resolve vault
    if args.vault_path:
        vault = Path(args.vault_path).expanduser().resolve()
    else:
        vault = detect_local_vault()
        if not vault:
            sys.exit("✖ Vault path not provided and no Markdown files found in current directory.")

    if not vault.is_dir():
        sys.exit(f"✖ Vault path not found: {vault}")

    # Output file
    if args.output_path:
        out = Path(args.output_path).expanduser().resolve()
        if out.is_dir(): out = out / default_output(vault).name
    else:
        out = default_output(vault)
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"Scanning vault: {vault}...")
    tasks_by_day = collect_tasks(str(vault))
    md = render_markdown(tasks_by_day)

    if args.summarize:
        cfg = load_config()
        openai_key = cfg.get("openai_api_key") or prompt_and_store(cfg, "openai_api_key", "OpenAI API key")
        if openai_key:
            try:
                print("Generating AI Summary...")
                summary = summarize_tasks(tasks_by_day, openai_key)
                md = "\n\n## AI Weekly Summary\n" + summary + "\n\n---\n" + md
            except Exception as e:
                print(f"⚠ Summary skipped: {e}")
        else:
            print("↪ Summary skipped – no API key provided.")

    try:
        out.write_text(md, encoding="utf-8")
        print(f"✓ Weekly report written → {out}")
    except Exception as exc:
        sys.exit(f"✖ Could not write report: {exc}")

def _launch_gui() -> None:
    try:
        import gui
        gui.main()
    except ImportError as err:
        print(f"⚠ GUI unavailable ({err}) – falling back to CLI.")
        cli_main()

if __name__ == "__main__":
    # If no arguments are passed, launch the GUI
    if len(sys.argv) == 1:
        _launch_gui()
    # Otherwise, run the CLI
    else:
        cli_main()