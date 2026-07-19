---
name: rust-ffmpeg
description: "Use when user asks to implement, evaluate, compare, select, or migrate Rust code for: video processing, audio processing, media conversion, multimedia handling. Triggers: (1) 'Rust function' + video/audio/media/mp4/mp3/wav/flac/mkv/avi/mov, (2) 'implement'/'write'/'create' + extract audio/convert video/transcode/encode/decode, (3) struct/trait design for media processing (VideoProcessor, MediaInfo, FilterGraph, TranscodeTask, AudioResampler, StreamReader, FrameConverter), (4) FFmpeg terms: AVPacket, AVFrame, IOContext, filter graph, loudnorm, overlay, mux, demux, remux, (5) media operations: extract audio, convert to mp4, resize video, trim video, merge videos, add watermark, generate thumbnail, batch convert, normalize audio, (6) batch/bulk: 'all .wav/.mp3/.mp4 files', 'batch transcode', 'convert all', 'bulk convert', (7) media inspection: detect/check video/audio stream, has audio, video duration, video resolution, stream info, codec info, media metadata, (8) video effects: GIF generation, screenshot/frame capture, rotate video, fade in/out, crop/cropdetect, mono to stereo, PSNR quality, showwaves visualization, (9) low-level: memory read/write, shared memory, ref_counted_frames, send_packet, avformat_find_stream_info, CodecID, ffmpeg::Error, av_log callback, EAGAIN handling, (10) async/concurrent: async transcode, progress callback, thread pool, retry logic, timeout, watchdog, (11) streaming: RTMP, HLS, live stream, broadcast, jitter buffer, latency, real-time, (12) hardware acceleration: GPU, NVENC, VideoToolbox, VAAPI, QSV, cuda, hwaccel, (13) modern codecs: AV1, HEVC, H.265, VP9, HDR, 10-bit, (14) debugging/probe: ffprobe, probe, corrupt file, integrity, testsrc, frame count, (15) subtitles: subtitles, srt, ass, vtt, burn subs, embed subs, (16) device capture: screen capture, webcam, camera capture, record screen, avfoundation, directshow, v4l2, microphone input, desktop capture, (17) library selection/migration: 'which FFmpeg library', 'compare libraries', 'ez-ffmpeg vs ffmpeg-next', 'migrate to ez-ffmpeg', 'port to', 'convert to ez-ffmpeg', 'switch from', 'rewrite using', 'refactor to ez-ffmpeg', 'can this be done with ez-ffmpeg', 'feasibility', 'should I use ez-ffmpeg or ffmpeg-next', 'library recommendation', 'best library for', (18) existing FFmpeg code review: 'check FFmpeg code', 'review FFmpeg implementation', 'can this work with ez-ffmpeg', 'evaluate current FFmpeg code', 'is ez-ffmpeg suitable', 'look at existing video/audio code', (19) detection/measurement: blackdetect, silencedetect, scene detection, cropdetect, EBU R128, LUFS, true peak, measure loudness, content analysis, QC, (20) GPU custom shaders: wgpu, WGSL, custom shader, headless GPU filter, compute shader, built-in GPU effects, beauty filter, chroma key, green screen, pixelate, mirror flip, (21) native subtitle burn-in: burn subtitles without libass, pure-Rust subtitle, hardsub, SubtitleFilter, (22) one-shot recipes: thumbnail, sprite sheet, storyboard, contact sheet, animated gif, HLS ABR ladder, adaptive bitrate ladder, master playlist, (23) mux control: -shortest, shortest stream, bitstream filter, bsf, h264_mp4toannexb, aac_adtstoasc, annexb, attach fonts, cover art, mkv attachment, forced keyframes, (24) in-memory frame/sample export (experimental, 0.14): extract frames to memory, decode to RGB, frame to tensor, FrameExtractor, AI frame ingest, CV pipeline, uniform sampling, video to frames for model, SampleExtractor, whisper PCM, extract audio to f32, ASR ingest, (25) frame push / video generation (experimental, 0.14): VideoWriter, push frames, generate video from frames, procedural video, render to video, frames to video, in-memory mp4, encode from memory, (26) modern streaming outputs: WHIP, WebRTC output, SRT output, capability probe, is_muxer_available, fMP4 HLS, fragmented mp4 segments. Libraries: ez-ffmpeg, ffmpeg-next, ffmpeg-sys-next, ffmpeg-sidecar."
license: MIT
metadata:
  author: Yeauty
  github: https://github.com/YeautyYE
  version: "1.3.0"
---

# Rust FFmpeg

Guide for implementing FFmpeg functionality in Rust: library selection, code generation, and problem solving.

## Selection Framework

| Library | Use When | Async | Safety | Trade-off |
|---------|----------|-------|--------|-----------|
| ez-ffmpeg | General tasks, CLI migration, RTMP server, custom Rust + WGSL GPU filters, native subtitle burn-in, detection/measurement, one-shot recipes, custom I/O, in-memory frame/sample export + frame push (VideoWriter) | ✅ Yes | Safe | Requires FFmpeg libs |
| ffmpeg-next | Frame-level control, codec internals, safe stream I/O (any `Read`/`Write`/`Seek`) | ❌ No | Safe | More boilerplate |
| ffmpeg-sys-next | Zero-copy, custom memory I/O, max performance | ❌ No | Unsafe | Manual memory mgmt |
| ffmpeg-sidecar | No FFmpeg installation possible | ❌ No | Safe | Process overhead, no custom I/O |

## Decision Logic

### Layer 1: Integration Method

**Default: Library Integration** (ez-ffmpeg/ffmpeg-next/ffmpeg-sys-next)
- Better performance, type-safe API, direct Frame access

**Alternative: Binary Approach** (ffmpeg-sidecar) - consider when:
- Cannot install FFmpeg development libraries
- Restricted CI/CD environment without admin access
- Pure CLI batch processing (no real-time needs)

If installation constrained → Load [ffmpeg_sidecar.md](references/ffmpeg_sidecar.md)

### Layer 2: Scenario Detection

| User Mentions | Load Reference |
|---------------|----------------|
| "convert format", "remux", "trim", "resize", "crop", "simple" | [video_transcoding.md](references/scenarios/video_transcoding.md) |
| "extract audio", "audio only", "audio track", "mp3 extract", "loudnorm", "normalize audio", "volume" | [audio_extraction.md](references/scenarios/audio_extraction.md) |
| "thumbnail", "first frame", "fast thumbnail", "skip_frame", "nokey", "keyframe-only", "multi-output", "concat", "watermark", "pipeline", "filter graph" | [transcoding.md](references/scenarios/transcoding.md) — for a one-shot thumbnail prefer `recipes::thumbnail` in [image_sequences.md](references/scenarios/image_sequences.md); for the fastest keyframe-only path (`skip_frame=nokey`, snaps to next keyframe) see [ez_ffmpeg/video.md](references/ez_ffmpeg/video.md#thumbnail-extraction) |
| "real-time", "RTMP", "HLS", "live", "stream", "capture", "webcam", "buffer", "backpressure", "jitter buffer", "network jitter", "ABR ladder", "HLS ladder", "adaptive bitrate", "master playlist", "VOD packaging" | [streaming_rtmp_hls.md](references/scenarios/streaming_rtmp_hls.md) |
| "GPU", "NVENC", "VideoToolbox", "hardware", "VAAPI", "QSV", "wgpu", "WGSL", "custom shader", "GPU filter", "compute shader", "libplacebo", "beauty filter", "chroma key", "green screen" | [hardware_acceleration.md](references/scenarios/hardware_acceleration.md) |
| "batch", "multiple files", "bulk", "parallel" | [batch_processing.md](references/scenarios/batch_processing.md) |
| "subtitles", "srt", "captions", "burn subs", "burn-in", "hardsub", "ass", "vtt", "native subtitle", "without libass", "no libass" | [subtitles.md](references/scenarios/subtitles.md) |
| "AV1", "AVIF", "HDR", "10-bit", "modern codec" | [modern_codecs.md](references/scenarios/modern_codecs.md) |
| "debug", "ffprobe", "inspect", "metadata", "error", "troubleshoot", "probe", "duration", "resolution", "corrupt", "integrity" | [debugging.md](references/scenarios/debugging.md) |
| "detect black frames", "silence detect", "scene detect", "scene change", "cropdetect", "EBU R128", "LUFS", "measure loudness", "true peak", "content analysis", "QC", "blackdetect", "silencedetect" | [debugging.md](references/scenarios/debugging.md) (typed `analysis` API) |
| "filter", "effect", "scale", "crop", "overlay", "watermark", "blur", "sharpen", "color", "brightness", "rotate", "flip", "fade", "speed", "slow motion" | [filters_effects.md](references/scenarios/filters_effects.md) |
| "image sequence", "frame extraction", "video to images", "images to video", "timelapse", "frame by frame", "sprite sheet", "storyboard", "contact sheet", "thumbnail grid" | [image_sequences.md](references/scenarios/image_sequences.md) |
| "one-shot recipe", "recipes module", "quick thumbnail", "thumbnail recipe", "sprite sheet recipe", "gif recipe", "HLS ladder recipe" (ez-ffmpeg `recipes`, no feature flag) | [image_sequences.md](references/scenarios/image_sequences.md) (thumbnail/sprite), [gif_creation.md](references/scenarios/gif_creation.md) (gif), [streaming_rtmp_hls.md](references/scenarios/streaming_rtmp_hls.md) (HLS ladder) |
| "test", "validate", "verify", "golden file", "checksum", "generate test video", "testsrc" | [testing.md](references/scenarios/testing.md) |
| "web server", "API", "S3", "async job", "integration", "tracing", "logging", "log callback", "av_log", "log redirect" | [integration.md](references/scenarios/integration.md) |
| "gif", "animated gif", "video to gif", "gif from video", "gif loop", "gif palette" | [gif_creation.md](references/scenarios/gif_creation.md) |
| "metadata", "chapter", "tag", "media info", "title", "artist", "album", "chapter marker" | [metadata_chapters.md](references/scenarios/metadata_chapters.md) |
| "screen capture", "webcam", "camera capture", "record screen", "avfoundation", "directshow", "v4l2", "device capture" | [capture.md](references/scenarios/capture.md) |
| "AVPacket", "AVFrame", "keyframe", "GOP", "NALU", "bitstream", "EAGAIN", "decode loop", "memory", "packet" | [ffmpeg_next.md](references/ffmpeg_next.md) + [ffmpeg_sys_next.md](references/ffmpeg_sys_next.md) |
| "custom io", "read callback", "write callback", "StreamIo", "memory input/output", "Read/Write/Seek source" | Safe first: ez-ffmpeg callbacks or ffmpeg-next [StreamIo](references/ffmpeg_next.md) (`input_from_stream`/`output_to_stream`) |
| "AVIOContext", "io context", "raw io callback", "zero-copy custom io" | [custom_io.md](references/ffmpeg_sys_next/custom_io.md) (low-level unsafe FFI, when the safe API can't express it) |
| "extract frames to memory", "decode to RGB", "frames for AI/ML", "frame to tensor", "frame export", "video to frames for a model", "FrameExtractor", "whisper PCM", "audio to f32", "SampleExtractor", "ASR ingest", "uniform N frames" | [frame_io.md](references/ez_ffmpeg/frame_io.md) (experimental, ez-ffmpeg 0.14) |
| "VideoWriter", "push frames", "generate video from frames", "procedural video", "render frames to video", "in-memory mp4", "encode from memory", "frames to video" | [frame_io.md](references/ez_ffmpeg/frame_io.md) (experimental, ez-ffmpeg 0.14) |
| "WHIP", "WebRTC output", "SRT output", "capability probe", "is_muxer_available", "output protocol available", "fMP4 HLS", "fragmented mp4 segments" | [streaming.md](references/ez_ffmpeg/streaming.md) (WHIP/SRT/capabilities) + [streaming_rtmp_hls.md](references/scenarios/streaming_rtmp_hls.md) (fMP4 ladder) |
| "which library", "compare", "vs", "migrate to", "port to", "convert to", "switch from", "rewrite using", "feasibility", "should I use", "best library", "evaluate", "review FFmpeg code", "can this work with" | [library_selection.md](references/library_selection.md) |

### Layer 3: Library Selection

> **CLI Migration**: Both ez-ffmpeg and ffmpeg-sidecar support CLI-style APIs. Choose based on constraints below.
> - ez-ffmpeg: [CLI Migration Guide](references/ez_ffmpeg/cli_migration.md) — library integration, native performance
> - ffmpeg-sidecar: [CLI to Rust Migration](references/ffmpeg_sidecar.md#cli-to-rust-migration) — process wrapper, no FFmpeg libs needed

1. **Need async/await?** → ez-ffmpeg (only library with native async)
2. **Need custom Rust frame processing?** → ez-ffmpeg FrameFilter (safe, simple API)
3. **Need custom GPU shaders (WGSL)?** → ez-ffmpeg `wgpu` feature (`WgpuFrameFilter`, headless, no display server) — check the built-in `wgpu_filter::effects` catalog first (13 typed effects, 0.13+); for native hardware filters (`scale_cuda`/`scale_vaapi`/`libplacebo`) probe with `get_gpu_filter_backends()`
4. **Need to burn in subtitles without libass?** → ez-ffmpeg `subtitle` feature (`SubtitleFilter`, pure-Rust ASS/SRT renderer, no `--enable-libass`)
5. **Need typed detection/measurement (black/silence/scene/crop/EBU R128)?** → ez-ffmpeg `analysis` module (`Analysis` one-shot or `MetadataEventFilter` streaming — no feature flag)
6. **Need a one-shot thumbnail / sprite sheet / GIF / HLS ABR ladder?** → ez-ffmpeg `recipes` module (no feature flag)
7. **Need frame-level codec control?** → ffmpeg-next for codec internals
8. **Need custom I/O from memory?** → ez-ffmpeg (read/write/seek callbacks), or ffmpeg-next **safe** stream I/O (`input_from_stream`/`output_to_stream`, any `Read`/`Write`/`Seek`); ffmpeg-sys-next for lowest-level control
9. **Need zero-copy or max performance?** → ffmpeg-sys-next (requires unsafe code)
10. **Cannot install FFmpeg libs?** → ffmpeg-sidecar (process-based, stdin/stdout only, no custom I/O)
11. **Need decoded frames/audio in memory for AI/CV/ASR?** → ez-ffmpeg `frame_export` (`FrameExtractor` → packed RGB, `SampleExtractor::for_whisper` → 16 kHz mono f32; no feature flag; experimental, 0.14) — see [frame_io.md](references/ez_ffmpeg/frame_io.md)
12. **Need to generate/push video from Rust-rendered frames?** → ez-ffmpeg `VideoWriter` (frame push into encode/mux/stream, no demuxer; experimental, 0.14) — see [frame_io.md](references/ez_ffmpeg/frame_io.md)

> **Note**: FrameFilter (custom Rust frame processing) is separate from custom I/O callbacks (custom data sources/sinks). ez-ffmpeg supports both.

## Quick Start

New to Rust FFmpeg? See [quick_start.md](references/quick_start.md) for 5-minute setup.

## Library References

- [ez-ffmpeg](references/ez_ffmpeg.md) - High-level API (sync and async)
- [ffmpeg-next](references/ffmpeg_next.md) - Medium-level API for advanced control
- [ffmpeg-sys-next](references/ffmpeg_sys_next.md) - Low-level unsafe FFI
- [ffmpeg-sidecar](references/ffmpeg_sidecar.md) - CLI wrapper

## Version Compatibility

| Library | Version | FFmpeg | Rust MSRV |
|---------|---------|--------|-----------|
| ez-ffmpeg | 0.14.0 | 7.1–8.x | 1.80+ (wgpu: 1.85+) |
| ffmpeg-next | 8.1.0 | 7.0–8.x | unspecified |
| ffmpeg-sys-next | 8.1.0 | 7.0–8.x | unspecified |
| ffmpeg-sidecar | 2.5.2 | Any | 1.79+ |

**Source**: [crates.io](https://crates.io)

**FFmpeg 7 vs 8**: all four libraries build against both FFmpeg 7 and 8 — **just use the current crate versions above**, no crate-major-to-system-major matching required. `ffmpeg-sys-next` 8.1.0 generates its bindings from the *installed* FFmpeg headers (bindgen) and emits compile-time `ffmpeg_7_0`/`ffmpeg_7_1`/`ffmpeg_8_0`/`ffmpeg_8_1` cfgs for the detected version, so `ffmpeg-next`/`ffmpeg-sys-next` 8.1.0 compile cleanly on FFmpeg **7.0 through 8.x** (libavcodec 61 on FFmpeg 7, 62 on FFmpeg 8); ez-ffmpeg 0.14.0 links either major the same way (its own documented floor is FFmpeg **7.1**, as its pipeline is ported from the FFmpeg `n7.1` sources). You would only pin `7.1.x` for reproducibility on a legacy toolchain — it is **not** required for FFmpeg 7 systems. (The old "pin 7.1.0" advice existed only because rust-ffmpeg 7.1.0 predated FFmpeg 8 support — the now-fixed [#246](https://github.com/zmwangx/rust-ffmpeg/issues/246) EXIF blocker, resolved in 8.0/8.1.) Note: when pulling `ffmpeg-next` **alongside** ez-ffmpeg 0.14, keep it at `8.1.0` to match ez-ffmpeg's re-exported types — a `7.1.0` mixed in collides via the `links = "ffmpeg"` key.

**Installation Issues**: [installation.md](references/installation.md) — includes the Windows vcpkg static-link `unresolved external symbol` fix (extra system libs in your app's `build.rs`; `VCPKG_ROOT` must be set in the shell, not via `std::env::set_var` in `build.rs`)

## Guidelines for Claude

When this skill activates, follow this workflow:

**For implementation tasks:**
1. **Identify task** — Determine: video/audio/streaming/inspection? Simple or complex?
2. **Select library** — Apply Layer 3 decision logic. State which library and why in one sentence
3. **Load references** — Follow Layer 2 scenario detection to load the right reference files
4. **Generate code** — Production-ready: proper error handling, `Result<>` return types, no `unwrap()` in library code
5. **Explain briefly** — One-line summary of approach before the code block. No lengthy tutorials
6. **Suggest next steps** — If applicable: performance optimization, hardware acceleration, or testing

**For evaluation/migration/selection tasks:**
1. **Load selection guide** — Load `library_selection.md` and relevant scenario references
2. **Assess requirements** — Identify constraints: async needs, frame-level access, install limitations, existing code patterns
3. **Compare options** — Apply Layer 3 decision logic against the specific use case
4. **Give verdict** — Clear feasibility conclusion with rationale. If migration is possible, show key API differences. If not, explain why and recommend the alternative

**Rules**:
- Follow Layer 3 decision logic to select the library
- Always add `Cargo.toml` dependencies when introducing a new library
- Use async when the user's context is async (tokio/actix/axum)
- If the user's need is ambiguous between libraries, ask — don't guess
- For complex pipelines, break into steps with comments, not monolithic blocks

## Interaction Examples

**User**: "Write a Rust function to extract audio from MP4"
**Claude**: Identify → audio extraction → apply Layer 3 (general task, no special requirements) → load `audio_extraction.md` → generate function with proper error handling → include `Cargo.toml` dep

**User**: "I need frame-level access to decode H.264 and apply custom processing"
**Claude**: Identify → frame-level + custom processing → ez-ffmpeg FrameFilter (safe, simple) or ffmpeg-next (codec internals) → ask user preference if unclear → load `ffmpeg_next.md` or `ez_ffmpeg/filters.md` → generate decode loop with proper EAGAIN handling

**User**: "How to do RTMP live streaming in Rust?"
**Claude**: Identify → streaming + real-time → ez-ffmpeg (async + RTMP server) → load `streaming_rtmp_hls.md` → generate RTMP push/server example → mention jitter buffer for production use

**User**: "Can this video trimming code be converted to ez-ffmpeg? Fall back to ffmpeg-next if not"
**Claude**: Identify → library migration feasibility → load `library_selection.md` + `video_transcoding.md` → review existing code against ez-ffmpeg API → assess feasibility → provide migration path or explain why ffmpeg-next is needed

**User**: "Which Rust FFmpeg library should I use for my project?"
**Claude**: Identify → library selection → load `library_selection.md` → ask about requirements (async? frame-level? install constraints?) → apply Layer 3 decision logic → recommend with rationale

## Best Practices

- **Codec copy first**: Use `-c copy` / stream copy when no re-encoding is needed — 10x faster, zero quality loss
- **Keyframe alignment**: For HLS/DASH segmentation use fixed-GOP codec opts (`g`/`keyint_min`/`sc_threshold`); for keyframes at known absolute times use `Output::set_force_key_frames("0,5,10.5")` (ez-ffmpeg 0.13+, list form — it is not an encoder AVOption, so `set_video_codec_opt` won't work)
- **Error propagation**: Return `Result<T, Box<dyn Error>>`, never panic in library code
- **Resource cleanup**: Use RAII patterns; `FfmpegContext`/`Decoder`/`Encoder` drop automatically
- **Hardware acceleration**: Probe availability at runtime before enabling — not all machines have GPU support. For GPU *filters*, probe `get_gpu_filter_backends()`; for custom shaders prefer the `wgpu` feature (`WgpuFrameFilter`, WGSL) — the `opengl` filter path is deprecated since ez-ffmpeg 0.11
- **Built-in GPU effects before custom WGSL**: ez-ffmpeg 0.13's `wgpu_filter::effects` catalog (adjust/beauty/sharpen/blur/pixelate/mirror/chroma-key + more, typed params, live updates) covers common live-streaming effects without writing shaders
- **Prefer recipes for one-shot jobs**: use `recipes::{thumbnail, sprite_sheet, animated_gif, HlsLadder}` instead of hand-rolling filter graphs — they bake in correct palettegen/paletteuse, seek modes, and fixed-GOP alignment
- **Measure, don't scrape logs**: use the typed `analysis` API (`Analysis` / `MetadataEventFilter`) for black/silence/scene/crop/EBU R128 instead of parsing `av_log` output
- **Frames in/out of memory (0.14)**: for AI/CV/ASR ingest use `frame_export::{FrameExtractor, SampleExtractor}` (packed RGB / whisper PCM, colorspace-correct); to generate video from Rust-rendered frames use `VideoWriter` — both experimental, no feature flag, no temp files (see [frame_io.md](references/ez_ffmpeg/frame_io.md))
- **Mixed stream lengths**: set `Output::set_shortest(true)` (ez-ffmpeg 0.13+, FFmpeg `-shortest` parity) to end the output when the shortest stream ends — e.g. video + longer music track
- **Graceful shutdown**: call `stop()` (blocks, flushes encoders, output is valid; 0.13 returns `Result` — check it), not `abort()` (emergency, output not guaranteed)
- **In-place frame edits**: inside a `FrameFilter`, call `make_frame_writable` before mutating frame data — decoder frames are refcounted and shared (0.13 helper)
- **Testing**: Use `testsrc` / `sine` filters to generate synthetic test media instead of shipping binary fixtures
