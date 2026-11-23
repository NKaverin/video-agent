from dataclasses import dataclass

from loguru import logger
from pipecat.frames.frames import Frame, LLMContextFrame, SystemFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


@dataclass
class FloorFrame(SystemFrame):
    """Whether an event in the video has the floor: the bot must not speak."""

    event_has_floor: bool


class FloorGate(FrameProcessor):
    def __init__(self):
        super().__init__()
        self._held = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, FloorFrame):
            self._held = frame.event_has_floor
            return
        if isinstance(frame, LLMContextFrame) and self._held:
            logger.info("Reply held: an event in the video has the floor")
            return

        await self.push_frame(frame, direction)
