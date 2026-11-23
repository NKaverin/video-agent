from loguru import logger
from pipecat.frames.frames import Frame, LLMMessagesAppendFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi.frames import RTVIClientMessageFrame

from scene import Event, Scene

SCENE_PROTOCOL = (
    "While the video plays, messages that start with 'On screen' describe what "
    "the user sees at that moment; the user did not say them. Use them to "
    "understand what the user talks about. Do not comment on them unprompted."
)

LATE_SECS = 2.0
COLDOWN_SECS = 10.0


class SceneTimeline(FrameProcessor):
    """Follows the browser's video clock and reports scene events"""

    def __init__(self, scene: Scene):
        super().__init__()
        self._scene = scene
        self._playing = False
        self._active: set[str] = set()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, RTVIClientMessageFrame) and frame.type == "video-time":
            await self._on_video_time(frame.data["time"], frame.data["playing"])

        await self.push_frame(frame, direction)

    async def _observe(self, event: Event, time: float) -> None:
        tags = ", ".join(event.tags)
        logger.info("{:6.1f}s start {} [{}] {}", time, event.id, tags, event.text)
        observation = (
            "On screen at " + str(round(time)) + "s [" + tags + "]: " + event.text
        )
        # It is context only
        await self.push_frame(
            LLMMessagesAppendFrame(
                messages=[{"role": "developer", "content": observation}],
                run_llm=False,
            )
        )

    async def _on_video_time(self, time: float, playing: bool) -> None:
        if playing != self._playing:
            logger.info("{:6.1f}s video {}", time, "playing" if playing else "paused")
            self._playing = playing

        events = self._scene.active_events(time)
        now_active = {event.id for event in events}

        for event_id in sorted(self._active - now_active):
            logger.info("{:6.1f}s end   {}", time, event_id)
        for event in events:
            if event.id not in self._active:
                await self._observe(event, time)
        self._active = now_active
