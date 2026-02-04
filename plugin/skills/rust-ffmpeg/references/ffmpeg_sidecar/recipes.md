# ffmpeg-sidecar: Recipes

**Detection Keywords**: quick start, example, recipe, frame iteration, basic usage, simple example
**Aliases**: recipes, examples, cookbook

Quick-start recipes for common ffmpeg-sidecar use cases.

> **Dependencies**: Examples use `anyhow` for error handling (following ffmpeg-sidecar's official examples):
> ```toml
> [dependencies]
> ffmpeg-sidecar = "2.4.0"
> anyhow = "1"
> ```

## Related Guides

| Guide | Content |
|-------|---------|
| [core.md](core.md) | Core API (FfmpegCommand, FfmpegChild) |
| [video.md](video.md) | Video encoding, decoding, filters |
| [audio.md](audio.md) | Audio extraction, mic capture |

## Hello World

The simplest ffmpeg-sidecar example - iterate over frames from a test source:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn main() -> anyhow::Result<()> {
    // Run an FFmpeg command that generates a test video
    let iter = FfmpegCommand::new() // Builder API like `std::process::Command`
        .testsrc()  // Discoverable aliases for FFmpeg args
        .rawvideo() // Convenient argument presets
        .spawn()?   // Ordinary `std::process::Child`
        .iter()?;   // Blocking iterator over logs and output

    // Use a regular "for" loop to read decoded video data
    for frame in iter.filter_frames() {
        println!("frame: {}x{}", frame.width, frame.height);
        let _pixels: Vec<u8> = frame.data; // raw RGB pixels
    }

    Ok(())
}
```

**Full example**: See `examples/hello_world.rs` in ffmpeg-sidecar repository.

## Basic Frame Iteration

Extract raw video frames for processing:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn extract_frames(input_path: &str) -> anyhow::Result<()> {
    let iter = FfmpegCommand::new()
        .input(input_path)
        .rawvideo()
        .spawn()?
        .iter()?;

    for frame in iter.filter_frames() {
        println!("Frame {}: {}x{} @ {:.2}s",
                 frame.frame_num, frame.width, frame.height, frame.timestamp);

        // Access raw RGB pixel data
        let pixels: &[u8] = &frame.data;
        let expected_size = (frame.width * frame.height * 3) as usize;
        assert_eq!(pixels.len(), expected_size);
    }

    Ok(())
}
```

## Progress Monitoring

Track encoding progress:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn transcode_with_progress(input: &str, output: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .input(input)
        .codec_video("libx264")
        .preset("medium")
        .crf(23)
        .output(output)
        .spawn()?
        .iter()?
        .for_each(|event| {
            if let ffmpeg_sidecar::event::FfmpegEvent::Progress(p) = event {
                println!("Frame: {}, FPS: {:.1}, Speed: {:.2}x",
                         p.frame, p.fps, p.speed);
            }
        });

    Ok(())
}
```

## Decode-Process-Encode Pipeline

Read frames, process in Rust, re-encode:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::FfmpegEvent;
use std::io::Write;

fn process_video(input: &str, output: &str) -> anyhow::Result<()> {
    // Decode to raw frames
    let mut decode_child = FfmpegCommand::new()
        .input(input)
        .rawvideo()
        .spawn()?;

    // Encode from raw frames (size must match input)
    let mut encode_child = FfmpegCommand::new()
        .format("rawvideo")
        .pix_fmt("rgb24")
        .size(1920, 1080)  // Adjust to match input resolution
        .input("pipe:0")
        .codec_video("libx264")
        .preset("medium")
        .overwrite()
        .output(output)
        .spawn()?;

    let mut encode_stdin = encode_child.take_stdin().unwrap();

    // Process frames from decoder
    for frame in decode_child.iter()?.filter_frames() {
        let processed_data = process_frame(&frame.data);
        encode_stdin.write_all(&processed_data)?;
    }

    // Close stdin to signal EOF to encoder
    drop(encode_stdin);

    // IMPORTANT: Drain encoder events to prevent hang
    encode_child.iter()?.for_each(|event| {
        if let FfmpegEvent::Progress(p) = event {
            println!("Encoding: frame={}, speed={:.2}x", p.frame, p.speed);
        }
    });

    Ok(())
}

fn process_frame(data: &[u8]) -> Vec<u8> {
    // Your processing logic here
    data.to_vec()
}
```

## Add Metadata

Add metadata to video file:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn add_metadata(input: &str, output: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .input(input)
        .args(["-metadata", "title=My Video"])
        .args(["-metadata", "author=John Doe"])
        .args(["-metadata", "year=2024"])
        .codec_video("copy")
        .codec_audio("copy")
        .output(output)
        .spawn()?
        .iter()?
        .for_each(|_| {});

    Ok(())
}
```

## Generate Test Video

Create test video with audio:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn generate_test_video(output: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .format("lavfi")
        .input("testsrc=size=1920x1080:rate=30:duration=10")
        .format("lavfi")
        .input("sine=frequency=440:duration=10")
        .codec_video("libx264")
        .preset("ultrafast")
        .codec_audio("aac")
        .output(output)
        .spawn()?
        .iter()?
        .for_each(|_| {});

    Ok(())
}
```

## Error Handling

Robust error handling:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::{FfmpegEvent, LogLevel};

fn transcode_with_error_handling(input: &str, output: &str) -> anyhow::Result<()> {
    let mut has_error = false;

    FfmpegCommand::new()
        .input(input)
        .output(output)
        .spawn()?
        .iter()?
        .for_each(|event| match event {
            FfmpegEvent::Error(msg) => {
                eprintln!("Error: {}", msg);
                has_error = true;
            }
            FfmpegEvent::Log(LogLevel::Error, msg) => {
                eprintln!("Log Error: {}", msg);
                has_error = true;
            }
            FfmpegEvent::Log(LogLevel::Warning, msg) => {
                eprintln!("Warning: {}", msg);
            }
            _ => {}
        });

    if has_error {
        anyhow::bail!("FFmpeg encountered errors");
    }

    Ok(())
}
```

## Next Steps

- [Video Processing](video.md) - Advanced video operations
- [Audio Processing](audio.md) - Audio extraction and processing
- [Streaming](streaming.md) - Real-time streaming and pipes
- [Monitoring](monitoring.md) - Progress tracking and metadata
