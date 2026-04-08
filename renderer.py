# renderer.py
from jinja2 import Template
from datetime import date, timedelta

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
    note_count  = sum(len(v) for v in week.values())
    total_tasks = sum(len(n["tasks"]) for v in week.values() for n in v)
    done_tasks  = sum(
        1
        for v in week.values()
        for n in v
        for t in n["tasks"]
        if "[x]" in t.lower()          # detects both [x] and [X]
    )
    open_tasks  = total_tasks - done_tasks
    return _TEMPLATE.render(
        start=mon, end=sun,
        notes=note_count,
        done_tasks=done_tasks,
        open_tasks=open_tasks,
        week=week,
    )
