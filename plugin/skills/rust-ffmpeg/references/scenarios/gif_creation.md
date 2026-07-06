# GIF Creation

**Detection Keywords**: gif, animated gif, video to gif, gif generation, gif from video, create gif, make gif, gif loop, gif palette, high quality gif
**Aliases**: gif conversion, animated image, gif export, gif extract

Create high-quality animated GIFs from video across all Rust FFmpeg libraries.

## Quick Example (30 seconds)

```rust
// ez-ffmpeg — one-shot recipe (preferred; no feature flag, default build)
// animated_gif builds the palettegen/paletteuse graph for you in a single call.
use ez_ffmpeg::recipes::{animated_gif, GifOptions};

animated_gif(
    "input.mp4",
    "output.gif",
    GifOptions {
        fps: 12,
        width: Some(480),
        ..GifOptions::default()
    },
)?;
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

## GIF Recipe Options (ez-ffmpeg)

`animated_gif` covers trimming, dithering, palette size, and looping through `GifOptions` — no manual filter string needed, and **no feature flag** (default build).

```rust
use ez_ffmpeg::recipes::{animated_gif, GifOptions, GifTrim, Dither, GifLoop};

// A 3-second, 480px-wide clip starting at 5s, capped at 128 colours, played 3 times.
animated_gif(
    "input.mp4",
    "clip.gif",
    GifOptions {
        fps: 15,
        width: Some(480),
        trim: Some(GifTrim::from_micros(5_000_000, 3_000_000)), // input-side trim
        dither: Dither::Bayer { scale: 3 },
        max_colors: Some(128),
        loop_: GifLoop::Count(3),
        ..GifOptions::default()
    },
)?;
```

- **`trim: Option<GifTrim>`** — trim applied on the **input** side (input seek + recording time), so the palette is built from exactly the chosen segment rather than the whole clip. Construct with `GifTrim::from_micros(start_us, duration_us)` or `GifTrim::from_durations(start, duration)` (from `std::time::Duration`).
- **`dither: Dither`** — `None`, `Bayer { scale }` (`scale` in `0..=5`), `Sierra2` (default), or `FloydSteinberg`.
- **`max_colors: Option<u32>`** — palette size, `4..=256`; `None` uses FFmpeg's default of 256.
- **`loop_: GifLoop`** — `Infinite` (default, `loop=0`), `Count(n)` (`n` in `1..=65535`), or `Once` (play once, `loop=-1`).
- **`fps` / `width`** — `width: None` keeps the source width; height is auto-derived to preserve aspect ratio.

## High-Quality GIF (Two-Pass with Palette)

*Advanced / custom fallback.* For ez-ffmpeg, prefer `animated_gif` above — it builds this optimized palette internally in a single call and adds trim/dither/loop control. Hand-roll the two-pass below only when you need a custom filter chain or an externally-supplied palette, or when using ffmpeg-sidecar / ffmpeg-next (which have no recipe).

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
