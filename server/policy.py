from scene import Event

RULES = (
    ("spoken_to", "note"),
    ("wait", "note"),
    ("departure", "ask"),
    ("approach", "cue"),
    ("sudden", "cue"),
)

SPEAKING_ACTIONS = ("cue", "ask")


def action_for(event: Event) -> str:
    tags = event.tags + ("sudden",) if event.sudden else event.tags
    for tag, action in RULES:
        if tag in tags:
            return action
    return "note"
