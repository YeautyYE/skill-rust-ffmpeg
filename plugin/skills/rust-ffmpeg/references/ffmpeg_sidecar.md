# ffmpeg-sidecar Reference

**Detection Keywords**: CLI wrapper, subprocess, binary approach, no compilation, process wrapper, ffmpeg command
**Aliases**: sidecar, subprocess ffmpeg, cli ffmpeg rust

FFmpeg process wrapper for Rust with typed event streams, progress monitoring, and cross-platform binary management.

**Crate**: https://crates.io/crates/ffmpeg-sidecar
**Version**: 2.4.0 ([crates.io](https://crates.io/crates/ffmpeg-sidecar))
**Repository**: https://github.com/nathanbabcock/ffmpeg-sidecar

> **When to Use**: Choose ffmpeg-sidecar when you need to wrap FFmpeg CLI commands with Rust type safety, cannot install FFmpeg development libraries, or prefer process-based isolation. For direct library integration, see [ez-ffmpeg](ez_ffmpeg.md) or [ffmpeg-next](ffmpeg_next.md).

## Table of Contents

- [Related Guides](#related-guides)
- [Quick Start](#quick-start)
- [CLI to Rust Migration](#cli-to-rust-migration)
- [Documentation Modules](#documentation-modules)
- [Core Architecture](#core-architecture)
  - [Three Core Types](#three-core-types)
- [Feature Flags](#feature-flags)
- [Platform Support](#platform-support)
- [Comparison with Other Libraries](#comparison-with-other-libraries)
- [When to Use ffmpeg-sidecar](#when-to-use-ffmpeg-sidecar)
- [Examples from Source](#examples-from-source)
- [Contributing](#contributing)
- [License](#license)
- [Related Documentation](#related-documentation)

## Related Guides

| Guide | Content |
|-------|---------|
| [ez_ffmpeg.md](ez_ffmpeg.md) | High-level API (alternative to sidecar) |
| [installation.md](installation.md) | Platform-specific setup |

## Quick Start

Add to `Cargo.toml`:
```toml
[dependencies]
ffmpeg-sidecar = "2.4.0"
```

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Auto-download FFmpeg if not installed
    #[cfg(feature = "download_ffmpeg")]
    ffmpeg_sidecar::download::auto_download()?;

    // Extract frames from video
    let iter = FfmpegCommand::new()
        .input("input.mp4")
        .rawvideo()
        .spawn()?
        .iter()?;

    for frame in iter.filter_frames() {
        println!("Frame {}: {}x{}", frame.frame_num, frame.width, frame.height);
    }

    Ok(())
}
```

## CLI to Rust Migration

| FFmpeg CLI | Rust Method | Notes |
|------------|-------------|-------|
| `-i input.mp4` | `.input("input.mp4")` | Multiple inputs supported |
| `-f format` | `.format("format")` | Before input or output |
| `-c:v libx264` | `.codec_video("libx264")` | Video codec |
| `-c:a aac` | `.codec_audio("aac")` | Audio codec |
| `-c:v copy` | `.codec_video("copy")` | Stream copy |
| `-s 1920x1080` | `.size(1920, 1080)` | Resolution |
| `-r 30` | `.rate(30.0)` | Frame rate |
| `-crf 23` | `.crf(23)` | Quality (0-51) |
| `-preset medium` | `.preset("medium")` | Encoding preset |
| `-t 10` | `.duration("10")` | Duration |
| `-ss 5` | `.seek("5")` | Seek position |
| `-vf scale=1280:720` | `.filter("scale=1280:720")` | Video filter |
| `-hwaccel cuda` | `.hwaccel("cuda")` | Hardware accel |
| `-vn` | `.no_video()` | Disable video |
| `-an` | `.no_audio()` | Disable audio |
| `-y` | `.overwrite()` | Overwrite output |
| `-map 0:v` | `.map("0:v")` | Stream mapping |
| `output.mp4` | `.output("output.mp4")` | Output file |
| `-` (stdout) | `.output("-")` | Pipe output |

## Documentation Modules

### Getting Started

- **[Setup and Installation](ffmpeg_sidecar/setup.md)**
  Installation, auto-download features, platform support, and troubleshooting

- **[Core API Reference](ffmpeg_sidecar/core.md)**
  Complete API documentation for FfmpegCommand, FfmpegChild, and FfmpegIterator

- **[Common Recipes](ffmpeg_sidecar/recipes.md)**
  Quick-start examples for common use cases

### Domain-Specific Guides

- **[Video Processing](ffmpeg_sidecar/video.md)**
  Video encoding, decoding, frame manipulation, filters, and test sources

- **[Audio Processing](ffmpeg_sidecar/audio.md)**
  Audio extraction, processing, level monitoring, and microphone capture

- **[Streaming](ffmpeg_sidecar/streaming.md)**
  Named pipes, TCP sockets, real-time streaming, and ffplay integration

- **[Monitoring and Metadata](ffmpeg_sidecar/monitoring.md)**
  Progress tracking, metadata extraction, ffprobe integration, and logging

### Advanced Topics

- **[Advanced Patterns](ffmpeg_sidecar/advanced.md)**
  Terminal video rendering, Whisper integration, custom filters, and experimental features

- **[Troubleshooting](ffmpeg_sidecar/troubleshooting.md)**
  Error handling, limitations, best practices, and performance optimization

## Core Architecture

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

### Three Core Types

1. **FfmpegCommand**: Builder API for constructing FFmpeg commands
   - Similar to `std::process::Command`
   - Fluent API with method chaining
   - Type-safe argument construction

2. **FfmpegChild**: Process wrapper with stdio control
   - Graceful shutdown with `quit()`
   - Interactive command support
   - Direct stdio access

3. **FfmpegIterator**: Typed event stream
   - Blocking iterator over FFmpeg events
   - Filter methods for specific event types
   - Metadata collection

## Feature Flags

| Feature | Description | Default |
|---------|-------------|---------|
| `download_ffmpeg` | Auto-download FFmpeg binaries | ✅ Enabled |
| `named_pipes` | Cross-platform named pipe support | ❌ Disabled |

## Platform Support

| Platform | Architecture | Status |
|----------|--------------|--------|
| Windows | x86_64 | ✅ Supported |
| macOS Intel | x86_64 | ✅ Supported |
| macOS Apple Silicon | arm64 | ✅ Supported |
| Linux | x86_64 | ✅ Supported |
| Linux | arm64 | ✅ Supported |

## Comparison with Other Libraries

| Feature | ffmpeg-sidecar | ez-ffmpeg | ffmpeg-next | ffmpeg-sys-next |
|---------|----------------|-----------|-------------|-----------------|
| **Approach** | Process wrapper | Safe Rust API | Safe bindings | Raw FFI |
| **FFmpeg Install** | Optional (auto-download) | Required | Required | Required |
| **Type Safety** | Event enums | Rust types | Rust types | Unsafe |
| **Learning Curve** | Low (CLI-like) | Medium | Medium | High |
| **Performance** | IPC overhead | Native | Native | Native |
| **Use Case** | CLI wrapping, isolation | General purpose | Advanced control | Maximum control |

## When to Use ffmpeg-sidecar

**Choose ffmpeg-sidecar when:**
- ✅ You're familiar with FFmpeg CLI commands
- ✅ You can't install FFmpeg development libraries
- ✅ You need process isolation
- ✅ You want auto-download functionality
- ✅ You need typed event streams
- ✅ You're prototyping or building tools

**Consider alternatives when:**
- ❌ You need maximum performance (use ez-ffmpeg or ffmpeg-next)
- ❌ You need fine-grained control over encoding (use ffmpeg-next)
- ❌ You're building a library (process overhead may not be acceptable)
- ❌ You need custom codecs or filters (use ffmpeg-sys-next)

## Examples from Source

The ffmpeg-sidecar repository includes 13 examples:

- `hello_world.rs` - Basic frame iteration
- `progress.rs` - Progress monitoring
- `h265_transcode.rs` - Decode-process-encode pipeline
- `metadata.rs` - Metadata operations
- `ffplay_preview.rs` - Real-time preview
- `named_pipes.rs` - Multiple outputs with named pipes
- `sockets.rs` - TCP socket streaming
- `download_ffmpeg.rs` - Manual download control
- `ffprobe.rs` - Media information extraction
- `game_of_life.rs` - Conway's Game of Life filter
- `mic_meter.rs` - Real-time microphone level monitoring
- `terminal_video.rs` - Terminal video rendering
- `trigger.rs` - Chainable transformations (WIP)

## Contributing

See the [official repository](https://github.com/nathanbabcock/ffmpeg-sidecar) for contribution guidelines.

## License

ffmpeg-sidecar is licensed under MIT or Apache-2.0.

## Related Documentation

- [ez-ffmpeg](ez_ffmpeg.md) - Safe Rust API for FFmpeg
- [ffmpeg-next](ffmpeg_next.md) - Safe Rust bindings
- [ffmpeg-sys-next](ffmpeg_sys_next.md) - Raw FFI bindings
- [Installation Guide](installation.md) - FFmpeg installation across all libraries
