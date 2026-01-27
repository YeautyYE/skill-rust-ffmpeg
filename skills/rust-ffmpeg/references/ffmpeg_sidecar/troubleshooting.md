# ffmpeg-sidecar: Troubleshooting

**Detection Keywords**: error handling, debug sidecar, ffmpeg error, log level, best practice, performance
**Aliases**: troubleshoot, debug, error fix

Error handling, common issues, best practices, and performance optimization.

> **Dependencies**: Examples use `anyhow` for error handling:
> ```toml
> [dependencies]
> ffmpeg-sidecar = "2.4.0"
> anyhow = "1"
> ```

## Related Guides

| Guide | Content |
|-------|---------|
| [setup.md](setup.md) | Installation, auto-download features |
| [core.md](core.md) | Core API reference |
| [monitoring.md](monitoring.md) | Progress tracking, logging |

## Error Handling Pattern

Robust error handling with event categorization:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::{FfmpegEvent, LogLevel};

fn process_with_error_handling(input: &str, output: &str) -> anyhow::Result<()> {
    let mut has_error = false;
    let mut error_messages = Vec::new();

    FfmpegCommand::new()
        .input(input)
        .codec_video("libx264")
        .output(output)
        .spawn()?
        .iter()?
        .for_each(|event| match event {
            FfmpegEvent::Error(msg) => {
                eprintln!("FFmpeg Error: {}", msg);
                error_messages.push(msg);
                has_error = true;
            }
            FfmpegEvent::Log(LogLevel::Error, msg) => {
                eprintln!("Log Error: {}", msg);
                has_error = true;
            }
            FfmpegEvent::Log(LogLevel::Warning, msg) => {
                eprintln!("Warning: {}", msg);
            }
            FfmpegEvent::Progress(p) => {
                println!("Frame: {}, Speed: {:.2}x", p.frame, p.speed);
            }
            _ => {}
        });

    if has_error {
        anyhow::bail!("FFmpeg errors: {:?}", error_messages);
    }
    Ok(())
}
```

## Common Issues

### FFmpeg Not Found

```rust
use ffmpeg_sidecar::command::ffmpeg_is_installed;
use ffmpeg_sidecar::download::auto_download;

fn ensure_ffmpeg() -> anyhow::Result<()> {
    if !ffmpeg_is_installed() {
        println!("FFmpeg not found, downloading...");
        #[cfg(feature = "download_ffmpeg")]
        auto_download()?;
    }
    Ok(())
}
```

### Process Hangs

If FFmpeg process hangs:

1. **Check for blocking operations**: Ensure stdin/stdout/stderr are properly handled
2. **Use iter()**: Always consume the iterator to completion
3. **Graceful shutdown**: Use `child.quit()` instead of `child.kill()`

```rust
// Anti-pattern: Not consuming iterator
let mut child = FfmpegCommand::new().input("input.mp4").output("output.mp4").spawn()?;
child.wait()?;  // May hang if stdout buffer fills

// Correct: Consume iterator
let mut child = FfmpegCommand::new().input("input.mp4").output("output.mp4").spawn()?;
child.iter()?.for_each(|_| {});  // Drains stdout/stderr
child.wait()?;  // Now safe
```

### Memory Issues

For large videos, process in chunks:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn process_large_video(input: &str) -> anyhow::Result<()> {
    let iter = FfmpegCommand::new()
        .input(input)
        .rawvideo()
        .spawn()?
        .iter()?;

    // Process frames one at a time, don't collect into Vec
    for frame in iter.filter_frames() {
        process_single_frame(&frame);
        // frame.data is dropped here, memory freed
    }
    Ok(())
}

fn process_single_frame(frame: &ffmpeg_sidecar::event::OutputVideoFrame) {
    // Process without keeping reference
}
```

### Invalid Input/Output

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use std::path::Path;

fn safe_transcode(input: &str, output: &str) -> anyhow::Result<()> {
    // Validate input exists
    if !Path::new(input).exists() {
        anyhow::bail!("Input file not found: {}", input);
    }

    // Ensure output directory exists
    if let Some(parent) = Path::new(output).parent() {
        std::fs::create_dir_all(parent)?;
    }

    FfmpegCommand::new()
        .input(input)
        .overwrite()  // Handle existing output
        .output(output)
        .spawn()?
        .iter()?
        .for_each(|_| {});

    Ok(())
}
```

## Best Practices

1. **Always call hide_banner()**: Reduces stderr noise
2. **Use filter methods**: More ergonomic than manual matching
3. **Handle errors**: Check for error events
4. **Graceful shutdown**: Use quit() not kill()
5. **Monitor progress**: Track encoding status
6. **Test with small clips**: Verify before large files
7. **Validate paths**: Check input exists, output writable

## Performance Tips

1. **Stream copy when possible**: `-c:v copy` avoids re-encoding
   ```rust
   .codec_video("copy")  // Fast, lossless
   ```

2. **Hardware acceleration**: Use when available
   ```rust
   .hwaccel("cuda")           // NVIDIA
   .hwaccel("videotoolbox")   // macOS
   .hwaccel("qsv")            // Intel
   ```

3. **Appropriate presets**: Balance speed vs quality
   ```rust
   .preset("ultrafast")  // Fastest, largest file
   .preset("medium")     // Default balance
   .preset("veryslow")   // Slowest, smallest file
   ```

4. **Parallel processing**: Use multiple FFmpeg instances for batch processing

## Limitations

- **Process overhead**: IPC adds latency vs native libraries
- **Platform-specific**: Some features require specific platforms
- **FFmpeg version**: Behavior depends on FFmpeg version
- **No direct memory access**: Frames copied through pipes
- **Event parsing**: Some FFmpeg output may not be parsed

## Debug Mode

Enable verbose logging for troubleshooting:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn debug_mode(input: &str, output: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .args(["-loglevel", "debug"])  // Maximum verbosity
        .print_command()               // Print command before execution
        .input(input)
        .output(output)
        .spawn()?
        .iter()?
        .for_each(|event| {
            println!("{:?}", event);  // Print all events
        });
    Ok(())
}
```

See [Core API](core.md) for complete reference.
