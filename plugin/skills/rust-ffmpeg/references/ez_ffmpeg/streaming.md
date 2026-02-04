# ez-ffmpeg: Streaming

**Detection Keywords**: rtmp server, stream output, hls output, live streaming, rtmp push, stream publish
**Aliases**: streaming output, live stream, rtmp embed

## Table of Contents

- [Related Guides](#related-guides)
- [Embedded High-Concurrency RTMP Server](#embedded-high-concurrency-rtmp-server)
  - [StreamBuilder API](#streambuilder-api)
  - [Traditional API (Full Control)](#traditional-api-full-control)
  - [External RTMP Server](#external-rtmp-server-no-rtmp-feature-needed)
- [RTMP Streaming](#rtmp-streaming)
- [Multi-Source Streaming](#multi-source-streaming)
- [RTMP Re-streaming](#rtmp-re-streaming)
- [HLS Generation](#hls-generation)
- [Live HLS Streaming](#live-hls-streaming)
- [Low-Latency Streaming Tips](#low-latency-streaming-tips)
- [Hardware-Accelerated Streaming](#hardware-accelerated-streaming)
- [Timestamp Preservation for Re-streaming](#timestamp-preservation-for-re-streaming)
- [SRT Streaming](#srt-streaming)
- [Async Streaming (with tokio)](#async-streaming-with-tokio)
- [Troubleshooting](#troubleshooting)

## Related Guides

| Guide | Content |
|-------|---------|
| [capture.md](capture.md) | Device capture (camera, screen) |
| [video.md](video.md) | Video transcoding, format conversion |
| [advanced.md](advanced.md) | Hardware acceleration, async processing |

## Embedded High-Concurrency RTMP Server

Enable with `features = ["rtmp"]`. Uses reactor pattern with edge-triggered IO (epoll/kqueue) for high-concurrency streaming.

**Architecture** (verified from source `src/rtmp/`):
- Thread model: 2 threads (accept thread + reactor thread)
- Reactor: Single-threaded event loop handling all connections
- Backpressure: 1MB warning, 2MB high, 4MB critical (disconnect)
- Max connections: Auto-detected from system FD limit (default 10000, capped at 80% of limit)

### StreamBuilder API

The simplest way to stream a file to an embedded RTMP server:

```rust
use ez_ffmpeg::rtmp::embed_rtmp_server::EmbedRtmpServer;

// Just 5 lines with clear, self-documenting parameters
let handle = EmbedRtmpServer::stream_builder()
    .address("localhost:1935")
    .app_name("my-app")
    .stream_key("my-stream")
    .input_file("video.mp4")
    // readrate defaults to 1.0 (realtime), no need to set explicitly
    .start()?;

handle.wait()?;
```

### Traditional API (Full Control)

Use when you need more control over the server, input, or FFmpeg context configuration:

```rust
use ez_ffmpeg::rtmp::embed_rtmp_server::EmbedRtmpServer;
use ez_ffmpeg::{FfmpegContext, Input, Output};

// 1. Create and start embedded RTMP server
let embed_rtmp_server = EmbedRtmpServer::new("localhost:1935")
    .start()?;

// 2. Create RTMP input (returns an Output that FFmpeg can push data into)
let output = embed_rtmp_server
    .create_rtmp_input("my-app", "my-stream")?;

// 3. Prepare input with builder pattern
let input = Input::from("video.mp4")
    .set_readrate(1.0);  // Optional: limit reading speed to 1x realtime

// 4. Build and run FFmpeg context
FfmpegContext::builder()
    .input(input)
    .output(output)
    .build()?.start()?.wait()?;
```

### External RTMP Server (No `rtmp` feature needed)

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

let input = Input::from("video.mp4")
    .set_readrate(1.0);

// RTMP requires FLV format with H.264 video and AAC audio
let output = Output::from("rtmp://localhost:1937/my-app/my-stream")
    .set_format("flv")
    .set_video_codec("libx264")
    .set_audio_codec("aac")
    .set_format_opt("flvflags", "no_duration_filesize");

FfmpegContext::builder()
    .input(input)
    .output(output)
    .build()?.start()?.wait()?;
```

**Note**: While the embedded RTMP server is production-capable with high-concurrency support, consider dedicated RTMP servers (nginx-rtmp, SRS) for very large-scale deployments.

## RTMP Streaming

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Push file to RTMP server
FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("rtmp://server/live/stream_key")
        .set_format("flv")
        .set_video_codec("libx264")
        .set_video_codec_opt("preset", "veryfast")
        .set_video_codec_opt("tune", "zerolatency")
        .set_audio_codec("aac")
        .set_audio_codec_opt("b", "128k"))
    .build()?.start()?.wait()?;

// With bitrate control (CBR for stable streaming)
FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("rtmp://server/live/stream_key")
        .set_format("flv")
        .set_video_codec("libx264")
        .set_video_codec_opt("b", "2500k")
        .set_video_codec_opt("maxrate", "2500k")
        .set_video_codec_opt("bufsize", "5000k")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;

// Real-time file streaming with read rate control
FfmpegContext::builder()
    .input(Input::from("video.mp4")
        .set_readrate(1.0))  // Read at 1x speed for real-time streaming
    .output(Output::from("rtmp://server/live/stream_key")
        .set_format("flv")
        .set_video_codec("libx264")
        .set_video_codec_opt("preset", "veryfast")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;
```

## Multi-Source Streaming

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Side-by-side streaming from two sources
FfmpegContext::builder()
    .input(Input::from("camera1.mp4").set_readrate(1.0))
    .input(Input::from("camera2.mp4").set_readrate(1.0))
    .independent_readrate()  // Sync multiple inputs independently
    .filter_desc("[0:v][1:v]hstack[outv]")
    .output(Output::from("rtmp://server/live/stream")
        .set_format("flv")
        .add_stream_map("outv")
        .set_video_codec("libx264")
        .set_video_codec_opt("preset", "veryfast"))
    .build()?.start()?.wait()?;

// Dynamic multi-source with hardware acceleration
// Note: Input::set_video_codec() specifies the DECODER (e.g., "h264" for hw decoding)
//       Output::set_video_codec() specifies the ENCODER (e.g., "libx264" for encoding)
let video_paths: Vec<(&str, &str, &str)> = vec![
    ("rtmp://source1/live/stream", "videotoolbox", "h264"),  // hwaccel + decoder
    ("rtmp://source2/live/stream", "", ""),
];

let inputs: Vec<Input> = video_paths.iter()
    .map(|(path, hwaccel, codec)| {
        let mut input = Input::from(*path).set_readrate(1.0);
        if !hwaccel.is_empty() {
            input = input.set_hwaccel(hwaccel);
        }
        if !codec.is_empty() {
            input = input.set_video_codec(codec);
        }
        input
    })
    .collect();

FfmpegContext::builder()
    .independent_readrate()
    .inputs(inputs)
    .filter_desc("[0:v][1:v]hstack[outv]")
    .output(Output::from("rtmp://server/live/combined")
        .set_format("flv")
        .add_stream_map("outv")
        .set_video_codec("libx264"))
    .build()?.start()?.wait()?;
```

## RTMP Re-streaming

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Pull from one RTMP and push to another
FfmpegContext::builder()
    .input(Input::from("rtmp://source/live/stream")
        .set_input_opt("live_start_index", "-1"))
    .output(Output::from("rtmp://destination/live/stream")
        .set_format("flv")
        .set_video_codec("copy")
        .set_audio_codec("copy"))
    .build()?.start()?.wait()?;
```

## HLS Generation

```rust
use ez_ffmpeg::{FfmpegContext, Output};

// Generate HLS with 4-second segments
FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("output/playlist.m3u8")
        .set_format("hls")
        .set_format_opt("hls_time", "4")
        .set_format_opt("hls_list_size", "0")  // Keep all segments
        .set_format_opt("hls_segment_filename", "output/segment_%03d.ts")
        .set_video_codec("libx264")
        .set_video_codec_opt("preset", "fast")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;

// HLS with multiple quality levels (manual)
// Create separate outputs for each quality level
FfmpegContext::builder()
    .input("video.mp4")
    .filter_desc("scale=1280:720")
    .output(Output::from("720p/playlist.m3u8")
        .set_format("hls")
        .set_format_opt("hls_time", "4")
        .set_video_codec("libx264")
        .set_video_codec_opt("b", "2500k"))
    .build()?.start()?.wait()?;
```

## Live HLS Streaming

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Live source to HLS
FfmpegContext::builder()
    .input(Input::from("rtmp://source/live/stream"))
    .output(Output::from("live/playlist.m3u8")
        .set_format("hls")
        .set_format_opt("hls_time", "2")
        .set_format_opt("hls_list_size", "5")  // Rolling window
        .set_format_opt("hls_flags", "delete_segments")
        .set_video_codec("libx264")
        .set_video_codec_opt("preset", "ultrafast")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;
```

## Low-Latency Streaming Tips

```rust
// Key settings for low latency:
Output::from("rtmp://server/live/stream")
    .set_video_codec("libx264")
    .set_video_codec_opt("preset", "ultrafast")  // Fastest encoding
    .set_video_codec_opt("tune", "zerolatency")  // Disable B-frames
    .set_video_codec_opt("g", "30")  // Keyframe every 30 frames
    .set_format_opt("flvflags", "no_duration_filesize")
```

## Hardware-Accelerated Streaming

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// NVIDIA NVENC for low-latency streaming
FfmpegContext::builder()
    .input(Input::from("video.mp4")
        .set_hwaccel("cuda"))
    .output(Output::from("rtmp://server/live/stream")
        .set_format("flv")
        .set_video_codec("h264_nvenc")
        .set_video_codec_opt("preset", "p1")  // Fastest NVENC preset
        .set_video_codec_opt("tune", "ll")    // Low latency
        .set_video_codec_opt("zerolatency", "1")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;

// macOS VideoToolbox
FfmpegContext::builder()
    .input(Input::from("video.mp4")
        .set_hwaccel("videotoolbox"))
    .output(Output::from("rtmp://server/live/stream")
        .set_format("flv")
        .set_video_codec("h264_videotoolbox")
        .set_video_codec_opt("realtime", "1")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;
```

## Timestamp Preservation for Re-streaming

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Preserve original timestamps when re-streaming
FfmpegContext::builder()
    .copyts()  // Copy timestamps from input
    .input(Input::from("rtmp://source/live/stream")
        .set_readrate(1.0))
    .output(Output::from("rtmp://destination/live/stream")
        .set_format("flv")
        .set_video_codec("copy")
        .set_audio_codec("copy"))
    .build()?.start()?.wait()?;
```

## SRT Streaming

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// SRT output (Secure Reliable Transport)
FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("srt://server:port?streamid=stream_key")
        .set_format("mpegts")
        .set_video_codec("libx264")
        .set_video_codec_opt("preset", "veryfast")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;

// SRT input to RTMP output
FfmpegContext::builder()
    .input(Input::from("srt://server:port?mode=caller"))
    .output(Output::from("rtmp://server/live/stream")
        .set_format("flv")
        .set_video_codec("copy")
        .set_audio_codec("copy"))
    .build()?.start()?.wait()?;
```

## Async Streaming (with tokio)

For async operations, enable the `async` feature and use `.await`:

> **Dependencies**:
> ```toml
> [dependencies]
> ez-ffmpeg = { version = "0.10.0", features = ["async"] }
> tokio = { version = "1", features = ["macros", "rt-multi-thread"] }
> ```

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    FfmpegContext::builder()
        .input("video.mp4")
        .output(Output::from("rtmp://server/live/stream")
            .set_format("flv")
            .set_video_codec("libx264")
            .set_audio_codec("aac"))
        .build()?.start()?.await?;
    Ok(())
}
```

## Troubleshooting

### Connection Issues

**RTMP connection refused**:
```
Error: Connection refused
```
- Verify RTMP server is running and accessible.
- Check firewall allows port 1935 (default RTMP port).
- Verify stream key and app name are correct.

**RTMP connection timeout**:
```
Error: Connection timed out
```
- Add timeout option: `.set_input_opt("timeout", "5000000")` (microseconds)
- Check network connectivity to server.
- For unstable networks, add reconnect options.

### Stream Quality Issues

**Choppy/stuttering playback**:
- Reduce encoding preset: `"ultrafast"` or `"veryfast"`
- Lower bitrate to match available bandwidth.
- Use CBR (constant bitrate) for stable streaming.
- Add buffer: `.set_video_codec_opt("bufsize", "5000k")`

**High latency**:
- Use `tune=zerolatency` to disable B-frames.
- Reduce keyframe interval: `.set_video_codec_opt("g", "30")`
- Use `preset=ultrafast` for fastest encoding.
- For HLS, reduce segment time: `.set_format_opt("hls_time", "1")`

**Audio/video sync issues**:
- Use `.copyts()` to preserve timestamps.
- For live streams with gaps: `.filter_desc("aresample=async=1")`
- Ensure consistent frame rate with `.filter_desc("fps=30")`

### Embedded RTMP Server Issues

**Port already in use**:
```
Error: Address already in use
```
- Check if another process is using port 1935.
- Use a different port: `EmbedRtmpServer::new("0.0.0.0:1936")`

**No stream received**:
- Verify OBS/encoder is pushing to correct URL: `rtmp://localhost:1935/app_name/stream_key`
- Check app name and stream key match `create_rtmp_input()` parameters.
- Ensure encoder starts before calling `create_rtmp_input()`.

### Hardware Acceleration Issues

**Encoder not found**:
```
Error: Encoder h264_nvenc not found
```
- Verify FFmpeg was compiled with hardware encoder support.
- Check GPU drivers are installed and up to date.
- For NVENC, ensure NVIDIA GPU is available.
- For VideoToolbox, only available on macOS.

**Hardware decode fails**:
- Not all codecs support hardware decode.
- Try without hwaccel first, then add if working.
- Some streams may have unsupported profiles.

