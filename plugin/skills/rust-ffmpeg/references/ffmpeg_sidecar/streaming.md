# ffmpeg-sidecar: Streaming

**Detection Keywords**: named pipe, tcp socket, ffplay, real-time stream, pipe output, socket stream
**Aliases**: streaming sidecar, pipe, socket

Real-time streaming, named pipes, TCP sockets, and ffplay integration.

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
| [advanced.md](advanced.md) | Terminal rendering, experimental |

## Named Pipes (Multiple Outputs)

Output video to separate named pipes (requires `named_pipes` feature):

```rust
#[cfg(feature = "named_pipes")]
use std::io::Read;
use std::sync::mpsc;
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::FfmpegEvent;
#[cfg(feature = "named_pipes")]
use ffmpeg_sidecar::named_pipes::NamedPipe;
#[cfg(feature = "named_pipes")]
use ffmpeg_sidecar::pipe_name;

#[cfg(feature = "named_pipes")]
fn video_pipe_output() -> anyhow::Result<()> {
    const VIDEO_PIPE: &str = pipe_name!("ffmpeg_video");

    let mut command = FfmpegCommand::new();
    command
        .hide_banner()
        .overwrite()
        .format("lavfi")
        .input("testsrc=duration=5")
        .format("rawvideo")
        .pix_fmt("rgb24")
        .output(VIDEO_PIPE);

    // Create pipe before spawning FFmpeg
    let mut video_pipe = NamedPipe::new(VIDEO_PIPE)?;

    // Synchronization: reader must wait until FFmpeg starts writing (critical on Windows)
    let (ready_tx, ready_rx) = mpsc::channel::<()>();

    let reader = std::thread::spawn(move || {
        ready_rx.recv().ok(); // Wait for FFmpeg to start
        let mut buf = vec![0; 320 * 240 * 3];
        let mut total = 0;
        while let Ok(n) = video_pipe.read(&mut buf) {
            if n == 0 { break; }
            total += n;
        }
        println!("Read {} total bytes from video pipe", total);
    });

    let mut child = command.spawn()?;
    let mut ready_sent = false;

    // Signal reader when FFmpeg starts producing output
    for event in child.iter()? {
        if !ready_sent {
            if let FfmpegEvent::Progress(_) = &event {
                ready_tx.send(()).ok();
                ready_sent = true;
            }
        }
    }

    reader.join().ok();
    Ok(())
}
```

## Real-time Preview with ffplay

Preview video in real-time (requires `ffplay` in PATH):

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn preview_with_ffplay(input: &str) -> anyhow::Result<()> {
    use std::process::{Command, Stdio};

    // Start ffplay
    let mut ffplay = Command::new("ffplay")
        .args(["-hide_banner", "-"])
        .stdin(Stdio::piped())
        .spawn()?;

    let mut ffplay_stdin = ffplay.stdin.take().unwrap();

    // Pipe FFmpeg output to ffplay
    let mut ffmpeg = FfmpegCommand::new()
        .input(input)
        .codec_video("copy")
        .format("matroska")
        .output("pipe:1")
        .spawn()?;

    let mut ffmpeg_stdout = ffmpeg.take_stdout().unwrap();

    std::io::copy(&mut ffmpeg_stdout, &mut ffplay_stdin)?;

    ffplay.wait()?;
    Ok(())
}
```

See [Core API](core.md) for complete streaming reference.

## TCP Socket Streaming

Stream to TCP socket (FFmpeg as client):

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use std::net::TcpListener;
use std::io::Read;
use std::thread;

fn tcp_streaming() -> anyhow::Result<()> {
    const TCP_PORT: u32 = 3000;

    // Start TCP listener in separate thread
    let listener = TcpListener::bind(format!("127.0.0.1:{}", TCP_PORT))?;

    // Spawn receiver thread
    thread::spawn(move || {
        if let Ok((mut stream, _)) = listener.accept() {
            let mut buf = vec![0u8; 1920 * 1080 * 3];
            while let Ok(n) = stream.read(&mut buf) {
                if n == 0 { break; }
                println!("Received {} bytes", n);
            }
        }
    });

    // FFmpeg outputs to TCP
    FfmpegCommand::new()
        .hide_banner()
        .format("lavfi")
        .input("testsrc=size=320x240:rate=30:duration=5")
        .format("rawvideo")
        .pix_fmt("rgb24")
        .output(format!("tcp://127.0.0.1:{}", TCP_PORT))
        .spawn()?
        .iter()?
        .for_each(|_| {});

    Ok(())
}
```

### Multi-Output TCP Streaming (Video, Audio, Subtitles)

Separate video, audio, and subtitles to different TCP ports:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::{FfmpegEvent, LogLevel};
use std::net::TcpListener;
use std::io::Read;
use std::thread;
use std::time::Duration;

fn multi_output_tcp_streaming() -> anyhow::Result<()> {
    const TCP_PORT: u32 = 3000;

    // Set up TCP listener that accepts multiple connections
    let listener_thread = thread::spawn(move || {
        let listener = TcpListener::bind(format!("127.0.0.1:{}", TCP_PORT)).unwrap();
        listener.set_nonblocking(true).unwrap();

        let mut handlers = Vec::new();
        loop {
            match listener.accept() {
                Ok((stream, _)) => {
                    handlers.push(thread::spawn(move || {
                        let mut stream = stream;
                        let mut buf = [0; 1024];
                        let mut total = 0;
                        loop {
                            match stream.read(&mut buf) {
                                Ok(0) => break,
                                Ok(n) => total += n,
                                Err(_) => break,
                            }
                        }
                        println!("Received {} bytes", total);
                    }));
                }
                Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                    thread::sleep(Duration::from_millis(10));
                }
                Err(_) => break,
            }
        }
    });

    thread::sleep(Duration::from_millis(1000)); // Wait for listener

    // FFmpeg with separate outputs for video, audio, subtitles
    FfmpegCommand::new()
        .hide_banner()
        .overwrite()
        // Video input (test pattern)
        .format("lavfi")
        .input("testsrc=size=1920x1080:rate=60:duration=10")
        // Audio input (sine wave)
        .format("lavfi")
        .input("sine=frequency=1000:duration=10")
        // Subtitle input (base64 encoded SRT)
        .format("srt")
        .input("data:text/plain;base64,MQ0KMDA6MDA6MDAsMDAwIC0tPiAwMDowMDoxMCw1MDANCkhlbGxvIFdvcmxkIQ==")
        // Video output
        .map("0:v")
        .format("rawvideo")
        .pix_fmt("rgb24")
        .output(format!("tcp://127.0.0.1:{}", TCP_PORT))
        // Audio output
        .map("1:a")
        .format("s16le")
        .output(format!("tcp://127.0.0.1:{}", TCP_PORT))
        // Subtitles output
        .map("2:s")
        .format("srt")
        .output(format!("tcp://127.0.0.1:{}", TCP_PORT))
        .spawn()?
        .iter()?
        .for_each(|event| {
            if let FfmpegEvent::Log(LogLevel::Info, msg) = event {
                if msg.starts_with("[out#") {
                    println!("{}", msg);
                }
            }
        });

    Ok(())
}
```

**Full example**: See `examples/sockets.rs` in ffmpeg-sidecar repository

## RTMP Streaming

Stream to RTMP server (e.g., YouTube, Twitch):

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::FfmpegEvent;

fn stream_to_rtmp(input: &str, rtmp_url: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .input(input)
        .realtime()                      // -re: read input at native frame rate
        .codec_video("libx264")
        .preset("veryfast")              // Low latency preset
        .args(["-tune", "zerolatency"])  // Minimize latency
        .args(["-b:v", "3M"])            // Video bitrate
        .codec_audio("aac")
        .args(["-b:a", "128k"])          // Audio bitrate
        .format("flv")                   // RTMP container format
        .output(rtmp_url)                // rtmp://server/app/stream_key
        .spawn()?
        .iter()?
        .for_each(|event| {
            if let FfmpegEvent::Progress(p) = event {
                println!("Streaming: frame={}, fps={:.1}, speed={:.2}x",
                         p.frame, p.fps, p.speed);
            }
        });
    Ok(())
}

// Usage: stream_to_rtmp("input.mp4", "rtmp://live.twitch.tv/app/your_stream_key")
```

## HLS Output

Generate HLS playlist for adaptive streaming:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn generate_hls(input: &str, output_dir: &str) -> anyhow::Result<()> {
    let playlist = format!("{}/playlist.m3u8", output_dir);
    let segment_pattern = format!("{}/segment%03d.ts", output_dir);

    FfmpegCommand::new()
        .input(input)
        .codec_video("libx264")
        .codec_audio("aac")
        .args(["-hls_time", "4"])         // 4-second segments
        .args(["-hls_list_size", "0"])    // Keep all segments in playlist
        .args(["-hls_segment_filename", &segment_pattern])
        .format("hls")
        .output(&playlist)
        .spawn()?
        .iter()?
        .for_each(|_| {});
    Ok(())
}
```

## Receive RTMP Stream

Capture incoming RTMP stream:

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn receive_rtmp(listen_url: &str, output: &str) -> anyhow::Result<()> {
    // FFmpeg listens on rtmp://localhost:1935/live/stream
    FfmpegCommand::new()
        .args(["-listen", "1"])           // Enable listen mode
        .input(listen_url)
        .codec_video("copy")
        .codec_audio("copy")
        .output(output)
        .spawn()?
        .iter()?
        .for_each(|_| {});
    Ok(())
}
```

See [Core API](core.md) for complete streaming reference.
