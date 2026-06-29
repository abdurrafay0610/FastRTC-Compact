# Changelog — fastrtc-compact

`fastrtc-compact` is a branch of [FastRTC](https://github.com/gradio-app/fastrtc) with the
**Gradio dependency removed**. Upstream FastRTC ships a built-in Gradio UI and a Gradio
custom component layered on top of a FastAPI + `aiortc` connection core. This branch keeps
that core — the `Stream.mount()` API surface that a custom frontend talks to — and removes
everything that existed only to serve the Gradio UI, to make the library smaller and
dependency-light.

Forked at FastRTC **v0.0.34**.

---

## [Unreleased]

### Removed — Gradio (entire runtime/import dependency)

The importable package no longer requires or imports Gradio.

- **`pyproject.toml`** — dropped `gradio>=4.0,<6.0` from `dependencies`; removed the
  `gradio-custom-component` keyword. Installing/importing `fastrtc` no longer pulls Gradio.
- **`backend/fastrtc/utils.py`** — `WebRTCData` and `WebRTCModel` now subclass Pydantic
  `BaseModel` / `RootModel` instead of Gradio's `GradioModel` / `GradioRootModel`. Those
  Gradio classes were thin Pydantic wrappers, so behavior is unchanged. This was the only
  Gradio import reachable from the non-UI connection core, so the swap de-Gradios `utils.py`,
  `tracks.py`, and `webrtc_connection_mixin.py` in one move.
- **`backend/fastrtc/__init__.py`** — removed `from .webrtc import WebRTC`; removed `WebRTC`
  and `UIArgs` from `__all__`. This is the cut that stops Gradio being imported transitively
  via `from fastrtc import Stream`. (`WebRTCData` is still exported, now from the
  Pydantic-based `utils`.)
- **`backend/fastrtc/webrtc.py`** — **deleted.** This file was the entire Gradio custom
  component: `class WebRTC(Component, WebRTCConnectionMixin)`, the `@server`-decorated
  `turn` / `offer` / `quit_output_stream`, the `Component` interface methods (`preprocess` /
  `postprocess` / `api_info` / `example_payload` / `example_value`), and all event wiring
  (`stream` / `tick` / `submit` / `change` / `on_additional_outputs`). The real offer handling
  lives in `webrtc_connection_mixin.handle_offer`, so none of it was needed by `mount()`.
- **`frontend/`** — **deleted.** The Svelte custom-component source tree (package name
  `gradio_webrtc`, built on `@gradio/*` packages) that produced the Gradio UI's frontend.
- **`backend/fastrtc/templates/`** — **deleted.** The compiled Gradio component frontend
  (bundled JS/CSS) that the build force-included into the wheel.
- **`upload_space.py`** — **deleted.** The Hugging Face Spaces deploy script, built on the
  Gradio SDK.
- **`backend/fastrtc/stream.py`** — removed `import gradio as gr`, `from gradio import Blocks`,
  `from gradio.components.base import Component`, and the `WebRTC` import. Deleted all Gradio
  UI / launch machinery:
  - `_generate_default_ui` (the `gr.Blocks` auto-UI builder)
  - the `ui` property/setter and the `_ui` attribute
  - `_wrap_gradio_launch` (wrapped `gradio.Blocks.launch`)
  - `_check_colab_or_spaces` and `_print_error` (the Colab/Spaces environment guard; used
    `gradio.utils.colab_check` / `get_space`)
  - the UI title helpers `_is_html_string` / `_format_title` / `_format_subtitle`
  - the `UIArgs` TypedDict (and the now-unused `TypedDict` / `NotRequired` imports)
  - the `concurrency_limit_gradio` attribute and the `curr_dir` module global
  - updated the `Stream` class and `__init__` docstrings to drop Gradio/UI references and the
    stale "Required when deploying on Colab or Spaces" note.

### Removed — `fastphone()`

- **`Stream.fastphone()`** removed. It created a public tunnel using Gradio's bundled tunnel
  binary to obtain a free temporary Hugging Face phone number — a Gradio-coupled convenience
  not used by a production deployment.
- **This does not remove telephone support in general.** The Twilio webhook path
  (`/telephone/incoming` → `handle_incoming_call`, `/telephone/handler` → `telephone_handler`)
  is pure FastAPI and remains in place; `fastphone()` only used it under the hood. Pointing
  your own Twilio number at the stream still works.

### Changed

- **`Stream._inject_startup_message`** — dropped the `self._check_colab_or_spaces()` call from
  its startup hook (the only thing that made it Gradio-dependent). It now only prints the
  API-docs startup message. A breadcrumb comment marks where the check used to be, so the
  Gradio dependency isn't reflexively reintroduced.

### Preserved (explicitly unaffected)

- **Connection core** — `backend/fastrtc/tracks.py` and
  `backend/fastrtc/webrtc_connection_mixin.py` were already Gradio-free and are untouched.
- **Production API surface** — `Stream.mount(app)` is intact: `/webrtc/offer`,
  `/websocket/offer`, and (currently) the Twilio telephone routes. The WebRTC offer/answer
  path runs entirely through the FastAPI + `aiortc` core.
- **Exports** — all non-UI public symbols remain (`Stream`, `ReplyOnPause`, `ReplyOnStopWords`,
  the stream handlers, TURN credential helpers, TTS/STT/VAD utilities, `AdditionalOutputs`,
  `WebRTCData`, etc.).

---

## Outstanding / not yet addressed

The **runtime/import path is Gradio-free**, but the following still reference Gradio or are
leftover and are not yet done:

- **Documentation is stale (planned for a later pass).** Still references Gradio throughout
  and does not reflect this branch: `docs/userguide/gradio.md` (entire page),
  `docs/userguide/streams.md`, `docs/reference/stream.md` (still documents `additional_inputs` /
  `additional_outputs` / `ui_args` / the `.ui` property), `docs/faq.md`, `docs/deployment.md`,
  `docs/index.md`, and `README.md` (the `.ui.launch()` feature bullet and Gradio badges).
- **`pyproject.toml` `[tool.hatch.build]` `artifacts`** lists build force-include patterns that
  now point at deleted files: `/backend/fastrtc/templates` (folder deleted) and an absolute
  `/Users/freddyboulton/.../site-packages/fastrtc/templates` path (the original author's local
  venv — only ever matched on their machine). Also `*.pyi` (Gradio's `cc build` generated a
  component stub; verify none remain). These are dead references — remove them, and if the list
  empties, drop the `artifacts` key and the now-empty `[tool.hatch.build]` table.
  `[tool.hatch.build.targets.wheel]` is separate and stays. Build-time only; no effect on
  `import fastrtc`.
- **`Stream.additional_outputs_handler`** (constructor parameter + assignment) is now
  orphaned — its only consumer was the deleted UI's `on_additional_outputs`. In a mount-only
  setup, outputs are read via `output_stream()` / `fetch_latest_output()`. Candidate for
  removal (signature change — verify `websocket.py` doesn't read it first).

### Open decision (not Gradio-related)

- **Twilio telephone routes** — keep them (phone dial-in interviews) or remove them for
  browser-only operation? Removing `handle_incoming_call` / `telephone_handler` would also let
  us drop the `twilio` dependency and the `Request` / `HTMLResponse` imports from `stream.py`,
  and the two telephone route registrations from `mount()`. `websocket_offer` stays either way
  (that's the browser WebSocket signaling path, not telephone).

---

## Verifying the Gradio removal

In an environment **without** Gradio installed, both of these should succeed:

```bash
python -c "import fastrtc; from fastrtc import Stream; print('ok')"
pytest test/test_webrtc_connection_mixin.py
```

The test's `MinimalTestStream` already bypasses Gradio, so it's a good baseline; the pass
condition is simply that the import and the connection-mixin tests run with Gradio absent.