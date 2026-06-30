# Utils

## `audio_to_bytes`

Convert an audio tuple containing sample rate and numpy array data into bytes (MP3-encoded).
Useful for sending data to external APIs from a `ReplyOnPause` handler.

Parameters
```
audio : tuple[int, np.ndarray]
    A tuple containing:
        - sample_rate (int): The audio sample rate in Hz
        - data (np.ndarray): The audio data as a numpy array
```

Returns
```
bytes
    The audio data encoded as MP3 bytes, suitable for transmission or storage
```

Example
```python
>>> sample_rate = 44100
>>> audio_data = np.array([0.1, -0.2, 0.3])  # Example audio samples
>>> audio_tuple = (sample_rate, audio_data)
>>> audio_bytes = audio_to_bytes(audio_tuple)
```

## `audio_to_file`

Save an audio tuple containing sample rate and numpy array data to a temporary `.mp3` file.

Parameters
```
audio : tuple[int, np.ndarray]
    A tuple containing:
        - sample_rate (int): The audio sample rate in Hz
        - data (np.ndarray): The audio data as a numpy array
```
Returns
```
str
    The path to the saved audio file
```
Example
```python
>>> sample_rate = 44100
>>> audio_data = np.array([0.1, -0.2, 0.3])  # Example audio samples
>>> audio_tuple = (sample_rate, audio_data)
>>> file_path = audio_to_file(audio_tuple)
>>> print(f"Audio saved to: {file_path}")
```

## `audio_to_float32`

Convert audio numpy array data to `float32`. `int16` input is scaled to the range `[-1.0, 1.0)`; `float32` input is returned unchanged.

Parameters
```
audio : np.ndarray
    The audio data as a numpy array (dtype int16 or float32).
    (Passing a (sample_rate, data) tuple is deprecated and will be removed
    in a future release — pass only the audio array.)
```
Returns
```
np.ndarray
    The audio data as a numpy array with dtype float32
```
Raises
```
TypeError
    If the array dtype is neither int16 nor float32.
```
Example
```python
>>> audio_data = np.array([0, 16384, -16384], dtype=np.int16)
>>> audio_float32 = audio_to_float32(audio_data)
```

## `audio_to_int16`

Convert audio numpy array data to `int16`. `float32` input is scaled to the `int16` range; `int16` input is returned unchanged.

Parameters
```
audio : np.ndarray
    The audio data as a numpy array (dtype int16 or float32).
    (Passing a (sample_rate, data) tuple is deprecated and will be removed
    in a future release — pass only the audio array.)
```
Returns
```
np.ndarray
    The audio data as a numpy array with dtype int16
```
Raises
```
TypeError
    If the array dtype is neither int16 nor float32.
```
Example
```python
>>> audio_data = np.array([0.1, -0.2, 0.3], dtype=np.float32)
>>> audio_int16 = audio_to_int16(audio_data)
```

## `aggregate_bytes_to_16bit`
Aggregate bytes to 16-bit audio samples.

This function takes an iterator of chunks and aggregates them into 16-bit audio samples.
It handles incomplete samples and combines them with the next chunk.

Parameters
```
chunks_iterator : Iterator[bytes]
    An iterator of byte chunks to aggregate
```
Returns
```
Iterator[NDArray[np.int16]]
    An iterator of 16-bit audio samples
```
Example
```python
>>> chunks_iterator = [b'\x00\x01', b'\x02\x03', b'\x04\x05']
>>> for chunk in aggregate_bytes_to_16bit(chunks_iterator):
>>>     print(chunk)
```

## `async_aggregate_bytes_to_16bit`

Aggregate bytes to 16-bit audio samples asynchronously. This is the `async` counterpart
to `aggregate_bytes_to_16bit`: it consumes an **async** iterator of byte chunks and yields
16-bit audio samples.

Parameters
```
chunks_iterator : AsyncIterator[bytes]
    An async iterator of byte chunks to aggregate
```
Returns
```
AsyncIterator[NDArray[np.int16]]
    An async iterator of 16-bit audio samples
```
Example
```python
>>> # async_chunks is an async iterator of byte chunks
>>> async for chunk in async_aggregate_bytes_to_16bit(async_chunks):
>>>     print(chunk)
```

## `wait_for_item`

Wait for an item from an `asyncio.Queue` with a timeout. If the timeout is reached, returns
`None` instead of blocking. This is useful to avoid blocking `emit` when the queue is empty.

Parameters
```
queue : asyncio.Queue
    The queue to wait for an item from
timeout : float, optional
    The timeout in seconds. Defaults to 0.1.
```
Returns
```
Any
    The item from the queue, or None if the timeout is reached
```

Example
```python
>>> queue = asyncio.Queue()
>>> queue.put_nowait(1)
>>> item = await wait_for_item(queue)
>>> print(item)
```

## `get_current_context`

Get the `Context` for the current stream connection. Useful from within a handler to access
the active connection's `webrtc_id` (and its `websocket`, when connected over WebSocket).

Returns
```
Context
    A dataclass containing:
        - webrtc_id (str): The unique ID of the current connection
        - websocket (WebSocket | None): The WebSocket, if connected over WebSocket
```
Raises
```
RuntimeError
    If called outside of an active stream context (no context is set).
```
Example
```python
>>> from fastrtc import get_current_context
>>> ctx = get_current_context()
>>> print(ctx.webrtc_id)
```