# collector.py
import os
from datetime import datetime, timedelta, date
from pathlib import Path
import re
import frontmatter

TASK_RE = re.compile(
    r'''^\s* # any leading whitespace
        [-*+]               # markdown bullet
        \s+                 # at least one space
        (?:\[[xX ]\]\s+)?   # OPTIONAL checkbox [ ], [x], [X]
        .+                  # the text itself
    ''',
    re.VERBOSE,
)
TAG_RE = re.compile(r'(?<!\w)#([\w/-]+)')  # #tag or #foo/bar

# Common date formats to check against
_COMMON_FMTS = ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y%m%d")


def _parse_date(raw) -> date | None:
    if isinstance(raw, date):
        return raw if not isinstance(raw, datetime) else raw.date()
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


def collect_tasks(vault_path: str):
    today = datetime.now().date()
    week_ago = today - timedelta(days=6)

    days = ["Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"]
    week: dict[str, list[dict]] = {d: [] for d in days}

    print("Scanning vault:", vault_path)
    count_files = 0

    for md_path in Path(vault_path).rglob("*.md"):
        count_files += 1
        try:
            post = frontmatter.load(md_path)
        except Exception:
            continue

        # 1. Try to get date from frontmatter
        raw_date = (
                post.metadata.get("date")
                or post.metadata.get("created")
                or post.metadata.get("modified")
        )
        note_date = _parse_date(raw_date)

        # 2. Try to parse date from the filename (e.g. "2026-04-08.md")
        if note_date is None:
            note_date = _parse_date(md_path.stem)

        # 3. ULTIMATE FALLBACK: Get the OS file modification time
        if note_date is None:
            try:
                mtime = md_path.stat().st_mtime
                note_date = date.fromtimestamp(mtime)
            except Exception:
                pass

        # If it's outside our 7-day window, skip it.
        if note_date is None or not (week_ago <= note_date <= today):
            continue

        # Extract tasks & tags
        tasks = [ln.rstrip() for ln in post.content.splitlines() if TASK_RE.match(ln)]
        front_tags = post.metadata.get("tags", [])
        if isinstance(front_tags, str):
            front_tags = [front_tags]
        body_tags = TAG_RE.findall(post.content)
        tags = sorted(set(front_tags) | set(body_tags))

        # Only add to the report if there is actually something to report
        if tasks or tags:
            week[note_date.strftime("%A")].append(
                {
                    "file": md_path.name,
                    "date": note_date,
                    "tasks": tasks,
                    "tags": tags,
                }
            )

    print("Total .md files seen:", count_files)
    return week