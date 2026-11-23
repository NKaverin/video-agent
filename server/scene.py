import json
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent.parent

SCENES_FILE = ROOT / "scenes" / "scenes.json"


@dataclass(frozen=True)
class Event:
    id: str
    start: float
    end: float
    tags: tuple[str, ...]
    text: str
    close: float | None = None
    sudden: bool = False

    def is_active(self, time: float) -> bool:
        return self.start <= time < self.end


@dataclass(frozen=True)
class Scene:
    id: str
    title: str
    duration: float
    description: str
    background: tuple[str, ...]
    events: tuple[Event, ...]
    triggers: tuple[str, ...]

    def active_events(self, time: float) -> list[Event]:
        return [event for event in self.events if event.is_active(time)]


def parse_event(raw: dict) -> Event:
    return Event(
        id=raw["id"],
        start=raw["start"],
        end=raw["end"],
        tags=tuple(raw["tags"]),
        text=raw["text"],
        close=raw.get("close"),
        sudden=raw.get("sudden", False),
    )


def parse_scene(scene_id: str, raw: dict) -> Scene:
    return Scene(
        id=scene_id,
        title=raw["title"],
        duration=raw["duration"],
        description=raw["description"],
        background=tuple(raw["background"]),
        events=tuple(parse_event(event) for event in raw["events"]),
        triggers=tuple(raw["triggers"]),
    )


def load_scenes() -> dict[str, Scene]:
    path = SCENES_FILE if SCENES_FILE.exists() else ""
    logger.info("Scenes from {}", path)
    raw_scenes = json.loads(path.read_text(encoding="utf-8"))
    return {
        scene_id: parse_scene(scene_id, raw) for scene_id, raw in raw_scenes.items()
    }
