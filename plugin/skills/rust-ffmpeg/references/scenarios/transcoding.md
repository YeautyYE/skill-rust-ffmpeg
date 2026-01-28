# Transcoding Scenarios

**Detection Keywords**: multi-output, multiple formats, concat videos, merge videos, watermark, logo overlay, decode encode pipeline, frame processing
**Aliases**: join, combine, multi-format, overlay, text overlay, transcode pipeline

Quick patterns for video transcoding, format conversion, and content manipulation.

## Related Scenarios

| Scenario | Content |
|----------|---------|
| [audio_extraction.md](audio_extraction.md) | First frame, thumbnail, audio extract, metadata |
| [streaming_rtmp_hls.md](streaming_rtmp_hls.md) | Real-time, RTMP, HLS, TCP, device capture |
| [hardware_acceleration.md](hardware_acceleration.md) | Hardware acceleration, progress monitoring |
| [batch_processing.md](batch_processing.md) | Batch transcoding, parallel processing |
| [subtitles.md](subtitles.md) | Subtitle extraction, burning, embedding |

---

## Quick Start

### Basic Format Conversion

**Using ez-ffmpeg**:
```rust
use ez_ffmpeg::FfmpegContext;

FfmpegContext::builder()
    .input("input.mp4")
    .output("output.webm")
    .build()?.start()?.wait()?;
```
**See also**: [ez_ffmpeg/video.md](../ez_ffmpeg/video.md)

**Using ffmpeg-sidecar**:
```rust
use ffmpeg_sidecar::command::FfmpegCommand;

FfmpegCommand::new()
    .input("input.mp4")
    .output("output.webm")
    .spawn()?.wait()?;
```
**See also**: [ffmpeg_sidecar/video.md](../ffmpeg_sidecar/video.md)

---

### Multi-Output (Single Input → Multiple Formats)

**Using ez-ffmpeg**:
```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output("output_720p.mp4")
    .output("output_480p.mp4")
    .build()?.start()?.wait()?;
```
**See also**: [ez_ffmpeg/video.md](../ez_ffmpeg/video.md)

**Using ffmpeg-sidecar**:
```rust
FfmpegCommand::new()
    .input("input.mp4")
    .output("output_720p.mp4")
    .output("output_480p.mp4")
    .spawn()?.wait()?;
```
**See also**: [ffmpeg_sidecar/video.md](../ffmpeg_sidecar/video.md)

---

### Concat Videos

**Using ez-ffmpeg** (simplified - FFmpeg auto-detects streams):
```rust
use ez_ffmpeg::FfmpegContext;

FfmpegContext::builder()
    .input("video1.mp4")
    .input("video2.mp4")
    .input("video3.mp4")
    .filter_desc("concat=n=3:v=1:a=1")  // n=number of inputs
    .output("merged.mp4")
    .build()?.start()?.wait()?;
```

**Using ez-ffmpeg** (explicit stream labels - for complex scenarios):
```rust
use ez_ffmpeg::FfmpegContext;

FfmpegContext::builder()
    .input("video1.mp4")
    .input("video2.mp4")
    .filter_desc("[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]")
    .output("merged.mp4")
    .build()?.start()?.wait()?;
```
**See also**: [ez_ffmpeg/filters.md](../ez_ffmpeg/filters.md)

**Using ffmpeg-sidecar** (simplified):
```rust
FfmpegCommand::new()
    .input("video1.mp4")
    .input("video2.mp4")
    .input("video3.mp4")
    .filter_complex("concat=n=3:v=1:a=1")
    .output("merged.mp4")
    .spawn()?.wait()?;
```

**Using ffmpeg-sidecar** (explicit stream labels):
```rust
FfmpegCommand::new()
    .input("video1.mp4")
    .input("video2.mp4")
    .filter_complex("[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]")
    .map("[v]")
    .map("[a]")
    .output("merged.mp4")
    .spawn()?.wait()?;
```
**See also**: [ffmpeg_sidecar/video.md](../ffmpeg_sidecar/video.md)

> **When to use explicit stream labels**: Use explicit labels (`[0:v][0:a]...`) when inputs have different stream configurations or when you need precise control. Use simplified form (`concat=n=3:v=1:a=1`) when all inputs have matching video and audio streams.

---

### Add Watermark

**Using ez-ffmpeg** (with scaling and transparency):
```rust
use ez_ffmpeg::{FfmpegContext, Output};

FfmpegContext::builder()
    .input("video.mp4")
    .input("logo.png")
    // Scale watermark to 100px width, convert to rgba, apply 70% opacity
    .filter_desc("[1:v]scale=100:-1,format=rgba,lut=a=val*0.7[wm];[0:v][wm]overlay=10:10")
    .output(Output::from("watermarked.mp4"))
    .build()?.start()?.wait()?;
```

**Using ez-ffmpeg** (simple overlay - when logo already has correct size/transparency):
```rust
FfmpegContext::builder()
    .input("video.mp4")
    .input("logo.png")
    .filter_desc("[0:v][1:v]overlay=10:10")
    .output("watermarked.mp4")
    .build()?.start()?.wait()?;
```
**See also**: [ez_ffmpeg/filters.md](../ez_ffmpeg/filters.md)

**Using ffmpeg-sidecar** (with scaling and transparency):
```rust
FfmpegCommand::new()
    .input("video.mp4")
    .input("logo.png")
    .filter_complex("[1:v]scale=100:-1,format=rgba,lut=a=val*0.7[wm];[0:v][wm]overlay=10:10")
    .output("watermarked.mp4")
    .spawn()?.wait()?;
```

**Using ffmpeg-sidecar** (simple overlay):
```rust
FfmpegCommand::new()
    .input("video.mp4")
    .input("logo.png")
    .filter_complex("[0:v][1:v]overlay=10:10")
    .output("watermarked.mp4")
    .spawn()?.wait()?;
```
**See also**: [ffmpeg_sidecar/video.md](../ffmpeg_sidecar/video.md)

> **Watermark filter explained**: `scale=100:-1` resizes to 100px width (height auto), `format=rgba` enables transparency, `lut=a=val*0.7` applies 70% opacity, `overlay=10:10` positions at x=10, y=10 from top-left.

---

### ffmpeg-next Frame-Level Pipeline

ffmpeg-next provides direct decode-encode control for advanced transcoding. The pattern transcodes video to H.264 while stream-copying audio and subtitle tracks:

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, decoder, encoder, format, frame, media, picture, Dictionary, Packet, Rational};
use std::collections::HashMap;

fn transcode_video(
    input_path: &str,
    output_path: &str,
    x264_opts: &str,  // e.g., "preset=medium" or "preset=veryslow,crf=18"
) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input_path)?;
    let mut octx = format::output(output_path)?;

    let best_video = ictx.streams().best(media::Type::Video)
        .map(|s| s.index());

    let mut stream_mapping = vec![-1i32; ictx.nb_streams() as usize];
    let mut ost_index = 0i32;

    // Set up video transcoder + stream copy for audio/subtitles
    for (ist_index, ist) in ictx.streams().enumerate() {
        let medium = ist.parameters().medium();
        if medium != media::Type::Video
            && medium != media::Type::Audio
            && medium != media::Type::Subtitle
        { continue; }

        stream_mapping[ist_index] = ost_index;
        ost_index += 1;

        if Some(ist_index) == best_video {
            // Video: set up transcoder (decoder + encoder)
            // ... see video_transcoding.md for full Transcoder struct
        } else {
            // Audio/subtitle: stream copy
            let mut ost = octx.add_stream(encoder::find(codec::Id::None))?;
            ost.set_parameters(ist.parameters());
            unsafe { (*ost.parameters().as_mut_ptr()).codec_tag = 0; }
        }
    }

    octx.write_header()?;

    // Main packet loop
    for (stream, mut packet) in ictx.packets() {
        let ist_index = stream.index();
        let ost_idx = stream_mapping[ist_index];
        if ost_idx < 0 { continue; }

        if Some(ist_index) == best_video {
            // Decode → re-encode video
            // decoder.send_packet(&packet) → receive_frame → encoder.send_frame → receive_packet
        } else {
            // Stream copy: rescale timestamps and write
            let ost_tb = octx.stream(ost_idx as _).unwrap().time_base();
            packet.rescale_ts(stream.time_base(), ost_tb);
            packet.set_position(-1);
            packet.set_stream(ost_idx as _);
            packet.write_interleaved(&mut octx)?;
        }
    }

    // Flush decoder and encoder EOF
    octx.write_trailer()?;
    Ok(())
}
```

For the complete Transcoder struct with flush handling, see [video_transcoding.md](video_transcoding.md) and [ffmpeg_next/transcoding.md](../ffmpeg_next/transcoding.md).

---

### Custom Frame Processing

**Using ez-ffmpeg FrameFilter**:
```rust
use ez_ffmpeg::filter::frame_filter::FrameFilter;

struct MyFilter;
impl FrameFilter for MyFilter {
    fn media_type(&self) -> AVMediaType { AVMediaType::AVMEDIA_TYPE_VIDEO }
    fn filter_frame(&mut self, frame: Frame, _ctx: &FrameFilterContext)
        -> Result<Option<Frame>, String> {
        Ok(Some(frame))  // Process frame here
    }
}
```
**See also**: [ez_ffmpeg/filters.md](../ez_ffmpeg/filters.md)

---

## Decision Guide

**Choose ez-ffmpeg if**:
- Need custom frame processing via FrameFilter
- Async workflows required
- Production application with multiple outputs
- Simple API preferred

**Choose ffmpeg-next if**:
- Need frame-level decode-encode control
- Need to integrate with custom codec settings (x264 options, etc.)
- Building a video processing pipeline with precise timestamp management

**Choose ffmpeg-sidecar if**:
- CLI-style operations
- Simple transcoding tasks
- Cannot install FFmpeg libraries
- Event-driven processing via stdout parsing

## Common Patterns

| Task | ez-ffmpeg | ffmpeg-sidecar |
|------|-----------|----------------|
| Format conversion | `.output("file.webm")` | `.output("file.webm")` |
| Multi-output | Multiple `.output()` | Multiple `.output()` |
| Concat | `.filter_desc("concat=...")` | `.filter_complex("concat=...")` |
| Watermark | `.filter_desc("overlay=...")` | `.filter_complex("overlay=...")` |
| Custom processing | `FrameFilter` trait | Not available |

## Advanced Topics

For advanced transcoding scenarios, see:
- [Hardware-accelerated encoding](hardware_acceleration.md)
- [Progress monitoring](hardware_acceleration.md)
- [Batch transcoding](batch_processing.md)
- [Complex filter graphs](../ez_ffmpeg/filters.md)
