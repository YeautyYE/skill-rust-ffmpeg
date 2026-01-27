# Video Transcoding

**Detection Keywords**: video transcoding, convert video format, how to convert video, video format conversion tutorial, change codec, h264 encode, video compression, format conversion, remux, trim video, resize video
**Aliases**: transcode, video conversion, format change, basic operations

Convert video between formats and codecs across all Rust FFmpeg libraries.

## Quick Example (30 seconds)

```rust
// ez-ffmpeg
use ez_ffmpeg::{FfmpegContext, Input, Output};

FfmpegContext::builder()
    .input(Input::from("input.mp4"))
    .output(Output::from("output.mp4").set_video_codec("libx264"))
    .build()?.start()?.wait()?;
```

```rust
// ffmpeg-sidecar
use ffmpeg_sidecar::command::FfmpegCommand;

FfmpegCommand::new()
    .input("input.mp4")
    .codec_video("libx264")
    .output("output.mp4")
    .spawn()?.wait()?;
```

## Library Comparison

| Aspect | ez-ffmpeg | ffmpeg-next | ffmpeg-sys-next | ffmpeg-sidecar |
|--------|-----------|-------------|-----------------|----------------|
| **Async support** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Code complexity** | Low | Medium | High | Low |
| **Type safety** | ✅ Full | ✅ Full | ⚠️ Unsafe | ✅ Full |
| **Frame access** | Via FrameFilter | ✅ Direct | ✅ Direct | Via iterator |
| **Use when** | General tasks | Codec control | Max performance | No install |

## Detailed Examples

For detailed transcoding examples, see library-specific guides:
- **ez-ffmpeg**: [ez_ffmpeg/video.md](../ez_ffmpeg/video.md) - format conversion, trimming, resizing, cropping, codec selection, bitrate control, watermarks, filters
- **ffmpeg-next**: [ffmpeg_next/transcoding.md](../ffmpeg_next/transcoding.md) - frame-by-frame processing, codec-specific operations, timestamp management
- **ffmpeg-sys-next**: [ffmpeg_sys_next/frame_codec.md](../ffmpeg_sys_next/frame_codec.md) - low-level operations
- **ffmpeg-sidecar**: [ffmpeg_sidecar/video.md](../ffmpeg_sidecar/video.md) - CLI wrapper transcoding

## When to Choose

See [Library Selection Guide](../library_selection.md) for detailed criteria.

## Common Patterns

### Change codec
```rust
// ez-ffmpeg
.output(Output::from("out.mp4").set_video_codec("libx265"))

// ffmpeg-sidecar
.codec_video("libx265")
```

### Change resolution
```rust
// ez-ffmpeg
.filter_desc("scale=1280:720")

// ffmpeg-sidecar
.args(["-vf", "scale=1280:720"])
```

### Trim video
```rust
// ez-ffmpeg: Use set_input_opt for time string, or _us methods for microseconds
.input(Input::from("in.mp4")
    .set_input_opt("ss", "00:01:00"))  // Start time
.output(Output::from("out.mp4")
    .set_recording_time_us(120_000_000))  // Duration: 2 minutes in microseconds

// ffmpeg-sidecar
.args(["-ss", "00:01:00", "-t", "00:02:00"])
```

### Change bitrate
```rust
// ez-ffmpeg: Use codec options for bitrate control
.output(Output::from("out.mp4")
    .set_video_codec("libx264")
    .set_video_codec_opt("b", "2M"))  // Set bitrate via codec option

// ffmpeg-sidecar
.args(["-b:v", "2M"])
```

## Related Scenarios

| Scenario | Guide |
|----------|-------|
| Audio extraction | [audio_extraction.md](audio_extraction.md) |
| Hardware acceleration | [hardware_acceleration.md](hardware_acceleration.md) |
| Batch processing | [batch_processing.md](batch_processing.md) |
