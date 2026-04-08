# collector.py
from datetime import datetime, timedelta
from pathlib import Path
import re
import frontmatter

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
TAG_RE = re.compile(r'(?<!\w)#([\w/-]+)')     # #tag or #foo/bar

def collect_tasks(vault_path: str):
    """Return dict  weekday → list[ note_dict ]."""
    today = datetime.now().date()
    week_ago = today - timedelta(days=6)

    # weekday keys initialised to empty lists
    days = ["Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"]
    week: dict[str, list[dict]] = {d: [] for d in days}

    # in collector.py, before 'for md_path in Path(...)'
    print("Scanning vault:", vault_path)
    count_files = 0
    for md_path in Path(vault_path).rglob("*.md"):
        count_files += 1
    print("Total .md files seen:", count_files)

    for md_path in Path(vault_path).rglob("*.md"):
        try:
            post = frontmatter.load(md_path)
        except Exception:
            continue

        date_str = post.metadata.get("date")
        if not date_str:
            continue
        try:
            note_date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
        except ValueError:
            continue
        if not (week_ago <= note_date <= today):
            continue

        # ── extract tasks & tags ───────────────────────────────────────────
        tasks = [ln.rstrip() for ln in post.content.splitlines() if TASK_RE.match(ln)]
        front_tags = post.metadata.get("tags", [])
        if isinstance(front_tags, str):
            front_tags = [front_tags]
        body_tags = TAG_RE.findall(post.content)
        tags = sorted(set(front_tags) | set(body_tags))

        week[note_date.strftime("%A")].append(
            {
                "file": md_path.name,
                "date": note_date,
                "tasks": tasks,
                "tags": tags,
            }
        )

    return week
