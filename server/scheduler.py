from planner import PlannedLine
from scene import Event, Scene
from timeline import FLOOR_TAGS

PREPARE_LEAD_S = 15.0
REFLECT_LAG_S = 10.0


def silent_episodes(scene: Scene) -> list[tuple[float, float]]:
    """Start and end of every event that the bot must not speak."""
    return [
        (event.start, event.end)
        for event in scene.events
        if any(tag in FLOOR_TAGS for tag in event.tags)
    ]


def window(line: PlannedLine, event: Event, length: float) -> tuple[float, float]:
    """Earliest and latest start"""
    if line.kind == "prepare":
        return event.start - PREPARE_LEAD_S, event.start - length
    if line.kind == "point":
        return event.start, event.end - length
    return event.end, event.end + REFLECT_LAG_S
