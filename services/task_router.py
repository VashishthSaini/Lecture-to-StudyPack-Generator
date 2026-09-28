SUPPORTED_TASKS = {
    "summary",
    "notes",
    "questions",
    "mcqs"
}

TASK_ALIASES = {
    "summarize": "summary",
    "summarisation": "summary",
    "summarization": "summary",
    "note": "notes",
    "key points": "notes",
    "key-points": "notes",
    "question": "questions",
    "quiz": "questions",
    "mcq": "mcqs",
    "multiple choice": "mcqs",
    "multiple-choice": "mcqs",
    "multiple choice questions": "mcqs",
}


def route_task(task_input):
    """
    Route a task request to the appropriate task type.

    Args:
        task_input: String describing the task (e.g., "generate summary", "create mcqs")

    Returns:
        dict: {
            "task_type": str (one of SUPPORTED_TASKS),
            "confidence": float (0.0-1.0),
            "error": str or None
        }
    """
    if not task_input or not isinstance(task_input, str):
        return {
            "task_type": None,
            "confidence": 0.0,
            "error": "Task input is required"
        }

    normalized = task_input.lower().strip()

    # Direct match
    for task in SUPPORTED_TASKS:
        if task == normalized:
            return {
                "task_type": task,
                "confidence": 1.0,
                "error": None
            }

    # Alias match (exact)
    for alias, canonical in TASK_ALIASES.items():
        if alias == normalized:
            return {
                "task_type": canonical,
                "confidence": 0.9,
                "error": None
            }

    # Alias partial match - check longer aliases first to prefer specific phrases
    # Sort by length descending so "multiple choice questions" matches before "question"
    sorted_aliases = sorted(TASK_ALIASES.items(), key=lambda x: -len(x[0]))
    for alias, canonical in sorted_aliases:
        if alias in normalized:
            return {
                "task_type": canonical,
                "confidence": 0.7,
                "error": None
            }

    # Partial match - check if any supported task keyword appears as a whole word in input
    import re
    for task in SUPPORTED_TASKS:
        # Use word boundary to match whole words only
        if re.search(r'\b' + re.escape(task) + r'\b', normalized):
            return {
                "task_type": task,
                "confidence": 0.5,
                "error": None
            }

    return {
        "task_type": None,
        "confidence": 0.0,
        "error": f"Unsupported task type. Supported: {', '.join(sorted(SUPPORTED_TASKS))}"
    }


def get_supported_tasks():
    """Return list of supported task types."""
    return sorted(SUPPORTED_TASKS)


def is_supported_task(task_type):
    """Check if a task type is supported."""
    return task_type in SUPPORTED_TASKS