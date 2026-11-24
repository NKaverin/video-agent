from pathlib import Path
from typing import Literal

from google import genai
from google.genai import types
from loguru import logger
from pydantic import BaseModel

from scene import Scene
from timing import budget_table, reserved_s

PLANNER_MODEL = "gemini-3.8-flash"
PLANNER_PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "planner.md"


class PlannedLine(BaseModel):
    event_id: str
    kind: Literal["prepare", "point", "reflect"]
    start_s: float
    text: str
    short: str
    priority: int
    why: str


class Plan(BaseModel):
    lines: list[PlannedLine]


def load_planner_prompt() -> str:
    if not PLANNER_PROMPT.exists():
        raise FileNotFoundError("No planner prompt: put it in " + str(PLANNER_PROMPT))
    prompt = PLANNER_PROMPT.read_text(encoding="utf-8")
    return prompt + "\n\nLongest line that fits:\n" + budget_table()


def plan_request(scene: Scene, said: list[str]) -> str:
    events = [
        " | ".join(
            [
                event.id,
                str(event.start) + "-" + str(event.end),
                ", ".join(event.tags),
                event.text,
            ]
        )
        for event in scene.events
    ]
    lines = [scene.as_context(), "Video length: " + str(scene.duration) + " s"]
    lines += ["", "Events (id | start-end s | tags | what happens):", *events]
    lines += ["", "What the user said before the video:"]
    lines += ["- " + text for text in said] or ["Nothing yet."]
    return "\n".join(lines)


async def make_plan(
    client: genai.Client, system_instruction: str, scene: Scene, said: list[str]
) -> Plan:
    response = await client.aio.models.generate_content(
        model=PLANNER_MODEL,
        contents=plan_request(scene, said),
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=Plan,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )
    return Plan.model_validate_json(response.text)


def log_plan(plan: Plan) -> None:
    for line in sorted(plan.lines, key=lambda line: line.start_s):
        logger.info(
            "{:6.1}s {} {:<7} P{} {:4.1f}s {}",
            line.start_s,
            line.event_id,
            line.kind,
            line.priority,
            reserved_s(line.text),
            line.text,
        )
