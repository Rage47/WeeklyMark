# Weekly Review (Week {{ start.isocalendar().week }} - {{ end }})
_Total notes:_ **{{ notes|length }}**
_Open tasks:_ **{{ tasks|length }}**

## Highlights
{% for n in notes %}
- **{{ n.path.stem }}** — {{ n.content|truncate(120) }}
{% endfor %}

## Task list
{% for t in tasks %}
- [ ] {{ t }}
{% endfor %}

## Tags
{{ tags|unique|join(", ") }}
