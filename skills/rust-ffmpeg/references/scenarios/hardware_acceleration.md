# Hardware Acceleration

**Detection Keywords**: gpu encoding, hardware acceleration, how to use gpu for video, speed up video encoding, nvenc, videotoolbox, vaapi, quicksync, cuda, hardware decode
**Aliases**: hwaccel, GPU encode, hardware encoder, NVENC, QSV, VideoToolbox

Use GPU and hardware encoders for faster video processing across all Rust FFmpeg libraries.

## Quick Example (30 seconds)

```rust
// ez-ffmpeg (macOS VideoToolbox)
use ez_ffmpeg::{FfmpegContext, Input, Output};

FfmpegContext::builder()
    .input(Input::from("input.mp4").set_hwaccel("videotoolbox"))
    .output(Output::from("output.mp4").set_video_codec("h264_videotoolbox"))
    .build()?.start()?.wait()?;
```

```rust
// ffmpeg-sidecar (NVIDIA NVENC)
use ffmpeg_sidecar::command::FfmpegCommand;

FfmpegCommand::new()
    .hwaccel("cuda")
    .input("input.mp4")
    .codec_video("h264_nvenc")
    .output("output.mp4")
    .spawn()?.wait()?;
```

## Library Comparison

| Aspect | ez-ffmpeg | ffmpeg-next | ffmpeg-sys-next | ffmpeg-sidecar |
|--------|-----------|-------------|-----------------|----------------|
| **Async support** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Code complexity** | Low | Medium | High | Low |
| **Type safety** | ✅ Full | ✅ Full | ⚠️ Unsafe | ✅ Full |
| **Use when** | General tasks | Codec control | Max performance | No install |

## Detailed Examples

For detailed hardware acceleration examples, see library-specific guides:
- **ez-ffmpeg**: [ez_ffmpeg/advanced.md](../ez_ffmpeg/advanced.md) - platform-specific hardware acceleration, performance tuning
- **ffmpeg-next**: [ffmpeg_next/transcoding.md](../ffmpeg_next/transcoding.md) - hardware decoder setup
- **ffmpeg-sys-next**: [ffmpeg_sys_next/hwaccel.md](../ffmpeg_sys_next/hwaccel.md) - low-level hardware operations
- **ffmpeg-sidecar**: [ffmpeg_sidecar/video.md](../ffmpeg_sidecar/video.md) - CLI wrapper hardware encoding

## When to Choose

See [Library Selection Guide](../library_selection.md) for detailed criteria.

## Platform Support Matrix

| Platform | Decoder | Encoder |
|----------|---------|---------|
| macOS | `videotoolbox` | `h264_videotoolbox` |
| NVIDIA | `cuda` / `cuvid` | `h264_nvenc` / `hevc_nvenc` |
| Intel | `qsv` | `h264_qsv` / `hevc_qsv` |
| AMD (Windows) | `d3d11va` | `h264_amf` / `hevc_amf` |
| AMD (Linux) | `vaapi` | `h264_vaapi` / `hevc_vaapi` |

## Common Patterns

### Platform-specific hardware acceleration
```rust
// macOS VideoToolbox
.set_hwaccel("videotoolbox")
.set_video_codec("h264_videotoolbox")

// NVIDIA NVENC
.set_hwaccel("cuda")
.set_video_codec("h264_nvenc")

// Intel QuickSync
.set_hwaccel("qsv")
.set_video_codec("h264_qsv")
```

### NVENC preset optimization
```rust
// ez-ffmpeg
.set_video_codec_opt("preset", "p4")  // Balanced quality/speed

// ffmpeg-sidecar
.args(["-preset", "p4"])
```

## Related Scenarios

| Scenario | Guide |
|----------|-------|
| Video transcoding | [video_transcoding.md](video_transcoding.md) |
| Streaming | [streaming_rtmp_hls.md](streaming_rtmp_hls.md) |
| Batch processing | [batch_processing.md](batch_processing.md) |
