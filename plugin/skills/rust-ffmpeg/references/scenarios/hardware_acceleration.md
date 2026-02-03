# Hardware Acceleration

**Detection Keywords**: gpu encoding, hardware acceleration, how to use gpu for video, speed up video encoding, nvenc, videotoolbox, vaapi, quicksync, cuda, hardware decode, d3d12va, amf, vulkan, cuvid, mf, media foundation
**Aliases**: hwaccel, GPU encode, hardware encoder, NVENC, QSV, VideoToolbox, VAAPI

Use GPU and hardware encoders for faster video processing across all Rust FFmpeg libraries.

## Table of Contents

- [Quick Example](#quick-example-30-seconds)
- [Platform Support Matrix](#platform-support-matrix)
- [Runtime Availability Detection](#runtime-availability-detection)
- [Platform-Specific Examples](#platform-specific-examples)
- [ffmpeg-next Hardware Transcoding](#ffmpeg-next-hardware-transcoding)
- [ffmpeg-sidecar Hardware Encoding](#ffmpeg-sidecar-hardware-encoding)
- [Decoder + Encoder Pipeline](#decoder--encoder-pipeline)
- [When to Use Hardware vs Software](#when-to-use-hardware-vs-software)
- [NVENC Preset Tuning](#nvenc-preset-tuning)
- [Library Comparison](#library-comparison)
- [Related Scenarios](#related-scenarios)

> **Dependencies**:
> ```toml
> # For ez-ffmpeg
> ez-ffmpeg = "0.9.0"
>
> # For ffmpeg-next
> ffmpeg-next = "7.1.0"
>
> # For ffmpeg-sidecar
> ffmpeg-sidecar = "2.4.0"
> ```

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

## Platform Support Matrix

| Platform | Decoder hwaccel | Decoder codec | Encoder codec | Notes |
|----------|----------------|---------------|---------------|-------|
| **macOS** | `videotoolbox` | (auto) | `h264_videotoolbox`, `hevc_videotoolbox` | Built-in on all Apple Silicon and recent Intel Macs |
| **NVIDIA** | `cuda` | `h264_cuvid` | `h264_nvenc`, `hevc_nvenc` | Requires NVIDIA GPU + driver |
| **Intel** | `qsv` | `h264_qsv` | `h264_qsv`, `hevc_qsv` | Intel 6th gen+ with iGPU |
| **AMD (Linux)** | `vaapi` | (auto) | `h264_vaapi`, `hevc_vaapi` | Via Mesa/AMDGPU driver |
| **AMD (Windows)** | `vulkan` | `h264_amf` | `h264_amf`, `hevc_amf` | AMF SDK required |
| **Windows (generic)** | `d3d12va` | (auto) | `h264_mf` | Media Foundation (any GPU) |

## Runtime Availability Detection

Check which hardware accelerations are available on the current system before using them:

```rust
// ez-ffmpeg — built-in runtime detection
use ez_ffmpeg::hwaccel::get_hwaccels;

fn detect_hwaccel() {
    let hwaccels = get_hwaccels();
    for accel in &hwaccels {
        println!("Available: {} (type: {:?})", accel.name, accel.hw_device_type);
    }

    // Check for a specific backend
    let has_cuda = hwaccels.iter().any(|a| a.name == "cuda");
    let has_videotoolbox = hwaccels.iter().any(|a| a.name == "videotoolbox");
    let has_vaapi = hwaccels.iter().any(|a| a.name == "vaapi");
    let has_qsv = hwaccels.iter().any(|a| a.name == "qsv");
}
```

```rust
// ffmpeg-sidecar — probe via CLI
use ffmpeg_sidecar::command::FfmpegCommand;

fn detect_hwaccel_sidecar() -> anyhow::Result<Vec<String>> {
    let output = std::process::Command::new("ffmpeg")
        .args(["-hide_banner", "-hwaccels"])
        .output()?;
    let text = String::from_utf8_lossy(&output.stdout);
    let accels: Vec<String> = text
        .lines()
        .skip(1) // Skip "Hardware acceleration methods:" header
        .map(|l| l.trim().to_string())
        .filter(|l| !l.is_empty())
        .collect();
    Ok(accels)
}
```

## Platform-Specific Examples

### macOS — VideoToolbox

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

fn transcode_videotoolbox(input_path: &str, output_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let input = Input::from(input_path)
        .set_hwaccel("videotoolbox");

    let output = Output::from(output_path)
        .set_video_codec("h264_videotoolbox")
        .set_audio_codec("aac");

    FfmpegContext::builder()
        .input(input)
        .output(output)
        .build()?
        .start()?
        .wait()?;

    Ok(())
}
```

### NVIDIA — CUDA decode + NVENC encode

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

fn transcode_nvidia(input_path: &str, output_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let input = Input::from(input_path)
        .set_hwaccel("cuda")
        .set_video_codec("h264_cuvid");  // Hardware decoder

    let output = Output::from(output_path)
        .set_video_codec("h264_nvenc")   // Hardware encoder
        .set_video_codec_opt("preset", "p4")  // Balanced preset
        .set_video_codec_opt("rc", "vbr")     // Variable bitrate
        .set_audio_codec("aac");

    FfmpegContext::builder()
        .input(input)
        .output(output)
        .build()?
        .start()?
        .wait()?;

    Ok(())
}
```

### Intel — QuickSync Video (QSV)

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

fn transcode_qsv(input_path: &str, output_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let input = Input::from(input_path)
        .set_hwaccel("qsv")
        .set_video_codec("h264_qsv");  // QSV decoder

    let output = Output::from(output_path)
        .set_video_codec("h264_qsv")  // QSV encoder
        .set_audio_codec("aac");

    FfmpegContext::builder()
        .input(input)
        .output(output)
        .build()?
        .start()?
        .wait()?;

    Ok(())
}
```

### AMD — Vulkan decode + AMF encode (Windows)

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

fn transcode_amd_windows(input_path: &str, output_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let input = Input::from(input_path)
        .set_hwaccel("vulkan");

    let output = Output::from(output_path)
        .set_video_codec("h264_amf")
        .set_audio_codec("aac");

    FfmpegContext::builder()
        .input(input)
        .output(output)
        .build()?
        .start()?
        .wait()?;

    Ok(())
}
```

### AMD — VAAPI (Linux)

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

fn transcode_amd_linux(input_path: &str, output_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let input = Input::from(input_path)
        .set_hwaccel("vaapi")
        .set_hwaccel_device("/dev/dri/renderD128");

    let output = Output::from(output_path)
        .set_video_codec("h264_vaapi")
        .set_audio_codec("aac");

    FfmpegContext::builder()
        .input(input)
        .output(output)
        .build()?
        .start()?
        .wait()?;

    Ok(())
}
```

### Windows — D3D12VA + Media Foundation

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

fn transcode_windows_generic(input_path: &str, output_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let input = Input::from(input_path)
        .set_hwaccel("d3d12va");

    let output = Output::from(output_path)
        .set_video_codec("h264_mf")  // Media Foundation encoder
        .set_audio_codec("aac");

    FfmpegContext::builder()
        .input(input)
        .output(output)
        .build()?
        .start()?
        .wait()?;

    Ok(())
}
```

## Cross-Platform Auto-Selection

Select the best available hardware encoder at runtime:

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};
use ez_ffmpeg::hwaccel::get_hwaccels;

fn transcode_with_best_hwaccel(
    input_path: &str,
    output_path: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    let hwaccels = get_hwaccels();
    let accel_names: Vec<&str> = hwaccels.iter().map(|a| a.name.as_str()).collect();

    let (hwaccel, encoder) = if accel_names.contains(&"videotoolbox") {
        ("videotoolbox", "h264_videotoolbox")
    } else if accel_names.contains(&"cuda") {
        ("cuda", "h264_nvenc")
    } else if accel_names.contains(&"qsv") {
        ("qsv", "h264_qsv")
    } else if accel_names.contains(&"vaapi") {
        ("vaapi", "h264_vaapi")
    } else {
        // Fallback to software encoding
        ("", "libx264")
    };

    let mut input = Input::from(input_path);
    if !hwaccel.is_empty() {
        input = input.set_hwaccel(hwaccel);
    }

    FfmpegContext::builder()
        .input(input)
        .output(Output::from(output_path)
            .set_video_codec(encoder)
            .set_audio_codec("aac"))
        .build()?
        .start()?
        .wait()?;

    Ok(())
}
```

## ffmpeg-next Software Transcoding (x264)

ffmpeg-next provides frame-level control over transcoding. This example uses software H.264 encoding via libx264 with configurable options. For hardware-accelerated encoders, substitute the codec (e.g., `codec::Id::H264` → a hardware encoder) and adjust options accordingly.

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, encoder, format, frame, media, picture, Dictionary, Packet};

/// Transcode video to H.264 with configurable x264 options.
/// Based on the upstream transcode-x264 example.
fn transcode_h264(
    input_path: &str,
    output_path: &str,
    x264_opts: &str, // e.g., "preset=medium" or "preset=veryslow,crf=18"
) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input_path)?;
    let mut octx = format::output(output_path)?;

    // Parse x264 option string into Dictionary
    let mut opts = Dictionary::new();
    for keyval in x264_opts.split(',') {
        let parts: Vec<&str> = keyval.split('=').collect();
        if parts.len() == 2 {
            opts.set(parts[0], parts[1]);
        }
    }

    // Find best video stream
    let ist = ictx.streams().best(media::Type::Video)
        .ok_or(ffmpeg::Error::StreamNotFound)?;
    let ist_index = ist.index();
    let ist_time_base = ist.time_base();

    // Set up decoder
    let mut decoder = codec::context::Context::from_parameters(ist.parameters())?
        .decoder()
        .video()?;

    // Set up encoder
    let codec = encoder::find(codec::Id::H264)
        .ok_or(ffmpeg::Error::EncoderNotFound)?;
    let mut ost = octx.add_stream(codec)?;
    let mut encoder = codec::context::Context::new_with_codec(codec)
        .encoder()
        .video()?;

    encoder.set_height(decoder.height());
    encoder.set_width(decoder.width());
    encoder.set_aspect_ratio(decoder.aspect_ratio());
    encoder.set_format(decoder.format());
    encoder.set_frame_rate(decoder.frame_rate());
    encoder.set_time_base(ist_time_base);

    if octx.format().flags().contains(format::Flags::GLOBAL_HEADER) {
        encoder.set_flags(codec::Flags::GLOBAL_HEADER);
    }

    let encoder = encoder.open_with(opts)?;
    ost.set_parameters(&encoder);

    // Copy non-video streams (audio, subtitles)
    let mut stream_mapping = vec![-1i32; ictx.nb_streams() as usize];
    stream_mapping[ist_index] = 0;
    let mut ost_idx = 1i32;
    for (i, stream) in ictx.streams().enumerate() {
        if i == ist_index { continue; }
        let medium = stream.parameters().medium();
        if medium == media::Type::Audio || medium == media::Type::Subtitle {
            stream_mapping[i] = ost_idx;
            ost_idx += 1;
            let mut out_stream = octx.add_stream(ffmpeg::encoder::find(codec::Id::None))?;
            out_stream.set_parameters(stream.parameters());
            unsafe { (*out_stream.parameters().as_mut_ptr()).codec_tag = 0; }
        }
    }

    octx.write_header()?;

    // Decode → Encode loop
    let ost_time_base = octx.stream(0).unwrap().time_base();
    for (stream, mut packet) in ictx.packets() {
        let idx = stream.index();
        let ost_idx = stream_mapping[idx];
        if ost_idx < 0 { continue; }

        if idx == ist_index {
            // Video: decode → encode
            decoder.send_packet(&packet)?;
            let mut decoded = frame::Video::empty();
            while decoder.receive_frame(&mut decoded).is_ok() {
                decoded.set_pts(decoded.timestamp());
                decoded.set_kind(picture::Type::None);
                encoder.send_frame(&decoded)?;
                let mut encoded = Packet::empty();
                while encoder.receive_packet(&mut encoded).is_ok() {
                    encoded.set_stream(0);
                    encoded.rescale_ts(ist_time_base, ost_time_base);
                    encoded.write_interleaved(&mut octx)?;
                }
            }
        } else {
            // Audio/subtitle: stream copy
            let ost_tb = octx.stream(ost_idx as _).unwrap().time_base();
            packet.rescale_ts(stream.time_base(), ost_tb);
            packet.set_position(-1);
            packet.set_stream(ost_idx as _);
            packet.write_interleaved(&mut octx)?;
        }
    }

    // Flush encoder
    encoder.send_eof()?;
    let mut encoded = Packet::empty();
    while encoder.receive_packet(&mut encoded).is_ok() {
        encoded.set_stream(0);
        encoded.rescale_ts(ist_time_base, ost_time_base);
        encoded.write_interleaved(&mut octx)?;
    }

    octx.write_trailer()?;
    Ok(())
}
```

For the complete Transcoder struct with reusable encode/flush helpers, see [ffmpeg_next/transcoding.md](../ffmpeg_next/transcoding.md).

## ffmpeg-sidecar Hardware Encoding

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

/// NVIDIA NVENC encoding with quality preset
fn encode_nvenc(input: &str, output: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .hwaccel("cuda")
        .input(input)
        .codec_video("h264_nvenc")
        .args(["-preset", "p4"])          // Quality preset (p1=fastest, p7=best)
        .args(["-rc", "vbr"])             // Variable bitrate
        .args(["-b:v", "5M"])             // Target bitrate
        .codec_audio("aac")
        .output(output)
        .spawn()?.wait()?;
    Ok(())
}

/// macOS VideoToolbox encoding
fn encode_videotoolbox(input: &str, output: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .hwaccel("videotoolbox")
        .input(input)
        .codec_video("h264_videotoolbox")
        .args(["-q:v", "60"])             // Quality (1-100, higher = better)
        .codec_audio("aac")
        .output(output)
        .spawn()?.wait()?;
    Ok(())
}

/// Intel QSV encoding
fn encode_qsv(input: &str, output: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .hwaccel("qsv")
        .input(input)
        .codec_video("h264_qsv")
        .args(["-preset", "medium"])
        .args(["-global_quality", "25"])  // Lower = better quality
        .codec_audio("aac")
        .output(output)
        .spawn()?.wait()?;
    Ok(())
}
```

## Decoder + Encoder Pipeline

Full hardware pipeline: decode on GPU, encode on GPU, avoid CPU-GPU transfers:

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

/// Full NVIDIA hardware pipeline — decode with CUVID, encode with NVENC
fn full_nvidia_pipeline(input_path: &str, output_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let input = Input::from(input_path)
        .set_hwaccel("cuda")
        .set_video_codec("h264_cuvid")               // GPU decoder
        .set_hwaccel_output_format("cuda");           // Keep frames on GPU

    let output = Output::from(output_path)
        .set_video_codec("h264_nvenc")                // GPU encoder
        .set_video_codec_opt("preset", "p4")
        .set_audio_codec("aac");

    FfmpegContext::builder()
        .input(input)
        .output(output)
        .build()?
        .start()?
        .wait()?;

    Ok(())
}
```

## When to Use Hardware vs Software

| Scenario | Recommendation | Reason |
|----------|---------------|--------|
| Batch transcoding (many files) | **Hardware** | GPU parallelism offloads CPU for other tasks |
| Single file, best quality | **Software** (libx264/libx265) | Software encoders produce better quality at same bitrate |
| Real-time capture/streaming | **Hardware** | Low latency, consistent frame delivery |
| No GPU available | **Software** | Only option; use `-preset faster` to trade quality for speed |
| Re-encoding with filters | **Hardware with care** | Some filters require CPU frames; use `hwdownload` if needed |
| Stream copy (no re-encoding) | **Neither** | Use codec copy — no encoding needed, 10x faster |

**Rule of thumb**: Use hardware for speed-sensitive workflows (live streaming, batch jobs). Use software when quality per bit matters most (archival, distribution masters).

## NVENC Preset Tuning

NVIDIA NVENC presets (SDK 12+):

| Preset | Speed | Quality | Use Case |
|--------|-------|---------|----------|
| `p1` | Fastest | Lowest | Real-time streaming |
| `p2` | Very fast | Low | Low-latency capture |
| `p3` | Fast | Below average | Fast transcoding |
| `p4` | Medium | Average | **Balanced default** |
| `p5` | Slow | Above average | High quality transcode |
| `p6` | Slower | High | Near-archive quality |
| `p7` | Slowest | Highest | Archive / mastering |

```rust
// ez-ffmpeg NVENC tuning
let output = Output::from("output.mp4")
    .set_video_codec("h264_nvenc")
    .set_video_codec_opt("preset", "p4")        // Balanced
    .set_video_codec_opt("rc", "vbr")           // Variable bitrate
    .set_video_codec_opt("b", "5M")             // Target 5 Mbps
    .set_video_codec_opt("maxrate", "8M")       // Peak 8 Mbps
    .set_video_codec_opt("bufsize", "10M");      // VBV buffer
```

## Library Comparison

| Aspect | ez-ffmpeg | ffmpeg-next | ffmpeg-sys-next | ffmpeg-sidecar |
|--------|-----------|-------------|-----------------|----------------|
| **Runtime detection** | `get_hwaccels()` API | Manual FFI calls | Manual FFI calls | CLI `-hwaccels` |
| **Async support** | Yes | No | No | No |
| **Code complexity** | Low | Medium | High | Low |
| **Type safety** | Full | Full | Unsafe | Full |
| **Use when** | General tasks | Codec control | Max performance | No install |

## Detailed Library References

- **ez-ffmpeg**: [ez_ffmpeg/advanced.md](../ez_ffmpeg/advanced.md) — platform-specific hardware acceleration, custom I/O
- **ffmpeg-next**: [ffmpeg_next/transcoding.md](../ffmpeg_next/transcoding.md) — hardware decoder setup, frame-level control
- **ffmpeg-sys-next**: [ffmpeg_sys_next/hwaccel.md](../ffmpeg_sys_next/hwaccel.md) — low-level hardware operations
- **ffmpeg-sidecar**: [ffmpeg_sidecar/video.md](../ffmpeg_sidecar/video.md) — CLI wrapper hardware encoding

## Related Scenarios

| Scenario | Guide |
|----------|-------|
| Video transcoding | [video_transcoding.md](video_transcoding.md) |
| Streaming (RTMP & HLS) | [streaming_rtmp_hls.md](streaming_rtmp_hls.md) |
| Batch processing | [batch_processing.md](batch_processing.md) |
| Device capture | [capture.md](capture.md) |
