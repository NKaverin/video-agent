from loguru import logger
from pipecat.frames.frames import Frame, TTSSpeakFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi.frames import RTVIClientMessageFrame

from planner import Plan, Planner
from scene import Scene
from scheduler import Slot, log_schedule, make_schedule


class Executor(FrameProcessor):
    """Speaks the scheduled lines on the video clock."""

    def __init__(self, scene: Scene, planner: Planner):
        super().__init__()
        self._scene = scene
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
