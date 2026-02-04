# ez-ffmpeg: Advanced Features

**Detection Keywords**: hardware acceleration, async processing, tokio, gpu encoding, videotoolbox, nvenc, qsv
**Aliases**: hwaccel, gpu encode, async ffmpeg

## Prerequisites

- ez-ffmpeg 0.10.0+ with FFmpeg 7.x
- For hardware acceleration: GPU drivers and codec support
  - macOS: VideoToolbox (built-in)
  - Linux: VAAPI/NVENC drivers
  - Windows: NVENC/QSV drivers
- For async: tokio runtime

## Table of Contents

- [Related Guides](#related-guides)
- [Hardware Acceleration](#hardware-acceleration)
- [Custom I/O Sources](#custom-io-sources)
- [Progress Monitoring](#progress-monitoring)
- [Mixing with ffmpeg-next](#mixing-with-ffmpeg-next)
- [Abort/Cancel Processing](#abortcancel-processing)
- [Scheduler State Management](#scheduler-state-management)
- [Null Output (Processing Without File)](#null-output-processing-without-file)
- [Channel-Based Frame Pipeline](#channel-based-frame-pipeline)
- [Multiple Outputs](#multiple-outputs)
- [Limitations & When to Use ffmpeg-next](#limitations--when-to-use-ffmpeg-next)
- [Error Handling](#error-handling)
- [Troubleshooting](#troubleshooting)

## Related Guides

| Guide | Content |
|-------|---------|
| [video.md](video.md) | Video transcoding, format conversion |
| [streaming.md](streaming.md) | RTMP server, streaming output |
| [filters.md](filters.md) | FFmpeg filters, custom filters |

## Hardware Acceleration

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// macOS VideoToolbox
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_hwaccel("videotoolbox"))
    .output(Output::from("output.mp4")
        .set_video_codec("h264_videotoolbox"))
    .build()?.start()?.wait()?;

// NVIDIA NVENC (CUDA)
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_hwaccel("cuda"))
    .output(Output::from("output.mp4")
        .set_video_codec("h264_nvenc")
        .set_video_codec_opt("preset", "p4")
        .set_video_codec_opt("rc", "vbr"))
    .build()?.start()?.wait()?;

// Intel Quick Sync (QSV)
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_hwaccel("qsv"))
    .output(Output::from("output.mp4")
        .set_video_codec("h264_qsv"))
    .build()?.start()?.wait()?;

// AMD AMF (Windows/Linux with Vulkan)
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_hwaccel("vulkan"))
    .output(Output::from("output.mp4")
        .set_video_codec("h264_amf"))
    .build()?.start()?.wait()?;

// Windows D3D12VA (DirectX 12)
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_hwaccel("d3d12va"))
    .output(Output::from("output.mp4")
        .set_video_codec("h264_mf"))  // Media Foundation encoder
    .build()?.start()?.wait()?;
```

**Hardware Encoder Summary**:
| Platform | Decoder (hwaccel) | Encoder |
|----------|-------------------|---------|
| macOS | `videotoolbox` | `h264_videotoolbox` |
| NVIDIA | `cuda` | `h264_nvenc` |
| Intel | `qsv` | `h264_qsv` |
| AMD | `vulkan` | `h264_amf` |
| Windows | `d3d12va` | `h264_mf` |

## Custom I/O Sources

Use callback-based I/O for non-file sources. Callbacks return `i32` directly (bytes read/written, 0 for EOF, negative for error).

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};
use std::sync::{Arc, Mutex};

// Custom input using read callback
// Assume video_bytes: Vec<u8> contains your video data
let video_bytes: Vec<u8> = std::fs::read("input.mp4")?;
let data = Arc::new(Mutex::new(video_bytes));
let position = Arc::new(Mutex::new(0usize));

let data_clone = data.clone();
let pos_clone = position.clone();

let input = Input::new_by_read_callback(move |buf: &mut [u8]| {
    let data = data_clone.lock().unwrap();
    let mut pos = pos_clone.lock().unwrap();

    // EOF: return AVERROR_EOF when all data has been read
    if *pos >= data.len() {
        return ffmpeg_sys_next::AVERROR_EOF;
    }

    let remaining = &data[*pos..];
    let len = std::cmp::min(buf.len(), remaining.len());
    buf[..len].copy_from_slice(&remaining[..len]);
    *pos += len;
    len as i32  // Return bytes read
});

FfmpegContext::builder()
    .input(input.set_format("mp4"))
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

```rust
// Custom output using write callback
use ez_ffmpeg::{FfmpegContext, Output};
use std::sync::{Arc, Mutex};
use std::fs::File;
use std::io::Write;

let file = Arc::new(Mutex::new(File::create("output.mp4")?));
let file_clone = file.clone();

let output = Output::new_by_write_callback(move |buf: &[u8]| {
    let mut f = file_clone.lock().unwrap();
    match f.write_all(buf) {
        Ok(_) => buf.len() as i32,  // Return bytes written
        Err(_) => -1,  // Return negative for error
    }
}).set_format("mp4");

FfmpegContext::builder()
    .input("input.mp4")
    .output(output)
    .build()?.start()?.wait()?;
```

```rust
// Custom output with seek callback (for seekable outputs)
use ez_ffmpeg::{FfmpegContext, Output};
use std::sync::{Arc, Mutex};
use std::fs::File;
use std::io::{Write, Seek, SeekFrom};

let file = Arc::new(Mutex::new(File::create("output.mp4")?));
let file_write = file.clone();
let file_seek = file.clone();

let output = Output::new_by_write_callback(move |buf: &[u8]| {
    let mut f = file_write.lock().unwrap();
    match f.write_all(buf) {
        Ok(_) => buf.len() as i32,
        Err(_) => -1,
    }
})
.set_format("mp4")
.set_seek_callback(move |offset, whence| {
    let mut f = file_seek.lock().unwrap();
    let pos = match whence {
        0 => SeekFrom::Start(offset as u64),
        1 => SeekFrom::Current(offset),
        2 => SeekFrom::End(offset),
        _ => return -1,
    };
    f.seek(pos).map(|p| p as i64).unwrap_or(-1)
});

FfmpegContext::builder()
    .input("input.mp4")
    .output(output)
    .build()?.start()?.wait()?;
```

```rust
// Complete seek callback with AVSEEK_SIZE and AVSEEK_FLAG_BYTE handling
// Required for formats that need to query file size or use byte-based seeking
// Note: Requires `ffmpeg-sys-next` dependency for FFmpeg constants
use ez_ffmpeg::{FfmpegContext, Input, Output};
use std::sync::{Arc, Mutex};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom, Write};

// Input with seek callback (handles AVSEEK_SIZE for file size queries)
let input_file = Arc::new(Mutex::new(File::open("input.mp4")?));
let input_read = input_file.clone();
let input_seek = input_file.clone();

let input = Input::new_by_read_callback(move |buf: &mut [u8]| {
    let mut f = input_read.lock().unwrap();
    match f.read(buf) {
        Ok(n) => n as i32,
        Err(_) => -1,
    }
})
.set_format("mp4")
.set_seek_callback(move |offset, whence| {
    let mut f = input_seek.lock().unwrap();

    // Handle AVSEEK_SIZE: FFmpeg queries total file size
    if whence == ffmpeg_sys_next::AVSEEK_SIZE {
        return f.metadata()
            .map(|m| m.len() as i64)
            .unwrap_or(ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO) as i64);
    }

    // Handle standard seek modes
    let pos = match whence {
        ffmpeg_sys_next::SEEK_SET => SeekFrom::Start(offset as u64),
        ffmpeg_sys_next::SEEK_CUR => SeekFrom::Current(offset),
        ffmpeg_sys_next::SEEK_END => SeekFrom::End(offset),
        _ => return ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::ESPIPE) as i64,
    };
    f.seek(pos).map(|p| p as i64).unwrap_or(-1)
});

// Output with seek callback (handles AVSEEK_FLAG_BYTE for byte-based seeking)
let output_file = Arc::new(Mutex::new(File::create("output.mp4")?));
let output_write = output_file.clone();
let output_seek = output_file.clone();

let output = Output::new_by_write_callback(move |buf: &[u8]| {
    let mut f = output_write.lock().unwrap();
    match f.write_all(buf) {
        Ok(_) => buf.len() as i32,
        Err(_) => -1,
    }
})
.set_format("mp4")
.set_seek_callback(move |offset, whence| {
    let mut f = output_seek.lock().unwrap();

    // Handle AVSEEK_SIZE: return file size
    if whence == ffmpeg_sys_next::AVSEEK_SIZE {
        return f.metadata()
            .map(|m| m.len() as i64)
            .unwrap_or(-1);
    }

    // Handle AVSEEK_FLAG_BYTE: byte-based absolute seek
    if whence == ffmpeg_sys_next::AVSEEK_FLAG_BYTE {
        return f.seek(SeekFrom::Start(offset as u64))
            .map(|p| p as i64)
            .unwrap_or(-1);
    }

    // Handle standard seek modes
    let pos = match whence {
        ffmpeg_sys_next::SEEK_SET => SeekFrom::Start(offset as u64),
        ffmpeg_sys_next::SEEK_CUR => SeekFrom::Current(offset),
        ffmpeg_sys_next::SEEK_END => SeekFrom::End(offset),
        _ => return -1,
    };
    f.seek(pos).map(|p| p as i64).unwrap_or(-1)
});

FfmpegContext::builder()
    .input(input)
    .output(output)
    .build()?.start()?.wait()?;
```

## Progress Monitoring

Progress monitoring uses a custom FrameFilter:

```rust
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ez_ffmpeg::{FfmpegContext, Output};
use ez_ffmpeg::container_info::get_duration_us;
use ffmpeg_next::Frame;
use ffmpeg_sys_next::{AVMediaType, AVRational};
use std::sync::Arc;

struct ProgressTracker {
    total_duration: i64,
    time_base: AVRational,
}

impl ProgressTracker {
    fn print_progress(&self, frame: &Frame) {
        if let Some(pts) = frame.pts() {
            if self.time_base.den == 0 { return; }
            let current = pts as f64 * self.time_base.num as f64 / self.time_base.den as f64;
            let total = self.total_duration as f64 / 1_000_000.0;
            let progress = (current / total * 100.0).min(100.0);
            println!("Progress: {:.1}%", progress);
        }
    }
}

struct ProgressFilter { tracker: Arc<ProgressTracker> }

impl FrameFilter for ProgressFilter {
    fn media_type(&self) -> AVMediaType { AVMediaType::AVMEDIA_TYPE_VIDEO }
    fn filter_frame(&mut self, frame: Frame, _: &FrameFilterContext) -> Result<Option<Frame>, String> {
        self.tracker.print_progress(&frame);
        Ok(Some(frame))
    }
}

// Usage
let tracker = Arc::new(ProgressTracker {
    total_duration: get_duration_us("input.mp4")?,
    time_base: AVRational { num: 1, den: 25 },  // Adjust based on stream info
});

let pipeline = FramePipelineBuilder::from(AVMediaType::AVMEDIA_TYPE_VIDEO)
    .filter("progress", Box::new(ProgressFilter { tracker }));

FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4").add_frame_pipeline(pipeline))
    .build()?.start()?.wait()?;
```

## Mixing with ffmpeg-next

For operations ez-ffmpeg doesn't expose directly, use ffmpeg-next (re-exported):

```rust
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ffmpeg_next::Frame;
use ffmpeg_sys_next::AVMediaType;

// Note: For advanced operations, add ffmpeg-next as a direct dependency
// For advanced operations, add ffmpeg-next as a direct dependency

struct CustomVideoFilter {
    // Custom state
}

impl FrameFilter for CustomVideoFilter {
    fn media_type(&self) -> AVMediaType {
        AVMediaType::AVMEDIA_TYPE_VIDEO
    }

    fn filter_frame(
        &mut self,
        frame: Frame,
        ctx: &FrameFilterContext,
    ) -> Result<Option<Frame>, String> {
        // Access frame data for custom processing
        // frame.data(), frame.linesize(), etc.
        Ok(Some(frame))
    }
}
```

## Abort/Cancel Processing

```rust
use ez_ffmpeg::FfmpegContext;
use std::thread;
use std::time::Duration;

let scheduler = FfmpegContext::builder()
    .input("long_video.mp4")
    .output("output.mp4")
    .build()?.start()?;

// Run in background, abort after condition
thread::spawn(move || {
    thread::sleep(Duration::from_secs(30));
    scheduler.abort();  // Cancel processing
});

// Or wait for completion
scheduler.wait()?;
```

## Scheduler State Management

```rust
use ez_ffmpeg::FfmpegContext;
use ez_ffmpeg::core::scheduler::ffmpeg_scheduler::Running;

// The scheduler has a Running state after start()
let scheduler = FfmpegContext::builder()
    .input("input.mp4")
    .output("output.mp4")
    .build()?.start()?;

// Check if processing has ended
loop {
    if scheduler.is_ended() {
        println!("Processing completed");
        break;
    }
    // Do other work...
    std::thread::sleep(std::time::Duration::from_millis(100));
}

// Abort if needed
scheduler.abort();
```

## Null Output (Processing Without File)

For frame processing without writing to file:

```rust
use ez_ffmpeg::{FfmpegContext, Input};
use ez_ffmpeg::core::context::null_output::create_null_output;
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ffmpeg_next::Frame;
use ffmpeg_sys_next::AVMediaType;

// Define a frame processor
struct FrameCounter {
    count: u64,
}

impl FrameFilter for FrameCounter {
    fn media_type(&self) -> AVMediaType {
        AVMediaType::AVMEDIA_TYPE_VIDEO
    }

    fn filter_frame(
        &mut self,
        frame: Frame,
        _ctx: &FrameFilterContext,
    ) -> Result<Option<Frame>, String> {
        self.count += 1;
        println!("Processed frame {}", self.count);
        Ok(Some(frame))
    }
}

// Process frames without creating output file
let pipeline = FramePipelineBuilder::from(AVMediaType::AVMEDIA_TYPE_VIDEO)
    .filter("counter", Box::new(FrameCounter { count: 0 }));

FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .add_frame_pipeline(pipeline))
    .output(create_null_output().set_format("null"))
    .build()?.start()?.wait()?;
```

## Channel-Based Frame Pipeline

For complex frame routing between multiple FFmpeg contexts:

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ez_ffmpeg::core::context::null_output::create_null_output;
use ffmpeg_next::Frame;
use ffmpeg_sys_next::AVMediaType;
use crossbeam_channel::{bounded, Receiver, Sender};

// Create channel for frame passing
let (tx, rx): (Sender<Frame>, Receiver<Frame>) = bounded(10);

// Source context: read and send frames
struct FrameSender { tx: Sender<Frame> }
impl FrameFilter for FrameSender {
    fn media_type(&self) -> AVMediaType { AVMediaType::AVMEDIA_TYPE_VIDEO }
    fn filter_frame(&mut self, frame: Frame, _: &FrameFilterContext) -> Result<Option<Frame>, String> {
        let _ = self.tx.send(frame.clone());
        Ok(Some(frame))
    }
}

// Run source in a thread
let source_handle = std::thread::spawn(move || -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    FfmpegContext::builder()
        .input(Input::from("input.mp4")
            .add_frame_pipeline(FramePipelineBuilder::from(AVMediaType::AVMEDIA_TYPE_VIDEO)
                .filter("sender", Box::new(FrameSender { tx }))))
        .output(create_null_output())
        .build()?.start()?.wait()?;
    Ok(())
});

// Process received frames in another context or thread
while let Ok(frame) = rx.recv() {
    // Process frame...
}

// Wait for source thread to complete
let _ = source_handle.join();
```

## Multiple Outputs

```rust
use ez_ffmpeg::{FfmpegContext, Output};

// Generate multiple resolutions
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output_1080p.mp4")
        .set_video_codec("libx264"))
    .output(Output::from("output_720p.mp4")
        .set_video_codec("libx264"))
    .build()?.start()?.wait()?;

// Note: For different resolutions, use filter_complex or separate runs
```

## Limitations & When to Use ffmpeg-next

ez-ffmpeg doesn't expose:

1. **Fine-grained codec control**
   - Custom GOP size, B-frame settings
   - → Add `ffmpeg-next` dependency for `ffmpeg_next::encoder::video::Video`

2. **Format-specific operations**
   - Custom demuxer/muxer behavior
   - → Use `ffmpeg_next::format::context`

3. **Pixel/sample format conversion**
   - Direct sws_scale access
   - → Use `ffmpeg_next::software::{scaling, resampling}`

4. **Zero-copy operations**
   - Bypass abstraction overhead
   - → Use `ffmpeg_sys_next` with unsafe

## Error Handling

```rust
use ez_ffmpeg::FfmpegContext;

// Pattern 1: Match-based error handling
match FfmpegContext::builder()
    .input("input.mp4")
    .output("output.mp4")
    .build()
{
    Ok(ctx) => {
        match ctx.start() {
            Ok(scheduler) => {
                if let Err(e) = scheduler.wait() {
                    eprintln!("Processing error: {}", e);
                }
            }
            Err(e) => eprintln!("Start error: {}", e),
        }
    }
    Err(e) => eprintln!("Build error: {}", e),
}

// Pattern 2: Using ? operator (recommended)
fn process_video() -> Result<(), Box<dyn std::error::Error>> {
    FfmpegContext::builder()
        .input("input.mp4")
        .output("output.mp4")
        .build()?
        .start()?
        .wait()?;
    Ok(())
}

// Pattern 3: With cleanup on error
fn process_with_cleanup() -> Result<(), Box<dyn std::error::Error>> {
    let scheduler = FfmpegContext::builder()
        .input("input.mp4")
        .output("output.mp4")
        .build()?
        .start()?;

    // If wait fails, scheduler is dropped and resources are cleaned up
    match scheduler.wait() {
        Ok(_) => Ok(()),
        Err(e) => {
            // Cleanup temporary files if needed
            let _ = std::fs::remove_file("output.mp4");
            Err(e.into())
        }
    }
}
```

## Troubleshooting

### Common Build Errors

**Input file not found**:
```
Error: No such file or directory
```
- Verify file path is correct and file exists.
- Use absolute paths for reliability.
- Check file permissions.

**Codec not found**:
```
Error: Encoder libx264 not found
```
- FFmpeg may not be compiled with the codec.
- Run `ffmpeg -encoders` to list available encoders.
- Install FFmpeg with required codecs or use vcpkg with codec features.

**Format not recognized**:
```
Error: Invalid data found when processing input
```
- File may be corrupted or incomplete.
- Try specifying format explicitly: `.set_format("mp4")`
- For raw streams, specify format and codec.

### Runtime Errors

**Out of memory**:
- Reduce resolution or quality settings.
- Process in chunks for large files.
- Use hardware acceleration to offload GPU.

**Permission denied on output**:
- Check write permissions for output directory.
- Ensure output file is not locked by another process.
- On Windows, check antivirus is not blocking.

### Custom I/O Errors

**Read callback returns wrong size**:
- Return value must match bytes actually read.
- Return 0 for EOF, negative for error.
- Ensure thread-safe access to shared data.

**Seek callback issues**:
- Return new position on success, -1 on error.
- Handle all whence values (0=SEEK_SET, 1=SEEK_CUR, 2=SEEK_END).
- Some formats require seeking; use non-seekable format if not supported.

### Performance Issues

**Slow encoding**:
- Use faster preset: `"ultrafast"` or `"veryfast"`
- Enable hardware acceleration.
- Reduce output resolution or quality.

**High CPU usage**:
- Limit threads: `.set_video_codec_opt("threads", "4")`
- Use hardware encoding (NVENC, VideoToolbox, QSV).
- Process during off-peak hours for batch jobs.

