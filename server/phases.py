from loguru import logger
from pipecat.frames.frames import FunctionCallResultProperties
from pipecat.processors.frameworks.rtvi.frames import RTVIServerMessageFrame
from pipecat.services.llm_service import FunctionCallParams

PHASES_PROTOCOL = (
    "A session has three parts. Briefing, before the video: in two or three "
    "sentences, tell the user what the video shows, without listing every "
    "moment. Ask what they expect and what worries them, one question at a "
    "time, and listen. Do not start the video yourself: when the user says "
    "they are ready, say one short sentence and call start_video. Watching: "
    "the video plays and you answer when the user speaks. Debrief, after the "
    "video ends: ask how it went compared with what they expected, one "
    "question at a time."
)


async def start_video(params: FunctionCallParams):
    """Start the video in the user's browser. Call only after the user says they are ready."""
    logger.info("starting the video")
    params.app_resources.adapt()

    await params.llm.push_frame(RTVIServerMessageFrame(data={"type": "play-video"}))
    await params.result_callback(
        {"started": True},
        properties=FunctionCallResultProperties(run_llm=False),
    )
