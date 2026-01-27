# ez-ffmpeg: Filters

**Detection Keywords**: video filter, scale, crop, overlay, filter chain, custom filter, frame filter, opengl filter
**Aliases**: ffmpeg filter, filter graph, video effects

## Table of Contents

- [Related Guides](#related-guides)
- [Built-in FFmpeg Filters](#built-in-ffmpeg-filters)
  - [Common Video Filters](#common-video-filters)
  - [Common Audio Filters](#common-audio-filters)
- [Custom Rust Filters (FrameFilter)](#custom-rust-filters-framefilter)
- [FrameFilter with Frame Request](#framefilter-with-frame-request)
- [Frame Sender Filter](#frame-sender-filter)
- [Custom Audio Filter Example](#custom-audio-filter-example)
- [Audio Filter with Resampling](#audio-filter-with-resampling)
- [OpenGL Filters (GPU Acceleration)](#opengl-filters-gpu-acceleration)
- [Video Effects Example](#video-effects-example)
- [Complex Filter Graphs](#complex-filter-graphs)
- [Troubleshooting](#troubleshooting)

## Related Guides

| Guide | Content |
|-------|---------|
| [video.md](video.md) | Video transcoding, format conversion |
| [audio.md](audio.md) | Audio extraction and processing |
| [advanced.md](advanced.md) | Hardware acceleration, custom filters |

## Built-in FFmpeg Filters

Use `filter_desc()` with standard FFmpeg filter syntax:

```rust
use ez_ffmpeg::FfmpegContext;

// Single filter
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("scale=1280:720")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Filter chain (comma-separated)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("scale=1280:720,fps=30,hue=s=0")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

### Common Video Filters

```rust
// Scale
.filter_desc("scale=1920:1080")
.filter_desc("scale=1280:-1")  // Preserve aspect ratio

// Crop
.filter_desc("crop=640:480:100:50")  // w:h:x:y

// Pad (add borders)
.filter_desc("pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black")

// Rotate
.filter_desc("rotate=PI/2")  // 90 degrees
.filter_desc("transpose=1")  // 90 clockwise

// Flip
.filter_desc("hflip")  // Horizontal
.filter_desc("vflip")  // Vertical

// Color adjustments
.filter_desc("hue=s=0")  // Grayscale
.filter_desc("eq=brightness=0.1:contrast=1.2")

// Blur
.filter_desc("boxblur=5:1")

// Sharpen
.filter_desc("unsharp=5:5:1.0")

// Overlay (watermark)
.filter_desc("[0:v][1:v]overlay=10:10")
```

### Common Audio Filters

```rust
// Volume
.filter_desc("volume=1.5")  // 150%
.filter_desc("volume=0.5")  // 50%

// Resample
.filter_desc("aresample=44100")

// Normalize
.filter_desc("loudnorm")

// Fade
.filter_desc("afade=t=in:st=0:d=3")  // Fade in 3 seconds
.filter_desc("afade=t=out:st=57:d=3")  // Fade out at 57s

// Channel manipulation
.filter_desc("pan=mono|c0=0.5*c0+0.5*c1")  // Stereo to mono
```

## Custom Rust Filters (FrameFilter)

Implement `FrameFilter` trait for custom frame processing:

```rust
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ez_ffmpeg::{FfmpegContext, Input, Output, Frame, AVMediaType};

struct GrayscaleFilter;

impl FrameFilter for GrayscaleFilter {
    fn media_type(&self) -> AVMediaType {
        AVMediaType::AVMEDIA_TYPE_VIDEO
    }

    // Optional: Initialize filter state when pipeline starts
    fn init(&mut self, _ctx: &FrameFilterContext) -> Result<(), String> {
        // Initialize resources, set up state
        Ok(())
    }

    fn filter_frame(
        &mut self,
        frame: Frame,
        _ctx: &FrameFilterContext,
    ) -> Result<Option<Frame>, String> {
        // Access frame data and modify pixels
        // frame.data(0) for Y plane, etc.
        Ok(Some(frame))
    }
}

// Usage on input side
let pipeline = FramePipelineBuilder::from(AVMediaType::AVMEDIA_TYPE_VIDEO)
    .filter("grayscale", Box::new(GrayscaleFilter));

FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .add_frame_pipeline(pipeline))
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Usage on output side
let pipeline = FramePipelineBuilder::from(AVMediaType::AVMEDIA_TYPE_VIDEO)
    .filter("grayscale", Box::new(GrayscaleFilter));

FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .add_frame_pipeline(pipeline))
    .build()?.start()?.wait()?;
```

## FrameFilter with Frame Request

For filters that need to request frames (e.g., looping, frame injection):

**Prerequisites**: Add `crossbeam-channel` to your `Cargo.toml`:
```toml
[dependencies]
crossbeam-channel = "0.5"
```

```rust
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ez_ffmpeg::{Frame, AVMediaType};
use crossbeam_channel::{Receiver, Sender};

struct FrameReceiveFilter {
    receiver: Receiver<Frame>,
    sender: Sender<()>,  // Signal for frame request
}

impl FrameFilter for FrameReceiveFilter {
    fn media_type(&self) -> AVMediaType {
        AVMediaType::AVMEDIA_TYPE_VIDEO
    }

    fn filter_frame(
        &mut self,
        _frame: Frame,
        _ctx: &FrameFilterContext,
    ) -> Result<Option<Frame>, String> {
        // Not used when request_frame is implemented
        Ok(None)
    }

    fn request_frame(
        &mut self,
        _ctx: &FrameFilterContext,
    ) -> Result<Option<Frame>, String> {
        // Signal that we need a frame
        let _ = self.sender.send(());

        // Wait for frame from external source
        match self.receiver.recv() {
            Ok(frame) => Ok(Some(frame)),
            Err(_) => Ok(None),  // Channel closed, end of stream
        }
    }
}
```

## Frame Sender Filter

For sending frames to external processing:

```rust
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ez_ffmpeg::{Frame, AVMediaType};
use crossbeam_channel::Sender;

struct FrameSenderFilter {
    sender: Sender<Frame>,
}

impl FrameFilter for FrameSenderFilter {
    fn media_type(&self) -> AVMediaType {
        AVMediaType::AVMEDIA_TYPE_VIDEO
    }

    fn filter_frame(
        &mut self,
        frame: Frame,
        _ctx: &FrameFilterContext,
    ) -> Result<Option<Frame>, String> {
        // Clone and send frame to external processor
        let cloned = frame.clone();
        if self.sender.send(cloned).is_err() {
            return Err("Failed to send frame".to_string());
        }
        Ok(Some(frame))  // Pass through original
    }
}
```

## Custom Audio Filter Example

```rust
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ez_ffmpeg::{Frame, AVMediaType};

struct VolumeFilter {
    gain: f32,
}

impl FrameFilter for VolumeFilter {
    fn media_type(&self) -> AVMediaType {
        AVMediaType::AVMEDIA_TYPE_AUDIO
    }

    fn filter_frame(
        &mut self,
        mut frame: Frame,
        _ctx: &FrameFilterContext,
    ) -> Result<Option<Frame>, String> {
        // Modify audio samples
        // Access via frame.data(0), frame.samples(), etc.
        Ok(Some(frame))
    }
}
```

## Audio Filter with Resampling

For audio filters that need specific sample format (e.g., float planar for processing):

**Note**: Requires `ffmpeg-next` and `ffmpeg-sys-next` dependencies for resampling and FFmpeg constants.

```rust
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ez_ffmpeg::{Frame, AVMediaType};

struct AudioProcessFilter {
    gain: f32,
    resampler: Option<ffmpeg_next::software::resampling::Context>,
}

impl FrameFilter for AudioProcessFilter {
    fn media_type(&self) -> AVMediaType {
        AVMediaType::AVMEDIA_TYPE_AUDIO
    }

    fn filter_frame(
        &mut self,
        mut frame: Frame,
        _ctx: &FrameFilterContext,
    ) -> Result<Option<Frame>, String> {
        // Get frame properties
        let format = unsafe { (*frame.as_ptr()).format };
        let nb_channels = unsafe { (*frame.as_ptr()).ch_layout.nb_channels };
        let sample_rate = unsafe { (*frame.as_ptr()).sample_rate };
        let ch_layout = unsafe { (*frame.as_ptr()).ch_layout };

        // Initialize resampler if format doesn't match expected (float planar stereo)
        if format != ffmpeg_sys_next::AVSampleFormat::AV_SAMPLE_FMT_FLTP as i32
           || nb_channels != 2 {
            if self.resampler.is_none() {
                let resampler = ffmpeg_next::software::resampling::Context::get(
                    unsafe { std::mem::transmute(format) },
                    ch_layout.into(),
                    sample_rate as u32,
                    ffmpeg_sys_next::AVSampleFormat::AV_SAMPLE_FMT_FLTP.into(),
                    ffmpeg_next::util::channel_layout::ChannelLayout::STEREO,
                    sample_rate as u32,
                ).map_err(|e| format!("Failed to create resampler: {:?}", e))?;
                self.resampler = Some(resampler);
            }

            // Resample frame to expected format
            if let Some(ref mut resampler) = self.resampler {
                let audio_frame: ffmpeg_next::frame::Audio = unsafe {
                    ffmpeg_next::frame::Audio::wrap(frame.as_mut_ptr())
                };
                let mut resampled = ffmpeg_next::frame::Audio::empty();
                resampler.run(&audio_frame, &mut resampled)
                    .map_err(|e| format!("Resample failed: {:?}", e))?;
                frame = Frame::from(resampled);
            }
        }

        // Now process audio in float planar format
        let nb_samples = unsafe { (*frame.as_ptr()).nb_samples } as usize;

        // Process left channel (plane 0)
        let left_data = frame.data(0);
        let left_samples: &mut [f32] = unsafe {
            std::slice::from_raw_parts_mut(left_data as *mut f32, nb_samples)
        };
        for sample in left_samples.iter_mut() {
            *sample *= self.gain;
        }

        // Process right channel (plane 1)
        let right_data = frame.data(1);
        let right_samples: &mut [f32] = unsafe {
            std::slice::from_raw_parts_mut(right_data as *mut f32, nb_samples)
        };
        for sample in right_samples.iter_mut() {
            *sample *= self.gain;
        }

        Ok(Some(frame))
    }
}
```

## OpenGL Filters (GPU Acceleration)

Enable with `features = ["opengl"]`:

```rust
use ez_ffmpeg::opengl::opengl_frame_filter::OpenGLFrameFilter;
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ez_ffmpeg::{FfmpegContext, Output, AVMediaType};

// Fragment shader for video effects (e.g., color inversion)
let fragment_shader = r#"
#version 330 core
in vec2 TexCoords;
out vec4 FragColor;
uniform sampler2D screenTexture;

void main() {
    vec4 color = texture(screenTexture, TexCoords);
    // Example: Invert colors
    FragColor = vec4(1.0 - color.rgb, color.a);
}
"#;

// Create frame pipeline with OpenGL filter
let frame_pipeline_builder: FramePipelineBuilder = AVMediaType::AVMEDIA_TYPE_VIDEO.into();
let filter = OpenGLFrameFilter::new_simple(fragment_shader.to_string()).unwrap();
let frame_pipeline_builder = frame_pipeline_builder.filter("effect", Box::new(filter));

// Apply to output
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .add_frame_pipeline(frame_pipeline_builder))
    .build()?.start()?.wait()?;
```

**Common Shader Effects**:
```glsl
// Grayscale
float gray = dot(color.rgb, vec3(0.299, 0.587, 0.114));
FragColor = vec4(gray, gray, gray, color.a);

// Sepia
vec3 sepia = vec3(
    dot(color.rgb, vec3(0.393, 0.769, 0.189)),
    dot(color.rgb, vec3(0.349, 0.686, 0.168)),
    dot(color.rgb, vec3(0.272, 0.534, 0.131))
);
FragColor = vec4(sepia, color.a);

// Vignette
vec2 center = TexCoords - 0.5;
float vignette = 1.0 - dot(center, center);
FragColor = vec4(color.rgb * vignette, color.a);
```

## Video Effects Example

```rust
use ez_ffmpeg::FfmpegContext;

// Apply multiple effects
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("eq=brightness=0.1:contrast=1.1,hue=h=10")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Vintage effect
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("curves=vintage,vignette")
    .output("vintage.mp4")
    .build()?.start()?.wait()?;

// Slow motion (0.5x speed)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("setpts=2.0*PTS")
    .output("slow.mp4")
    .build()?.start()?.wait()?;

// Speed up (2x speed)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("setpts=0.5*PTS,atempo=2.0")
    .output("fast.mp4")
    .build()?.start()?.wait()?;
```

## Complex Filter Graphs

```rust
use ez_ffmpeg::FfmpegContext;

// Picture-in-picture
FfmpegContext::builder()
    .input("main.mp4")
    .input("pip.mp4")
    .filter_desc("[1:v]scale=320:180[pip];[0:v][pip]overlay=W-w-10:H-h-10")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Side-by-side comparison
FfmpegContext::builder()
    .input("video1.mp4")
    .input("video2.mp4")
    .filter_desc("[0:v]scale=640:360[left];[1:v]scale=640:360[right];[left][right]hstack")
    .output("comparison.mp4")
    .build()?.start()?.wait()?;
```

## Troubleshooting

### Common Filter Issues

**Filter not found**:
```
Error: No such filter: 'xxx'
```
- Check FFmpeg was compiled with the filter. Run `ffmpeg -filters` to list available filters.
- Some filters require specific FFmpeg build options (e.g., `libass` for subtitles).

**Invalid filter graph**:
```
Error: Invalid filter graph description
```
- Verify filter syntax matches FFmpeg documentation.
- Check stream labels match (e.g., `[0:v]` for first input video).
- Ensure output labels are used in stream maps.

**Frame format mismatch**:
```
Error: Discarding frame with invalid format
```
- Add format conversion filter: `.filter_desc("format=yuv420p")`
- For audio: `.filter_desc("aformat=sample_fmts=fltp")`

### FrameFilter Issues

**Filter not receiving frames**:
- Verify `media_type()` returns correct type (`AVMEDIA_TYPE_VIDEO` or `AVMEDIA_TYPE_AUDIO`).
- Check pipeline is attached to correct input/output.
- Ensure `filter_frame()` returns `Ok(Some(frame))` to pass frames through.

**Channel communication deadlock** (with crossbeam):
- Use bounded channels with appropriate capacity.
- Ensure sender/receiver are in separate threads.
- Handle channel closure gracefully in `request_frame()`.

### OpenGL Filter Issues

**OpenGL context not available**:
- Ensure `opengl` feature is enabled in `Cargo.toml`.
- On headless servers, use virtual framebuffer (Xvfb on Linux).
- Check GPU drivers are properly installed.

