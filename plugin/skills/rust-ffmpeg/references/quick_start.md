# Quick Start Guide

**Detection Keywords**: quick start, getting started, first project, hello world, minimal example, setup guide
**Aliases**: quickstart, tutorial, beginner, introduction

Get started with Rust FFmpeg in 5 minutes.

## Choose Your Library

### Option 1: ez-ffmpeg

**Use when**: General use, async workflows, CLI migration, embedded RTMP server

```rust
// Sync version (simpler, no async runtime needed)
use ez_ffmpeg::FfmpegContext;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    FfmpegContext::builder()
        .input("input.mp4")
        .output("output.mp4")
        .build()?
        .start()?
        .wait()?;
    Ok(())
}
```

**Installation** (sync):
```toml
[dependencies]
ez-ffmpeg = "0.10.0"
```

**Async version** (requires `async` feature):
```rust
use ez_ffmpeg::FfmpegContext;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    FfmpegContext::builder()
        .input("input.mp4")
        .output("output.mp4")
        .build()?
        .start()?
        .await?;  // Non-blocking async
    Ok(())
}
```

**Installation** (async):
```toml
[dependencies]
ez-ffmpeg = { version = "0.10.0", features = ["async"] }
tokio = { version = "1", features = ["macros", "rt-multi-thread"] }
```

**Next steps**: [ez_ffmpeg.md](ez_ffmpeg.md)

---

### Option 2: ffmpeg-next

**Use when**: Frame-level control, codec-specific operations, mixing with ez-ffmpeg

```rust
use ffmpeg_next as ffmpeg;

fn main() -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    // Open input and get video stream info
    let ictx = ffmpeg::format::input(&"input.mp4")?;
    let input_stream = ictx.streams().best(ffmpeg::media::Type::Video)
        .ok_or(ffmpeg::Error::StreamNotFound)?;

    // Get decoder from stream parameters
    let context = ffmpeg::codec::context::Context::from_parameters(input_stream.parameters())?;
    let decoder = context.decoder().video()?;

    println!("Input: {}x{} @ {} fps",
        decoder.width(),
        decoder.height(),
        input_stream.avg_frame_rate());

    // For full transcoding with encode loop, see ffmpeg_next/transcoding.md
    Ok(())
}
```

**Installation**:
```toml
[dependencies]
ffmpeg-next = "7.1.0"
```

**Important**: ffmpeg-next requires explicit decode/encode loops for transcoding. The example above shows input inspection only. For complete transcoding with frame processing, see [ffmpeg_next/transcoding.md](ffmpeg_next/transcoding.md).

**Next steps**: [ffmpeg_next.md](ffmpeg_next.md)

---

### Option 3: ffmpeg-sys-next

**Use when**: Maximum performance, zero-copy operations

```rust
use ffmpeg_sys_next as ffmpeg;
use std::ptr;

fn main() {
    unsafe {
        // Note: av_register_all() is deprecated in FFmpeg 4+ and removed in FFmpeg 7+
        // Modern FFmpeg auto-registers codecs

        let mut fmt_ctx: *mut ffmpeg::AVFormatContext = ptr::null_mut();
        let filename = std::ffi::CString::new("input.mp4").unwrap();

        if ffmpeg::avformat_open_input(
            &mut fmt_ctx,
            filename.as_ptr(),
            ptr::null_mut(),
            ptr::null_mut()
        ) < 0 {
            panic!("Cannot open input file");
        }

        // Low-level FFI operations...

        ffmpeg::avformat_close_input(&mut fmt_ctx);
    }
}
```

**Installation**:
```toml
[dependencies]
ffmpeg-sys-next = "7.1.0"
```

**Next steps**: [ffmpeg_sys_next.md](ffmpeg_sys_next.md)

---

### Option 4: ffmpeg-sidecar

**Use when**: No FFmpeg installation required

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::FfmpegEvent;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    FfmpegCommand::new()
        .input("input.mp4")
        .output("output.mp4")
        .args(["-c:v", "libx264", "-crf", "23"])
        .spawn()?
        .wait()?;

    Ok(())
}
```

**Installation**:
```toml
[dependencies]
ffmpeg-sidecar = "2.4.0"
```

**Next steps**: [ffmpeg_sidecar.md](ffmpeg_sidecar.md)

---

## Common First Tasks

| Task | Library Options | Guide |
|------|-----------------|-------|
| Convert video format | ez-ffmpeg, ffmpeg-next, ffmpeg-sidecar | [video_transcoding.md](scenarios/video_transcoding.md) |
| Extract audio | ez-ffmpeg, ffmpeg-next, ffmpeg-sidecar | [audio_extraction.md](scenarios/audio_extraction.md) |
| Generate thumbnails | ez-ffmpeg, ffmpeg-next, ffmpeg-sidecar | [video_transcoding.md](scenarios/video_transcoding.md) |
| Stream to RTMP | ez-ffmpeg, ffmpeg-next, ffmpeg-sidecar | [streaming_rtmp_hls.md](scenarios/streaming_rtmp_hls.md) |
| Hardware encoding | All libraries | [hardware_acceleration.md](scenarios/hardware_acceleration.md) |
| Batch processing | ez-ffmpeg, ffmpeg-next, ffmpeg-sidecar | [batch_processing.md](scenarios/batch_processing.md) |

## Installation Help

See [installation.md](installation.md) for platform-specific FFmpeg installation instructions.
