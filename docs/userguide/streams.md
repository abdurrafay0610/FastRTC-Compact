# Core Concepts


The core of FastRTC is the `Stream` object. It can be used to stream audio, video, or both.

Here's a simple example of creating a video stream that flips the video vertically. We'll use it to explain the core concepts of the `Stream` object. Click on the plus icons to get a link to the relevant section.

```python
from fastrtc import Stream
import numpy as np

def detection(image):
    return np.flip(image, axis=0)

stream = Stream(
    handler=detection, # (1)
    modality="video", # (2)
    mode="send-receive", # (3)
)
```

1. See [Handlers](#handlers) for more information.
2. See [Modalities](#modalities) for more information.
3. See [Stream Modes](#stream-modes) for more information.

Run:

```py
from fastapi import FastAPI

app = FastAPI()
stream.mount(app)

# uvicorn app:app --host 0.0.0.0 --port 8000
```

### Stream Modes

FastRTC supports three streaming modes:

- `send-receive`: Bidirectional streaming (default)
- `send`: Client-to-server only 
- `receive`: Server-to-client only

### Modalities

FastRTC supports three modalities:

- `video`: Video streaming
- `audio`: Audio streaming  
- `audio-video`: Combined audio and video streaming

### Handlers

The `handler` argument is the main argument of the `Stream` object. A handler should be a function or a class that inherits from `StreamHandler` or `AsyncStreamHandler` depending on the modality and mode.


| Modality | send-receive | send | receive |
|----------|--------------|------|----------|
| video | Function that takes a video frame and returns a new video frame | Function that takes a video frame and returns a new frame | Function that takes a video frame and returns a new frame |
| audio | `StreamHandler` or `AsyncStreamHandler` subclass | `StreamHandler` or `AsyncStreamHandler` subclass | Generator yielding audio frames |
| audio-video | `AudioVideoStreamHandler` or `AsyncAudioVideoStreamHandler` subclass | Not Supported Yet | Not Supported Yet |


## Methods

The primary method of the `Stream` is `.mount(app)`:

- `.mount(app)`: Mount the stream on a [FastAPI](https://fastapi.tiangolo.com/) app. Perfect for integrating with your already existing production system or for building a custom UI. It adds the WebRTC (`/webrtc/offer`), WebSocket (`/websocket/offer`), and Twilio telephone (`/telephone/incoming`, `/telephone/handler`) endpoints.

!!! warning
    Websocket docs are only available for audio streams. Telephone docs are only available for audio streams in `send-receive` mode.

## Additional Inputs

You can pass additional input data to your handler at runtime. For `ReplyOnPause` and `ReplyOnStopWords`, this data is automatically passed to your generator as extra arguments; for `StreamHandler`s, you request it explicitly.

!!! tip
    For audio `StreamHandlers`, please read the special [note](../audio#requesting-inputs) on requesting inputs.

### Input Hooks

You update the inputs by using the `set_input` method of the `Stream` object. A common pattern is to use a `POST` request to send the updated data.

```python
from pydantic import BaseModel, Field
from fastapi import FastAPI

class InputData(BaseModel):
    webrtc_id: str
    conf_threshold: float = Field(ge=0, le=1)

app = FastAPI()
stream.mount(app)

@app.post("/input_hook")
async def _(data: InputData):
    stream.set_input(data.webrtc_id, data.conf_threshold)
```

The updated data will be passed to the handler on the **next** call.


## Additional Outputs

You can return additional output from the handler by returning an instance of `AdditionalOutputs`. Let's modify our previous example to also return the number of detections in the frame.

```python
from fastrtc import Stream, AdditionalOutputs

def detection(image, conf_threshold=0.3):
    processed_frame, n_objects = process_frame(image, conf_threshold)
    return processed_frame, AdditionalOutputs(n_objects)

stream = Stream(
    handler=detection,
    modality="video",
    mode="send-receive",
)
```

The handler returns the processed frame along with `AdditionalOutputs(n_objects)`. (`conf_threshold` defaults to `0.3` and can be updated at runtime via the [input hook](#input-hooks) above.)

!!! tip
    Since the webRTC is very low latency, you probably don't want to return an additional output on each frame. 

### Output Hooks

You access the output data by calling the `output_stream` method of the `Stream` object. A common pattern is to use a `GET` request to get a stream of the output data.

```python
from fastapi.responses import StreamingResponse

@app.get("/updates")
async def stream_updates(webrtc_id: str):
    async def output_stream():
        async for output in stream.output_stream(webrtc_id):
            # Output is the AdditionalOutputs instance
            # Be sure to serialize it however you would like
            yield f"data: {output.args[0]}\n\n"

    return StreamingResponse(
        output_stream(), 
        media_type="text/event-stream"
    )
```

## Custom Routes and Frontend Integration

You can add custom routes for serving your own frontend or handling additional functionality once you have mounted the stream on a FastAPI app.

```python
from fastapi.responses import HTMLResponse
from fastapi import FastAPI
from fastrtc import Stream

stream = Stream(...)

app = FastAPI()
stream.mount(app)

# Serve a custom frontend
@app.get("/")
async def serve_frontend():
    return HTMLResponse(content=open("index.html").read())

```

## Telephone Integration

You can connect a `Stream` to a SIP provider like Twilio to give your application a real phone number. Mounting the stream with `stream.mount(app)` exposes the `/telephone/incoming` webhook and the `/telephone/handler` WebSocket that Twilio connects to.

See the [Telephone Integration](../audio#telephone-integration) section of the audio guide for the full Twilio setup, including configuring the webhook and handling inbound and outbound calls.

## Concurrency

1. You can limit the number of concurrent connections by setting the `concurrency_limit` argument.
2. You can limit the amount of time (in seconds) a connection can stay open by setting the `time_limit` argument.

```python
stream = Stream(
    handler=handler,
    concurrency_limit=10,
    time_limit=3600
)
```