import asyncio
import os
from pathlib import Path
from time import monotonic
from typing import Literal

from google import genai
from google.genai import errors, types
from loguru import logger
from pydantic import BaseModel, ValidationError

from scene import Scene
from timing import budget_table, reserved_s

PLANNER_MODEL = "gemini-3.8-flash"
PLANNER_PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "planner.md"

PLAN_FILE = Path(__file__).resolve().parent.parent / "runs" / "plan.json"


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


def plan_request(scene: Scene, said: list[str], current: Plan | None) -> str:
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
    if current:
        lines += ["", "Current plan:", current.model_dump_json(indent=1)]
    lines += ["", "What the user said, in order:"]
    lines += ["- " + text for text in said] or ["Nothing yet."]
    return "\n".join(lines)


async def make_plan(
    client: genai.Client,
    system_instruction: str,
    scene: Scene,
    said: list[str],
    current: Plan | None,
) -> Plan:
    response = await client.aio.models.generate_content(
        model=PLANNER_MODEL,
        contents=plan_request(scene, said, current),
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
        logger.debug(
            "{:6.1f}s {} {:<7} P{} {:4.1f}s {}",
            line.start_s,
            line.event_id,
            line.kind,
            line.priority,
            reserved_s(line.text),
            line.text,
        )


class Planner:
    """An initial plan from the scene"""

    def __init__(self, scene: Scene, system_instruction: str):
        self._client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        self._scene = scene
        self._system_instruction = system_instruction
        self._said: list[str] = []
        self._task: asyncio.Task | None = None
        self.plan: Plan | None = None
        self.watching = False

    async def _make(self, said: list[str]) -> None:
        started = monotonic()
        try:
            plan = await make_plan(
                self._client, self._system_instruction, self._scene, said, self.plan
            )
        except (errors.APIError, ValidationError) as error:
            logger.error("Planning failed: {}", error)
            return
        self.plan = plan
        PLAN_FILE.write_text(plan.model_dump_json(indent=1), encoding="utf-8")
        logger.info(
            "Plan ready in {:.1f}s, from {} things the user said",
            monotonic() - started,
            len(said),
        )
        log_plan(plan)

    def start(self) -> None:
        self._task = asyncio.create_task(self._make([]))

    def user_said(self, text: str) -> None:
        self._said.append(text)

    async def _adapt(self, initial: asyncio.Task | None) -> None:
        if initial:
            await initial
        await self._make(list(self._said))

    def adapt(self) -> None:
        self.watching = True
        self._task = asyncio.create_task(self._adapt(self._task))

    async def close(self) -> None:
        if self._task:
            self._task.cancel()
