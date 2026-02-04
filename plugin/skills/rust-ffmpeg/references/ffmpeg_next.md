# ffmpeg-next Reference

**Detection Keywords**: rust bindings, medium-level API, codec control, frame access, safe wrapper, decoder encoder
**Aliases**: ffmpeg-next, ffmpeg_next, safe bindings

**Crate**: https://crates.io/crates/ffmpeg-next
**Documentation**: https://docs.rs/ffmpeg-next
**Version**: 7.x (tracks FFmpeg major versions)
**FFmpeg Compatibility**: 7.x (libavcodec 61.x)

## Related Guides

| Guide | Content |
|-------|---------|
| [ez_ffmpeg.md](ez_ffmpeg.md) | High-level API (sync and async) |
| [ffmpeg_sys_next.md](ffmpeg_sys_next.md) | Low-level unsafe FFI |
| [installation.md](installation.md) | Platform-specific setup |

## Table of Contents

- [Prerequisites](#prerequisites)
- [Overview](#overview)
- [When to Use](#when-to-use)
- [Core API Reference](#core-api-reference)
- [Error Handling](#error-handling)
- [Thread Safety](#thread-safety)
- [Performance Tips](#performance-tips)
- [Common Pitfalls](#common-pitfalls)
- [Mixing with ez-ffmpeg](#mixing-with-ez-ffmpeg)

### Topic Guides

| Guide | Description |
|-------|-------------|
| [Video Core](ffmpeg_next/video.md) | Seeking, scaling context, timestamp management (PTS/DTS) |
| [Video Transcoding](ffmpeg_next/transcoding.md) | H.264 transcoding, frame extraction, thumbnail generation |
| [Video Output](ffmpeg_next/output.md) | PNG/JPEG saving, container remuxing, hardware acceleration |
| [Audio Operations](ffmpeg_next/audio.md) | Resampling, format conversion, audio transcoding with filters |
| [Filter Graph](ffmpeg_next/filters.md) | Audio/video filter pipelines, common filters reference |
| [Network Streaming](ffmpeg_next/streaming.md) | RTMP/HLS input/output, network protocols |
| [Metadata Operations](ffmpeg_next/metadata.md) | Reading metadata, codec info, chapter handling |
| [Low-Level FFI](ffmpeg_next/ffi.md) | Direct FFmpeg C API access via ffmpeg_sys_next |

## Prerequisites

> **Full installation guide**: See [installation.md](installation.md) for comprehensive platform-specific instructions, troubleshooting, Docker/CI configuration, and the `build` feature fallback.

### Quick Start

**System dependencies** (one-time setup, see [installation.md](installation.md) for complete list):
- **macOS**: `brew install ffmpeg pkg-config`
- **Linux**: `sudo apt install libavcodec-dev libavformat-dev libavutil-dev libavfilter-dev libswscale-dev libswresample-dev pkg-config clang`
- **Windows**: See [installation.md](installation.md) for vcpkg setup

### Cargo.toml

```toml
[dependencies]
ffmpeg-next = "7.1.0"
```

**Feature options**:
```toml
# Static linking (bundles pre-built FFmpeg libraries)
ffmpeg-next = { version = "7.1.0", features = ["static"] }

# Build from source (last resort when system FFmpeg unavailable)
ffmpeg-next = { version = "7.1.0", features = ["build"] }
```

> **Feature hierarchy**: `build` includes `static`. The `static` feature links against pre-built libraries; `build` compiles FFmpeg from source. See [installation.md](installation.md) for detailed `build` feature usage and license options.

## Overview

ffmpeg-next provides safe Rust bindings for FFmpeg, offering medium-level control over multimedia processing. It wraps the FFmpeg C API with Rust's type safety and memory management.

**Key characteristics**:
- 100% safe API (no unsafe blocks required for normal usage)
- Direct access to codec parameters, frame data, and stream information
- Pixel format conversion via `software::scaling::Context`
- Audio resampling via `software::resampling::Context`
- Filter graph support for complex processing pipelines

## When to Use

### Primary Use Cases

1. **Codec fine-grained control**
   - Custom GOP size, bitrate modes, profile/level settings
   - Encoder-specific parameters (x264 presets, CRF values)
   - Decoder configuration

2. **Format handling**
   - Container remuxing without re-encoding
   - Stream selection and mapping
   - Metadata manipulation

3. **Pixel/Sample conversion**
   - `scaling::Context` for video format conversion
   - `resampling::Context` for audio sample rate/format conversion
   - Color space transformations

4. **Frame-level operations**
   - Direct frame data access (`frame.data()`, `frame.linesize()`)
   - Timestamp manipulation (PTS, DTS)
   - Frame buffer management

5. **Packet-level operations**
   - Stream copying without decoding
   - PTS gap detection and handling
   - Seeking and clipping

### Decision Matrix

| Scenario | Recommendation |
|----------|----------------|
| Standard transcoding, streaming | ez-ffmpeg |
| Custom encoder parameters | ffmpeg-next |
| Pixel format conversion in custom filter | ffmpeg-next within ez-ffmpeg FrameFilter |
| Audio resampling with specific parameters | ffmpeg-next within ez-ffmpeg FrameFilter |
| Container remuxing | ffmpeg-next (or ez-ffmpeg) |
| Metadata reading/writing | Either (ffmpeg-next for more detail) |
| Packet-level clipping | ffmpeg-next |
| Audio mixing with SIMD | ffmpeg-next + ffmpeg-sys-next |

## Core API Reference

> **Note**: The following code snippets assume you have declared the crate alias:
> ```rust
> extern crate ffmpeg_next as ffmpeg;
> ```
> This allows using `ffmpeg::` throughout your code instead of `ffmpeg_next::`.

### Initialization

```rust
extern crate ffmpeg_next as ffmpeg;

fn main() -> Result<(), ffmpeg::Error> {
    // Required: Initialize FFmpeg library (safe to call multiple times)
    ffmpeg::init()?;

    // Optional: Set log level
    ffmpeg::log::set_level(ffmpeg::log::Level::Warning);

    Ok(())
}
```

### Input/Output Context

```rust
use ffmpeg::{format, media};

// Open input file
let mut ictx = format::input("input.mp4")?;

// Open output file
let mut octx = format::output("output.mp4")?;

// Access streams
for stream in ictx.streams() {
    println!("Stream {}: {:?}", stream.index(), stream.parameters().medium());
}

// Find best stream by type
if let Some(video_stream) = ictx.streams().best(media::Type::Video) {
    println!("Best video stream: {}", video_stream.index());
}

// Get container duration (in AV_TIME_BASE units)
let duration_secs = ictx.duration() as f64 / f64::from(ffmpeg::ffi::AV_TIME_BASE);
```

### Decoder Setup

```rust
use ffmpeg::{codec, decoder};

let stream = ictx.streams().best(media::Type::Video).unwrap();
let context = codec::context::Context::from_parameters(stream.parameters())?;
let mut decoder = context.decoder().video()?;

// Access decoder properties
println!("Width: {}, Height: {}", decoder.width(), decoder.height());
println!("Format: {:?}", decoder.format());
println!("Frame rate: {:?}", decoder.frame_rate());
```

### Encoder Setup

```rust
use ffmpeg::{codec, encoder, Dictionary};

// Find encoder by codec ID
let codec = encoder::find(codec::Id::H264).unwrap();

// Create encoder context
let mut encoder = codec::context::Context::new_with_codec(codec)
    .encoder()
    .video()?;

// Configure encoder
encoder.set_width(1920);
encoder.set_height(1080);
encoder.set_format(ffmpeg::format::Pixel::YUV420P);
encoder.set_time_base(ffmpeg::Rational(1, 30));
encoder.set_frame_rate(Some(ffmpeg::Rational(30, 1)));

// Set encoder options (e.g., x264 preset)
let mut opts = Dictionary::new();
opts.set("preset", "medium");
opts.set("crf", "23");

let encoder = encoder.open_with(opts)?;
```

### Packet Processing

```rust
use ffmpeg::Packet;

// Note: This assumes a stream_mapping has been created and output streams
// have been added with add_stream(), and write_header() has been called.
// See the complete remuxing example in metadata.md for full context.

// Create stream mapping: input_index -> output_index (-1 if skipped)
let mut stream_mapping: Vec<i32> = vec![-1; ictx.nb_streams() as usize];
let mut ist_time_bases = vec![ffmpeg::Rational(0, 1); ictx.nb_streams() as usize];
let mut ost_index = 0i32;

for (ist_index, ist) in ictx.streams().enumerate() {
    // Only remux audio, video, subtitle streams
    let medium = ist.parameters().medium();
    if medium != media::Type::Audio
        && medium != media::Type::Video
        && medium != media::Type::Subtitle {
        continue;
    }
    stream_mapping[ist_index] = ost_index;
    ist_time_bases[ist_index] = ist.time_base();
    ost_index += 1;
    // Add output stream...
}

octx.write_header()?;

// Process packets with proper stream mapping
for (stream, mut packet) in ictx.packets() {
    let ist_index = stream.index();
    let ost_index = stream_mapping[ist_index];
    if ost_index < 0 {
        continue; // Skip unmapped streams
    }

    let ost = octx.stream(ost_index as usize).unwrap();
    packet.rescale_ts(ist_time_bases[ist_index], ost.time_base());
    packet.set_position(-1);
    packet.set_stream(ost_index as usize);
    packet.write_interleaved(&mut octx)?;
}
```

### Frame Processing

```rust
use ffmpeg::frame;

// Video frame
let mut video_frame = frame::Video::empty();
while decoder.receive_frame(&mut video_frame).is_ok() {
    let pts = video_frame.timestamp();
    let width = video_frame.width();
    let height = video_frame.height();

    // Access raw data
    let plane0 = video_frame.data(0);  // Y plane for YUV
    let linesize = video_frame.stride(0);

    // Process frame...
}

// Audio frame
let mut audio_frame = frame::Audio::empty();
while decoder.receive_frame(&mut audio_frame).is_ok() {
    let samples = audio_frame.samples();
    let rate = audio_frame.rate();
    let channels = audio_frame.channels();

    // Access raw data
    let data = audio_frame.data(0);
}
```

## Error Handling

ffmpeg-next uses a custom `Error` type that wraps FFmpeg error codes:

```rust
use ffmpeg::Error;

fn handle_errors() -> Result<(), Error> {
    let result = ffmpeg::format::input("nonexistent.mp4");

    match result {
        Ok(_ctx) => { /* success */ }
        Err(Error::InvalidData) => println!("Invalid or corrupt file"),
        Err(Error::StreamNotFound) => println!("No suitable stream found"),
        Err(Error::DecoderNotFound) => println!("Required decoder not available"),
        Err(Error::EncoderNotFound) => println!("Required encoder not available"),
        Err(Error::Eof) => println!("End of file reached"),
        Err(e) => println!("Other error: {}", e),
    }

    Ok(())
}
```

## EAGAIN/EOF Handling Patterns

FFmpeg codecs use a non-blocking send/receive pattern. Understanding EAGAIN and EOF is critical:

```rust
use ffmpeg::{decoder, encoder, frame, Error, Packet};

/// Robust decode loop with EAGAIN handling
fn decode_frames(
    decoder: &mut decoder::Video,
    packet: &Packet,
) -> Result<Vec<frame::Video>, Error> {
    let mut frames = Vec::new();

    // Send packet to decoder (may return EAGAIN if internal buffer full)
    match decoder.send_packet(packet) {
        Ok(()) => {}
        Err(Error::Other { errno }) if errno == ffmpeg::error::EAGAIN => {
            // Decoder buffer full, drain first then retry
            drain_decoder(decoder, &mut frames)?;
            decoder.send_packet(packet)?;
        }
        Err(e) => return Err(e),
    }

    drain_decoder(decoder, &mut frames)?;
    Ok(frames)
}

/// Drain all available frames from decoder
fn drain_decoder(
    decoder: &mut decoder::Video,
    frames: &mut Vec<frame::Video>,
) -> Result<(), Error> {
    let mut frame = frame::Video::empty();
    loop {
        match decoder.receive_frame(&mut frame) {
            Ok(()) => {
                frames.push(frame.clone());
            }
            Err(Error::Other { errno }) if errno == ffmpeg::error::EAGAIN => {
                // No more frames available, need more input
                break;
            }
            Err(Error::Eof) => {
                // Decoder fully flushed
                break;
            }
            Err(e) => return Err(e),
        }
    }
    Ok(())
}

/// Flush decoder at end of stream
fn flush_decoder(
    decoder: &mut decoder::Video,
) -> Result<Vec<frame::Video>, Error> {
    let mut frames = Vec::new();

    // Signal EOF to decoder
    decoder.send_eof()?;

    // Drain remaining frames
    drain_decoder(decoder, &mut frames)?;
    Ok(frames)
}
```

**Key patterns**:
- `send_packet` → `receive_frame` loop for decoding
- `send_frame` → `receive_packet` loop for encoding
- EAGAIN means "try again later" - drain output first
- EOF signals end of stream - must flush remaining data
- Always clone frames if storing them (they're reused internally)

## Thread Safety

- **Input/Output contexts**: Not thread-safe, use one per thread
- **Decoders/Encoders**: Not thread-safe, use one per thread
- **Scaling/Resampling contexts**: Not thread-safe, create per-thread instances
- **Global initialization**: `ffmpeg::init()` is safe to call multiple times

For multi-threaded processing, create separate contexts per thread or use channels to coordinate.

## Performance Tips

1. **Reuse contexts**: Create scaling/resampling contexts once, reuse for all frames
2. **Choose appropriate scaling flags**: `FAST_BILINEAR` for speed, `LANCZOS` for quality
3. **Avoid unnecessary conversions**: Keep native pixel/sample formats when possible
4. **Use stream copy when possible**: Remux instead of transcode when formats are compatible
5. **Batch operations**: Process multiple files in sequence rather than parallel for memory efficiency
6. **Lazy initialization**: Initialize scalers/resamplers on first frame when dimensions become known

## Common Pitfalls

1. **Forgetting `ffmpeg::init()`**: Always call before any FFmpeg operations
2. **Time base confusion**: Always rescale timestamps when copying between streams
3. **Codec tag issues**: Reset `codec_tag = 0` when remuxing to different containers
4. **Missing EOF handling**: Always send EOF to decoder/encoder and flush remaining frames
5. **Frame ownership**: Frames are reused; copy data if needed for later use
6. **Stride vs width**: When accessing raw frame data, use stride (linesize) not width

## Mixing with ez-ffmpeg

**Common pattern**: Use ez-ffmpeg for orchestration, ffmpeg-next for specific operations within FrameFilter implementations.

```rust
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ffmpeg_next::software::scaling::{Context as ScalingContext, Flags};
use ffmpeg_next::format::Pixel;
use ffmpeg_next::Frame;
use ffmpeg_sys_next::AVMediaType;

struct FormatConverter {
    scaler: Option<ScalingContext>,
    target_format: Pixel,
}

impl FrameFilter for FormatConverter {
    fn media_type(&self) -> AVMediaType {
        AVMediaType::AVMEDIA_TYPE_VIDEO
    }

    fn filter_frame(
        &mut self,
        frame: Frame,
        _ctx: &FrameFilterContext,
    ) -> Result<Option<Frame>, String> {
        // Convert generic Frame to Video for scaling operations
        let video_frame: ffmpeg_next::frame::Video = unsafe {
            ffmpeg_next::frame::Video::wrap(frame.as_ptr() as *mut _)
        };

        // Initialize scaler on first frame (lazy init)
        if self.scaler.is_none() {
            self.scaler = Some(ScalingContext::get(
                video_frame.format(),
                video_frame.width(),
                video_frame.height(),
                self.target_format,
                video_frame.width(),
                video_frame.height(),
                Flags::FAST_BILINEAR | Flags::BITEXACT,
            ).map_err(|e| e.to_string())?);
        }

        let mut output = ffmpeg_next::frame::Video::empty();
        self.scaler.as_mut().unwrap()
            .run(&video_frame, &mut output)
            .map_err(|e| e.to_string())?;

        Ok(Some(Frame::from(output)))
    }
}
```

## Troubleshooting

### Common Issues

**Linker errors on build**:
- Ensure FFmpeg development libraries are installed
- Set `PKG_CONFIG_PATH` to FFmpeg's pkgconfig directory
- See [installation.md](installation.md) for platform-specific setup

**"Decoder/Encoder not found"**:
- FFmpeg may not be compiled with the codec
- Check available codecs: `ffmpeg -encoders | grep libx264`
- Reinstall FFmpeg with required codec support

**"Invalid data found when processing input"**:
- File may be corrupted or format not recognized
- Try specifying format explicitly in code
- Verify file plays in VLC or ffplay

**Memory leaks or crashes**:
- Ensure `ffmpeg::init()` is called once at startup
- Drop codec contexts before format contexts
- Use `ffmpeg::log::set_level()` to debug

**Thread safety issues**:
- FFmpeg contexts are not Send/Sync by default
- Process in single thread or use channels to transfer data
- Clone frame data, not frame references, across threads
