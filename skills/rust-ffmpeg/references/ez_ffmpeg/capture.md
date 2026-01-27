# ez-ffmpeg: Device Capture

**Detection Keywords**: screen capture, camera capture, webcam, avfoundation, device input, record screen, microphone input
**Aliases**: capture device, screen recording, camera input

## Related Guides

| Guide | Content |
|-------|---------|
| [video.md](video.md) | Video transcoding, format conversion, clipping |
| [streaming.md](streaming.md) | RTMP server, streaming output |
| [advanced.md](advanced.md) | Hardware acceleration, async processing |

## macOS: AVFoundation

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Capture camera + microphone (by device index)
let input = Input::from("0:0")  // video:audio device indices
    .set_format("avfoundation")
    .set_input_opt("framerate", "30")
    .set_input_opt("video_size", "1280x720");

// Capture by device name
let input = Input::from("FaceTime HD Camera:Built-in Microphone")
    .set_format("avfoundation")
    .set_input_opt("framerate", "30")
    .set_input_opt("video_size", "1280x720");

// Screen capture (device index 1 is typically screen)
let input = Input::from("1:none")  // Screen only, no audio
    .set_format("avfoundation")
    .set_input_opt("framerate", "30")
    .set_input_opt("capture_cursor", "1");

let output = Output::from("capture.mp4")
    .set_video_codec("libx264")
    .set_video_codec_opt("preset", "ultrafast")
    .set_audio_codec("aac");

let scheduler = FfmpegContext::builder()
    .input(input)
    .output(output)
    .build()?.start()?;

// Record for 10 seconds then stop
// Note: abort() immediately stops processing. For capture scenarios,
// the output file will be valid up to the point of abort.
std::thread::sleep(std::time::Duration::from_secs(10));
scheduler.abort();
```

## Windows: DirectShow

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Capture camera + microphone (by device name)
let input = Input::from("video=Integrated Webcam:audio=Microphone")
    .set_format("dshow")
    .set_input_opt("framerate", "30")
    .set_input_opt("video_size", "1280x720");

let output = Output::from("capture.mp4")
    .set_video_codec("libx264")
    .set_video_codec_opt("preset", "ultrafast")
    .set_audio_codec("aac");

let scheduler = FfmpegContext::builder()
    .input(input)
    .output(output)
    .build()?.start()?;

// Record for duration then stop capture
std::thread::sleep(std::time::Duration::from_secs(10));
scheduler.abort();
```

## Linux: V4L2 + ALSA

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Video from V4L2
let video_input = Input::from("/dev/video0")
    .set_format("v4l2")
    .set_input_opt("framerate", "30")
    .set_input_opt("video_size", "1280x720");

// Audio from ALSA
let audio_input = Input::from("hw:0")
    .set_format("alsa");

let output = Output::from("capture.mp4")
    .set_video_codec("libx264")
    .set_video_codec_opt("preset", "ultrafast")
    .set_audio_codec("aac");

let scheduler = FfmpegContext::builder()
    .input(video_input)
    .input(audio_input)
    .output(output)
    .build()?.start()?;

std::thread::sleep(std::time::Duration::from_secs(10));
scheduler.abort();
```

## Cross-Platform Pattern

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

fn create_capture_input() -> Input {
    #[cfg(target_os = "macos")]
    {
        Input::from("0:0")
            .set_format("avfoundation")
            .set_input_opt("framerate", "30")
            .set_input_opt("video_size", "1280x720")
    }

    #[cfg(target_os = "windows")]
    {
        Input::from("video=Integrated Webcam:audio=Microphone")
            .set_format("dshow")
            .set_input_opt("framerate", "30")
            .set_input_opt("video_size", "1280x720")
    }

    #[cfg(target_os = "linux")]
    {
        Input::from("/dev/video0")
            .set_format("v4l2")
            .set_input_opt("framerate", "30")
            .set_input_opt("video_size", "1280x720")
    }
}
```

## List Available Devices

For device enumeration, see [query.md](query.md#list-capture-devices).

```rust
use ez_ffmpeg::device::{get_input_video_devices, get_input_audio_devices};

// List video capture devices (returns Vec<String>)
let video_devices = get_input_video_devices()?;
for device in video_devices {
    println!("Video device: {}", device);
}

// List audio capture devices (returns Vec<String>)
let audio_devices = get_input_audio_devices()?;
for device in audio_devices {
    println!("Audio device: {}", device);
}
```

## Live Streaming from Capture

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Capture and stream to RTMP
let input = Input::from("0:0")
    .set_format("avfoundation")
    .set_input_opt("framerate", "30")
    .set_input_opt("video_size", "1280x720");

let output = Output::from("rtmp://server/live/stream_key")
    .set_format("flv")
    .set_video_codec("libx264")
    .set_video_codec_opt("preset", "ultrafast")
    .set_video_codec_opt("tune", "zerolatency")
    .set_audio_codec("aac");

FfmpegContext::builder()
    .input(input)
    .output(output)
    .build()?.start()?.wait()?;
```

## Separate Video and Audio Devices

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// macOS: Capture video and audio from separate devices
let video_input = Input::from("FaceTime HD Camera")
    .set_format("avfoundation")
    .set_input_opt("framerate", "30")
    .set_input_opt("video_size", "1920x1080");

let audio_input = Input::from("MacBook Pro Microphone")
    .set_format("avfoundation");

let output = Output::from("capture.mp4")
    .add_stream_map("0:v")
    .add_stream_map("1:a")
    .set_video_codec("libx264")
    .set_video_codec_opt("preset", "ultrafast")
    .set_audio_codec("aac");

let scheduler = FfmpegContext::builder()
    .input(video_input)
    .input(audio_input)
    .output(output)
    .build()?.start()?;
```

## Hardware-Accelerated Capture

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// macOS: VideoToolbox encoding for capture
let input = Input::from("0:0")
    .set_format("avfoundation")
    .set_input_opt("framerate", "30")
    .set_input_opt("video_size", "1920x1080")
    .set_input_opt("pixel_format", "uyvy422");

let output = Output::from("capture.mp4")
    .set_video_codec("h264_videotoolbox")
    .set_video_codec_opt("realtime", "1")
    .set_audio_codec("aac");

FfmpegContext::builder()
    .input(input)
    .output(output)
    .build()?.start()?;

// Windows: NVENC encoding for capture
let input = Input::from("video=Webcam:audio=Microphone")
    .set_format("dshow")
    .set_input_opt("framerate", "30");

let output = Output::from("capture.mp4")
    .set_video_codec("h264_nvenc")
    .set_video_codec_opt("preset", "p1")
    .set_audio_codec("aac");

FfmpegContext::builder()
    .input(input)
    .output(output)
    .build()?.start()?;
```

## Capture with Preview (Dual Output)

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Record to file while streaming preview
let input = Input::from("0:0")
    .set_format("avfoundation")
    .set_input_opt("framerate", "30");

// File output (high quality)
let file_output = Output::from("recording.mp4")
    .set_video_codec("libx264")
    .set_video_codec_opt("crf", "18")
    .set_audio_codec("aac");

// Preview output (low latency)
let preview_output = Output::from("rtmp://localhost/preview/stream")
    .set_format("flv")
    .set_video_codec("libx264")
    .set_video_codec_opt("preset", "ultrafast")
    .set_video_codec_opt("tune", "zerolatency")
    .set_audio_codec("aac");

FfmpegContext::builder()
    .input(input)
    .output(file_output)
    .output(preview_output)
    .build()?.start()?;
```

## Capture with Overlay

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Add watermark to capture
let camera_input = Input::from("0:0")
    .set_format("avfoundation")
    .set_input_opt("framerate", "30");

let watermark_input = Input::from("logo.png");

FfmpegContext::builder()
    .input(camera_input)
    .input(watermark_input)
    .filter_desc("[0:v][1:v]overlay=W-w-10:H-h-10[outv]")
    .output(Output::from("capture_with_logo.mp4")
        .add_stream_map("outv")
        .add_stream_map("0:a")
        .set_video_codec("libx264")
        .set_audio_codec("aac"))
    .build()?.start()?;
```
