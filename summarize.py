import openai


def summarize_tasks(week_dict, openai_api_key):
    """Create a ~200-word summary of all tasks & tags in week_dict."""
    if not openai_api_key:
        raise ValueError("OpenAI API key missing.")

    openai.api_key = openai_api_key

    # Flatten tasks & tags
    all_tasks: list[str] = []
    all_tags: set[str] = set()

    for weekday, notes in week_dict.items():
        for note in notes:
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
            model="gpt-4o-mini",  # Updated to current fastest/cheapest model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes and reviews weekly notes."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
    except Exception as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc}")

    return rsp.choices[0].message.content.strip()