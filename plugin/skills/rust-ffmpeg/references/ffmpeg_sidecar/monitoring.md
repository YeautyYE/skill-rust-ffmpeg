# ffmpeg-sidecar: Monitoring

**Detection Keywords**: progress tracking, ffprobe, metadata extraction, encoding progress, fps, speed, event
**Aliases**: progress monitor, ffprobe rust, encoding status

Progress tracking, metadata extraction, ffprobe integration, and logging.

> **Dependencies**: Examples use `anyhow` for error handling:
> ```toml
> [dependencies]
> ffmpeg-sidecar = "2.4.0"
> anyhow = "1"
> ```

## Related Guides

| Guide | Content |
|-------|---------|
| [video.md](video.md) | Video encoding, decoding, filters |
| [audio.md](audio.md) | Audio extraction, mic capture |
| [troubleshooting.md](troubleshooting.md) | Error handling, debugging |

## Progress Monitoring

Track encoding progress:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::FfmpegEvent;

fn monitor_progress(input: &str, output: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .input(input)
        .codec_video("libx264")
        .output(output)
        .spawn()?
        .iter()?
        .for_each(|event| {
            if let FfmpegEvent::Progress(p) = event {
                println!("Frame: {}, FPS: {:.1}, Speed: {:.2}x, Time: {}",
                         p.frame, p.fps, p.speed, p.time);
            }
        });
    Ok(())
}
```

## Metadata Collection

Collect stream metadata:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn collect_metadata(input: &str) -> anyhow::Result<()> {
    let mut child = FfmpegCommand::new()
        .input(input)
        .rawvideo()
        .spawn()?;

    let mut iter = child.iter()?;
    let metadata = iter.collect_metadata()?;

    println!("Duration: {:?}", metadata.duration());
    println!("Input streams: {}", metadata.input_streams.len());
    println!("Output streams: {}", metadata.output_streams.len());

    for stream in &metadata.input_streams {
        println!("Stream {}: {} ({})",
                 stream.index, stream.codec_type, stream.codec_name);
    }

    Ok(())
}
```

## Error Handling

Robust error handling:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::{FfmpegEvent, LogLevel};

fn process_with_errors(input: &str, output: &str) -> anyhow::Result<()> {
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

See [Core API](core.md) for complete monitoring reference.

## ffprobe Version Check

Check if ffprobe is available:

```rust
use ffmpeg_sidecar::ffprobe::ffprobe_version;
use ffmpeg_sidecar::download::auto_download;

fn check_ffprobe() -> anyhow::Result<()> {
    // Auto-download if needed
    #[cfg(feature = "download_ffmpeg")]
    auto_download()?;
    
    // Check version
    let version = ffprobe_version()?;
    println!("ffprobe version: {}", version);
    
    Ok(())
}
```

**Note**: Not all FFmpeg distributions include ffprobe in their bundle.

**Full example**: See `examples/ffprobe.rs` in ffmpeg-sidecar repository

See [Core API](core.md) for complete monitoring reference.
