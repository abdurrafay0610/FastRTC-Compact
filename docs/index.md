<div style='text-align: center; margin-bottom: 1rem; display: flex; justify-content: center; align-items: center;'>
    <img src="fastrtc_logo.png"
         alt="FastRTC-Compact Logo"
         style="height: 40px; margin-right: 10px;">
    <h1 style='margin: 0;'>FastRTC-Compact</h1>
</div>

<div style="display: flex; flex-direction: row; justify-content: center; gap: 5px;">
<a href="https://github.com/abdurrafay0610/FastRTC-Compact" target="_blank"><img alt="GitHub" src="https://img.shields.io/badge/github-FastRTC--Compact-white?logo=github&logoColor=black"></a>
<img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</div>

<h3 style='text-align: center'>
The lightweight real-time communication library for Python.
</h3>

Turn any Python function into a real-time audio or video stream over WebRTC or WebSockets — without the heavyweight dependencies.

FastRTC-Compact is a fork of [FastRTC](https://github.com/gradio-app/fastrtc) (v0.0.34) built for production deployments that serve their own frontend. It removes Gradio (~312 MB) and the librosa/numba resampling stack (~400 MB, replaced with [soxr](https://github.com/dofuuz/python-soxr)), cutting the installed footprint from roughly **1.05 GB to ~345 MB** while keeping the full WebRTC/WebSocket core, voice activity detection, turn-taking logic, and Twilio dial-in support.

It is a **drop-in replacement**: the import name is still `fastrtc`, so existing code works unchanged.

## Installation

FastRTC-Compact is not on PyPI yet — install directly from GitHub:

```bash
pip install "fastrtc-compact @ git+https://github.com/abdurrafay0610/FastRTC-Compact.git"
```

To use built-in pause detection (see [ReplyOnPause](userguide/audio/#reply-on-pause)), speech-to-text (see [Speech To Text](userguide/audio/#speech-to-text)), and text-to-speech (see [Text To Speech](userguide/audio/#text-to-speech)), install the `vad`, `stt`, and `tts` extras:

```bash
pip install "fastrtc-compact[vad, stt, tts] @ git+https://github.com/abdurrafay0610/FastRTC-Compact.git"
```

!!! warning "One fastrtc per environment"
    Do not install `fastrtc-compact` and the upstream `fastrtc` package in the same
    environment — both provide the `fastrtc` import and will clash.

## Quickstart

Import the [Stream](userguide/streams) class, pass in a [handler](userguide/streams/#handlers), and mount it on a [FastAPI](https://fastapi.tiangolo.com/) app with `.mount(app)` — perfect for integrating with your existing production system and serving your own frontend.

=== "Echo Audio"

    ```python
    from fastrtc import Stream, ReplyOnPause
    import numpy as np

    def echo(audio: tuple[int, np.ndarray]):
        # The function will be passed the audio until the user pauses
        # Implement any iterator that yields audio
        # See "LLM Voice Chat" for a more complete example
        yield audio

    stream = Stream(
        handler=ReplyOnPause(echo),
        modality="audio",
        mode="send-receive",
    )
    ```

=== "LLM Voice Chat"

    ```py
    import os

    from fastrtc import (ReplyOnPause, Stream, get_stt_model, get_tts_model)
    from openai import OpenAI

    sambanova_client = OpenAI(
        api_key=os.getenv("SAMBANOVA_API_KEY"), base_url="https://api.sambanova.ai/v1"
    )
    stt_model = get_stt_model()
    tts_model = get_tts_model()

    def echo(audio):
        prompt = stt_model.stt(audio)
        response = sambanova_client.chat.completions.create(
            model="Meta-Llama-3.2-3B-Instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        prompt = response.choices[0].message.content
        for audio_chunk in tts_model.stream_tts_sync(prompt):
            yield audio_chunk

    stream = Stream(ReplyOnPause(echo), modality="audio", mode="send-receive")
    ```

=== "Webcam Stream"

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

Run it by mounting the stream on a FastAPI app:

```py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()
stream.mount(app)

# Optional: serve your own frontend
@app.get("/")
async def _():
    return HTMLResponse(content=open("index.html").read())

# uvicorn app:app --host 0.0.0.0 --port 8000
```

`mount()` registers `/webrtc/offer` (WebRTC signaling), `/websocket/offer` (WebSocket streaming), and the Twilio dial-in routes `/telephone/incoming` and `/telephone/handler` — point your own Twilio number at the stream for phone support.

Learn more about the [Stream](userguide/streams) in the user guide.

## Key Features

:material-feather:{ .lg } **Lightweight** — ~345 MB installed vs ~1.05 GB for upstream FastRTC. No Gradio, no librosa/numba; audio resampling handled by soxr.

:material-swap-horizontal:{ .lg } **Drop-in replacement** — imports as `fastrtc`, so switching requires no code changes.

:speaking_head:{ .lg } **Automatic Voice Detection and Turn Taking** built-in — only worry about the logic for responding to the user.

:material-lightning-bolt:{ .lg } **WebRTC Support** — `.mount(app)` adds a WebRTC endpoint to a FastAPI app for your own frontend.

:simple-webstorm:{ .lg } **WebSocket Support** — the same `.mount(app)` adds a WebSocket endpoint.

:telephone:{ .lg } **Telephone Support** — Twilio dial-in routes are mounted automatically; connect your own Twilio number.

:robot:{ .lg } **Completely customizable backend** — a `Stream` mounts on any FastAPI app, so you can extend it to fit your production application.

## Roadmap

- Optional `huggingface_hub` dependency with the Silero VAD model vendored as package data
- Streaming STT, TTS, and LLM support
- [Pipecat smart_turn](https://github.com/pipecat-ai/smart-turn) integration for smarter pause detection

## Examples

See the [cookbook](cookbook.md).

## Credits

FastRTC-Compact is based on [FastRTC](https://github.com/gradio-app/fastrtc) by Freddy Boulton. MIT licensed; original copyright preserved.