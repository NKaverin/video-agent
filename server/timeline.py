from time import monotonic

from loguru import logger
from pipecat.frames.frames import Frame, LLMMessagesAppendFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi.frames import RTVIClientMessageFrame

from policy import SPEAKING_ACTIONS, action_for
from scene import Event, Scene

NOTE_PROTOCOL = (
    "The user is watching a video while talking to you. Messages that start with "
    "'Scene note' describe what is on screen; the user did not say them. Each note "
    "names an action. cue: in one short sentence, tell the user what is about to "
    "happen and to stay with it. ask: ask one short question about what just "
    "happened. note: say nothing about it; it is background for later."
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
        self._last_spoken = float("-inf")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, RTVIClientMessageFrame) and frame.type == "video-time":
            await self._on_video_time(frame.data["time"], frame.data["playing"])

        await self.push_frame(frame, direction)

    def _timed_action(self, event: Event, action: str, time: float) -> str:
        """The policy's action would be a note if would come too late"""
        if action not in SPEAKING_ACTIONS:
            return action
        if time - event.start > LATE_SECS:
            logger.info(
                "{:6.1f}s {} joined late, note instead of {}", time, event.id, action
            )
            return "note"
        now = monotonic()
        if now - self._last_spoken < COLDOWN_SECS:
            logger.info(
                "{:6.1f}s {} in cooldown, note instead of {}", time, event.id, action
            )
            return "note"
        self._last_spoken = now
        return action

    async def _add_note(self, event: Event, action: str) -> None:
        note = "Scene note (" + action + "): " + event.text
        await self.push_frame(
            LLMMessagesAppendFrame(
                messages=[{"role": "developer", "content": note}],
                run_llm=action in SPEAKING_ACTIONS,
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
                tags = ", ".join(event.tags)
                action = self._timed_action(event, action_for(event), time)
                logger.info(
                    "{:6.1f}s start {} [{}] {}: {}",
                    time,
                    event.id,
                    tags,
                    action,
                    event.text,
                )
                await self._add_note(event, action)
        self._active = now_active
