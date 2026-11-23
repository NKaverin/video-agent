from loguru import logger
from pipecat.frames.frames import (
    BotSpeakingFrame,
    Frame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    TranscriptionFrame,
    UserSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class TranscriptPrinter(FrameProcessor):
    """Logs each transcript and passes every frame on unchanged"""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            logger.info("User: {}", frame.text)

        await self.push_frame(frame, direction)


NOISY_FRAMES = (
    InputAudioRawFrame,
    OutputAudioRawFrame,
    UserSpeakingFrame,
    BotSpeakingFrame,
)


class FrameLogger(FrameProcessor):
    """Logs every frame passing except noisy ones"""

    def __init__(self, label: str):
        super().__init__()
        self._label = label

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if not isinstance(frame, NOISY_FRAMES):
            logger.debug("{} {} {}", self._label, direction.name, frame)

        await self.push_frame(frame, direction)
