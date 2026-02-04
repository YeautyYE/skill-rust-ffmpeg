---
name: rust-ffmpeg
description: "Use when user asks to implement, evaluate, compare, select, or migrate Rust code for: video processing, audio processing, media conversion, multimedia handling. Triggers: (1) 'Rust function' + video/audio/media/mp4/mp3/wav/flac/mkv/avi/mov, (2) 'implement'/'write'/'create' + extract audio/convert video/transcode/encode/decode, (3) struct/trait design for media processing (VideoProcessor, MediaInfo, FilterGraph, TranscodeTask, AudioResampler, StreamReader, FrameConverter), (4) FFmpeg terms: AVPacket, AVFrame, IOContext, filter graph, loudnorm, overlay, mux, demux, remux, (5) media operations: extract audio, convert to mp4, resize video, trim video, merge videos, add watermark, generate thumbnail, batch convert, normalize audio, (6) batch/bulk: 'all .wav/.mp3/.mp4 files', 'batch transcode', 'convert all', 'bulk convert', (7) media inspection: detect/check video/audio stream, has audio, video duration, video resolution, stream info, codec info, media metadata, (8) video effects: GIF generation, screenshot/frame capture, rotate video, fade in/out, crop/cropdetect, mono to stereo, PSNR quality, showwaves visualization, (9) low-level: memory read/write, shared memory, ref_counted_frames, send_packet, avformat_find_stream_info, CodecID, ffmpeg::Error, av_log callback, EAGAIN handling, (10) async/concurrent: async transcode, progress callback, thread pool, retry logic, timeout, watchdog, (11) streaming: RTMP, HLS, live stream, broadcast, jitter buffer, latency, real-time, (12) hardware acceleration: GPU, NVENC, VideoToolbox, VAAPI, QSV, cuda, hwaccel, (13) modern codecs: AV1, HEVC, H.265, VP9, HDR, 10-bit, (14) debugging/probe: ffprobe, probe, corrupt file, integrity, testsrc, frame count, (15) subtitles: subtitles, srt, ass, vtt, burn subs, embed subs, (16) device capture: screen capture, webcam, camera capture, record screen, avfoundation, directshow, v4l2, microphone input, desktop capture, (17) library selection/migration: 'which FFmpeg library', 'compare libraries', 'ez-ffmpeg vs ffmpeg-next', 'migrate to ez-ffmpeg', 'port to', 'convert to ez-ffmpeg', 'switch from', 'rewrite using', 'refactor to ez-ffmpeg', 'can this be done with ez-ffmpeg', 'feasibility', 'should I use ez-ffmpeg or ffmpeg-next', 'library recommendation', 'best library for', (18) existing FFmpeg code review: 'check FFmpeg code', 'review FFmpeg implementation', 'can this work with ez-ffmpeg', 'evaluate current FFmpeg code', 'is ez-ffmpeg suitable', 'look at existing video/audio code'. Libraries: ez-ffmpeg, ffmpeg-next, ffmpeg-sys-next, ffmpeg-sidecar."
license: MIT
metadata:
  author: Yeauty
  github: https://github.com/YeautyYE
  version: "1.0.0"
---

# Rust FFmpeg

Guide for implementing FFmpeg functionality in Rust: library selection, code generation, and problem solving.

## Selection Framework

| Library | Use When | Async | Safety | Trade-off |
|---------|----------|-------|--------|-----------|
| ez-ffmpeg | General tasks, CLI migration, RTMP server, custom Rust filters, custom I/O | ✅ Yes | Safe | Requires FFmpeg libs |
| ffmpeg-next | Frame-level control, codec internals, custom I/O (via FFI) | ❌ No | Safe | More boilerplate |
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
| "thumbnail", "first frame", "multi-output", "concat", "watermark", "pipeline", "filter graph" | [transcoding.md](references/scenarios/transcoding.md) |
| "real-time", "RTMP", "HLS", "live", "stream", "capture", "webcam", "buffer", "backpressure", "jitter buffer", "network jitter" | [streaming_rtmp_hls.md](references/scenarios/streaming_rtmp_hls.md) |
| "GPU", "NVENC", "VideoToolbox", "hardware", "VAAPI", "QSV" | [hardware_acceleration.md](references/scenarios/hardware_acceleration.md) |
| "batch", "multiple files", "bulk", "parallel" | [batch_processing.md](references/scenarios/batch_processing.md) |
| "subtitles", "srt", "captions", "burn subs" | [subtitles.md](references/scenarios/subtitles.md) |
| "AV1", "AVIF", "HDR", "10-bit", "modern codec" | [modern_codecs.md](references/scenarios/modern_codecs.md) |
| "debug", "ffprobe", "inspect", "metadata", "error", "troubleshoot", "probe", "duration", "resolution", "corrupt", "integrity" | [debugging.md](references/scenarios/debugging.md) |
| "filter", "effect", "scale", "crop", "overlay", "watermark", "blur", "sharpen", "color", "brightness", "rotate", "flip", "fade", "speed", "slow motion" | [filters_effects.md](references/scenarios/filters_effects.md) |
| "image sequence", "frame extraction", "video to images", "images to video", "timelapse", "frame by frame" | [image_sequences.md](references/scenarios/image_sequences.md) |
| "test", "validate", "verify", "golden file", "checksum", "generate test video", "testsrc" | [testing.md](references/scenarios/testing.md) |
| "web server", "API", "S3", "async job", "integration", "tracing", "logging", "log callback", "av_log", "log redirect" | [integration.md](references/scenarios/integration.md) |
| "gif", "animated gif", "video to gif", "gif from video", "gif loop", "gif palette" | [gif_creation.md](references/scenarios/gif_creation.md) |
| "metadata", "chapter", "tag", "media info", "title", "artist", "album", "chapter marker" | [metadata_chapters.md](references/scenarios/metadata_chapters.md) |
| "screen capture", "webcam", "camera capture", "record screen", "avfoundation", "directshow", "v4l2", "device capture" | [capture.md](references/scenarios/capture.md) |
| "AVPacket", "AVFrame", "keyframe", "GOP", "NALU", "bitstream", "EAGAIN", "decode loop", "memory", "packet" | [ffmpeg_next.md](references/ffmpeg_next.md) + [ffmpeg_sys_next.md](references/ffmpeg_sys_next.md) |
| "custom io", "io context", "AVIOContext", "read callback", "write callback" | [custom_io.md](references/ffmpeg_sys_next/custom_io.md) |
| "which library", "compare", "vs", "migrate to", "port to", "convert to", "switch from", "rewrite using", "feasibility", "should I use", "best library", "evaluate", "review FFmpeg code", "can this work with" | [library_selection.md](references/library_selection.md) |

### Layer 3: Library Selection

> **CLI Migration**: Both ez-ffmpeg and ffmpeg-sidecar support CLI-style APIs. Choose based on constraints below.
> - ez-ffmpeg: [CLI Migration Guide](references/ez_ffmpeg/cli_migration.md) — library integration, native performance
> - ffmpeg-sidecar: [CLI to Rust Migration](references/ffmpeg_sidecar.md#cli-to-rust-migration) — process wrapper, no FFmpeg libs needed

1. **Need async/await?** → ez-ffmpeg (only library with native async)
2. **Need custom Rust frame processing?** → ez-ffmpeg FrameFilter (safe, simple API)
3. **Need frame-level control?** → ffmpeg-next for codec internals
4. **Need custom I/O from memory?** → ez-ffmpeg (read/write/seek callbacks); use ffmpeg-next/ffmpeg-sys-next for lower-level control
5. **Need zero-copy or max performance?** → ffmpeg-sys-next (requires unsafe code)
6. **Cannot install FFmpeg libs?** → ffmpeg-sidecar (process-based, stdin/stdout only, no custom I/O)

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
| ez-ffmpeg | 0.10.0 | 7.x | 1.70+ |
| ffmpeg-next | 7.1.0 | 7.x | 1.63+ |
| ffmpeg-sys-next | 7.1.0 | 7.x | 1.63+ |
| ffmpeg-sidecar | 2.4.0 | Any | 1.70+ |

**Source**: [crates.io](https://crates.io)

Why not 8.x (ffmpeg-next / ffmpeg-sys-next)? Upstream rust-ffmpeg issue [#246](https://github.com/zmwangx/rust-ffmpeg/issues/246) reports a compilation error with FFmpeg 8.0 due to missing EXIF side data types (AV_FRAME_DATA_EXIF, AV_PKT_DATA_EXIF). We pin to 7.1.0 until it is resolved.

**Installation Issues**: [installation.md](references/installation.md)

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
- **Keyframe alignment**: Set `force_key_frames` for HLS/DASH segmentation to avoid playback glitches
- **Error propagation**: Return `Result<T, Box<dyn Error>>`, never panic in library code
- **Resource cleanup**: Use RAII patterns; `FfmpegContext`/`Decoder`/`Encoder` drop automatically
- **Hardware acceleration**: Probe availability at runtime before enabling — not all machines have GPU support
- **Testing**: Use `testsrc` / `sine` filters to generate synthetic test media instead of shipping binary fixtures
