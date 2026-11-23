from loguru import logger
from pipecat.frames.frames import Frame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi.frames import RTVIClientMessageFrame

from scene import Scene

NOTE_PROTOCOL = (
    "The user is watching a video while talking to you. Messages that start with "
    "'Scene note' describe what is on screen; the user did not say them. Each note "
    "names an action. cue: in one short sentence, tell the user what is about to "
    "happen and to stay with it. ask: ask one short question about what just "
    "happened. note: say nothing about it; it is background for later."
)


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
            self._on_video_time(frame.data["time"], frame.data["playing"])

        await self.push_frame(frame, direction)

    def _on_video_time(self, time: float, playing: bool) -> None:
        if playing != self._playing:
            logger.info("{:6.1f}s video {}", time, "playing" if playing else "paused")
            self._playing = playing

        events = self._scene.active_events(time)
        now_active = {event.id for event in events}

        for event_id in sorted(self._active - now_active):
            logger.info("{:6.1}s end {}", time, event_id)
        for event in events:
            if event.id not in self._active:
                tags = ", ".join(event.tags)
                logger.info(
                    "{:6.1f}s start {} [{}] {}", time, event.id, tags, event.text
                )
        self._active = now_active
