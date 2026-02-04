# ffmpeg-sidecar: Advanced Topics

**Detection Keywords**: terminal video, ascii art, whisper integration, custom filter, experimental, game of life, ffplay preview, pipe to ffplay
**Aliases**: advanced sidecar, terminal render, whisper, ffplay debug

Terminal video rendering, ffplay preview, Whisper integration, custom filters, and experimental features.

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
| [streaming.md](streaming.md) | Named pipes, TCP sockets |
| [recipes.md](recipes.md) | Quick-start examples |

## Terminal Video Rendering

Render video to terminal using ASCII art:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn render_to_terminal(input: &str) -> anyhow::Result<()> {
    // Scale down and convert to RGB for terminal display
    let iter = FfmpegCommand::new()
        .input(input)
        .filter("scale=80:60,format=rgb24")
        .rawvideo()
        .spawn()?
        .iter()?;

    for frame in iter.filter_frames() {
        // Clear screen
        print!("\x1b[2J\x1b[H");

        // Convert pixels to ASCII
        for y in 0..frame.height {
            for x in 0..frame.width {
                let idx = ((y * frame.width + x) * 3) as usize;
                let brightness = frame.data[idx];
                let char = match brightness {
                    0..=63 => ' ',
                    64..=127 => '.',
                    128..=191 => ':',
                    _ => '#',
                };
                print!("{}", char);
            }
            println!();
        }

        std::thread::sleep(std::time::Duration::from_millis(33));
    }

    Ok(())
}
```

## Graceful Shutdown

Gracefully stop long-running FFmpeg processes:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::FfmpegEvent;

fn graceful_shutdown(input: &str, output: &str) -> anyhow::Result<()> {
    let mut child = FfmpegCommand::new()
        .input(input)
        .codec_video("libx264")
        .output(output)
        .spawn()?;

    let mut iter = child.iter()?;
    let mut should_quit = false;

    for event in &mut iter {
        if let FfmpegEvent::Progress(p) = event {
            if p.frame >= 100 {
                should_quit = true;
                break;
            }
        }
    }

    drop(iter);  // Drop iterator before calling quit

    if should_quit {
        child.quit()?;
    }

    let status = child.wait()?;
    println!("Exited with: {:?}", status);

    Ok(())
}
```

See [Core API](core.md) for complete advanced features reference.

## FFplay Preview Pipeline

Pipe FFmpeg output to ffplay for real-time debugging and preview:

```rust
use std::io::{Read, Write};
use std::process::{Command, Stdio};
use ffmpeg_sidecar::command::FfmpegCommand;

fn ffplay_preview() -> anyhow::Result<()> {
    // Generate test video with FFmpeg
    let mut ffmpeg = FfmpegCommand::new()
        .realtime()
        .format("lavfi")
        .input("testsrc=size=1920x1080:rate=60")
        .codec_video("rawvideo")
        .format("avi")
        .output("-")
        .spawn()?;

    // Start ffplay to receive the stream
    let mut ffplay = Command::new("ffplay")
        .args(["-i", "-"])
        .stdin(Stdio::piped())
        .spawn()?;

    let mut ffmpeg_stdout = ffmpeg.take_stdout().unwrap();
    let mut ffplay_stdin = ffplay.stdin.take().unwrap();

    // Pipe from ffmpeg stdout to ffplay stdin
    let buf = &mut [0u8; 4096];
    loop {
        let n = ffmpeg_stdout.read(buf)?;
        if n == 0 {
            break;
        }
        ffplay_stdin.write_all(&buf[..n])?;
    }

    Ok(())
}
```

**Full example**: See `examples/ffplay_preview.rs` in ffmpeg-sidecar repository

## Game of Life Filter Preview

Preview Conway's Game of Life using FFmpeg's `life` filter with ffplay:

```rust
use std::process::Command;

fn game_of_life_preview() -> anyhow::Result<()> {
    // Use ffplay to display the life filter visualization
    // life filter parameters:
    //   s=300x200     - grid size
    //   mold=10       - mold effect (dying cells leave trails)
    //   r=60          - frame rate
    //   ratio=0.08    - initial cell density
    //   death_color   - color of dying cells
    //   life_color    - color of living cells
    Command::new("ffplay")
        .arg("-hide_banner")
        .arg("-f").arg("lavfi")
        .arg("-i").arg("life=s=300x200:mold=10:r=60:ratio=0.08:death_color=#C83232:life_color=#00ff00,scale=1200:800:flags=16")
        .spawn()?
        .wait()?;
    Ok(())
}
```

**Full example**: See `examples/game_of_life.rs` in ffmpeg-sidecar repository

## Real-time Whisper Transcription

Transcribe audio in real-time using FFmpeg's Whisper filter:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::FfmpegEvent;

fn whisper_transcription(audio_device: &str) -> anyhow::Result<()> {
    let whisper_filter = "whisper=model=./whisper.cpp/models/ggml-base.en.bin:destination=-:queue=2";
    
    let iter = FfmpegCommand::new()
        .format("dshow")  // Windows
        .args(["-audio_buffer_size", "50"])
        .input(format!("audio={}", audio_device))
        .arg("-af")
        .arg(whisper_filter)
        .format("null")
        .output("-")
        .spawn()?
        .iter()?;
    
    for event in iter {
        if let FfmpegEvent::OutputChunk(chunk) = event {
            if let Ok(text) = String::from_utf8(chunk) {
                print!("{}", text.trim());
            }
        }
    }
    
    Ok(())
}
```

**Requirements**:
- FFmpeg built with `--enable-whisper`
- Whisper model file downloaded
- Platform-specific audio input configuration

**Full example**: See `examples/whisper.rs` in ffmpeg-sidecar repository (prototype code)

---
[← Back to Index](../ffmpeg_sidecar.md)
