# ffmpeg-sidecar: Audio Processing

**Detection Keywords**: sidecar audio, extract audio, audio level, microphone, mic meter, audio monitor
**Aliases**: audio extraction sidecar, mic capture

Audio extraction, processing, level monitoring, and microphone capture with ffmpeg-sidecar.

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
| [monitoring.md](monitoring.md) | Progress tracking, metadata |
| [streaming.md](streaming.md) | Named pipes, TCP sockets |

## Extract Audio

Extract audio from video:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn extract_audio(input: &str, output: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .input(input)
        .no_video()
        .codec_audio("aac")
        .output(output)
        .spawn()?
        .iter()?
        .for_each(|_| {});
    Ok(())
}
```

## Audio Level Monitoring

Monitor audio levels using ebur128 filter:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::FfmpegEvent;

fn monitor_audio_levels(input: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .input(input)
        .args(["-af", "ebur128=peak=true"])
        .format("null")
        .output("-")
        .spawn()?
        .iter()?
        .for_each(|event| {
            if let FfmpegEvent::Log(_, msg) = event {
                if msg.contains("lavfi.r128.M=") {
                    println!("Audio level: {}", msg);
                }
            }
        });
    Ok(())
}
```

## Microphone Capture (Windows)

Real-time microphone level monitoring:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::{FfmpegEvent, LogLevel};

fn capture_microphone() -> anyhow::Result<()> {
    // List audio devices
    let audio_device = FfmpegCommand::new()
        .hide_banner()
        .args(["-list_devices", "true"])
        .format("dshow")
        .input("dummy")
        .spawn()?
        .iter()?
        .into_ffmpeg_stderr()
        .find(|line| line.contains("(audio)"))
        .and_then(|line| line.split('"').nth(1).map(|s| s.to_string()))
        .ok_or_else(|| anyhow::anyhow!("No audio device found"))?;

    println!("Listening to: {}", audio_device);

    // Capture and analyze
    FfmpegCommand::new()
        .format("dshow")
        .args(["-audio_buffer_size", "50"])
        .input(format!("audio={}", audio_device))
        .args(["-af", "ebur128=metadata=1,ametadata=print"])
        .format("null")
        .output("-")
        .spawn()?
        .iter()?
        .for_each(|event| {
            if let FfmpegEvent::Log(LogLevel::Info, msg) = event {
                if msg.contains("lavfi.r128.M=") {
                    if let Some(volume) = msg.split("lavfi.r128.M=").last() {
                        println!("Volume: {}", volume);
                    }
                }
            }
        });

    Ok(())
}
```

See [Core API](core.md) for complete audio processing reference.
