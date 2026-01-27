# ffmpeg-sidecar: Core API

**Detection Keywords**: ffmpeg command, ffmpeg child, ffmpeg iterator, builder api, spawn, event stream
**Aliases**: sidecar api, command builder, process wrapper

Complete API reference for ffmpeg-sidecar's three core types: FfmpegCommand, FfmpegChild, and FfmpegIterator.

## Table of Contents

- [Related Guides](#related-guides)
- [Architecture Overview](#architecture-overview)
- [FfmpegCommand - Builder API](#ffmpegcommand---builder-api)
- [FfmpegChild - Process Handle](#ffmpegchild---process-handle)
- [FfmpegIterator - Event Stream](#ffmpegiterator---event-stream)
- [Event Types](#event-types)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

## Related Guides

| Guide | Content |
|-------|---------|
| [setup.md](setup.md) | Installation, auto-download features |
| [recipes.md](recipes.md) | Quick-start examples |
| [video.md](video.md) | Video encoding, decoding, filters |

## Architecture Overview

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  FfmpegCommand  │────▶│  FfmpegChild │────▶│ FfmpegIterator  │
│  (Builder API)  │     │  (Process)   │     │ (Event Stream)  │
└─────────────────┘     └──────────────┘     └─────────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
   .input()              .take_stdin()         .filter_frames()
   .output()             .take_stdout()        .filter_progress()
   .codec_video()        .quit()               .filter_errors()
   .spawn()              .wait()               .filter_chunks()
```

## FfmpegCommand - Builder API

Builder pattern for constructing FFmpeg commands, similar to `std::process::Command`.

### Construction

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

// Use FFmpeg from PATH
let mut cmd = FfmpegCommand::new();

// Use custom FFmpeg binary path
let mut cmd = FfmpegCommand::new_with_path("/usr/local/bin/ffmpeg");
```

### Input/Output Methods

```rust
// Input files
cmd.input("input.mp4");              // -i input.mp4
cmd.input("https://example.com/stream.m3u8");  // Network input

// Output files
cmd.output("output.mp4");            // output.mp4
cmd.output("-");                     // stdout

// Format specification
cmd.format("lavfi");                 // -f lavfi (before input)
cmd.format("mp4");                   // -f mp4 (before output)

// Overwrite behavior
cmd.overwrite();                     // -y (overwrite without asking)
cmd.no_overwrite();                  // -n (never overwrite)
```

### Codec Selection

```rust
// Video codec
cmd.codec_video("libx264");          // -c:v libx264
cmd.codec_video("libx265");          // -c:v libx265
cmd.codec_video("copy");             // -c:v copy (stream copy)

// Audio codec
cmd.codec_audio("aac");              // -c:a aac
cmd.codec_audio("libmp3lame");       // -c:a libmp3lame
cmd.codec_audio("copy");             // -c:a copy

// Subtitle codec
cmd.codec_subtitle("mov_text");      // -c:s mov_text
```

### Video Options

```rust
// Resolution
cmd.size(1920, 1080);                // -s 1920x1080

// Frame rate
cmd.rate(30.0);                      // -r 30
cmd.rate(23.976);                    // -r 23.976

// Pixel format
cmd.pix_fmt("yuv420p");              // -pix_fmt yuv420p
cmd.pix_fmt("rgb24");                // -pix_fmt rgb24

// Quality control
cmd.crf(23);                         // -crf 23 (0-51, lower = better)
cmd.preset("medium");                // -preset medium
// Presets: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow

// Frame count limit
cmd.frames(100);                     // -frames:v 100
```

### Time Control

```rust
// Duration
cmd.duration("10");                  // -t 10 (seconds)
cmd.duration("00:01:30");            // -t 00:01:30 (HH:MM:SS)

// End position
cmd.to("30");                        // -to 30
cmd.to("00:05:00");                  // -to 00:05:00

// Seek (before input = fast, after input = accurate)
cmd.seek("5");                       // -ss 5 (before input)
cmd.seek("00:00:05.500");            // -ss 00:00:05.500

// Seek from end
cmd.seek_eof("-10");                 // -sseof -10 (last 10 seconds)
```

### Stream Selection

```rust
// Map specific streams
cmd.map("0:v");                      // -map 0:v (first input, video)
cmd.map("1:a:0");                    // -map 1:a:0 (second input, first audio)
cmd.map("0:2");                      // -map 0:2 (first input, stream index 2)

// Disable streams
cmd.no_video();                      // -vn (no video)
cmd.no_audio();                      // -an (no audio)
cmd.no_subtitle();                   // -sn (no subtitles)
```

### Filters

```rust
// Simple video filter
cmd.filter("scale=1280:720");                    // -vf scale=1280:720
cmd.filter("fps=30");                            // -vf fps=30

// Complex filtergraph
cmd.filter_complex("[0:v][1:v]overlay=10:10");   // -filter_complex ...
cmd.filter_complex("split[a][b];[a]pad=2*iw[A];[A][b]overlay=w"); // Multiple filters
```

### Hardware Acceleration

```rust
// Enable hardware acceleration
cmd.hwaccel("cuda");                 // -hwaccel cuda (NVIDIA)
cmd.hwaccel("videotoolbox");         // -hwaccel videotoolbox (macOS)
cmd.hwaccel("qsv");                  // -hwaccel qsv (Intel Quick Sync)
cmd.hwaccel("vaapi");                // -hwaccel vaapi (Linux VA-API)
```

### Realtime Playback

```rust
// Read input at native frame rate
cmd.readrate(1.0);                   // -readrate 1.0

// Output at native frame rate
cmd.realtime();                      // -re
```

### Raw Video Output

For frame-by-frame processing:

```rust
// Output raw RGB24 frames to stdout
cmd.rawvideo();                      // -c:v rawvideo -f rawvideo -pix_fmt rgb24 -

// Note: rawvideo() automatically sets output to stdout ("-")
// Do NOT call .pipe_stdout() after .rawvideo()
```

### Test Sources

```rust
// Generate test video (5 seconds by default)
cmd.testsrc();                       // -f lavfi -i testsrc=duration=5

// Custom test source
cmd.format("lavfi")
   .input("testsrc=size=1920x1080:rate=30:duration=10");
```

### Debug and Logging

```rust
// Hide FFmpeg banner
cmd.hide_banner();                   // -hide_banner

// Print command before execution
cmd.print_command();                 // Prints to stdout

// Custom arguments
cmd.arg("-loglevel");                // Add single argument
cmd.arg("debug");
cmd.args(["-threads", "4"]);         // Add multiple arguments
```

### Spawning Process

```rust
// Spawn FFmpeg process
let child = cmd.spawn()?;            // Returns FfmpegChild

// Access underlying std::process::Command
let inner_cmd = cmd.as_inner();      // &Command
let inner_cmd_mut = cmd.as_inner_mut(); // &mut Command
```

## FfmpegChild - Process Control

Wrapper around spawned FFmpeg process with stdio control.

### Basic Usage

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

let mut child = FfmpegCommand::new()
    .input("input.mp4")
    .output("output.mp4")
    .spawn()?;

// Create event iterator
let iter = child.iter()?;

// Wait for completion
let status = child.wait()?;
```

### Stdio Control

```rust
// Take ownership of stdio handles
let stdin = child.take_stdin();      // Option<ChildStdin>
let stdout = child.take_stdout();    // Option<ChildStdout>
let stderr = child.take_stderr();    // Option<ChildStderr>

// Note: iter() consumes stdout and stderr
// After calling iter(), take_stdout() and take_stderr() return None
```

### Process Control

```rust
// Graceful shutdown (sends 'q' command to stdin)
child.quit()?;

// Force terminate
child.kill()?;

// Wait for process to exit
let status = child.wait()?;
println!("Exit code: {:?}", status.code());
```

### Interactive Commands

Send commands to FFmpeg during processing:

```rust
// Show help
child.send_stdin_command(b"?")?;

// Increase verbosity
child.send_stdin_command(b"+")?;

// Decrease verbosity
child.send_stdin_command(b"-")?;

// Quit gracefully
child.send_stdin_command(b"q")?;  // Same as child.quit()

// Seek forward 10 seconds (when using -stdin)
child.send_stdin_command(b"seek 10")?;
```

## FfmpegIterator - Event Stream

Blocking iterator over parsed FFmpeg events.

### Event Types

```rust
use ffmpeg_sidecar::event::FfmpegEvent;

pub enum FfmpegEvent {
    // Metadata (parsed from stderr)
    ParsedVersion(FfmpegVersion),
    ParsedConfiguration(FfmpegConfiguration),
    ParsedInput(FfmpegInput),
    ParsedOutput(FfmpegOutput),
    ParsedInputStream(Stream),
    ParsedOutputStream(Stream),
    ParsedDuration(FfmpegDuration),
    ParsedStreamMapping(String),

    // Runtime events
    Log(LogLevel, String),
    Error(String),
    Progress(FfmpegProgress),

    // Output data
    OutputFrame(OutputVideoFrame),
    OutputChunk(Vec<u8>),

    // Lifecycle
    LogEOF,
    Done,
}
```

### Progress Structure

```rust
pub struct FfmpegProgress {
    pub frame: u32,           // Current frame number
    pub fps: f32,             // Processing speed (frames per second)
    pub q: f32,               // Quality factor
    pub size_kb: u32,         // Output size in KB
    pub time: String,         // Timestamp "HH:MM:SS.ms"
    pub bitrate_kbps: f32,    // Bitrate in kbps
    pub speed: f32,           // Processing speed multiplier (1.0 = realtime)
    pub raw_log_message: String,
}
```

### Video Frame Structure

```rust
pub struct OutputVideoFrame {
    pub width: u32,
    pub height: u32,
    pub pix_fmt: String,      // e.g., "rgb24", "yuv420p"
    pub output_index: u32,    // Which output stream (for multiple outputs)
    pub data: Vec<u8>,        // Raw pixel data
    pub frame_num: u32,       // Frame number
    pub timestamp: f32,       // Timestamp in seconds
}
```

### Basic Iteration

```rust
let mut child = FfmpegCommand::new()
    .input("input.mp4")
    .output("output.mp4")
    .spawn()?;

let iter = child.iter()?;

for event in iter {
    match event {
        FfmpegEvent::Progress(p) => {
            println!("Frame: {}, FPS: {:.1}, Speed: {:.2}x",
                     p.frame, p.fps, p.speed);
        }
        FfmpegEvent::Log(level, msg) => {
            println!("[{:?}] {}", level, msg);
        }
        FfmpegEvent::Error(msg) => {
            eprintln!("Error: {}", msg);
        }
        _ => {}
    }
}
```

### Filter Methods

Convenience methods for filtering specific event types:

```rust
let iter = child.iter()?;

// Filter only video frames
for frame in iter.filter_frames() {
    println!("Frame {}: {}x{} @ {:.2}s",
             frame.frame_num, frame.width, frame.height, frame.timestamp);

    // Access raw pixel data
    let pixels: &[u8] = &frame.data;
    let expected_size = (frame.width * frame.height * 3) as usize; // RGB24
    assert_eq!(pixels.len(), expected_size);
}

// Filter only progress updates
for progress in iter.filter_progress() {
    println!("Progress: frame={}, fps={:.1}, speed={:.2}x",
             progress.frame, progress.fps, progress.speed);
}

// Filter only errors
for error in iter.filter_errors() {
    eprintln!("Error: {}", error);
}

// Filter raw output chunks (for non-rawvideo formats)
for chunk in iter.filter_chunks() {
    // chunk: Vec<u8>
    // Write to file, network, etc.
}
```

### Metadata Collection

Collect all metadata before processing frames:

```rust
let mut child = FfmpegCommand::new()
    .input("input.mp4")
    .rawvideo()
    .spawn()?;

let mut iter = child.iter()?;

// Collect metadata (blocks until all metadata is parsed)
let metadata = iter.collect_metadata()?;

println!("Duration: {:?}", metadata.duration());
println!("Input streams: {}", metadata.input_streams.len());
println!("Output streams: {}", metadata.output_streams.len());

// Continue processing frames
for frame in iter.filter_frames() {
    // Process frames...
}
```

### Raw Stderr Access

For custom parsing or logging:

```rust
let iter = child.iter()?;

// Convert to raw stderr line iterator
for line in iter.into_ffmpeg_stderr() {
    println!("FFmpeg: {}", line);
}
```

## Type Definitions

### LogLevel

```rust
pub enum LogLevel {
    Info,
    Warning,
    Error,
    Fatal,
    Unknown,
}
```

### Stream

```rust
pub struct Stream {
    pub index: u32,
    pub codec_type: String,  // "video", "audio", "subtitle"
    pub codec_name: String,  // "h264", "aac", etc.
    // Additional fields...
}
```

### FfmpegMetadata

```rust
pub struct FfmpegMetadata {
    pub outputs: Vec<FfmpegOutput>,
    pub output_streams: Vec<Stream>,
    pub inputs: Vec<FfmpegInput>,
    pub input_streams: Vec<Stream>,
    // ...
}

impl FfmpegMetadata {
    pub fn duration(&self) -> Option<f64>;
}
```

## Best Practices

1. **Always call hide_banner()**: Reduces stderr noise
2. **Use filter methods**: More ergonomic than manual matching
3. **Collect metadata early**: Call `collect_metadata()` before frame processing
4. **Handle errors**: Check for `FfmpegEvent::Error` events
5. **Graceful shutdown**: Use `child.quit()` instead of `child.kill()`
6. **Don't mix stdio access**: After calling `iter()`, don't use `take_stdout()`/`take_stderr()`

## Next Steps

- [Common Recipes](recipes.md) - Quick start with common use cases
- [Video Processing](video.md) - Video encoding, decoding, and frame manipulation
- [Audio Processing](audio.md) - Audio extraction, processing, and analysis
- [Streaming](streaming.md) - Named pipes, TCP sockets, and real-time streaming
