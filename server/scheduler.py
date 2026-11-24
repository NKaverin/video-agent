from dataclasses import dataclass

from loguru import logger

from planner import Plan, PlannedLine
from scene import Event, Scene
from timeline import FLOOR_TAGS
from timing import reserved_s

PREPARE_LEAD_S = 15.0
REFLECT_LAG_S = 10.0
GAP_S = 1.0


@dataclass
class Slot:
    line: PlannedLine
    text: str
    start: float
    end: float


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


def crosses(start: float, length: float, episodes: list[tuple[float, float]]) -> bool:
    return any(start < end and start + length > begin for begin, end in episodes)


def closest_start(
    want: float,
    length: float,
    earliest: float,
    latest: float,
    episodes: list[tuple[float, float]],
) -> float | None:
    """The allowed start nearest to 'want'"""
    candidates = [min(max(want, earliest), latest), earliest, latest]
    for begin, end in episodes:
        candidates += [begin - length, end]
    allowed = [
        start
        for start in candidates
        if earliest <= start <= latest and not crosses(start, length, episodes)
    ]
    return min(allowed, key=lambda start: abs(start - want), default=None)


def fit(
    line: PlannedLine,
    event: Event,
    scene: Scene,
    episodes: list[tuple[float, float]],
    free_from: float,
) -> Slot | None:
    for text in (line.text, line.short):
        length = reserved_s(text)
        earliest, latest = window(line, event, length)
        earliest = max(earliest, free_from, 0.0)
        latest = min(latest, scene.duration - length)
        start = closest_start(line.start_s, length, earliest, latest, episodes)
        if start is not None:
            return Slot(line, text, start, start + length)
    return None


def make_schedule(
    scene: Scene, plan: Plan
) -> tuple[list[Slot], list[tuple[PlannedLine, str]]]:
    events = {event.id: event for event in scene.events}
    episodes = silent_episodes(scene)
    placed: list[Slot] = []
    dropped: list[tuple[PlannedLine, str]] = []
    for line in sorted(plan.lines, key=lambda line: line.start_s):
        event = events.get(line.event_id)
        if event is None:
            dropped.append((line, "unknown event"))
            continue
        free_from = placed[-1].end + GAP_S if placed else 0.0
        slot = fit(line, event, scene, episodes, free_from)
        if slot is None and placed and placed[-1].line.priority > line.priority:
            previous = placed.pop()
            free_from = placed[-1].end + GAP_S if placed else 0.0
            slot = fit(line, event, scene, episodes, free_from)
            if slot is None:
                placed.append(previous)
            else:
                dropped.append((previous.line, "made room for " + line.event_id))
        if slot is None:
            dropped.append((line, "no room"))
        else:
            placed.append(slot)
    return placed, dropped


def status(slot: Slot) -> str:
    notes = []
    if slot.text == slot.line.short:
        notes.append("short")
    shift = slot.start - slot.line.start_s
    if abs(shift) >= 0.05:
        notes.append("moved" + format(shift, "+1f") + "s")
    return ", ".join(notes) or "ok"


def log_schedule(placed: list[Slot], dropped: list[tuple[PlannedLine, str]]) -> None:
    for slot in placed:
        logger.info(
            "{:6.1f}s {} {:<7} p{} {:4.1f}s {:<20} {}",
            slot.start,
            slot.line.event_id,
            slot.line.kind,
            slot.line.priority,
            slot.end - slot.start,
            status(slot),
            slot.text,
        )
    for line, reason in dropped:
        logger.info(
            "dropped {} {} P{} at {:.1f}s, {}: {}",
            line.event_id,
            line.kind,
            line.priority,
            line.start_s,
            reason,
            line.text,
        )
