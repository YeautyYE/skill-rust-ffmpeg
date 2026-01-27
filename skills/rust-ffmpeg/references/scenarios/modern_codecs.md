# Modern Codec Support

**Detection Keywords**: av1, avif, hdr, 10-bit, hdr10, hlg, vp9, hevc, modern codecs, high dynamic range
**Aliases**: next-gen codecs, advanced video, high bit depth, wide color gamut

Modern video codec support including AV1, AVIF, HDR, and 10-bit processing.

## Table of Contents

- [Related Scenarios](#related-scenarios)
- [Quick Start](#quick-start)
- [Decision Guide](#decision-guide)
- [Common Patterns](#common-patterns)
- [Advanced Topics](#advanced-topics)
- [Troubleshooting](#troubleshooting)

## Related Scenarios

| Scenario | Content |
|----------|---------|
| [transcoding.md](transcoding.md) | Standard transcoding patterns |
| [hardware_acceleration.md](hardware_acceleration.md) | Hardware acceleration |

---

## Quick Start

### AV1 Encoding

**Using ez-ffmpeg**:
```rust
use ez_ffmpeg::{FfmpegContext, Output};

FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.webm")
        .set_video_codec("libaom-av1")
        .set_video_codec_opt("crf", "30")
        .set_video_codec_opt("cpu-used", "4"))
    .build()?.start()?.wait()
```

**Using ffmpeg-next** (frame-level control):
```rust
use ffmpeg_next as ffmpeg;

fn encode_av1() -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let codec = ffmpeg::encoder::find_by_name("libaom-av1")
        .ok_or(ffmpeg::Error::EncoderNotFound)?;

    // Configure encoder with AV1-specific options
    let mut encoder = ffmpeg::codec::context::Context::new_with_codec(codec)
        .encoder().video()?;

    // Set AV1 options via private data
    // Note: Full transcoding requires decode loop - see ffmpeg_next/transcoding.md

    Ok(())
}
```

**Using ffmpeg-sidecar**:
```rust
FfmpegCommand::new()
    .input("input.mp4")
    .codec_video("libaom-av1")
    .args(["-crf", "30", "-cpu-used", "4"])
    .output("output.webm")
    .spawn()?.wait()
```

### AVIF Image

**Using ez-ffmpeg**:
```rust
FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("frame.avif")
        .set_video_codec("libaom-av1")
        .set_video_codec_opt("still-picture", "1")
        .set_max_video_frames(1))
    .build()?.start()?.wait()?
```

**Using ffmpeg-sidecar**:
```rust
FfmpegCommand::new()
    .input("video.mp4")
    .codec_video("libaom-av1")
    .args(["-still-picture", "1", "-frames:v", "1"])
    .output("frame.avif")
    .spawn()?.wait()
```

### HDR10 Preserve

**Using ez-ffmpeg**:
```rust
FfmpegContext::builder()
    .input("hdr_input.mp4")
    .output(Output::from("hdr_output.mp4")
        .set_video_codec("libx265")
        .set_video_codec_opt("x265-params",
            "hdr-opt=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc"))
    .build()?.start()?.wait()
```

**Using ffmpeg-sidecar**:
```rust
FfmpegCommand::new()
    .input("hdr_input.mp4")
    .codec_video("libx265")
    .args(["-x265-params", "hdr-opt=1:colorprim=bt2020:transfer=smpte2084"])
    .output("hdr_output.mp4")
    .spawn()?.wait()
```

### 10-bit Encoding

**Using ez-ffmpeg**:
```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .set_video_codec("libx265")
        .set_video_codec_opt("profile", "main10")
        .set_video_codec_opt("pix_fmt", "yuv420p10le"))
    .build()?.start()?.wait()
```

**Using ffmpeg-sidecar**:
```rust
FfmpegCommand::new()
    .input("input.mp4")
    .codec_video("libx265")
    .args(["-profile:v", "main10", "-pix_fmt", "yuv420p10le"])
    .output("output.mp4")
    .spawn()?.wait()
```

**See also**: [ez_ffmpeg/advanced.md](../ez_ffmpeg/advanced.md) for detailed codec configuration

---

## Decision Guide

```
IF need maximum compression → AV1 (slow, best quality)
ELIF need fast modern codec → SVT-AV1 (faster than libaom)
ELIF need HDR support → HEVC with HDR10 metadata
ELIF need 10-bit color → Set profile=main10 + pix_fmt=yuv420p10le
ELIF need image format → AVIF with still-picture=1
ELSE → H.264 for compatibility
```

---

## Common Patterns

| Pattern | ez-ffmpeg | ffmpeg-sidecar |
|---------|-----------|----------------|
| AV1 quality | `.set_video_codec_opt("crf", "30")` | `.args(["-crf", "30"])` |
| Fast AV1 | `.set_video_codec_opt("cpu-used", "6")` | `.args(["-cpu-used", "6"])` |
| AVIF image | `.set_video_codec_opt("still-picture", "1")` | `.args(["-still-picture", "1"])` |
| HDR10 | `.set_video_codec_opt("x265-params", "hdr-opt=1:...")` | `.args(["-x265-params", "hdr-opt=1:..."])` |
| 10-bit | `.set_video_codec_opt("pix_fmt", "yuv420p10le")` | `.args(["-pix_fmt", "yuv420p10le"])` |

---

## Advanced Topics

### Codec Comparison

| Codec | Compression | Speed | 10-bit | HDR | Browser |
|-------|-------------|-------|--------|-----|---------|
| AV1 | Excellent | Slow | ✅ | ✅ | Modern |
| HEVC | Very Good | Medium | ✅ | ✅ | Safari |
| VP9 | Very Good | Medium | ✅ | ✅ | Good |
| H.264 | Good | Fast | ❌ | ❌ | Universal |

### Encoder Options

**AV1 (libaom-av1)**:
- `crf`: 0-63 (23-30 recommended)
- `cpu-used`: 0-8 (4-6 recommended)
- `row-mt`: 0-1 (enable multithreading)

**HEVC (libx265)**:
- `crf`: 0-51 (18-28 recommended)
- `preset`: ultrafast-veryslow
- `profile`: main, main10

**VP9 (libvpx-vp9)**:
- `crf`: 0-63 (30-40 recommended)
- `profile`: 0=8-bit, 2=10-bit
- `row-mt`: 0-1

### Pixel Format Conversion

For 10-bit and HDR workflows, pixel format conversion is often required.

**Using ffmpeg-next** (for frame-level control):
```rust
use ffmpeg_next as ffmpeg;
use ffmpeg::software::scaling::{Context as ScalingContext, Flags};

// Convert 8-bit to 10-bit
let mut scaler = ScalingContext::get(
    ffmpeg::format::Pixel::YUV420P,   // Source: 8-bit
    1920, 1080,
    ffmpeg::format::Pixel::YUV420P10LE, // Dest: 10-bit
    1920, 1080,
    Flags::BILINEAR,
)?;

// Apply to frame
let mut output_frame = ffmpeg::frame::Video::empty();
scaler.run(&input_frame, &mut output_frame)?;
```

**Using ffmpeg-sys-next** (maximum control):
```rust
use ffmpeg_sys_next::{sws_getContext, sws_scale, SWS_BILINEAR};

unsafe {
    let sws_ctx = sws_getContext(
        1920, 1080, AV_PIX_FMT_YUV420P,    // Source
        1920, 1080, AV_PIX_FMT_YUV420P10LE, // Dest
        SWS_BILINEAR as i32,
        std::ptr::null_mut(), std::ptr::null_mut(), std::ptr::null(),
    );
    // See ffmpeg_sys_next/frame_codec.md for complete example
}
```

See [ffmpeg_next/video.md](../ffmpeg_next/video.md) for complete scaling examples.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Unknown encoder 'libaom-av1'" | Reinstall FFmpeg with `--enable-libaom` |
| Very slow AV1 | Use `cpu-used=6` or higher |
| HDR metadata lost | Use `x265-params` with HDR options |
| 10-bit not working | Set `profile=main10` for HEVC, `profile=2` for VP9 |
