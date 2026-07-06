# ez-ffmpeg: Filters

**Detection Keywords**: video filter, scale, crop, overlay, filter chain, custom filter, frame filter, wgpu filter, WGSL shader, GPU custom filter, native subtitle burn-in, opengl filter (deprecated)
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
- [GPU Custom Filters (wgpu)](#gpu-custom-filters-wgpu)
- [Native Subtitle Burn-in](#native-subtitle-burn-in-subtitle-feature)
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
use ez_ffmpeg::{FfmpegContext, Input, Output};
use ffmpeg_next::Frame;
use ffmpeg_sys_next::AVMediaType;

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
use ffmpeg_next::Frame;
use ffmpeg_sys_next::AVMediaType;
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
use ffmpeg_next::Frame;
use ffmpeg_sys_next::AVMediaType;
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
use ffmpeg_next::Frame;
use ffmpeg_sys_next::AVMediaType;

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
use ffmpeg_next::Frame;
use ffmpeg_sys_next::AVMediaType;

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

## Custom Tile Filter Example (Advanced)

A complete example showing how to create a custom video filter that tiles the input frame into a 2x2 grid:

**Prerequisites**: Add dependencies to your `Cargo.toml`:
```toml
[dependencies]
ez-ffmpeg = "0.12.0"
ffmpeg-next = "8.1.0"
ffmpeg-sys-next = "8.1.0"
log = "0.4"
env_logger = "0.11"
```

**tile_filter.rs** - The custom filter implementation:
```rust
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ez_ffmpeg::util::ffmpeg_utils::av_err2str;
use ffmpeg_next::Frame;
use ffmpeg_sys_next::{av_frame_copy_props, av_frame_get_buffer, AVMediaType, AVPixelFormat};

/// Creates a 2x2 tiled output from input frame.
/// Input: 320x240 → Output: 640x480
/// Requirements: YUV420P format, even dimensions
pub struct Tile2x2Filter;

impl Tile2x2Filter {
    pub fn new() -> Self { Self }

    fn validate_frame(&self, frame: &Frame) -> Result<(), String> {
        unsafe {
            let width = (*frame.as_ptr()).width;
            let height = (*frame.as_ptr()).height;
            let format: AVPixelFormat = std::mem::transmute((*frame.as_ptr()).format);

            if format != AVPixelFormat::AV_PIX_FMT_YUV420P {
                return Err(format!(
                    "Unsupported pixel format: {:?}. Add .filter_desc(\"format=yuv420p\") before this filter.",
                    format
                ));
            }
            if width % 2 != 0 || height % 2 != 0 {
                return Err(format!("Dimensions must be even. Got: {}x{}", width, height));
            }
        }
        Ok(())
    }

    unsafe fn copy_plane_to_tiles(
        &self, src_data: *const u8, src_linesize: i32,
        dst_data: *mut u8, dst_linesize: i32,
        plane_width: usize, plane_height: usize,
    ) {
        for tile_y in 0..2 {
            for tile_x in 0..2 {
                let dst_offset_x = tile_x * plane_width;
                let dst_offset_y = tile_y * plane_height;
                for row in 0..plane_height {
                    let src_row = src_data.add(row * src_linesize as usize);
                    let dst_row = dst_data.add((dst_offset_y + row) * dst_linesize as usize + dst_offset_x);
                    std::ptr::copy_nonoverlapping(src_row, dst_row, plane_width);
                }
            }
        }
    }
}

impl FrameFilter for Tile2x2Filter {
    fn media_type(&self) -> AVMediaType { AVMediaType::AVMEDIA_TYPE_VIDEO }

    fn init(&mut self, ctx: &FrameFilterContext) -> Result<(), String> {
        log::info!("Initializing Tile2x2Filter: {}", ctx.name());
        Ok(())
    }

    fn filter_frame(&mut self, frame: Frame, _ctx: &FrameFilterContext) -> Result<Option<Frame>, String> {
        unsafe {
            if frame.as_ptr().is_null() || frame.is_empty() {
                return Ok(Some(frame));
            }
        }
        self.validate_frame(&frame)?;

        unsafe {
            let w = (*frame.as_ptr()).width;
            let h = (*frame.as_ptr()).height;

            let mut out = Frame::empty();
            (*out.as_mut_ptr()).width = w * 2;
            (*out.as_mut_ptr()).height = h * 2;
            (*out.as_mut_ptr()).format = (*frame.as_ptr()).format;

            let ret = av_frame_get_buffer(out.as_mut_ptr(), 0);
            if ret < 0 { return Err(format!("Buffer alloc failed: {}", av_err2str(ret))); }

            av_frame_copy_props(out.as_mut_ptr(), frame.as_ptr());

            // Copy Y plane (full resolution)
            self.copy_plane_to_tiles(
                (*frame.as_ptr()).data[0], (*frame.as_ptr()).linesize[0],
                (*out.as_mut_ptr()).data[0], (*out.as_mut_ptr()).linesize[0],
                w as usize, h as usize,
            );
            // Copy U plane (half resolution)
            self.copy_plane_to_tiles(
                (*frame.as_ptr()).data[1], (*frame.as_ptr()).linesize[1],
                (*out.as_mut_ptr()).data[1], (*out.as_mut_ptr()).linesize[1],
                (w / 2) as usize, (h / 2) as usize,
            );
            // Copy V plane (half resolution)
            self.copy_plane_to_tiles(
                (*frame.as_ptr()).data[2], (*frame.as_ptr()).linesize[2],
                (*out.as_mut_ptr()).data[2], (*out.as_mut_ptr()).linesize[2],
                (w / 2) as usize, (h / 2) as usize,
            );

            Ok(Some(out))
        }
    }
}
```

**main.rs** - Using the custom filter:
```rust
mod tile_filter;

use crate::tile_filter::Tile2x2Filter;
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ez_ffmpeg::{FfmpegContext, Output};
use ffmpeg_sys_next::AVMediaType;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    let pipeline: FramePipelineBuilder = AVMediaType::AVMEDIA_TYPE_VIDEO.into();
    let pipeline = pipeline.filter("tile_2x2", Box::new(Tile2x2Filter::new()));

    FfmpegContext::builder()
        .input("input.mp4")
        .filter_desc("format=yuv420p")  // Required: convert to YUV420P
        .output(Output::from("output.mp4").add_frame_pipeline(pipeline))
        .build()?
        .start()?
        .wait()?;

    Ok(())
}
```

**Full example**: See `examples/custom_tile_filter/` in ez-ffmpeg repository

## GPU Custom Filters (wgpu)

Run a custom **WGSL** fragment shader on every frame, on the GPU, and **headless**
— no X11/Wayland/display, so it works on servers. wgpu does GPU-side YUV↔RGB with
the correct BT.601/709 (limited/full) matrix, supports output resize, live
parameter updates, and per-stage timing, and is `Send` without unsafe. It
supersedes the deprecated OpenGL filter.

Enable the feature and add `bytemuck` (for `#[derive(Pod)]` on param structs):
```toml
[dependencies]
ez-ffmpeg = { version = "0.12.0", features = ["wgpu"] }
bytemuck = { version = "1.8", features = ["derive"] }
env_logger = "0.11"
```

Full example — a colour `adjust` shader with **live parameter updates** and
**per-frame GPU timing**:
```rust
use bytemuck::{Pod, Zeroable};
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ez_ffmpeg::wgpu_filter::WgpuFrameFilter;
use ez_ffmpeg::{AVMediaType, FfmpegContext, Input, Output};

#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
struct AdjustParams {
    brightness: f32,
    contrast: f32,
    saturation: f32,
    _pad: f32,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::init();
    let shader = include_str!("shaders/adjust.wgsl"); // WGSL fragment shader

    let mut builder = WgpuFrameFilter::builder().shader_wgsl(shader);
    builder = builder.params(AdjustParams { brightness: 0.0, contrast: 1.1, saturation: 1.0, _pad: 0.0 });
    let filter = builder.build()?;
    let stats = filter.stats_handle();

    // Live parameter updates while the pipeline runs:
    let handle = filter.params_handle::<AdjustParams>()?;
    std::thread::spawn(move || {
        for i in 0..100 {
            handle.set(AdjustParams {
                brightness: 0.0,
                contrast: 1.1,
                saturation: (i as f32 / 50.0 - 1.0).abs() * 2.0,
                _pad: 0.0,
            });
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
    });

    let pipeline: FramePipelineBuilder = AVMediaType::AVMEDIA_TYPE_VIDEO.into();
    let pipeline = pipeline.filter("wgpu_effect", Box::new(filter));

    let output = Output::from("output_adjust.mp4")
        .set_video_codec("libx264")
        .set_audio_codec("aac")
        .add_frame_pipeline(pipeline);

    FfmpegContext::builder()
        .input(Input::from("input.mp4"))
        // WgpuFrameFilter accepts YUV420P/422P/444P (and J variants) or NV12
        // directly; only other formats (e.g. 10-bit) need a `format=yuv420p`
        // filter_desc before the frame pipeline.
        .output(output)
        .build()?
        .start()?
        .wait()?;

    // Per-stage timing collected during the run (WgpuFilterStats is Copy).
    if let Ok(s) = stats.lock() {
        println!(
            "done | {} frames | upload {:.2}ms gpu {:.2}ms download {:.2}ms per frame",
            s.frames,
            s.upload_secs / s.frames.max(1) as f64 * 1000.0,
            s.gpu_secs / s.frames.max(1) as f64 * 1000.0,
            s.download_secs / s.frames.max(1) as f64 * 1000.0,
        );
    }
    Ok(())
}
```

Minimal grayscale WGSL that matches the shader **contract** — fragment entry
point `fs_main`, `@group(0)` bindings `texture1` / `sampler1` / `ez: EzUniforms`.
(A shader with params, like `adjust.wgsl` above, additionally binds them at
`@group(1) @binding(0)`.)
```wgsl
@group(0) @binding(0) var texture1: texture_2d<f32>;
@group(0) @binding(1) var sampler1: sampler;
struct EzUniforms { play_time: f32, width: f32, height: f32, _pad: f32 };
@group(0) @binding(2) var<uniform> ez: EzUniforms;

@fragment
fn fs_main(@location(0) tex_coord: vec2<f32>) -> @location(0) vec4<f32> {
    let color = textureSample(texture1, sampler1, tex_coord);
    let gray = dot(color.rgb, vec3<f32>(0.299, 0.587, 0.114));
    return vec4<f32>(vec3<f32>(gray), 1.0);
}
```

Builder knobs (all on `WgpuFrameFilter::builder()`): `.shader_wgsl(..)`,
`.output_size(w, h)` (GPU resize), `.params(initial)`, `.frames_in_flight(n)`
(default 2 = GPU/CPU overlap; 1 = synchronous). For a shader with no params,
`WgpuFrameFilter::new_simple(shader)?` is a one-liner. Live updates go through
`filter.params_handle::<P>()?` + `handle.set(value)`; timing through
`filter.stats_handle()` → `WgpuFilterStats { frames, upload_secs, gpu_secs, download_secs }`.

### Deprecated: OpenGL

The `opengl` feature and `OpenGLFrameFilter` are `#[deprecated(since = "0.11.0")]`.
Prefer the wgpu filter above: it is headless (no X11/Wayland or Xvfb virtual
framebuffer), does correct GPU-side colour conversion, and is `Send` without
unsafe. Existing OpenGL code still compiles, but new code should use `WgpuFrameFilter`.

## Native Subtitle Burn-in (subtitle feature)

Burn `.srt`/`.ass`/`.vtt` (or in-memory subtitle content) into video with a
pure-Rust renderer — **no `--enable-libass` FFmpeg build flag and no system
libass required**. Enable `features = ["subtitle"]` and attach `SubtitleFilter`
to the output frame pipeline:

```rust
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ez_ffmpeg::subtitle::SubtitleFilter;
use ez_ffmpeg::{AVMediaType, FfmpegContext, Output};

// `srt` is any &str of SubRip content (from a file, DB, or ASR output).
let filter = SubtitleFilter::builder()
    .srt_content(srt)                       // or .file("subs.srt") / .ass_content(script)
    .force_style("FontSize=28,Outline=1")   // FFmpeg force_style semantics
    .build()?;

let pipeline: FramePipelineBuilder = AVMediaType::AVMEDIA_TYPE_VIDEO.into();
FfmpegContext::builder()
    .input("video.mp4")
    .output(
        Output::from("output.mp4")
            .add_frame_pipeline(pipeline.filter("subtitles", Box::new(filter))),
    )
    .build()?.start()?.wait()?;
```

Full walkthrough (source options, fonts, `FontProvider` / `TextShaping`) in
[scenarios/subtitles.md](../scenarios/subtitles.md#burn-subtitles-hardcode).

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

### wgpu Filter Issues

**No GPU adapter found**:
- wgpu selects an available backend (Vulkan/Metal/DX12/GL); make sure GPU drivers
  are installed. On headless Linux, a real or software Vulkan device (e.g. Mesa
  lavapipe) suffices — no X11/Wayland display or Xvfb needed.

**Frame format rejected**:
- `WgpuFrameFilter` accepts YUV420P/422P/444P (and J variants) and NV12 directly.
  For other formats (e.g. 10-bit), add `.filter_desc("format=yuv420p")` before the
  frame pipeline.

**WGSL shader fails to compile**:
- The fragment entry point must be `fs_main` with `@group(0)` bindings
  `texture1` / `sampler1` / `ez: EzUniforms`; bind user params at `@group(1) @binding(0)`.

