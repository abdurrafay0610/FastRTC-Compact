# `Stream` Class

```python
Stream(
    handler: HandlerType,
    *,
    additional_outputs_handler: Callable | None = None,
    mode: Literal["send-receive", "receive", "send"] = "send-receive",
    modality: Literal["video", "audio", "audio-video"] = "video",
    concurrency_limit: int | None | Literal["default"] = "default",
    time_limit: float | None = None,
    allow_extra_tracks: bool = False,
    rtp_params: dict[str, Any] | None = None,
    rtc_configuration: RTCConfigurationCallable | None = None,
    server_rtc_configuration: dict[str, Any] | None = None,
    track_constraints: dict[str, Any] | None = None,
    verbose: bool = True,
)
```

Define an audio, video, or audio-video stream, mountable on a FastAPI app.

This class encapsulates the logic for handling real-time communication (WebRTC) streams, including setting up peer connections, managing tracks, and integrating with FastAPI for HTTP and WebSocket API endpoints. It supports different modes (send, receive, send-receive) and modalities (audio, video, audio-video). It also provides built-in telephone integration via Twilio.

## Attributes

| Name                         | Type                                          | Description                                                              |
| :--------------------------- | :-------------------------------------------- | :----------------------------------------------------------------------- |
| `mode`                       | `Literal["send-receive", "receive", "send"]`  | The direction of the stream.                                             |
| `modality`                   | `Literal["video", "audio", "audio-video"]`    | The type of media stream.                                                |
| `rtp_params`                 | `dict[str, Any] \| None`                      | Parameters for RTP encoding.                                             |
| `event_handler`              | `HandlerType`                                 | The main function to process stream data.                                |
| `concurrency_limit`          | `int`                                         | The maximum number of concurrent connections allowed.                    |
| `time_limit`                 | `float \| None`                               | Time limit in seconds for the event handler execution.                   |
| `allow_extra_tracks`         | `bool`                                        | Whether to allow extra tracks beyond the specified modality.             |
| `additional_outputs_handler` | `Callable \| None`                            | An optional function to process the `AdditionalOutputs` emitted by the handler. |
| `track_constraints`          | `dict[str, Any] \| None`                      | Constraints for media tracks (e.g., resolution).                         |
| `rtc_configuration`          | `RTCConfigurationCallable \| None`            | Configuration for the client-side RTCPeerConnection (e.g., ICE servers). May be a dict or a sync/async callable that returns one. |
| `server_rtc_configuration`   | `dict[str, Any] \| None`                      | Configuration for the server-side RTCPeerConnection. Setting `iceServers` to an empty list means no ICE servers are used on the server. |
| `verbose`                    | `bool`                                        | Whether to print verbose logging on startup.                            |

## Methods

### `mount`

```python
mount(app: FastAPI, path: str = "", tags: list[str | Enum] | None = None)
```

Mount the stream's API endpoints onto a FastAPI application.

This method adds the necessary routes (`/webrtc/offer`, `/telephone/handler`, `/telephone/incoming`, `/websocket/offer`) to the provided FastAPI app, prefixed with the optional `path`. It also injects a startup message into the app's lifespan.

**Args:**

| Name   | Type                        | Description                                                                                      |
| :----- | :-------------------------- | :----------------------------------------------------------------------------------------------- |
| `app`  | `FastAPI`                   | The FastAPI application instance.                                                                |
| `path` | `str`                       | An optional URL prefix for the mounted routes.                                                   |
| `tags` | `list[str \| Enum] \| None` | Optional OpenAPI tags to organize the mounted endpoints in the API documentation. |

**Example:**

```python
from fastapi import FastAPI
from fastrtc import Stream

app = FastAPI(openapi_tags=[{
    "name": "fastrtc",
    "description": "Real-time communication endpoints"
}])

stream = Stream(handler=my_handler, mode="send-receive", modality="audio")
stream.mount(app, path="/api/v1/llm", tags=["fastrtc"])
```

---

### `offer`

```python
async offer(body: Body)
```

Handle an incoming WebRTC offer via HTTP POST.

Processes the SDP offer and ICE candidates from the client to establish a WebRTC connection.

**Args:**

| Name   | Type   | Description                                                                                             |
| :----- | :----- | :------------------------------------------------------------------------------------------------------ |
| `body` | `Body` | A Pydantic model containing the SDP offer, optional ICE candidate, type ('offer'), and a unique WebRTC ID. |

**Returns:**

*   A dictionary containing the SDP answer generated by the server.

---

### `handle_incoming_call`

```python
async handle_incoming_call(request: Request)
```

Handle incoming telephone calls (e.g., via Twilio).

Generates TwiML instructions to connect the incoming call to the WebSocket handler (`/telephone/handler`) for audio streaming.

**Args:**

| Name      | Type      | Description                                                  |
| :-------- | :-------- | :----------------------------------------------------------- |
| `request` | `Request` | The FastAPI Request object for the incoming call webhook. |

**Returns:**

*   An `HTMLResponse` containing the TwiML instructions as XML.

---

### `telephone_handler`

```python
async telephone_handler(websocket: WebSocket)
```

The websocket endpoint for streaming audio over Twilio phone.

**Args:**

| Name        | Type        | Description                             |
| :---------- | :---------- | :-------------------------------------- |
| `websocket` | `WebSocket` | The incoming WebSocket connection object. |

---

### `websocket_offer`

```python
async websocket_offer(websocket: WebSocket)
```

Handle WebRTC signaling over a WebSocket connection. Provides an alternative to the HTTP POST `/webrtc/offer` endpoint for exchanging SDP offers/answers and ICE candidates via WebSocket messages.

**Args:**

| Name        | Type        | Description                             |
| :---------- | :---------- | :-------------------------------------- |
| `websocket` | `WebSocket` | The incoming WebSocket connection object. |