# GIF Creation

**Detection Keywords**: gif, animated gif, video to gif, gif generation, gif from video, create gif, make gif, gif loop, gif palette, high quality gif
**Aliases**: gif conversion, animated image, gif export, gif extract

Create high-quality animated GIFs from video across all Rust FFmpeg libraries.

## Quick Example (30 seconds)

```rust
// ez-ffmpeg — basic GIF
use ez_ffmpeg::{FfmpegContext, Output};

FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("fps=10,scale=320:-1:flags=lanczos")
    .output("output.gif")
    .build()?.start()?.wait()?;
```

```rust
// ffmpeg-sidecar — basic GIF
use ffmpeg_sidecar::command::FfmpegCommand;

FfmpegCommand::new()
    .input("input.mp4")
    .args(["-vf", "fps=10,scale=320:-1:flags=lanczos"])
    .output("output.gif")
    .spawn()?.wait()?;
```

## High-Quality GIF (Two-Pass with Palette)

Single-pass GIF uses a global 256-color palette → banding artifacts. Two-pass generates an optimized palette first → significantly better quality.

### ez-ffmpeg

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

let input_file = "input.mp4";
let palette_file = "palette.png";
let output_file = "output.gif";

// Pass 1: Generate optimized palette
FfmpegContext::builder()
    .input(input_file)
    .filter_desc("fps=10,scale=320:-1:flags=lanczos,palettegen")
    .output(Output::from(palette_file))
    .build()?.start()?.wait()?;

// Pass 2: Apply palette to generate GIF
FfmpegContext::builder()
    .input(input_file)
    .input(palette_file)
    .filter_desc("[0:v]fps=10,scale=320:-1:flags=lanczos[v];[v][1:v]paletteuse")
    .output(output_file)
    .build()?.start()?.wait()?;

// Cleanup
std::fs::remove_file(palette_file).ok();
```

### ffmpeg-sidecar

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

// Pass 1: Generate palette
FfmpegCommand::new()
    .input("input.mp4")
    .args(["-vf", "fps=10,scale=320:-1:flags=lanczos,palettegen"])
    .output("palette.png")
    .spawn()?.wait()?;

// Pass 2: Apply palette
FfmpegCommand::new()
    .input("input.mp4")
    .input("palette.png")
    .args(["-lavfi", "[0:v]fps=10,scale=320:-1:flags=lanczos[v];[v][1:v]paletteuse"])
    .output("output.gif")
    .spawn()?.wait()?;
```

## Library Comparison

| Aspect | ez-ffmpeg | ffmpeg-next | ffmpeg-sys-next | ffmpeg-sidecar |
|--------|-----------|-------------|-----------------|----------------|
| **Two-pass palette** | ✅ filter_desc | ✅ Manual filter graph | ✅ Manual filter graph | ✅ CLI args |
| **Code complexity** | Low | High | Very High | Low |
| **Use when** | General tasks | Custom frame processing | Max performance | No install |

## Common Patterns

### GIF from video segment
```rust
// ez-ffmpeg: GIF from 5s to 10s
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_start_time_us(5_000_000)
        .set_recording_time_us(5_000_000))
    .filter_desc("fps=10,scale=480:-1:flags=lanczos")
    .output("clip.gif")
    .build()?.start()?.wait()?;
```

### Control GIF size
```rust
// fps and scale are the two main levers:
// - Lower fps (8-15) = smaller file, choppier motion
// - Smaller scale = smaller file, less detail
.filter_desc("fps=8,scale=240:-1:flags=lanczos")  // ~1-2MB for 5s
.filter_desc("fps=15,scale=480:-1:flags=lanczos")  // ~5-10MB for 5s
```

### Infinite loop vs no loop
```rust
// ez-ffmpeg: Loop forever (default GIF behavior)
.output("loop.gif")

// No loop (play once)
.output(Output::from("no_loop.gif")
    .set_format_opt("loop", "-1"))
```

## Quality Tips

- **Always use `lanczos`** for scaling — sharper than default bilinear
- **Two-pass palette** is worth the extra step for any public-facing GIF
- **fps=10-15** is the sweet spot — below 10 feels choppy, above 15 adds size with diminishing returns
- **Max width 480-640px** — larger GIFs balloon in file size with minimal perceived quality gain
- Consider **WebP** (`output.webp`) as a modern alternative with better compression

## Detailed Examples

- **ez-ffmpeg**: [ez_ffmpeg/video.md](../ez_ffmpeg/video.md) — filter_desc patterns
- **ez-ffmpeg CLI migration**: [ez_ffmpeg/cli_migration.md](../ez_ffmpeg/cli_migration.md#video-to-gif) — FFmpeg CLI to Rust
- **ffmpeg-sidecar**: [ffmpeg_sidecar/video.md](../ffmpeg_sidecar/video.md) — CLI wrapper approach

## Related Scenarios

- [Video Transcoding](video_transcoding.md) — format conversion basics
- [Batch Processing](batch_processing.md) — convert multiple videos to GIF
