---
name: rust-ffmpeg
# Trigger budget: <=300 words. Never append release groups; description edits must pass
# claudedocs/skill-trigger-regression-corpus.md and record accepted misses there.
description: "Use when the user asks to implement, evaluate, compare, select, or migrate Rust code for video, audio, or media processing with FFmpeg, or for struct/trait design for media processing. Operations: transcode, encode, decode, convert format, remux, trim, resize, crop, concat, merge, watermark, overlay, rotate, fade, batch convert, extract audio, normalize loudness (loudnorm), thumbnail, sprite sheet, animated GIF, image sequences, metadata and chapters, subtitles (srt, ass, vtt, burn-in without libass), device capture (screen, webcam, microphone, v4l2, avfoundation, directshow), streaming (embedded RTMP server, HLS, ABR ladder, WHIP, WebRTC, SRT, fMP4, live broadcast, jitter buffer), hardware acceleration (NVENC, VideoToolbox, VAAPI, QSV, CUDA), GPU shaders (wgpu, WGSL, chroma key, beauty filter), modern codecs (AV1, HEVC, H.265, VP9, 10-bit, HDR, HDR to SDR tone mapping), detection and QC (blackdetect, silencedetect, scene detection, cropdetect, EBU R128, LUFS, true peak), inspection (ffprobe, stream info, duration, resolution, codec info, corrupt file, integrity), test media (testsrc, sine). FFmpeg concepts and C API: AVPacket, AVFrame, AVFormatContext, AVCodecID, avformat_find_stream_info, AVSEEK_SIZE, EAGAIN, av_log, mux, demux, filter graph, bitstream filters (h264_mp4toannexb, aac_adtstoasc), forced keyframes, -shortest, custom I/O callbacks, async transcode, progress reporting (ProgressHandle), per-stream encoders (StreamMap, -c:v:0), per-output filters (set_video_filter), frame export to memory (FrameExtractor, SampleExtractor, whisper PCM, frame to tensor), frame push (VideoWriter), encoded packet export (PacketSink, WebCodecs, avcC, AudioSpecificConfig, RTP packetizer, fMP4 segmenter), CLI translation (from_cli_args, emit_rust_code). Libraries: ez-ffmpeg, ffmpeg-next, ffmpeg-sys-next, ffmpeg-sidecar — including which-library and X vs Y comparisons, migration and porting, and feasibility review of existing FFmpeg code."
license: MIT
metadata:
  author: Yeauty
  github: https://github.com/YeautyYE
---

# Rust FFmpeg

Guide for implementing FFmpeg functionality in Rust: library selection, code generation, and problem solving.

## Selection Framework

| Library | Use When | Async | Safety | Trade-off |
|---------|----------|-------|--------|-----------|
| ez-ffmpeg | General tasks, CLI migration, RTMP server, custom Rust + WGSL GPU filters, native subtitle burn-in, detection/measurement, one-shot recipes, custom I/O, in-memory frame/sample export + frame push (VideoWriter), typed per-output progress | ✅ Yes | Safe | Requires FFmpeg libs |
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
| "thumbnail", "first frame", "fast thumbnail", "skip_frame", "nokey", "keyframe-only", "multi-output", "concat", "watermark", "pipeline", "filter graph" | [pipelines_multi_output.md](references/scenarios/pipelines_multi_output.md) — for a one-shot thumbnail prefer `recipes::thumbnail` in [image_sequences.md](references/scenarios/image_sequences.md); for the fastest keyframe-only path (`skip_frame=nokey`, snaps to next keyframe) see [ez_ffmpeg/video.md](references/ez_ffmpeg/video.md#thumbnail-extraction) |
| "real-time", "RTMP", "HLS", "live", "stream", "capture", "webcam", "buffer", "backpressure", "jitter buffer", "network jitter", "ABR ladder", "HLS ladder", "adaptive bitrate", "master playlist", "VOD packaging" | [streaming_rtmp_hls.md](references/scenarios/streaming_rtmp_hls.md) |
| "GPU", "NVENC", "VideoToolbox", "hardware", "VAAPI", "QSV", "wgpu", "WGSL", "custom shader", "GPU filter", "compute shader", "libplacebo", "beauty filter", "chroma key", "green screen" | [hardware_acceleration.md](references/scenarios/hardware_acceleration.md) |
| "batch", "multiple files", "bulk", "parallel" | [batch_processing.md](references/scenarios/batch_processing.md) |
| "subtitles", "srt", "captions", "burn subs", "burn-in", "hardsub", "ass", "vtt", "native subtitle", "without libass", "no libass" | [subtitles.md](references/scenarios/subtitles.md) |
| "AV1", "AVIF", "HDR", "10-bit", "modern codec", "HDR to SDR", "tone mapping", "tonemap", "washed out colors", "PQ", "HLG" | [modern_codecs.md](references/scenarios/modern_codecs.md) |
| "debug", "ffprobe", "inspect", "metadata", "error", "troubleshoot", "probe", "duration", "resolution", "corrupt", "integrity" | [debugging.md](references/scenarios/debugging.md) |
| "detect black frames", "silence detect", "scene detect", "scene change", "cropdetect", "EBU R128", "LUFS", "measure loudness", "true peak", "content analysis", "QC", "blackdetect", "silencedetect" | [detection_analysis.md](references/scenarios/detection_analysis.md) (typed `analysis` API) |
| "filter", "effect", "scale", "crop", "overlay", "watermark", "blur", "sharpen", "color", "brightness", "rotate", "flip", "fade", "speed", "slow motion" | [filters_effects.md](references/scenarios/filters_effects.md) |
| "image sequence", "frame extraction", "video to images", "images to video", "timelapse", "frame by frame", "sprite sheet", "storyboard", "contact sheet", "thumbnail grid" | [image_sequences.md](references/scenarios/image_sequences.md) |
| "one-shot recipe", "recipes module", "quick thumbnail", "thumbnail recipe", "sprite sheet recipe", "gif recipe", "HLS ladder recipe" (ez-ffmpeg `recipes`, no feature flag) | [image_sequences.md](references/scenarios/image_sequences.md) (thumbnail/sprite), [gif_creation.md](references/scenarios/gif_creation.md) (gif), [streaming_rtmp_hls.md](references/scenarios/streaming_rtmp_hls.md) (HLS ladder) |
| "test", "validate", "verify", "golden file", "checksum", "generate test video", "testsrc" | [testing.md](references/scenarios/testing.md) |
| "web server", "API", "S3", "async job", "integration", "tracing", "logging", "log callback", "av_log", "log redirect" | [integration.md](references/scenarios/integration.md) |
| "gif", "animated gif", "video to gif", "gif from video", "gif loop", "gif palette" | [gif_creation.md](references/scenarios/gif_creation.md) |
| "metadata", "chapter", "tag", "media info", "title", "artist", "album", "chapter marker" | [metadata_chapters.md](references/scenarios/metadata_chapters.md) |
| "screen capture", "webcam", "camera capture", "record screen", "avfoundation", "directshow", "v4l2", "device capture" | [capture.md](references/scenarios/capture.md) |
| "AVPacket", "AVFrame", "keyframe", "GOP", "NALU", "bitstream", "EAGAIN", "decode loop", "memory", "packet" | [ffmpeg_next.md](references/ffmpeg_next.md) + [ffmpeg_sys_next.md](references/ffmpeg_sys_next.md) |
| "avformat_find_stream_info", "AVSEEK_SIZE", "AVFormatContext", "AVCodecID", "raw C API", "FFI" | [ffmpeg_sys_next.md](references/ffmpeg_sys_next.md) + [custom_io.md](references/ffmpeg_sys_next/custom_io.md) |
| "custom io", "read callback", "write callback", "StreamIo", "memory input/output", "Read/Write/Seek source" | Safe APIs: [advanced.md](references/ez_ffmpeg/advanced.md#custom-io-sources) (ez-ffmpeg callbacks) or [ffmpeg_next.md](references/ffmpeg_next.md) (`StreamIo`) |
| "AVIOContext", "io context", "raw io callback", "zero-copy custom io" | [custom_io.md](references/ffmpeg_sys_next/custom_io.md) (unsafe FFI) |
| "extract frames to memory", "decode to RGB", "frames for AI/ML", "frame to tensor", "frame export", "video to frames for a model", "FrameExtractor", "whisper PCM", "audio to f32", "SampleExtractor", "ASR ingest", "uniform N frames" | [frame_io.md](references/ez_ffmpeg/frame_io.md) (experimental, ez-ffmpeg 0.14) |
| "VideoWriter", "push frames", "generate video from frames", "procedural video", "render frames to video", "in-memory mp4", "encode from memory", "frames to video" | [frame_io.md](references/ez_ffmpeg/frame_io.md) (experimental, ez-ffmpeg 0.14) |
| "WHIP", "WebRTC output", "SRT output", "capability probe", "is_muxer_available", "output protocol available", "fMP4 HLS", "fragmented mp4 segments" | [streaming.md](references/ez_ffmpeg/streaming.md) (WHIP/SRT/capabilities) + [streaming_rtmp_hls.md](references/scenarios/streaming_rtmp_hls.md) (fMP4 ladder) |
| "encoded packet export", "packet sink", "PacketSink", "webcodecs", "EncodedVideoChunk", "EncodedAudioChunk", "h.264 access units", "aac frames", "avcC", "AudioSpecificConfig", "rtp packetizer", "fmp4 segmenter", "job failure", "on_job_failed", "JobFailureSummary" | [packet_sink.md](references/ez_ffmpeg/packet_sink.md) (experimental, ez-ffmpeg 0.15; job-failure summaries 0.16) |
| "progress", "progress bar", "percent complete", "ETA", "how far along", "encoding speed", "progress_handle", "ProgressHandle", "progress snapshot" | [advanced.md](references/ez_ffmpeg/advanced.md#progress-monitoring); batch per-file counting: [batch_processing.md](references/scenarios/batch_processing.md) |
| "per-stream encoder", "different codec per stream", "StreamMap", "-c:v:0", "indexed stream options", "per-stream codec options" | [video.md](references/ez_ffmpeg/video.md#per-stream-encoder-selection-streammap) (ez-ffmpeg 0.16) |
| "run ffmpeg command in rust", "from_cli_args", "emit_rust_code", "translate ffmpeg command", "cli feature", "cli-compat", "verified shape" | [cli_compat.md](references/ez_ffmpeg/cli_compat.md) (`cli` feature); manual mapping: [cli_migration.md](references/ez_ffmpeg/cli_migration.md) |
| "version compatibility", "FFmpeg 7 vs 8", "linking error", "build fails", "links = ffmpeg", "install", "vcpkg" | [installation.md](references/installation.md) |
| "which library", "compare", "vs", "migrate to", "port to", "convert to", "switch from", "rewrite using", "feasibility", "should I use", "best library", "evaluate", "review FFmpeg code", "can this work with" | [library_selection.md](references/library_selection.md) |

> Multiple rows can match one request — load **all** applicable references, then follow the most specific row's target first.

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
13. **Need to feed a WebCodecs decoder, RTP/SRT packetizer, or hand-rolled fMP4 segmenter straight from the encoder?** → ez-ffmpeg `packet_sink` (`PacketSink`, strict H.264-only/AAC tier, no container; no feature flag; experimental, 0.15) — see [packet_sink.md](references/ez_ffmpeg/packet_sink.md)
14. **Need to run or auto-translate an existing ffmpeg CLI command?** → ez-ffmpeg `cli` feature (`from_cli_args`/`emit_rust_code`, narrow golden-tested subset — 6 verified shapes; 0.15) — see [cli_compat.md](references/ez_ffmpeg/cli_compat.md); anything outside that subset still needs the manual [cli_migration.md](references/ez_ffmpeg/cli_migration.md) tables

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
| ez-ffmpeg | 0.18.0 | 7.1–8.x | 1.80+ (wgpu: 1.85+) |
| ffmpeg-next | 8.1.0 | 7.0–8.x | unspecified |
| ffmpeg-sys-next | 8.1.0 | 7.0–8.x | unspecified |
| ffmpeg-sidecar | 2.5.2 | Any | 1.79+ |

**Source**: [crates.io](https://crates.io)

**FFmpeg 7 vs 8**: all four libraries build against both majors with the current crate versions above — no crate-major-to-system-major matching. Guard: when pulling `ffmpeg-next` **alongside** ez-ffmpeg, keep it at `8.1.0` — a `7.1.0` mixed in collides via the `links = "ffmpeg"` key. Bindgen mechanics, the legacy 7.1-pin rationale, and the rust-ffmpeg #246 history: see [installation.md](references/installation.md#version-compatibility).

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

**User**: "I need frame-level access to decode H.264 and apply custom processing"
**Claude**: Identify → frame-level + custom processing → ez-ffmpeg FrameFilter (safe, simple) or ffmpeg-next (codec internals) → ask user preference if unclear → load `ffmpeg_next.md` or `ez_ffmpeg/filters.md` → generate decode loop with proper EAGAIN handling

**User**: "Can this video trimming code be converted to ez-ffmpeg? Fall back to ffmpeg-next if not"
**Claude**: Identify → library migration feasibility → load `library_selection.md` + `video_transcoding.md` → review existing code against ez-ffmpeg API → assess feasibility → provide migration path or explain why ffmpeg-next is needed

**User**: "Can you just run this ffmpeg command from Rust instead of me hand-writing the builder chain?"
**Claude**: Identify → automatic CLI translation → load `cli_compat.md` → if the command matches one of the 6 verified shapes, use `cli::from_cli_args`/`emit_rust_code`, flagging the FFmpeg-7.1-only runtime gate on execution → otherwise fall back to the manual `cli_migration.md` tables

## Best Practices

- **Codec copy first**: use `-c copy` / stream copy only when no re-encoding is needed — 10x faster, zero quality loss
- **Keyframe alignment**: for HLS/DASH segmentation use fixed-GOP codec opts (`g`/`keyint_min`/`sc_threshold`); for keyframes at known absolute times use `Output::set_force_key_frames("0,5,10.5")` — it is **not** an encoder AVOption, so `set_video_codec_opt` is silently ignored
- **Error propagation**: return `Result<T, Box<dyn Error>>`, never panic in library code
- **Resource cleanup**: rely on RAII — `FfmpegContext`/`Decoder`/`Encoder` drop automatically; don't add manual cleanup
- **Hardware acceleration**: probe availability at runtime before enabling (`get_gpu_filter_backends()` for GPU filters); `opengl` is deprecated — use `wgpu` (see [hardware_acceleration.md](references/scenarios/hardware_acceleration.md))
- **Built-in GPU effects before custom WGSL**: check the typed `wgpu_filter::effects` catalog before writing shaders (see [filters.md](references/ez_ffmpeg/filters.md))
- **Prefer recipes for one-shot jobs**: `recipes::{thumbnail, sprite_sheet, animated_gif, HlsLadder}` bake in the correctness details (see [image_sequences.md](references/scenarios/image_sequences.md), [gif_creation.md](references/scenarios/gif_creation.md), [streaming_rtmp_hls.md](references/scenarios/streaming_rtmp_hls.md))
- **Measure, don't scrape logs**: typed `analysis` API for black/silence/scene/crop/EBU R128 (see [detection_analysis.md](references/scenarios/detection_analysis.md))
- **Frames in/out of memory**: `frame_export::{FrameExtractor, SampleExtractor}` for AI/CV/ASR ingest, `VideoWriter` for frame push — experimental, default build. Guard: the default conversion precision changed in 0.15 — byte-identical 0.14 output needs `.conversion_precision(ConversionPrecision::High)` (see [frame_io.md](references/ez_ffmpeg/frame_io.md))
- **Encoded packets (PacketSink)**: strict tier is H.264 **libx264-only** + AAC, and backpressure **blocks by design** — a slow consumer stalls the encoders; drain concurrently, never only after `wait()` (see [packet_sink.md](references/ez_ffmpeg/packet_sink.md))
- **Automatic CLI translation**: `from_cli_args`/`emit_rust_code` cover only 6 golden-tested shapes, and `from_cli_args` execution refuses any unverified runtime — **FFmpeg 7.1 only as of 0.16** (8.x refused even for verified shapes; `emit_rust_code` unaffected). Indexed per-stream options (`-c:v:0`) are permanently outside the subset — port them with `StreamMap` (see [cli_compat.md](references/ez_ffmpeg/cli_compat.md), fallback [cli_migration.md](references/ez_ffmpeg/cli_migration.md))
- **Mixed stream lengths**: `Output::set_shortest(true)` (FFmpeg `-shortest` parity) ends the output when the shortest stream ends — without it, video + longer music keeps running to the longer stream
- **Typed progress**: use `progress_handle()` snapshots, not hand-rolled FrameFilters. Guard: every metric is `Option` — `None` means unknowable (HLS/`null` muxers, packet-sink outputs), never fabricate zero; percentage needs your own total via `percent_of(total_us)` (see [advanced.md](references/ez_ffmpeg/advanced.md#progress-monitoring))
- **Per-stream encoders**: same-type streams in one output need `StreamMap` per-map codecs (`-c:v:0` parity); per-map settings override per-type setters key by key, and copy×re-encode conflicts fail typed at `build()` (see [video.md](references/ez_ffmpeg/video.md#per-stream-encoder-selection-streammap))
- **HDR→SDR needs tone mapping, not scaling**: naive `scale,format=yuv420p` yields washed-out gray; route on `StreamInfo::Video` `color_transfer` (PQ=16/HLG=18 — transfer, *not* primaries) and use the cookbook chains (see [modern_codecs.md](references/scenarios/modern_codecs.md))
- **Graceful shutdown**: `stop()` flushes and returns `Result` (check it — output valid on `Ok`); `abort()` is the hard cancel with no output guarantee. The embedded RTMP server's `stop()` joins its threads — never call it from inside a logger (see [streaming.md](references/ez_ffmpeg/streaming.md))
- **In-place frame edits**: call `make_frame_writable` before mutating frame data in a `FrameFilter` — decoder frames are refcounted and shared
- **Testing**: prefer lavfi-generated media (`testsrc`/`sine`) over shipping binary fixtures where suitable (see [testing.md](references/scenarios/testing.md))
