# FastRTC-Compact

**A lean, Gradio-free fork of [FastRTC](https://github.com/gradio-app/fastrtc).**

<div style="display: flex; flex-direction: row; justify-content: center">
<a href="https://github.com/abdurrafay0610/FastRTC-Compact" target="_blank"><img alt="GitHub" src="https://img.shields.io/badge/github-FastRTC--Compact-white?logo=github&logoColor=black"></a>
</div>

Turn any Python function into a real-time audio and video stream over WebRTC or WebSockets — without the Gradio, librosa and their dependencies baggage of upstream.

> **This is a fork.** It tracks FastRTC `v0.0.34` and strips everything not needed for a
> production, bring-your-own-frontend deployment. The public `Stream` API and the `fastrtc`
> import path are unchanged, so code that mounts a stream on FastAPI works as-is.

---

## What's different from upstream

**Removed / out of scope**

- **Gradio** — the entire auto-UI (`.ui.launch()`), the Gradio `WebRTC` component, and the bundled Svelte / compiled frontend assets.
- **librosa + numba + llvmlite** — replaced by [`soxr`](https://pypi.org/project/soxr/) for audio resampling. Same resampler quality (`soxr_hq`), roughly **400 MB lighter**, and no one-time JIT compilation stall on the first call.
- **`fastphone()`** — the free temporary phone number (HF token + Gradio tunneling) has been removed.
- **HuggingFace Spaces tooling** — `upload_space.py` and related helpers.

**Kept**

- WebRTC and WebSocket endpoints via `.mount(app)`.
- Voice Activity Detection and turn-taking (`ReplyOnPause`, optional `vad` extra).
- Optional TTS / STT / stop-word extras.

The result is a much smaller dependency tree and image footprint, suitable for packaging as a plain FastAPI / WebRTC library.

---

## Installation

This fork is distributed from git (it is **not** published to PyPI under this name):

```bash
pip install "git+https://github.com/abdurrafay0610/FastRTC-Compact.git"
```

To use built-in pause detection (see [ReplyOnPause](https://fastrtc.org/userguide/audio/#reply-on-pause)) and text to speech (see [Text To Speech](https://fastrtc.org/userguide/audio/#text-to-speech)), add the `vad` and `tts` extras:

```bash
pip install "fastrtc-compact[vad,tts] @ git+https://github.com/abdurrafay0610/FastRTC-Compact.git"
```

Other optional extras: `stt`, `stopword`.

> **Naming:** the distribution is `fastrtc-compact`, but the import path is unchanged —
> `from fastrtc import Stream, ReplyOnPause`. It is a drop-in replacement for code already
> written against FastRTC.

---

## Key Features

- 🗣️ **Automatic voice detection & turn-taking** — only worry about the logic for responding to the user; `ReplyOnPause` handles detecting when they've finished speaking.
- 🔌 **WebRTC support** — `.mount(app)` adds a `/webrtc/offer` endpoint to a FastAPI app for your own frontend.
- ⚡️ **WebSocket support** — the same `.mount(app)` adds a `/websocket/offer` endpoint.
- 🤖 **Fully customizable backend** — a `Stream` mounts onto any FastAPI app, so you can extend it to fit your production system.

---

## Quickstart

### Echo Audio

```python
from fastrtc import Stream, ReplyOnPause
import numpy as np

def echo(audio: tuple[int, np.ndarray]):
    # The function is passed the audio until the user pauses.
    # Implement any iterator that yields audio.
    yield audio

stream = Stream(
    handler=ReplyOnPause(echo),
    modality="audio",
    mode="send-receive",
)
```

### LLM Voice Chat

```python
from fastrtc import (
    ReplyOnPause, Stream,
    audio_to_bytes, aggregate_bytes_to_16bit,
)
import numpy as np
from groq import Groq
import anthropic
from elevenlabs import ElevenLabs

groq_client = Groq()
claude_client = anthropic.Anthropic()
tts_client = ElevenLabs()


def response(audio: tuple[int, np.ndarray]):
    prompt = groq_client.audio.transcriptions.create(
        file=("audio-file.mp3", audio_to_bytes(audio)),
        model="whisper-large-v3-turbo",
        response_format="verbose_json",
    ).text
    reply = claude_client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    response_text = " ".join(
        block.text
        for block in reply.content
        if getattr(block, "type", None) == "text"
    )
    iterator = tts_client.text_to_speech.convert_as_stream(
        text=response_text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
        output_format="pcm_24000",
    )
    for chunk in aggregate_bytes_to_16bit(iterator):
        audio_array = np.frombuffer(chunk, dtype=np.int16).reshape(1, -1)
        yield (24000, audio_array)

stream = Stream(
    modality="audio",
    mode="send-receive",
    handler=ReplyOnPause(response),
)
```

### Webcam Stream

```python
from fastrtc import Stream
import numpy as np


def flip_vertically(image):
    return np.flip(image, axis=0)


stream = Stream(
    handler=flip_vertically,
    modality="video",
    mode="send-receive",
)
```

---

## Running the Stream

Mount the stream on a FastAPI app and serve your own frontend:

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastrtc import Stream, ReplyOnPause

app = FastAPI()
stream = Stream(handler=ReplyOnPause(...), modality="audio", mode="send-receive")
stream.mount(app)

# Optional: serve your frontend
@app.get("/")
async def index():
    return HTMLResponse(content=open("index.html").read())

# uvicorn app:app --host 0.0.0.0 --port 8000
```

`mount()` registers the following routes (prefixed with the optional `path` argument):

| Endpoint              | Protocol   | Purpose                          |
| :-------------------- | :--------- | :------------------------------- |
| `/webrtc/offer`       | HTTP POST  | WebRTC SDP / ICE exchange        |
| `/websocket/offer`    | WebSocket  | WebSocket streaming              |
| `/telephone/incoming` | HTTP POST  | Twilio inbound call webhook \*   |
| `/telephone/handler`  | WebSocket  | Twilio media-stream handler \*   |

> \* **Telephone (Twilio):** dial-in routes are still mounted, so you can point your own
> Twilio number at `/telephone/incoming`. The zero-config `fastphone()` temporary number is
> gone. _(Pending decision: keep these routes for phone dial-in, or strip them for a
> browser-only deployment.)_

---

## Examples

For end-to-end demos (Gemini / OpenAI / Claude voice chat, Whisper transcription, object
detection, and more), see the [upstream FastRTC cookbook](https://fastrtc.org/cookbook/).
Those demos are built against the original library and its Gradio UI; adapt the handler
logic to a `.mount(app)` deployment when porting them to this fork.

---

## Credits

Forked from [FastRTC](https://github.com/gradio-app/fastrtc) by the Gradio team. MIT licensed.