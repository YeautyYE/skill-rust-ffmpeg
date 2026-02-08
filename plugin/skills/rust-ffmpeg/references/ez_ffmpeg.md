# ez-ffmpeg Reference

**Detection Keywords**: high-level API, simple transcoding, builder pattern, easy ffmpeg, video conversion, format conversion
**Aliases**: ez-ffmpeg, ezffmpeg, simple ffmpeg rust

**Version**: 0.10.0 | [Repository](https://github.com/YeautyYE/ez-ffmpeg) | [Docs](https://docs.rs/ez-ffmpeg)

Safe, ergonomic Rust FFmpeg interface with Builder pattern API.

## Prerequisites

- **FFmpeg**: 7.x installed on system (see [installation.md](installation.md) for platform-specific setup)
- **Rust**: 1.70+ (MSRV)

## Table of Contents

- [Related Guides](#related-guides)
- [Core Pattern](#core-pattern)
- [Builder Methods Quick Reference](#builder-methods-quick-reference)
- [Input Configuration](#input-configuration)
- [Output Configuration](#output-configuration)
- [High-Frequency Examples](#high-frequency-examples)
- [Scenario Index](#scenario-index)
- [Installation](#installation)
- [Features](#features)

## Related Guides

| Guide | Content |
|-------|---------|
| [ffmpeg_next.md](ffmpeg_next.md) | Medium-level API for codec control |
| [ffmpeg_sys_next.md](ffmpeg_sys_next.md) | Low-level unsafe FFI |
| [installation.md](installation.md) | Platform-specific setup |

## Core Pattern

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Basic pipeline
    FfmpegContext::builder()
        .input(Input::from("input.mp4").set_input_opt("key", "value"))
        .filter_desc("scale=1280:720")  // Optional FFmpeg filter
        .output(Output::from("output.mp4").set_video_codec("libx264"))
        .build()?
        .start()?
        .wait()?;  // Blocks until completion

    Ok(())
}
```

### Async Pattern

For async workflows, enable the `async` feature:

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    FfmpegContext::builder()
        .input(Input::from("input.mp4"))
        .output(Output::from("output.mp4"))
        .build()?
        .start()?
        .await?;  // Non-blocking async

    Ok(())
}
```

## Builder Methods Quick Reference

| Method | Purpose | Example |
|--------|---------|---------|
| `input()` | Add single input | `.input("video.mp4")` |
| `inputs()` | Add multiple inputs | `.inputs(vec![input1, input2])` |
| `output()` | Add output | `.output("out.mp4")` |
| `filter_desc()` | FFmpeg filter string | `.filter_desc("scale=1280:720")` |
| `copyts()` | Preserve timestamps | `.copyts()` |
| `independent_readrate()` | Multi-input sync | `.independent_readrate()` |

## Input Configuration

The `input()` method accepts both string paths (`&str`, `String`) and `Input` objects via the `Into<Input>` trait.

```rust
use ez_ffmpeg::Input;
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ffmpeg_sys_next::AVMediaType;

// Simple string input
FfmpegContext::builder()
    .input("video.mp4")  // &str automatically converts to Input
    // ...

// Configured Input object
let input = Input::from("video.mp4")
    .set_format("mp4")                    // Force format
    .set_start_time_us(60_000_000)        // Start time in microseconds
    .set_recording_time_us(30_000_000)    // Recording duration in microseconds
    .set_stop_time_us(90_000_000)         // Stop time in microseconds
    .set_hwaccel("videotoolbox")          // Hardware acceleration
    .set_video_codec("h264_cuvid")        // Decoder
    .set_readrate(1.0);                   // Read rate control

// With custom frame pipeline (see filters.md for FrameFilter implementation)
let pipeline = FramePipelineBuilder::from(AVMediaType::AVMEDIA_TYPE_VIDEO)
    .filter("my_filter", Box::new(MyFrameFilter));
let input_with_pipeline = Input::from("video.mp4")
    .add_frame_pipeline(pipeline);
```

## Output Configuration

The `output()` method accepts both string paths (`&str`, `String`) and `Output` objects via the `Into<Output>` trait.

```rust
use ez_ffmpeg::Output;
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ffmpeg_sys_next::{AVMediaType, AVRational};

// Simple string output
FfmpegContext::builder()
    .input("input.mp4")
    .output("output.mp4")  // &str automatically converts to Output
    // ...

// Configured Output object
let output = Output::from("output.mp4")
    .set_format("mp4")                    // Container format
    .set_video_codec("libx264")           // Video encoder
    .set_video_codec_opt("preset", "fast") // Encoder option
    .set_video_codec_opt("crf", "23")     // Quality
    .set_audio_codec("aac")               // Audio encoder
    .set_audio_codec_opt("b", "128k")     // Audio bitrate
    .set_format_opt("t", "60")            // Duration limit
    .set_max_video_frames(1)              // Frame limit (thumbnails)
    .set_video_qscale(2)                  // Quality scale
    .set_framerate(AVRational { num: 30, den: 1 })  // Output framerate
    .set_pix_fmt("yuv420p")               // Output pixel format
    .set_start_time_us(0)                 // Output start time
    .set_recording_time_us(30_000_000)    // Output recording duration
    .set_stop_time_us(30_000_000)         // Output stop time
    .add_stream_map("0:v")                // Map video stream
    .add_stream_map("0:a")                // Map audio stream
    .add_stream_map_with_copy("0:a")      // Copy stream without re-encode
    .add_metadata("title", "My Video");   // Output metadata

// Stream disable flags (equivalent to FFmpeg's -vn, -an, -sn, -dn)
let audio_only = Output::from("audio.mp3")
    .disable_video();                     // Disable video, keep audio only

let video_only = Output::from("video.mp4")
    .disable_audio();                     // Disable audio, keep video only

// With custom frame pipeline (see filters.md for FrameFilter implementation)
let pipeline = FramePipelineBuilder::from(AVMediaType::AVMEDIA_TYPE_VIDEO)
    .filter("my_filter", Box::new(MyFrameFilter));
let output_with_pipeline = Output::from("output.mp4")
    .add_frame_pipeline(pipeline);
```

## High-Frequency Examples

**Transcoding** (format conversion):
```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output("output.mov")
    .build()?.start()?.wait()?;
```

**Async Processing** (requires `async` feature + tokio runtime):
```rust
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    FfmpegContext::builder()
        .input("input.mp4")
        .output("output.mp4")
        .build()?.start()?.await?;
    Ok(())
}
```

**Multi-Input with Timestamp Sync**:
```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

let input1 = Input::from("video1.mp4").set_readrate(1.0);
let input2 = Input::from("video2.mp4").set_readrate(1.0);
let output = Output::from("output.mp4")
    .set_video_codec("libx264");

FfmpegContext::builder()
    .copyts()                    // Preserve timestamps
    .independent_readrate()      // Sync multiple inputs
    .inputs(vec![input1, input2])
    .filter_desc("[0:v][1:v]overlay=10:10")
    .output(output)
    .build()?.start()?.wait()?;
```

## Scenario Index

| Scenario | File | Use Cases |
|----------|------|-----------|
| **CLI Migration** | [cli_migration.md](ez_ffmpeg/cli_migration.md) | FFmpeg CLI to Rust conversion, option mapping |
| Video Processing | [video.md](ez_ffmpeg/video.md) | Transcoding, clipping, merging, thumbnail, watermark |
| Audio Processing | [audio.md](ez_ffmpeg/audio.md) | Extraction, conversion, resampling |
| Streaming | [streaming.md](ez_ffmpeg/streaming.md) | RTMP push, HLS generation, re-streaming |
| Device Capture | [capture.md](ez_ffmpeg/capture.md) | Camera, microphone, screen capture |
| Media Query | [query.md](ez_ffmpeg/query.md) | Duration, metadata, codecs, devices |
| Filters | [filters.md](ez_ffmpeg/filters.md) | Built-in filters, custom FrameFilter, OpenGL |
| Advanced | [advanced.md](ez_ffmpeg/advanced.md) | Hardware accel, custom I/O, frame pipelines |

## Installation

> **Full installation guide**: See [installation.md](installation.md) for comprehensive platform-specific instructions, troubleshooting, Docker/CI configuration, and the `build` feature fallback.

### Quick Start

```toml
[dependencies]
ez-ffmpeg = { version = "0.10.0", features = ["async"] }
```

**System dependencies** (one-time setup, see [installation.md](installation.md) for complete list):
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install libavcodec-dev libavformat-dev libavutil-dev libavfilter-dev libavdevice-dev libswscale-dev libswresample-dev pkg-config clang`
- **Windows**: See [installation.md](installation.md) for vcpkg setup

**Feature options**:
```toml
# Static linking (Windows recommended)
ez-ffmpeg = { version = "0.10.0", features = ["async", "static"] }

# Build from source (last resort when system FFmpeg unavailable)
ez-ffmpeg = { version = "0.10.0", features = ["async", "build"] }
```

> See [installation.md](installation.md) for detailed `build` feature usage and license options (GPL, non-free).

## Features

| Feature | Purpose |
|---------|---------|
| `async` | Tokio async support |
| `rtmp` | Embedded high-concurrency RTMP server |
| `opengl` | GPU-accelerated filters |
| `static` | Static linking (Windows) |
