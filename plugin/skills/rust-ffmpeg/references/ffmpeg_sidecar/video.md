# ffmpeg-sidecar: Video Processing

**Detection Keywords**: sidecar video, frame extract, test source, video filter, encode video, decode video
**Aliases**: video sidecar, frame manipulation

Video encoding, decoding, frame manipulation, filters, and test sources with ffmpeg-sidecar.

> **Dependencies**: Examples use `anyhow` for error handling:
> ```toml
> [dependencies]
> ffmpeg-sidecar = "2.4.0"
> anyhow = "1"
> ```

## Related Guides

| Guide | Content |
|-------|---------|
| [audio.md](audio.md) | Audio extraction, mic capture |
| [streaming.md](streaming.md) | Named pipes, TCP sockets |
| [monitoring.md](monitoring.md) | Progress tracking, metadata |

## Basic Video Operations

### Extract Frames

Extract raw video frames for processing:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn extract_frames(input: &str) -> anyhow::Result<()> {
    let iter = FfmpegCommand::new()
        .input(input)
        .rawvideo()  // Output raw RGB24 frames
        .spawn()?
        .iter()?;

    for frame in iter.filter_frames() {
        println!("Frame {}: {}x{} @ {:.2}s",
                 frame.frame_num, frame.width, frame.height, frame.timestamp);

        // Access raw pixel data
        let pixels: &[u8] = &frame.data;
        let expected_size = (frame.width * frame.height * 3) as usize;
        assert_eq!(pixels.len(), expected_size);
    }

    Ok(())
}
```

### Video Transcoding

Convert between video formats:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn transcode_video(input: &str, output: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .input(input)
        .codec_video("libx264")
        .preset("medium")
        .crf(23)
        .codec_audio("aac")
        .output(output)
        .spawn()?
        .iter()?
        .for_each(|event| {
            if let ffmpeg_sidecar::event::FfmpegEvent::Progress(p) = event {
                println!("Progress: frame={}, fps={:.1}, speed={:.2}x",
                         p.frame, p.fps, p.speed);
            }
        });

    Ok(())
}
```

## Decode-Process-Encode Pipeline

Process video frames in Rust between decode and encode:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::{FfmpegEvent, LogLevel};
use std::io::Write;

fn process_video_pipeline(input: &str, output: &str) -> anyhow::Result<()> {
    // Decode to raw frames
    let mut decoder = FfmpegCommand::new()
        .input(input)
        .rawvideo()
        .spawn()?;

    let frames = decoder.iter()?.filter_frames();

    // Encode processed frames
    let mut encoder = FfmpegCommand::new()
        .args(["-f", "rawvideo", "-pix_fmt", "rgb24"])
        .args(["-s", "1920x1080", "-r", "30"])
        .input("-")
        .codec_video("libx265")
        .preset("medium")
        .overwrite()
        .output(output)
        .spawn()?;

    let mut stdin = encoder.take_stdin().unwrap();

    // Process frames synchronously (no threading needed)
    for frame in frames {
        let processed = process_frame(&frame.data, frame.width, frame.height);
        stdin.write_all(&processed)?;
    }
    drop(stdin);

    // Monitor encoding progress
    encoder.iter()?.for_each(|event| match event {
        FfmpegEvent::Progress(p) => {
            println!("Encoding: frame={}, fps={:.1}", p.frame, p.fps);
        }
        FfmpegEvent::Log(LogLevel::Error, msg) => {
            eprintln!("Error: {}", msg);
        }
        _ => {}
    });

    Ok(())
}

fn process_frame(data: &[u8], _width: u32, _height: u32) -> Vec<u8> {
    // Your processing logic here
    data.to_vec()
}
```

## Conway's Game of Life

Generate Conway's Game of Life animation (requires `ffplay` in PATH):

```rust
use std::process::Command;

fn game_of_life_preview() -> anyhow::Result<()> {
    Command::new("ffplay")
        .arg("-hide_banner")
        .arg("-f").arg("lavfi")
        .arg("-i").arg(
            "life=s=300x200:mold=10:r=60:ratio=0.08:\
             death_color=#C83232:life_color=#00ff00,\
             scale=1200:800:flags=16"
        )
        .spawn()?
        .wait()?;
    Ok(())
}
```

## Hardware Acceleration

### NVIDIA CUDA

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn encode_with_cuda(input: &str, output: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .hwaccel("cuda")
        .input(input)
        .codec_video("h264_nvenc")
        .preset("p4")
        .args(["-b:v", "5M"])
        .output(output)
        .spawn()?
        .iter()?
        .for_each(|_| {});
    Ok(())
}
```

See [Core API](core.md) for complete video processing reference.
