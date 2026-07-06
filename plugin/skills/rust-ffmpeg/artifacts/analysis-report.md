# skill-rust-ffmpeg Update & Review Report

**Date**: 2026-07-07
**Scope**: Version alignment to current releases, coverage of ez-ffmpeg 0.12 capabilities, and a Claude↔Codex cross-model review of the changes.

---

## Library versions (verified against source, not assumed)

| Library | Version | FFmpeg | Rust MSRV | Source of truth |
|---------|---------|--------|-----------|-----------------|
| ez-ffmpeg | 0.12.0 | 7.0–8.x | 1.80 | `Cargo.toml`, `README.md` |
| ffmpeg-next | 8.1.0 | 7.0–8.x | unspecified (no `rust-version`) | `Cargo.toml`, `build.rs` |
| ffmpeg-sys-next | 8.1.0 | 7.0–8.x | unspecified | `Cargo.toml`, `build.rs` |
| ffmpeg-sidecar | 2.5.2 | Any | 1.79 | `Cargo.toml` |

**FFmpeg 8**: rust-ffmpeg [#246](https://github.com/zmwangx/rust-ffmpeg/issues/246) (the FFmpeg 8 EXIF-side-data blocker) was fixed and shipped in 8.0/8.1. `ffmpeg-sys-next` 8.1.0 generates bindings from the installed FFmpeg headers (bindgen) and emits `ffmpeg_7_x`/`ffmpeg_8_x` cfgs, so the current crates build against **both** FFmpeg 7 and 8 — no crate-major-to-system-major matching is required. The prior "pin 7.1.0" guidance is obsolete.

---

## Capabilities added (ez-ffmpeg 0.11/0.12, previously undocumented)

All grounded in real `src/` + `examples/`; feature flags verified against `Cargo.toml`.

1. **Native subtitle burn-in** — `SubtitleFilter` (feature `subtitle`): pure-Rust ASS/SRT renderer inside the frame pipeline, no `--enable-libass`. → `scenarios/subtitles.md`, `ez_ffmpeg/filters.md`.
2. **GPU custom filters (wgpu)** — `WgpuFrameFilter` (feature `wgpu`): headless WGSL shaders, live params, per-stage stats. Replaces the OpenGL path (`#[deprecated(since=0.11.0)]`). Plus `get_gpu_filter_backends()` probing. → `ez_ffmpeg/filters.md`, `scenarios/hardware_acceleration.md`.
3. **Detection & measurement** — `analysis` module (no feature flag): `Analysis` one-shot + `MetadataEventFilter` streaming return typed black/silence/scene/crop/EBU-R128 results. → `scenarios/debugging.md`, `scenarios/audio_extraction.md`.
4. **One-shot recipes** — `recipes` module (no feature flag): `thumbnail`/`sprite_sheet`/`animated_gif`/`HlsLadder`. → `scenarios/image_sequences.md`, `gif_creation.md`, `streaming_rtmp_hls.md`.

Also documented: ffmpeg-next 8.x safe stream I/O (`StreamIo` + `input_from_stream`/`output_to_stream`), `Frame::has_decode_errors()`, `input_with_interrupt`; ffmpeg-sidecar 2.5 `KEEP_ONLY_FFMPEG`.

---

## Correctness fixes (compile-level errors removed)

| File | Was | Now |
|------|-----|-----|
| `ez_ffmpeg/cli_migration.md` | `set_audio_sample_fmt("s16")`, `set_vsync_method("...")` | `AVSampleFormat`/`VSyncMethod` enums |
| `ez_ffmpeg/cli_migration.md`, `ez_ffmpeg/video.md` | `map_metadata_from_input(0)` | 3-arg form returning `Result` |
| `ez_ffmpeg.md` | `set_format_opt("t","60")` (no-op) | `set_recording_time_us(60_000_000)` |
| `ez_ffmpeg.md`, `installation.md` | ez-ffmpeg `features=["build"]` (no such feature) | build via `ffmpeg-sys-next/build` |
| `ffmpeg_sidecar/core.md` | `no_subtitle()` (does not exist) | `.args(["-sn"])` |
| `ffmpeg_sidecar/{core,monitoring}.md` | wrong `Stream` fields | real `stream_index`/`format` + `video_data()`/`audio_data()` |
| `scenarios/capture.md`, `ez_ffmpeg/capture.md` | `abort()` to stop a capture | `stop()` (valid file); `abort()` = cancel-only |
| `scenarios/metadata_chapters.md` | chapters "Not yet supported" | `get_chapter_metadata` / `add_chapter_metadata` |

---

## Cross-model review (Claude ↔ Codex)

Three Codex agents (API-correctness, factual-accuracy, consistency) reviewed the diff against the real library source; every finding was then independently re-verified against source before acting.

- **Confirmed & fixed (8)**: the "crate major must match system FFmpeg major" wording (wrong — 8.1.0 supports FFmpeg 7 too, verified via `ffmpeg-sys-next/build.rs`); one-shot-recipe routing gap; custom-I/O routing pointing only to the unsafe doc; a residual `abort()`-for-capture contradiction; plus minor wording/consistency items.
- **Rejected (1)**: a claimed `?`-on-`Result<_, String>` compile error — false positive; std provides `From<String> for Box<dyn Error>`, and the upstream `wgpu_effects` example uses the same pattern.

---

## Assessment

Skill now tracks current releases, documents the four 0.12 capability areas with source-grounded examples, and its code samples were checked for compile-level correctness against the real crates. Remaining MSRV values for `ffmpeg-next`/`ffmpeg-sys-next` are honestly marked "unspecified" (the crates declare none).
