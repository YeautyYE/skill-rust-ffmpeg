# Filters and Effects

**Detection Keywords**: filter, effect, scale, crop, overlay, watermark, blur, sharpen, color, brightness, contrast, hue, saturation, fade, transition, drawtext, rotate, flip
**Aliases**: video filter, audio filter, filter chain, filter graph, video effects, audio effects

Cross-library guide for applying filters and effects to audio and video.

## Quick Reference

| Operation | ez-ffmpeg | ffmpeg-next | ffmpeg-sidecar |
|-----------|-----------|-------------|----------------|
| Single filter | `.filter_desc("scale=1280:720")` | `filter::Graph` + parse | `.args(["-vf", "..."])` |
| Filter chain | `.filter_desc("scale=...,fps=...")` | Chain in parse string | `.args(["-vf", "...,..."])` |
| Complex filter | `.filter_desc("[0:v][1:v]overlay=...")` | Multi-input graph | `.filter_complex("...")` |
| Custom filter | `FrameFilter` trait | Direct frame access | N/A (CLI only) |

## Video Filters

### Scaling (Resize)

#### ez-ffmpeg

```rust
use ez_ffmpeg::{FfmpegContext, Output};

// Scale to exact dimensions
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("scale=1280:720")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Preserve aspect ratio (-1 = auto)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("scale=1280:-1")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Scale with high-quality algorithm
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("scale=1920:1080:flags=lanczos")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

#### ffmpeg-next

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::software::scaling::{Context as ScalingContext, Flags};
use ffmpeg::format::Pixel;

fn scale_frame(
    frame: &ffmpeg::frame::Video,
    target_width: u32,
    target_height: u32,
) -> Result<ffmpeg::frame::Video, ffmpeg::Error> {
    let mut scaler = ScalingContext::get(
        frame.format(),
        frame.width(),
        frame.height(),
        Pixel::YUV420P,
        target_width,
        target_height,
        Flags::LANCZOS,
    )?;

    let mut output = ffmpeg::frame::Video::empty();
    scaler.run(frame, &mut output)?;
    Ok(output)
}
```

#### ffmpeg-sidecar

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

FfmpegCommand::new()
    .input("input.mp4")
    .args(["-vf", "scale=1280:720"])
    .output("output.mp4")
    .spawn()?.wait()?;
```

### Cropping

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Crop: width:height:x:y
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("crop=640:480:100:50")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Center crop
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("crop=640:480:(iw-640)/2:(ih-480)/2")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Auto-detect black bars and crop
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("cropdetect=24:16:0")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

#### ffmpeg-sidecar

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

FfmpegCommand::new()
    .input("input.mp4")
    .args(["-vf", "crop=640:480:100:50"])
    .output("output.mp4")
    .spawn()?.wait()?;
```

### Rotation and Flipping

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Rotate 90 degrees clockwise
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("transpose=1")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Rotate 90 degrees counter-clockwise
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("transpose=2")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Rotate by arbitrary angle (radians)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("rotate=PI/4")  // 45 degrees
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Horizontal flip
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("hflip")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Vertical flip
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("vflip")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

### Color Adjustments

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Brightness, contrast, saturation
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("eq=brightness=0.1:contrast=1.2:saturation=1.5")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Hue adjustment
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("hue=h=90:s=1.5")  // Shift hue by 90 degrees
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Convert to grayscale
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("hue=s=0")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Color curves (vintage effect)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("curves=vintage")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Gamma correction
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("eq=gamma=1.5")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

### Blur and Sharpen

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Box blur
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("boxblur=5:1")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Gaussian blur
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("gblur=sigma=5")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Sharpen
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("unsharp=5:5:1.0:5:5:0.0")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

### Overlay and Watermark

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Image watermark at top-left
FfmpegContext::builder()
    .input("video.mp4")
    .input("watermark.png")
    .filter_desc("overlay=10:10")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Bottom-right corner
FfmpegContext::builder()
    .input("video.mp4")
    .input("watermark.png")
    .filter_desc("overlay=main_w-overlay_w-10:main_h-overlay_h-10")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Center overlay
FfmpegContext::builder()
    .input("video.mp4")
    .input("watermark.png")
    .filter_desc("overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Picture-in-picture
FfmpegContext::builder()
    .input("main.mp4")
    .input("pip.mp4")
    .filter_desc("[1:v]scale=320:180[pip];[0:v][pip]overlay=W-w-10:H-h-10")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

#### ffmpeg-sidecar

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

FfmpegCommand::new()
    .input("video.mp4")
    .input("watermark.png")
    .filter_complex("[0:v][1:v]overlay=10:10")
    .output("output.mp4")
    .spawn()?.wait()?;
```

### Text Overlay

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Simple text
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("drawtext=text='Hello World':x=10:y=10:fontsize=24:fontcolor=white")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Text with background box
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("drawtext=text='Title':x=(w-text_w)/2:y=50:fontsize=48:fontcolor=white:box=1:boxcolor=black@0.5")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Timestamp overlay
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("drawtext=text='%{pts\\:hms}':x=10:y=10:fontsize=24:fontcolor=white")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

### Speed Changes

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Slow motion (0.5x speed)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("setpts=2.0*PTS")
    .output("slow.mp4")
    .build()?.start()?.wait()?;

// Speed up (2x speed) - video only
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("setpts=0.5*PTS")
    .output("fast.mp4")
    .build()?.start()?.wait()?;

// Speed up with audio (2x)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]")
    .output("fast.mp4")
    .build()?.start()?.wait()?;
```

### Fade Effects

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Fade in from black (first 2 seconds)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("fade=t=in:st=0:d=2")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Fade out to black (last 2 seconds, starting at 58s)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("fade=t=out:st=58:d=2")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Both fade in and fade out
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("fade=t=in:st=0:d=2,fade=t=out:st=58:d=2")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

## Audio Filters

### Volume Adjustment

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Increase volume by 50%
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("volume=1.5")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Decrease volume to 50%
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("volume=0.5")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Volume in dB
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("volume=3dB")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

#### ffmpeg-next

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::filter;

fn create_volume_filter(
    decoder: &ffmpeg::codec::decoder::Audio,
    volume: f32,
) -> Result<filter::Graph, ffmpeg::Error> {
    let mut graph = filter::Graph::new();

    let args = format!(
        "time_base={}:sample_rate={}:sample_fmt={}:channel_layout=0x{:x}",
        decoder.time_base(),
        decoder.rate(),
        decoder.format().name(),
        decoder.channel_layout().bits()
    );
    graph.add(&filter::find("abuffer").unwrap(), "in", &args)?;
    graph.add(&filter::find("abuffersink").unwrap(), "out", "")?;

    let filter_spec = format!("volume={}", volume);
    graph.output("in", 0)?.input("out", 0)?.parse(&filter_spec)?;
    graph.validate()?;

    Ok(graph)
}
```

### Audio Normalization

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Loudness normalization (EBU R128)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("loudnorm=I=-16:TP=-1.5:LRA=11")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Simple normalization
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("loudnorm")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

### Audio Fade

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Fade in (first 3 seconds)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("afade=t=in:st=0:d=3")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Fade out (starting at 57 seconds, 3 second duration)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("afade=t=out:st=57:d=3")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

### Audio Tempo

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Speed up audio 1.5x (without pitch change)
FfmpegContext::builder()
    .input("input.mp3")
    .filter_desc("atempo=1.5")
    .output("output.mp3")
    .build()?.start()?.wait()?;

// Slow down audio 0.75x
FfmpegContext::builder()
    .input("input.mp3")
    .filter_desc("atempo=0.75")
    .output("output.mp3")
    .build()?.start()?.wait()?;

// For extreme speed changes (>2x), chain atempo filters
FfmpegContext::builder()
    .input("input.mp3")
    .filter_desc("atempo=2.0,atempo=2.0")  // 4x speed
    .output("output.mp3")
    .build()?.start()?.wait()?;
```

### Audio Resampling

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Resample to 44100 Hz
FfmpegContext::builder()
    .input("input.mp3")
    .filter_desc("aresample=44100")
    .output("output.mp3")
    .build()?.start()?.wait()?;
```

#### ffmpeg-next

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::software::resampling::Context as ResamplingContext;
use ffmpeg::util::channel_layout::ChannelLayout;
use ffmpeg::format::Sample;

fn resample_audio(
    frame: &ffmpeg::frame::Audio,
    target_rate: u32,
) -> Result<ffmpeg::frame::Audio, ffmpeg::Error> {
    let mut resampler = ResamplingContext::get(
        frame.format(),
        frame.channel_layout(),
        frame.rate(),
        Sample::F32(ffmpeg::format::sample::Type::Planar),
        ChannelLayout::STEREO,
        target_rate,
    )?;

    let mut output = ffmpeg::frame::Audio::empty();
    resampler.run(frame, &mut output)?;
    Ok(output)
}
```

### Channel Manipulation

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

// Stereo to mono
FfmpegContext::builder()
    .input("input.mp3")
    .filter_desc("pan=mono|c0=0.5*c0+0.5*c1")
    .output("output.mp3")
    .build()?.start()?.wait()?;

// Mono to stereo
FfmpegContext::builder()
    .input("input.mp3")
    .filter_desc("pan=stereo|c0=c0|c1=c0")
    .output("output.mp3")
    .build()?.start()?.wait()?;

// Swap left and right channels
FfmpegContext::builder()
    .input("input.mp3")
    .filter_desc("pan=stereo|c0=c1|c1=c0")
    .output("output.mp3")
    .build()?.start()?.wait()?;
```

## Complex Filter Graphs

### Side-by-Side Comparison

#### ez-ffmpeg

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

FfmpegContext::builder()
    .input(Input::from("video1.mp4").set_readrate(1.0))
    .input(Input::from("video2.mp4").set_readrate(1.0))
    .independent_readrate()
    .filter_desc("[0:v]scale=640:360[left];[1:v]scale=640:360[right];[left][right]hstack")
    .output(Output::from("comparison.mp4")
        .set_video_codec("libx264"))
    .build()?.start()?.wait()?;
```

### Vertical Stack

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

FfmpegContext::builder()
    .input("top.mp4")
    .input("bottom.mp4")
    .filter_desc("[0:v]scale=1280:360[top];[1:v]scale=1280:360[bottom];[top][bottom]vstack")
    .output("stacked.mp4")
    .build()?.start()?.wait()?;
```

### Grid Layout (2x2)

#### ez-ffmpeg

```rust
use ez_ffmpeg::FfmpegContext;

FfmpegContext::builder()
    .input("v1.mp4")
    .input("v2.mp4")
    .input("v3.mp4")
    .input("v4.mp4")
    .filter_desc(
        "[0:v]scale=640:360[v0];\
         [1:v]scale=640:360[v1];\
         [2:v]scale=640:360[v2];\
         [3:v]scale=640:360[v3];\
         [v0][v1]hstack[top];\
         [v2][v3]hstack[bottom];\
         [top][bottom]vstack"
    )
    .output("grid.mp4")
    .build()?.start()?.wait()?;
```

### Video with Audio from Different Source

#### ez-ffmpeg

```rust
use ez_ffmpeg::{FfmpegContext, Output};

FfmpegContext::builder()
    .input("video.mp4")
    .input("audio.mp3")
    .output(Output::from("output.mp4")
        .add_stream_map("0:v")
        .add_stream_map("1:a")
        .set_video_codec("libx264")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;
```

## Custom Rust Filters (ez-ffmpeg)

### FrameFilter Trait

```rust
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ez_ffmpeg::{FfmpegContext, Input, Output};
use ffmpeg_next::Frame;
use ffmpeg_sys_next::AVMediaType;

struct BrightnessFilter {
    adjustment: f32,
}

impl FrameFilter for BrightnessFilter {
    fn media_type(&self) -> AVMediaType {
        AVMediaType::AVMEDIA_TYPE_VIDEO
    }

    fn filter_frame(
        &mut self,
        mut frame: Frame,
        _ctx: &FrameFilterContext,
    ) -> Result<Option<Frame>, String> {
        // Access Y plane (luminance) for YUV frames
        let data = frame.data_mut(0);
        for pixel in data.iter_mut() {
            let adjusted = (*pixel as f32 * self.adjustment).clamp(0.0, 255.0);
            *pixel = adjusted as u8;
        }
        Ok(Some(frame))
    }
}

// Usage
let pipeline = FramePipelineBuilder::from(AVMediaType::AVMEDIA_TYPE_VIDEO)
    .filter("brightness", Box::new(BrightnessFilter { adjustment: 1.2 }));

FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .add_frame_pipeline(pipeline))
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

## Common Filter Reference

### Video Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `scale` | Resize video | `scale=1280:720` |
| `crop` | Crop video | `crop=640:480:100:50` |
| `pad` | Add padding | `pad=1920:1080:(ow-iw)/2:(oh-ih)/2` |
| `rotate` | Rotate by angle | `rotate=PI/2` |
| `transpose` | Rotate 90° | `transpose=1` (clockwise) |
| `hflip` | Horizontal flip | `hflip` |
| `vflip` | Vertical flip | `vflip` |
| `fps` | Change frame rate | `fps=30` |
| `setpts` | Modify timestamps | `setpts=0.5*PTS` (2x speed) |
| `overlay` | Overlay video | `overlay=10:10` |
| `drawtext` | Draw text | `drawtext=text='Hello':x=10:y=10` |
| `eq` | Color adjustment | `eq=brightness=0.1:contrast=1.2` |
| `hue` | Hue/saturation | `hue=h=90:s=1.5` |
| `curves` | Color curves | `curves=vintage` |
| `boxblur` | Box blur | `boxblur=5:1` |
| `gblur` | Gaussian blur | `gblur=sigma=5` |
| `unsharp` | Sharpen | `unsharp=5:5:1.0` |
| `fade` | Fade in/out | `fade=t=in:st=0:d=2` |
| `vignette` | Vignette effect | `vignette` |

### Audio Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `volume` | Adjust volume | `volume=1.5` |
| `loudnorm` | Normalize loudness | `loudnorm=I=-16` |
| `atempo` | Change tempo | `atempo=1.5` |
| `aresample` | Resample audio | `aresample=44100` |
| `afade` | Audio fade | `afade=t=in:st=0:d=3` |
| `pan` | Channel remix | `pan=mono|c0=0.5*c0+0.5*c1` |
| `lowpass` | Low-pass filter | `lowpass=f=3000` |
| `highpass` | High-pass filter | `highpass=f=200` |
| `aecho` | Echo effect | `aecho=0.8:0.88:60:0.4` |
| `amix` | Mix audio | `amix=inputs=2` |

## Library Selection Guide

| Use Case | Recommended | Reason |
|----------|-------------|--------|
| Simple filters | ez-ffmpeg | Clean API, minimal code |
| Filter chains | ez-ffmpeg | Single `filter_desc()` call |
| Custom pixel processing | ez-ffmpeg + FrameFilter | Rust-native frame access |
| Complex multi-input | ez-ffmpeg | Built-in stream mapping |
| Low-level filter graph | ffmpeg-next | Direct FFmpeg filter API |
| CLI-like operations | ffmpeg-sidecar | Direct FFmpeg access |

## Troubleshooting

### Filter Not Found

```
Error: No such filter: 'xxx'
```

- Check FFmpeg was compiled with the filter: `ffmpeg -filters | grep xxx`
- Some filters require specific build options (e.g., `libass` for subtitles)

### Invalid Filter Graph

```
Error: Invalid filter graph description
```

- Verify filter syntax matches FFmpeg documentation
- Check stream labels match (e.g., `[0:v]` for first input video)
- Ensure all filter outputs are connected

### Format Mismatch

```
Error: Discarding frame with invalid format
```

- Add format conversion: `.filter_desc("format=yuv420p")`
- For audio: `.filter_desc("aformat=sample_fmts=fltp")`

## Related Guides

| Guide | Content |
|-------|---------|
| [video_transcoding.md](video_transcoding.md) | Video format conversion |
| [audio_extraction.md](audio_extraction.md) | Audio processing |
| [batch_processing.md](batch_processing.md) | Processing multiple files |
