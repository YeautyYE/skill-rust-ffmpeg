# Device Capture

**Detection Keywords**: screen capture, webcam, camera capture, record screen, screen recording, device capture, avfoundation, directshow, v4l2, microphone, desktop capture, capture device
**Aliases**: screen record, camera input, webcam capture, device recording, video capture

Capture video/audio from screen, webcam, and microphone across all Rust FFmpeg libraries.

## Quick Example (30 seconds)

```rust
// ez-ffmpeg — macOS webcam capture
use ez_ffmpeg::{FfmpegContext, Input, Output};

let input = Input::from("0:0")  // video:audio device indices
    .set_format("avfoundation")
    .set_input_opt("framerate", "30")
    .set_input_opt("video_size", "1280x720");

let scheduler = FfmpegContext::builder()
    .input(input)
    .output(Output::from("capture.mp4")
        .set_video_codec("libx264")
        .set_video_codec_opt("preset", "ultrafast")
        .set_audio_codec("aac"))
    .build()?.start()?;

// Record 10 seconds then stop
std::thread::sleep(std::time::Duration::from_secs(10));
scheduler.abort();
```

```rust
// ffmpeg-sidecar — macOS webcam capture
use ffmpeg_sidecar::command::FfmpegCommand;

FfmpegCommand::new()
    .args(["-f", "avfoundation", "-framerate", "30", "-video_size", "1280x720"])
    .input("0:0")
    .codec_video("libx264")
    .args(["-preset", "ultrafast"])
    .codec_audio("aac")
    .args(["-t", "10"])  // Record 10 seconds
    .output("capture.mp4")
    .spawn()?.wait()?;
```

## Library Comparison

| Aspect | ez-ffmpeg | ffmpeg-next | ffmpeg-sys-next | ffmpeg-sidecar |
|--------|-----------|-------------|-----------------|----------------|
| **Async support** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Graceful stop** | ✅ `abort()` | Manual signal | Manual signal | Process kill |
| **Device enumeration** | ✅ Built-in API | ❌ Manual | ❌ Manual | Via CLI args |
| **Code complexity** | Low | High | Very High | Low |
| **Use when** | General capture | Custom processing | Max performance | No install |

## Platform Device Formats

| Platform | Format | Video Device | Audio Device |
|----------|--------|-------------|-------------|
| macOS | `avfoundation` | `"0"` or device name | `"0"` or device name |
| Windows | `dshow` | `"video=Webcam Name"` | `"audio=Mic Name"` |
| Linux | `v4l2` + `alsa` | `"/dev/video0"` | `"hw:0"` |

## Common Patterns

### Screen capture (macOS)
```rust
// ez-ffmpeg
let input = Input::from("1:none")  // Screen device, no audio
    .set_format("avfoundation")
    .set_input_opt("framerate", "30")
    .set_input_opt("capture_cursor", "1");
```

### List available devices
```rust
// ez-ffmpeg — built-in device enumeration
use ez_ffmpeg::device::{get_input_video_devices, get_input_audio_devices};

let video_devices = get_input_video_devices()?;
let audio_devices = get_input_audio_devices()?;
```

### Capture + live stream simultaneously
```rust
// ez-ffmpeg — dual output: file + RTMP
let input = Input::from("0:0")
    .set_format("avfoundation")
    .set_input_opt("framerate", "30");

FfmpegContext::builder()
    .input(input)
    .output(Output::from("recording.mp4")   // High quality file
        .set_video_codec("libx264")
        .set_video_codec_opt("crf", "18")
        .set_audio_codec("aac"))
    .output(Output::from("rtmp://server/live/key")  // Low latency stream
        .set_format("flv")
        .set_video_codec("libx264")
        .set_video_codec_opt("preset", "ultrafast")
        .set_video_codec_opt("tune", "zerolatency")
        .set_audio_codec("aac"))
    .build()?.start()?;
```

### Cross-platform capture
```rust
fn create_capture_input() -> Input {
    #[cfg(target_os = "macos")]
    { Input::from("0:0").set_format("avfoundation")
        .set_input_opt("framerate", "30").set_input_opt("video_size", "1280x720") }

    #[cfg(target_os = "windows")]
    { Input::from("video=Integrated Webcam:audio=Microphone").set_format("dshow")
        .set_input_opt("framerate", "30").set_input_opt("video_size", "1280x720") }

    #[cfg(target_os = "linux")]
    { Input::from("/dev/video0").set_format("v4l2")
        .set_input_opt("framerate", "30").set_input_opt("video_size", "1280x720") }
}
```

## Capture Tips

- **Always use `ultrafast` preset** for real-time capture — encoding must keep up with input framerate
- **Hardware encoding** (`h264_videotoolbox` on macOS, `h264_nvenc` on NVIDIA) reduces CPU load significantly
- **`abort()` is safe** in ez-ffmpeg — output file is valid up to the abort point
- **Separate video/audio devices** when built-in combo device has quality issues

## Detailed Examples

- **ez-ffmpeg**: [ez_ffmpeg/capture.md](../ez_ffmpeg/capture.md) — full platform coverage, hardware-accelerated capture, overlay, dual output
- **ffmpeg-sidecar**: [ffmpeg_sidecar/video.md](../ffmpeg_sidecar/video.md) — CLI wrapper capture

## Related Scenarios

- [Streaming (RTMP & HLS)](streaming_rtmp_hls.md) — stream captured content
- [Hardware Acceleration](hardware_acceleration.md) — GPU-accelerated encoding for capture
