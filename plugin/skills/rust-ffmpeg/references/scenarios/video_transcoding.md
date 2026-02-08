# Video Transcoding

**Detection Keywords**: video transcoding, convert video format, how to convert video, video format conversion tutorial, change codec, h264 encode, video compression, format conversion, remux, trim video, resize video, crop video, bitrate, crf, two-pass, codec copy, stream copy
**Aliases**: transcode, video conversion, format change, basic operations, re-encode, remux

Convert video between formats and codecs across all Rust FFmpeg libraries.

## Table of Contents

- [Quick Example](#quick-example-30-seconds)
- [Codec Copy (Remux)](#codec-copy-remux)
- [Change Codec](#change-codec)
- [Quality Control (CRF / CBR / VBR)](#quality-control-crf--cbr--vbr)
- [Change Resolution](#change-resolution)
- [Trim Video](#trim-video)
- [Crop Video](#crop-video)
- [Two-Pass Encoding](#two-pass-encoding)
- [ffmpeg-next Frame-Level Transcoding](#ffmpeg-next-frame-level-transcoding)
- [ffmpeg-next Remux (Stream Copy)](#ffmpeg-next-remux-stream-copy)
- [Library Comparison](#library-comparison)
- [Related Scenarios](#related-scenarios)

> **Dependencies**:
> ```toml
> # For ez-ffmpeg
> ez-ffmpeg = "0.10.0"
>
> # For ffmpeg-next
> ffmpeg-next = "7.1.0"
>
> # For ffmpeg-sidecar
> ffmpeg-sidecar = "2.4.0"
> ```

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

## Codec Copy (Remux)

When you only need to change the container format (e.g., MKV to MP4) without re-encoding, use codec copy. This is 10x faster and causes zero quality loss.

```rust
// ez-ffmpeg — remux MKV to MP4
use ez_ffmpeg::{FfmpegContext, Input, Output};

fn remux(input_path: &str, output_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    FfmpegContext::builder()
        .input(Input::from(input_path))
        .output(Output::from(output_path)
            .set_video_codec("copy")
            .set_audio_codec("copy"))
        .build()?
        .start()?
        .wait()?;
    Ok(())
}
```

```rust
// ffmpeg-sidecar — remux
use ffmpeg_sidecar::command::FfmpegCommand;

fn remux(input_path: &str, output_path: &str) -> anyhow::Result<()> {
    FfmpegCommand::new()
        .input(input_path)
        .codec_video("copy")
        .codec_audio("copy")
        .output(output_path)
        .spawn()?.wait()?;
    Ok(())
}
```

```rust
// ffmpeg-next — remux with stream copy
// Based on the upstream remux.rs example.
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, encoder, format, media, Rational};

fn remux(input_path: &str, output_path: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input_path)?;
    let mut octx = format::output(output_path)?;

    let mut stream_mapping = vec![0i32; ictx.nb_streams() as usize];
    let mut ist_time_bases = vec![Rational(0, 1); ictx.nb_streams() as usize];
    let mut ost_index = 0i32;

    for (ist_index, ist) in ictx.streams().enumerate() {
        let medium = ist.parameters().medium();
        if medium != media::Type::Audio
            && medium != media::Type::Video
            && medium != media::Type::Subtitle
        {
            stream_mapping[ist_index] = -1;
            continue;
        }
        stream_mapping[ist_index] = ost_index;
        ist_time_bases[ist_index] = ist.time_base();
        ost_index += 1;

        let mut ost = octx.add_stream(encoder::find(codec::Id::None))?;
        ost.set_parameters(ist.parameters());
        // Reset codec_tag to avoid container incompatibility
        unsafe { (*ost.parameters().as_mut_ptr()).codec_tag = 0; }
    }

    octx.set_metadata(ictx.metadata().to_owned());
    octx.write_header()?;

    for (stream, mut packet) in ictx.packets() {
        let ist_index = stream.index();
        let ost_index = stream_mapping[ist_index];
        if ost_index < 0 { continue; }

        let ost = octx.stream(ost_index as _).unwrap();
        packet.rescale_ts(ist_time_bases[ist_index], ost.time_base());
        packet.set_position(-1);
        packet.set_stream(ost_index as _);
        packet.write_interleaved(&mut octx)?;
    }

    octx.write_trailer()?;
    Ok(())
}
```

## Change Codec

```rust
// ez-ffmpeg — encode to H.265
use ez_ffmpeg::{FfmpegContext, Input, Output};

fn encode_h265(input_path: &str, output_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    FfmpegContext::builder()
        .input(Input::from(input_path))
        .output(Output::from(output_path)
            .set_video_codec("libx265")
            .set_audio_codec("aac"))
        .build()?
        .start()?
        .wait()?;
    Ok(())
}
```

```rust
// ffmpeg-sidecar
FfmpegCommand::new()
    .input("input.mp4")
    .codec_video("libx265")
    .codec_audio("aac")
    .output("output.mp4")
    .spawn()?.wait()?;
```

## Quality Control (CRF / CBR / VBR)

### CRF (Constant Rate Factor) — Best for File-Based Output

CRF targets consistent visual quality. Lower values = better quality, larger files.

| Codec | Good Range | Default | Visually Lossless |
|-------|-----------|---------|-------------------|
| libx264 | 18–28 | 23 | ~18 |
| libx265 | 22–32 | 28 | ~22 |
| libsvtav1 | 20–35 | 35 | ~20 |

```rust
// ez-ffmpeg — CRF encoding
use ez_ffmpeg::{FfmpegContext, Input, Output};

fn encode_crf(input_path: &str, output_path: &str, crf: &str) -> Result<(), Box<dyn std::error::Error>> {
    FfmpegContext::builder()
        .input(Input::from(input_path))
        .output(Output::from(output_path)
            .set_video_codec("libx264")
            .set_video_codec_opt("crf", crf)       // e.g., "18" for high quality
            .set_video_codec_opt("preset", "medium")
            .set_audio_codec("aac"))
        .build()?
        .start()?
        .wait()?;
    Ok(())
}
```

```rust
// ffmpeg-sidecar — CRF encoding
FfmpegCommand::new()
    .input("input.mp4")
    .codec_video("libx264")
    .args(["-crf", "18", "-preset", "medium"])
    .codec_audio("aac")
    .output("output.mp4")
    .spawn()?.wait()?;
```

### CBR (Constant Bitrate) — Best for Streaming

```rust
// ez-ffmpeg — CBR encoding
FfmpegContext::builder()
    .input(Input::from("input.mp4"))
    .output(Output::from("output.mp4")
        .set_video_codec("libx264")
        .set_video_codec_opt("b", "4M")            // Target 4 Mbps
        .set_video_codec_opt("maxrate", "4M")      // Cap at 4 Mbps
        .set_video_codec_opt("bufsize", "8M")      // VBV buffer size
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;
```

### VBR (Variable Bitrate) — Balanced

```rust
// ez-ffmpeg — VBR encoding
FfmpegContext::builder()
    .input(Input::from("input.mp4"))
    .output(Output::from("output.mp4")
        .set_video_codec("libx264")
        .set_video_codec_opt("b", "4M")            // Target average
        .set_video_codec_opt("maxrate", "6M")      // Allow peaks
        .set_video_codec_opt("bufsize", "8M")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;
```

## Change Resolution

```rust
// ez-ffmpeg — scale to 720p
FfmpegContext::builder()
    .input(Input::from("input.mp4"))
    .output(Output::from("output.mp4")
        .set_video_codec("libx264")
        .filter_desc("scale=1280:720"))
    .build()?.start()?.wait()?;
```

```rust
// ffmpeg-sidecar
FfmpegCommand::new()
    .input("input.mp4")
    .codec_video("libx264")
    .args(["-vf", "scale=1280:720"])
    .output("output.mp4")
    .spawn()?.wait()?;
```

**Preserve aspect ratio** (scale width to 1280, auto-calculate height):
```rust
// Scale width to 1280, height auto (divisible by 2)
.filter_desc("scale=1280:-2")

// ffmpeg-sidecar
.args(["-vf", "scale=1280:-2"])
```

## Trim Video

### Seek Position: Before vs After Input

Place `-ss` **before** the input for fast seek (jumps to nearest keyframe). Place it **after** the input for frame-accurate seek (slower, decodes from start).

```rust
// ez-ffmpeg — fast seek (keyframe-aligned, recommended for most cases)
use ez_ffmpeg::{FfmpegContext, Input, Output};

fn trim_fast(input_path: &str, output_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    FfmpegContext::builder()
        .input(Input::from(input_path)
            .set_start_time_us(60_000_000))             // 60 seconds in microseconds
        .output(Output::from(output_path)
            .set_recording_time_us(120_000_000)          // Duration: 2 minutes (microseconds)
            .set_video_codec("copy")
            .set_audio_codec("copy"))
        .build()?
        .start()?
        .wait()?;
    Ok(())
}
```

```rust
// ffmpeg-sidecar — fast seek
FfmpegCommand::new()
    .args(["-ss", "00:01:00"])   // Before -i = fast keyframe seek
    .input("input.mp4")
    .args(["-t", "00:02:00"])    // Duration
    .codec_video("copy")
    .codec_audio("copy")
    .output("output.mp4")
    .spawn()?.wait()?;
```

```rust
// ffmpeg-sidecar — frame-accurate seek (slower)
FfmpegCommand::new()
    .input("input.mp4")
    .args(["-ss", "00:01:00"])   // After -i = frame-accurate (slower)
    .args(["-t", "00:02:00"])
    .codec_video("libx264")     // Must re-encode for frame accuracy
    .codec_audio("aac")
    .output("output.mp4")
    .spawn()?.wait()?;
```

## Crop Video

```rust
// ez-ffmpeg — crop to 1280x720 starting at (100, 50)
FfmpegContext::builder()
    .input(Input::from("input.mp4"))
    .output(Output::from("output.mp4")
        .set_video_codec("libx264")
        .filter_desc("crop=1280:720:100:50"))  // w:h:x:y
    .build()?.start()?.wait()?;
```

```rust
// ffmpeg-sidecar — auto-detect crop region, then apply
// Step 1: Detect black bars
FfmpegCommand::new()
    .input("input.mp4")
    .args(["-vf", "cropdetect=24:16:0"])
    .args(["-f", "null", "-"])
    .spawn()?.wait()?;
// Parse output for "crop=W:H:X:Y" and apply in step 2

// Step 2: Apply detected crop
FfmpegCommand::new()
    .input("input.mp4")
    .args(["-vf", "crop=1920:800:0:140"])  // Values from step 1
    .codec_video("libx264")
    .output("output.mp4")
    .spawn()?.wait()?;
```

## Two-Pass Encoding

Two-pass encoding analyzes the video in the first pass and optimizes bitrate distribution in the second pass. Use this when targeting a specific file size or bitrate with maximum quality.

```rust
// ez-ffmpeg — two-pass encoding
use ez_ffmpeg::{FfmpegContext, Input, Output};

fn two_pass_encode(
    input_path: &str,
    output_path: &str,
    target_bitrate: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Pass 1: Analyze
    FfmpegContext::builder()
        .input(Input::from(input_path))
        .output(Output::from("/dev/null")    // Discard output (use "NUL" on Windows)
            .set_video_codec("libx264")
            .set_video_codec_opt("b", target_bitrate)
            .set_video_codec_opt("pass", "1")
            .set_format("null"))
        .build()?
        .start()?
        .wait()?;

    // Pass 2: Encode with analysis data
    FfmpegContext::builder()
        .input(Input::from(input_path))
        .output(Output::from(output_path)
            .set_video_codec("libx264")
            .set_video_codec_opt("b", target_bitrate)
            .set_video_codec_opt("pass", "2")
            .set_audio_codec("aac"))
        .build()?
        .start()?
        .wait()?;

    Ok(())
}
```

```rust
// ffmpeg-sidecar — two-pass encoding
use ffmpeg_sidecar::command::FfmpegCommand;

fn two_pass_encode(input: &str, output: &str, bitrate: &str) -> anyhow::Result<()> {
    // Pass 1
    FfmpegCommand::new()
        .overwrite()
        .input(input)
        .codec_video("libx264")
        .args(["-b:v", bitrate, "-pass", "1"])
        .args(["-f", "null"])
        .output(if cfg!(windows) { "NUL" } else { "/dev/null" })
        .spawn()?.wait()?;

    // Pass 2
    FfmpegCommand::new()
        .overwrite()
        .input(input)
        .codec_video("libx264")
        .args(["-b:v", bitrate, "-pass", "2"])
        .codec_audio("aac")
        .output(output)
        .spawn()?.wait()?;

    Ok(())
}
```

## ffmpeg-next Frame-Level Transcoding

ffmpeg-next provides direct control over the decode-encode pipeline. The pattern follows:

1. Open input/output contexts
2. Set up decoder from input stream parameters
3. Set up encoder with target codec and settings
4. Loop: `send_packet` → `receive_frame` → `send_frame` → `receive_packet`
5. Flush decoder and encoder at EOF

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, decoder, encoder, format, frame, media, picture, Dictionary, Packet, Rational};

struct Transcoder {
    ost_index: usize,
    decoder: decoder::Video,
    input_time_base: Rational,
    encoder: encoder::Video,
}

impl Transcoder {
    fn new(
        ist: &format::stream::Stream,
        octx: &mut format::context::Output,
        ost_index: usize,
        x264_opts: Dictionary,
    ) -> Result<Self, ffmpeg::Error> {
        let global_header = octx.format().flags().contains(format::Flags::GLOBAL_HEADER);

        let decoder = codec::context::Context::from_parameters(ist.parameters())?
            .decoder()
            .video()?;

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
        encoder.set_time_base(ist.time_base());

        if global_header {
            encoder.set_flags(codec::Flags::GLOBAL_HEADER);
        }

        let opened = encoder.open_with(x264_opts)?;
        ost.set_parameters(&opened);

        Ok(Self {
            ost_index,
            decoder,
            input_time_base: ist.time_base(),
            encoder: opened,
        })
    }

    fn send_packet_to_decoder(&mut self, packet: &Packet) -> Result<(), ffmpeg::Error> {
        self.decoder.send_packet(packet)
    }

    fn receive_and_process_decoded_frames(
        &mut self,
        octx: &mut format::context::Output,
        ost_time_base: Rational,
    ) -> Result<(), ffmpeg::Error> {
        let mut frame = frame::Video::empty();
        while self.decoder.receive_frame(&mut frame).is_ok() {
            let timestamp = frame.timestamp();
            frame.set_pts(timestamp);
            frame.set_kind(picture::Type::None);
            self.encoder.send_frame(&frame)?;
            self.receive_and_write_packets(octx, ost_time_base)?;
        }
        Ok(())
    }

    fn receive_and_write_packets(
        &mut self,
        octx: &mut format::context::Output,
        ost_time_base: Rational,
    ) -> Result<(), ffmpeg::Error> {
        let mut encoded = Packet::empty();
        while self.encoder.receive_packet(&mut encoded).is_ok() {
            encoded.set_stream(self.ost_index);
            encoded.rescale_ts(self.input_time_base, ost_time_base);
            encoded.write_interleaved(octx)?;
        }
        Ok(())
    }

    fn flush(&mut self, octx: &mut format::context::Output, ost_time_base: Rational) -> Result<(), ffmpeg::Error> {
        self.decoder.send_eof()?;
        self.receive_and_process_decoded_frames(octx, ost_time_base)?;
        self.encoder.send_eof()?;
        self.receive_and_write_packets(octx, ost_time_base)?;
        Ok(())
    }
}
```

Key points for the decode-encode loop:
- **Timestamp handling**: Copy `timestamp()` to `pts`, reset `kind` to `Type::None` so the encoder makes its own keyframe decisions.
- **Stream copy for non-video**: Use `rescale_ts` + `write_interleaved` for audio/subtitle pass-through.
- **Flush at EOF**: Call `send_eof()` on both decoder and encoder to drain buffered frames.
- **GLOBAL_HEADER flag**: Required when the output container stores codec config separately (e.g., MP4).

For the full working example, see [ffmpeg_next/transcoding.md](../ffmpeg_next/transcoding.md).

## ffmpeg-next Remux (Stream Copy)

When no re-encoding is needed, ffmpeg-next can copy packets directly between containers:

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, encoder, format, media, Rational};

fn remux_ffmpeg_next(input_path: &str, output_path: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input_path)?;
    let mut octx = format::output(output_path)?;

    let mut stream_mapping = vec![0i32; ictx.nb_streams() as usize];
    let mut ist_time_bases = vec![Rational(0, 1); ictx.nb_streams() as usize];
    let mut ost_index = 0i32;

    for (i, ist) in ictx.streams().enumerate() {
        let medium = ist.parameters().medium();
        if medium != media::Type::Audio
            && medium != media::Type::Video
            && medium != media::Type::Subtitle
        {
            stream_mapping[i] = -1;
            continue;
        }
        stream_mapping[i] = ost_index;
        ist_time_bases[i] = ist.time_base();
        ost_index += 1;

        let mut ost = octx.add_stream(encoder::find(codec::Id::None))?;
        ost.set_parameters(ist.parameters());
        unsafe { (*ost.parameters().as_mut_ptr()).codec_tag = 0; }
    }

    octx.set_metadata(ictx.metadata().to_owned());
    octx.write_header()?;

    for (stream, mut packet) in ictx.packets() {
        let ist_index = stream.index();
        let ost_index = stream_mapping[ist_index];
        if ost_index < 0 { continue; }

        let ost = octx.stream(ost_index as _).unwrap();
        packet.rescale_ts(ist_time_bases[ist_index], ost.time_base());
        packet.set_position(-1);
        packet.set_stream(ost_index as _);
        packet.write_interleaved(&mut octx)?;
    }

    octx.write_trailer()?;
    Ok(())
}
```

**Note**: The `codec_tag = 0` reset is required to avoid incompatible codec tag errors when remuxing between different container formats (e.g., MKV to MP4).

## Library Comparison

| Aspect | ez-ffmpeg | ffmpeg-next | ffmpeg-sys-next | ffmpeg-sidecar |
|--------|-----------|-------------|-----------------|----------------|
| **Async support** | Yes | No | No | No |
| **Code complexity** | Low | Medium | High | Low |
| **Type safety** | Full | Full | Unsafe | Full |
| **Frame access** | Via FrameFilter | Direct | Direct | Via iterator |
| **Two-pass** | Built-in | Manual | Manual | Built-in |
| **Use when** | General tasks | Codec control | Max performance | No install |

## Related Scenarios

| Scenario | Guide |
|----------|-------|
| Audio extraction | [audio_extraction.md](audio_extraction.md) |
| Hardware acceleration | [hardware_acceleration.md](hardware_acceleration.md) |
| Batch processing | [batch_processing.md](batch_processing.md) |
| Modern codecs (AV1, HEVC) | [modern_codecs.md](modern_codecs.md) |
| GIF creation | [gif_creation.md](gif_creation.md) |
