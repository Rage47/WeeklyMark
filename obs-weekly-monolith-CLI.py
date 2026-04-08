# collector.py
from datetime import datetime, timedelta
from pathlib import Path
import re
import frontmatter
from jinja2 import Template
from datetime import date, timedelta
import requests
import openai
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path
import toml

# before
# TASK_RE = re.compile(r'^\s*[-*+]\s+\[[xX ]\]\s+.*')

# after  – checkbox part is now optional (?: ... )?
TASK_RE = re.compile(
    r'''^\s*                # any leading whitespace
        [-*+]               # markdown bullet
        \s+                 # at least one space
        (?:\[[xX ]\]\s+)?   # OPTIONAL checkbox [ ], [x], [X]
        .+                  # the text itself
    ''',
    re.VERBOSE,
)
TAG_RE = re.compile(r'(?<!\w)#([\w/-]+)')  # #tag or #foo/bar
from pathlib import Path
from datetime import date, datetime, timedelta
import frontmatter, re
import inspect, sys, traceback


# ──────────────────────────────────────────────────────────────────────
# tiny date parser that uses ONLY the standard library
# ──────────────────────────────────────────────────────────────────────
_COMMON_FMTS = (
    "%Y-%m-%d",          # 2025-06-07
    "%Y/%m/%d",          # 2025/06/07
    "%d-%m-%Y",          # 07-06-2025
    "%d/%m/%Y",          # 07/06/2025
    "%Y%m%d",            # 20250607
)

def _parse_date(raw) -> date | None:
    """Return a `date` from various YAML front-matter representations."""
    if isinstance(raw, date):
        # covers both `date` and `datetime`
        return raw if isinstance(raw, date) and not isinstance(raw, datetime) else raw.date()

    if not isinstance(raw, str):
        return None

    raw = raw.strip()

    # 1️⃣  ISO-8601 shortcut (works for '2025-06-07' and '2025-06-07T09:00')
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        pass

    # 2️⃣  several common strftime formats
    for fmt in _COMMON_FMTS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue

    return None
# ──────────────────────────────────────────────────────────────────────


def collect_tasks(vault_path: str | Path, *, days_back: int = 7):
    """
    Scan `vault_path` for Markdown notes in the last `days_back`
    days (default = one week) and return { weekday → [note_dict] }.
    """
    vault = Path(vault_path).expanduser().resolve()
    today = date.today()
    since = today - timedelta(days=days_back)

    # initialise Monday … Sunday → empty list
    week: dict[str, list[dict]] = {d: [] for d in
        ["Monday", "Tuesday", "Wednesday", "Thursday",
         "Friday", "Saturday", "Sunday"]}

    md_files = list(vault.rglob("*.md"))
    print(f"Scanning vault → {vault}")
    print(f"Total .md files seen: {len(md_files)}")

    for md_path in md_files:
        try:
            post = frontmatter.load(md_path)
        except Exception as exc:
            print("⚠️  skipping", md_path, "—", exc)
            continue

        # ---------- date handling ----------
        raw_date = (
            post.metadata.get("date")
            or post.metadata.get("created")
            or post.metadata.get("modified")
        )
        note_date = _parse_date(raw_date)
        if note_date is None or not (since <= note_date <= today):
            continue

        # ---------- task & tag extraction ----------
        tasks = [ln.rstrip() for ln in post.content.splitlines()
                 if TASK_RE.match(ln)]

        front_tags = post.metadata.get("tags", [])
        if isinstance(front_tags, str):
            front_tags = [front_tags]

        body_tags = TAG_RE.findall(post.content)
        tags = sorted(set(front_tags) | set(body_tags))

        week[note_date.strftime("%A")].append(
            {
                "file": md_path.relative_to(vault).as_posix(),
                "date": note_date,
                "tasks": tasks,
                "tags": tags,
            }
        )

    return week


# renderer.py



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


def render_markdown(week):
    mon, sun = _week_range()
    note_count = sum(len(v) for v in week.values())
    total_tasks = sum(len(n["tasks"]) for v in week.values() for n in v)
    done_tasks = sum(
        1
        for v in week.values()
        for n in v
        for t in n["tasks"]
        if "[x]" in t.lower()  # detects both [x] and [X]
    )
    open_tasks = total_tasks - done_tasks
    return _TEMPLATE.render(
        start=mon, end=sun,
        notes=note_count,
        done_tasks=done_tasks,
        open_tasks=open_tasks,
        week=week,
    )


# summarize.py


GUMROAD_VERIFY_URL = "https://api.gumroad.com/v2/licenses/verify"
PRODUCT_ID = "IDSEv2EnJP2gfWNDavjlow=="


# summarize.py
class GumroadHTTPError(RuntimeError):
    """Network or HTTP level failure (5xx, 404, timeout…)."""


class InvalidLicenseError(RuntimeError):
    """Licence exists but is invalid, refunded, or for another product."""


def verify_license(license_key: str):
    """Raise *InvalidLicenseError* on bad key, *GumroadHTTPError* on 4xx/5xx."""
    data = {"product_id": PRODUCT_ID, "license_key": license_key}
    try:
        resp = requests.post(GUMROAD_VERIFY_URL, data=data, timeout=5)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        # 404, 5xx, network unreachable, etc.
        raise GumroadHTTPError(f"Gumroad HTTP error: {exc}") from exc

    payload = resp.json()
    if not payload.get("success"):
        raise InvalidLicenseError(payload.get("message", "Invalid licence key"))


# summarize.py  (only add these few lines near the top)

# -------------------------------------------------------------------- #

def summarize_tasks(week_dict, openai_api_key, licence_key):
    """Create a ~200-word summary of all tasks & tags in week_dict."""

    # verify_license(licence_key)

    if not openai_api_key:
        raise ValueError("OpenAI API key missing.")
    openai.api_key = openai_api_key

    # ── flatten tasks & tags from the new data structure ──────────────────
    all_tasks: list[str] = []
    all_tags: set[str] = set()

    for weekday, notes in week_dict.items():
        for note in notes:  # notes is a list now
            all_tasks.extend(note["tasks"])
            all_tags.update(note["tags"])

    if not all_tasks and not all_tags:
        return "No tasks or tags found for the last 7 days."

    tasks_text = "\n".join(f"- {t}" for t in all_tasks)
    tags_text = ", ".join(sorted(all_tags))

    prompt = (
        "Summarize the following weekly tasks and tags in about 200 words.\n\n"
        f"Tasks:\n{tasks_text}\n\n"
        f"Tags: {tags_text}\n"
    )

    try:
        rsp = openai.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[
                {"role": "system", "content":
                    "You are a helpful assistant that summarizes and reviews weekly notes."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
    except Exception as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc}")

    return rsp.choices[0].message.content.strip()


# obs_weekly/__main__.py


CONFIG_FILE = Path.home() / ".obs_weekly_config.toml"


# ────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ────────────────────────────────────────────────────────────────────────────
def week_range_today() -> tuple[date, date]:
    """Return this Monday-Sunday date range as (monday, sunday)."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())  # Monday = 0
    sunday = monday + timedelta(days=6)
    return monday, sunday


def default_output(vault: Path) -> Path:
    monday, sunday = week_range_today()
    fname = (
        f"Weekly Report; {monday:%d} to {sunday:%d} "
        f"{sunday:%B} {sunday:%Y}.md"
    )
    return vault / fname


def load_config() -> dict:
    """Load config; create an empty file on first run."""
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text("{}")
    try:
        return toml.load(CONFIG_FILE)
    except Exception as exc:
        print(f"⚠  Config error ({exc}); resetting {CONFIG_FILE}.", file=sys.stderr)
        CONFIG_FILE.write_text("{}")
        return {}


def save_config(cfg: dict) -> None:
    try:
        toml.dump(cfg, CONFIG_FILE.open("w"))
    except Exception as exc:
        print(f"✖  Could not write config file: {exc}", file=sys.stderr)


def prompt_and_store(cfg: dict, key: str, label: str) -> str | None:
    value = input(f"{label} (leave blank to skip): ").strip()
    if value:
        cfg[key] = value
        save_config(cfg)
    return value or None


def detect_local_vault() -> Path | None:
    # 1️⃣ folder where the executable is located
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    if any(base.glob("*.md")):
        return base
    # 2️⃣ fallback: original current-dir logic
    cwd = Path.cwd()
    if any(cwd.glob("*.md")):
        return cwd
    return None



# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        prog="obs-weekly",
        description="Generate a weekly Obsidian report (with optional GPT summary).",
    )
    # 1️⃣  make positional arg optional
    parser.add_argument(
        "vault_path",
        nargs="?",  # ← changed
        help="Path to your Obsidian vault (defaults to CWD if it already contains *.md files)",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        help="Output file OR directory (default: vault/Weekly-<range>.md)",
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Add a ~200-word GPT summary (requires premium licence)",
    )
    args = parser.parse_args()

    # ── resolve vault ──────────────────────────────────────────────────────
    if args.vault_path:
        vault = Path(args.vault_path).expanduser().resolve()
    else:
        vault = detect_local_vault()
        if vault:
            print(f"ℹ  No vault path supplied – using current directory: {vault}")
        else:
            sys.exit(
                "✖  Vault path not provided and no Markdown files found in the current directory."
            )

    if not vault.is_dir():
        sys.exit(f"✖  Vault path not found: {vault}")

    # ── choose output file ─────────────────────────────────────────────────
    if args.output_path:
        out = Path(args.output_path).expanduser().resolve()
        if out.is_dir():
            out = out / default_output(vault).name
    else:
        out = default_output(vault)
    out.parent.mkdir(parents=True, exist_ok=True)

    # ── choose output file ─────────────────────────────────────────────────
    if args.output_path:
        out = Path(args.output_path).expanduser().resolve()
        if out.is_dir():
            out = out / default_output(vault).name
    else:
        out = default_output(vault)
    out.parent.mkdir(parents=True, exist_ok=True)

    # ── load / prompt config ───────────────────────────────────────────────
    cfg = load_config()

    # ── licence is mandatory for all tiers ────────────────────────────────
    licence_key = cfg.get("gumroad_license_key") or prompt_and_store(
        cfg, "gumroad_license_key", "Gumroad licence key (required)"
    )
    if not licence_key:
        sys.exit("✖  A valid Gumroad licence key is required to run this tool.")

    try:
        # verify_license(licence_key)  # reuse the same helper as summarize.py
        print('LICSENSE CHECK SKIPPED')
    except (InvalidLicenseError, GumroadHTTPError) as err:
        sys.exit(f"✖  Licence check failed: {err}")

    # Always okay to run basic mode
    tasks_by_day = collect_tasks(str(vault))

    md = render_markdown(tasks_by_day)
    # ── optional premium summary ───────────────────────────────────────────
    # ── optional premium summary ───────────────────────────────────────────
    if args.summarize:
        # make sure we have some starting values (may be None)
        openai_key = cfg.get("openai_api_key") or prompt_and_store(cfg, "openai_api_key", "OpenAI API key")

        licence_key = cfg.get("gumroad_license_key") or prompt_and_store(cfg, "gumroad_license_key",
                                                                         "Gumroad licence key")

        attempts = 0
        while attempts < 2:
            if not (openai_key and licence_key):
                print("↪  Summary skipped – keys were not provided.")
                break

            try:
                summary = summarize_tasks(tasks_by_day, openai_key, licence_key)
                md = "\n\n## Weekly Summary\n" + summary + "\n" + md
                break  # 👍 success → exit loop
            except RuntimeError as err:
                # network glitch OR invalid licence
                print(f"⚠  Summary skipped: {err}")
                # let user decide to retry or bail out
                new_key = input("Paste a new Gumroad licence key (leave blank to skip): ").strip()
                if new_key:
                    licence_key = new_key
                    cfg["gumroad_license_key"] = new_key
                    save_config(cfg)
                    attempts += 1
                    # loop again with new key (unlimited retries)
                    continue
                else:
                    print("↪  Skipping summary for this run.")
                    break

    # ── write report ───────────────────────────────────────────────────────
    try:
        out.write_text(md, encoding="utf-8")
        print(f"✓  Weekly report written → {out}")
    except Exception as exc:
        sys.exit(f"✖  Could not write report: {exc}")


if __name__ == "__main__":
    main()
