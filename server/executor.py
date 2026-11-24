from loguru import logger
from pipecat.frames.frames import Frame, LLMContextFrame, TTSSpeakFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi.frames import RTVIClientMessageFrame

from planner import Plan, Planner
from scene import Scene
from scheduler import Slot, log_schedule, make_schedule, silent_episodes
from timing import max_chars

REPLAY_DELAY_S = 1.5
# A reply shorte than this is not worth it
MIN_REPLY_CHARS = 20


class Executor(FrameProcessor):
    """Speaks the scheduled lines on the video clock."""

    def __init__(self, scene: Scene, planner: Planner):
        super().__init__()
        self._scene = scene
        self._episodes = silent_episodes(scene)
        self._planner = planner
        self._plan: Plan | None = None
        self._slots: list[Slot] = []
        self._time = 0.0
        self._playing = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, RTVIClientMessageFrame) and frame.type == "video-time":
            self._time = frame.data["time"]
            self._playing = frame.data["playing"]
            if self._playing:
                await self._speak_due()
            elif (
                isinstance(frame, LLMContextFrame)
                and self._playing
                and not self._budget_reply(frame)
            ):
                return

        await self.push_frame(frame, direction)

    async def _speak_due(self) -> None:
        plan = self._planner.plan
        if plan is not None and plan is not self._plan:
            self._plan = plan
            placed, dropped = make_schedule(self._scene, plan)
            log_schedule(placed, dropped)
            self._slots = [slot for slot in placed if slot.start >= self._time]
        while self._slots and self._slots[0].start <= self._time:
            slot = self._slots.pop(0)
            logger.info("{:6.1f}s say {} {}", self._time, slot.line.event_id, slot.text)
            await self.push_frame(TTSSpeakFrame(slot.text))

    def _next_busy(self) -> float:
        """When the bot must next be quiet: a silent episode or a planned line."""
        starts = [begin for begin, _ in self._episodes if begin > self._time]
        starts += [slot.start for slot in self._slots]
        return min(starts, default=self._scene.duration)

    def _budget_reply(self, frame: LLMContextFrame) -> bool:
        budget = self._next_busy() - self._time - REPLAY_DELAY_S
        chars = max_chars(budget)
        if chars < MIN_REPLY_CHARS:
            logger.info("{:6.1f}s reply held: {:.1f}s free", self._time, budget)
            return False
        logger.info(
            "{:6.1f}s reply budget: {:.1f}s: {} characters", self._time, budget, chars
        )
        frame.context.add_message(
            {
                "role": "developer",
                "content": "Reply in at most " + str(chars) + " characters.",
            }
        )
        return True
