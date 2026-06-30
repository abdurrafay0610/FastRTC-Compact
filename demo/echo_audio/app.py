"""
Minimal echo test harness for fastrtc-compact.

Exercises the real path: getUserMedia -> /webrtc/offer -> aiortc -> ReplyOnPause
VAD -> emit loop -> track teardown. Uses ReplyOnPause (not a raw handler) on
purpose, since your ReplyOnSoftHardPause inherits from it -- this is the closest
minimal stand-in for your production handler.

Run:
    pip install -e ".[vad]" uvicorn        # from your fork checkout
    uvicorn app:app --host 127.0.0.1 --port 8000
    # open http://localhost:8000
"""

import numpy as np
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from fastrtc import ReplyOnPause, Stream


def echo(audio: tuple[int, np.ndarray]):
    # Called with the speech segment captured before each pause.
    # Yield it straight back so you hear yourself after you stop talking.
    yield audio


stream = Stream(
    handler=ReplyOnPause(echo),
    modality="audio",
    mode="send-receive",
)

app = FastAPI()

# Adds /webrtc/offer, /websocket/offer, and (currently) the Twilio telephone
# routes. Browser-only echo test only touches /webrtc/offer.
stream.mount(app)


@app.get("/")
async def index():
    with open("index.html") as f:
        return HTMLResponse(f.read())