# Video Streaming

## Input/Output Streaming

We already saw this example in the [Quickstart](../../#quickstart) and the [Core Concepts](../streams) section.

=== "Code"
    
    ``` py title="Input/Output Streaming"
    from fastrtc import Stream

    def detection(image, conf_threshold=0.3): # (1)
        processed_frame = process_frame(image, conf_threshold)
        return processed_frame # (2)

    stream = Stream(
        handler=detection,
        modality="video",
        mode="send-receive", # (3)
    )
    ```

    1. The webcam frame will be represented as a numpy array of shape (height, width, RGB).
    2. The function must return a numpy array. Additional arguments (like `conf_threshold`) can be supplied at runtime via the [input hook](../streams#input-hooks).
    3. Set the `modality="video"` and `mode="send-receive"`
=== "Notes"
    1. The webcam frame will be represented as a numpy array of shape (height, width, RGB).
    2. The function must return a numpy array. Additional arguments (like `conf_threshold`) can be supplied at runtime via the [input hook](../streams#input-hooks).
    3. Set the `modality="video"` and `mode="send-receive"`

## Server-to-Client Only

In this case, we stream from the server to the client so we will write a generator function that yields the next frame from the video (as a numpy array)
and set the `mode="receive"` in the `Stream`.

=== "Code"
    ``` py title="Server-To-Client"
    from fastrtc import Stream
    import cv2

    def generation():
        url = "https://download.tsi.telecom-paristech.fr/gpac/dataset/dash/uhd/mux_sources/hevcds_720p30_2M.mp4"
        cap = cv2.VideoCapture(url)
        iterating = True
        while iterating:
            iterating, frame = cap.read()
            yield frame

    stream = Stream(
        handler=generation,
        modality="video",
        mode="receive"
    )
    ```

## Skipping Frames

If your event handler is not quite real-time yet, then the output feed will look very laggy.

To fix this, you can set the `skip_frames` parameter to `True`. This will skip the frames that are received while the event handler is still running.

``` py title="Skipping Frames"
import time

import numpy as np
from fastrtc import Stream, VideoStreamHandler


def process_image(image):
    time.sleep(
        0.2
    )  # Simulating 200ms processing time per frame; input arrives faster (30 FPS).
    return np.flip(image, axis=0)


stream = Stream(
    handler=VideoStreamHandler(process_image, skip_frames=True),
    modality="video",
    mode="send-receive",
)
```

## Setting the Output Frame Rate

You can set the output frame rate by setting the `fps` parameter in the `VideoStreamHandler`.

``` py title="Setting the Output Frame Rate"
import time

import cv2
from fastrtc import Stream, VideoStreamHandler, AdditionalOutputs


def generation():
    url = "https://github.com/user-attachments/assets/9636dc97-4fee-46bb-abb8-b92e69c08c71"
    cap = cv2.VideoCapture(url)
    iterating = True

    # FPS calculation variables
    frame_count = 0
    start_time = time.time()
    fps = 0

    while iterating:
        iterating, frame = cap.read()

        # Calculate and print FPS
        frame_count += 1
        elapsed_time = time.time() - start_time
        if elapsed_time >= 1.0:  # Update FPS every second
            fps = frame_count / elapsed_time
            yield frame, AdditionalOutputs(fps)
            frame_count = 0
            start_time = time.time()
        else:
            yield frame


stream = Stream(
    handler=VideoStreamHandler(generation, fps=60),
    modality="video",
    mode="receive",
)
```

The FPS value yielded via `AdditionalOutputs` can be read on the client through the [output hook](../streams#output-hooks).