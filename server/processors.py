from loguru import logger
from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class TranscriptPrinter(FrameProcessor):
    """Logs each transcript and passes every frame on unchanged"""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            logger.info("User: {}", frame.text)

        await self.push_frame(frame, direction)
