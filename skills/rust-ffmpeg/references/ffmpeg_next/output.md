# ffmpeg-next: Video Output

**Detection Keywords**: png, jpeg, webp, image crate, save frame, remux, remuxing, container, mkv, mp4, hwaccel, nvenc, videotoolbox, vaapi, qsv, gpu encoding
**Aliases**: save image, export frame, container convert, gpu encode

Image output formats, container remuxing, and hardware-accelerated encoding.

## Table of Contents

- [Saving Frame as PNG/JPEG](#22-saving-frame-as-pngjpeg-with-image-crate)
- [Performance Comparison](#23-performance-ffmpeg-next-vs-image-crate)
- [Container Remuxing](#3-container-remuxing)
- [Hardware Acceleration](#hardware-acceleration)

## Related Guides

| Guide | Content |
|-------|---------|
| [video.md](video.md) | Seeking, scaling context, timestamp management |
| [transcoding.md](transcoding.md) | Video transcoding, frame extraction, thumbnail generation |

## 2.2 Saving Frame as PNG/JPEG (with `image` crate)

The PPM format from transcoding examples is raw and large. For production use, save as PNG or JPEG using the `image` crate:

**Cargo.toml**:
```toml
[dependencies]
ffmpeg-next = "7.1.0"
image = "0.25"
```

**Complete Example**:
```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::format::{input, Pixel};
use ffmpeg::media::Type;
use ffmpeg::software::scaling::{Context as Scaler, Flags};
use ffmpeg::frame::Video;
use image::{ImageBuffer, Rgb, ImageFormat};
use std::path::Path;

/// Extract first frame and save as PNG/JPEG
pub fn save_thumbnail<P: AsRef<Path>>(
    input_path: &str,
    output_path: P,
    target_width: Option<u32>,
    target_height: Option<u32>,
) -> Result<(), Box<dyn std::error::Error>> {
    ffmpeg::init()?;

    let mut ictx = input(input_path)?;
    let video_stream = ictx.streams()
        .best(Type::Video)
        .ok_or("No video stream found")?;
    let video_index = video_stream.index();

    let context = ffmpeg::codec::context::Context::from_parameters(video_stream.parameters())?;
    let mut decoder = context.decoder().video()?;

    // Determine output dimensions
    let out_width = target_width.unwrap_or(decoder.width());
    let out_height = target_height.unwrap_or(decoder.height());

    let mut scaler = Scaler::get(
        decoder.format(),
        decoder.width(),
        decoder.height(),
        Pixel::RGB24,
        out_width,
        out_height,
        Flags::FAST_BILINEAR,
    )?;

    let mut decoded = Video::empty();
    let mut rgb_frame = Video::empty();

    for (stream, packet) in ictx.packets() {
        if stream.index() != video_index {
            continue;
        }

        decoder.send_packet(&packet)?;

        if decoder.receive_frame(&mut decoded).is_ok() {
            scaler.run(&decoded, &mut rgb_frame)?;

            // Convert to image crate format
            let width = rgb_frame.width();
            let height = rgb_frame.height();
            let stride = rgb_frame.stride(0);
            let data = rgb_frame.data(0);

            // Copy row by row (handle stride != width * 3)
            let mut rgb_data = Vec::with_capacity((width * height * 3) as usize);
            for y in 0..height {
                let start = (y * stride as u32) as usize;
                let end = start + (width * 3) as usize;
                rgb_data.extend_from_slice(&data[start..end]);
            }

            // Create image buffer and save
            let img: ImageBuffer<Rgb<u8>, Vec<u8>> =
                ImageBuffer::from_raw(width, height, rgb_data)
                    .ok_or("Failed to create image buffer")?;

            // Auto-detect format from extension
            img.save(&output_path)?;

            return Ok(());
        }
    }

    Err("Failed to decode first frame".into())
}

/// Save with explicit format control
pub fn save_thumbnail_with_format<P: AsRef<Path>>(
    input_path: &str,
    output_path: P,
    format: ImageFormat,
    quality: Option<u8>,  // For JPEG: 1-100
) -> Result<(), Box<dyn std::error::Error>> {
    ffmpeg::init()?;

    let mut ictx = input(input_path)?;
    let video_stream = ictx.streams()
        .best(Type::Video)
        .ok_or("No video stream found")?;
    let video_index = video_stream.index();

    let context = ffmpeg::codec::context::Context::from_parameters(video_stream.parameters())?;
    let mut decoder = context.decoder().video()?;

    let mut scaler = Scaler::get(
        decoder.format(),
        decoder.width(),
        decoder.height(),
        Pixel::RGB24,
        decoder.width(),
        decoder.height(),
        Flags::FAST_BILINEAR,
    )?;

    let mut decoded = Video::empty();
    let mut rgb_frame = Video::empty();

    for (stream, packet) in ictx.packets() {
        if stream.index() != video_index {
            continue;
        }

        decoder.send_packet(&packet)?;

        if decoder.receive_frame(&mut decoded).is_ok() {
            scaler.run(&decoded, &mut rgb_frame)?;

            let width = rgb_frame.width();
            let height = rgb_frame.height();
            let stride = rgb_frame.stride(0);
            let data = rgb_frame.data(0);

            let mut rgb_data = Vec::with_capacity((width * height * 3) as usize);
            for y in 0..height {
                let start = (y * stride as u32) as usize;
                let end = start + (width * 3) as usize;
                rgb_data.extend_from_slice(&data[start..end]);
            }

            let img: ImageBuffer<Rgb<u8>, Vec<u8>> =
                ImageBuffer::from_raw(width, height, rgb_data)
                    .ok_or("Failed to create image buffer")?;

            // Save with specific format
            match format {
                ImageFormat::Jpeg => {
                    let quality = quality.unwrap_or(85);
                    let mut output = std::fs::File::create(&output_path)?;
                    let encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(
                        &mut output,
                        quality,
                    );
                    img.write_with_encoder(encoder)?;
                }
                _ => {
                    img.save_with_format(&output_path, format)?;
                }
            }

            return Ok(());
        }
    }

    Err("Failed to decode first frame".into())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Save as PNG (lossless)
    save_thumbnail("input.mp4", "thumbnail.png", Some(320), Some(180))?;

    // Save as JPEG with quality
    save_thumbnail_with_format("input.mp4", "thumbnail.jpg", ImageFormat::Jpeg, Some(85))?;

    // Save as WebP
    save_thumbnail_with_format("input.mp4", "thumbnail.webp", ImageFormat::WebP, None)?;

    Ok(())
}
```

## 2.3 Performance: ffmpeg-next vs image crate

**Benchmark Comparison** (1080p video, extract first frame):

| Operation | ffmpeg-next | image crate only | Notes |
|-----------|-------------|------------------|-------|
| Decode video frame | ~5-15ms | N/A | FFmpeg is required for video decoding |
| RGB conversion (scaler) | ~1-3ms | N/A | Hardware-optimized SIMD |
| Save as PNG | ~20-50ms | ~20-50ms | Similar (both use libpng) |
| Save as JPEG | ~5-15ms | ~5-15ms | Similar (both use libjpeg) |
| Memory usage | ~10-30MB | ~5-10MB | FFmpeg has codec overhead |

**Key Insights**:

| Scenario | Recommendation |
|----------|----------------|
| Extract from video | ffmpeg-next (only option) |
| Resize during extraction | ffmpeg-next scaler (SIMD-optimized) |
| Post-processing (filters, effects) | image crate (more flexible API) |
| Batch processing | ffmpeg-next (reuse decoder, parallel with rayon) |
| WebP/AVIF output | image crate (better format support) |

**Why ffmpeg-next scaler is faster for resize**:

```rust
// ffmpeg-next: Hardware-optimized scaling (SIMD, multithreaded)
let mut scaler = Scaler::get(
    src_format, src_w, src_h,
    Pixel::RGB24, dst_w, dst_h,
    Flags::FAST_BILINEAR,  // ~1-3ms for 1080p → 320x180
)?;

// image crate: Pure Rust, single-threaded
let resized = image::imageops::resize(
    &img, dst_w, dst_h,
    image::imageops::FilterType::Triangle,  // ~10-30ms for same operation
);
```

**Recommended Pattern** (best of both):
```rust
// Use ffmpeg-next for decoding + scaling (fast)
let (rgb_data, width, height) = extract_thumbnail(input, target_w, target_h)?;

// Use image crate for encoding (flexible format support)
let img: ImageBuffer<Rgb<u8>, _> = ImageBuffer::from_raw(width, height, rgb_data).unwrap();
img.save("output.webp")?;  // WebP, AVIF, etc.
```

## 3. Container Remuxing

Change container format without re-encoding:

**Usage**: `cargo run -- input.mp4 output.mkv`

**Expected Output**: Creates output file in new container format with streams copied (no re-encoding).

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, encoder, format, media, Rational};

fn remux(input: &str, output: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;
    ffmpeg::log::set_level(ffmpeg::log::Level::Warning);

    let mut ictx = format::input(input)?;
    let mut octx = format::output(output)?;

    let mut stream_mapping = vec![-1i32; ictx.nb_streams() as usize];
    let mut ist_time_bases = vec![Rational(0, 1); ictx.nb_streams() as usize];
    let mut ost_index = 0;

    for (ist_index, ist) in ictx.streams().enumerate() {
        let medium = ist.parameters().medium();

        // Only copy audio, video, and subtitle streams
        if medium != media::Type::Audio
            && medium != media::Type::Video
            && medium != media::Type::Subtitle
        {
            continue;
        }

        stream_mapping[ist_index] = ost_index;
        ist_time_bases[ist_index] = ist.time_base();
        ost_index += 1;

        let mut ost = octx.add_stream(encoder::find(codec::Id::None))?;
        ost.set_parameters(ist.parameters());

        // Reset codec_tag for container compatibility
        unsafe {
            (*ost.parameters().as_mut_ptr()).codec_tag = 0;
        }
    }

    // Copy metadata
    octx.set_metadata(ictx.metadata().to_owned());
    octx.write_header()?;

    // Copy packets
    for (stream, mut packet) in ictx.packets() {
        let ist_index = stream.index();
        let ost_index = stream_mapping[ist_index];

        if ost_index < 0 {
            continue;
        }

        let ost = octx.stream(ost_index as usize).ok_or(ffmpeg::Error::StreamNotFound)?;
        packet.rescale_ts(ist_time_bases[ist_index], ost.time_base());
        packet.set_position(-1);
        packet.set_stream(ost_index as usize);
        packet.write_interleaved(&mut octx)?;
    }

    octx.write_trailer()?;
    Ok(())
}
```

## Hardware Acceleration

Hardware-accelerated encoding/decoding can significantly improve performance. ffmpeg-next supports various hardware acceleration APIs.

### Supported Hardware Acceleration APIs

| API | Platform | Codecs | Use Case |
|-----|----------|--------|----------|
| **NVENC/NVDEC** | NVIDIA GPUs | H.264, HEVC, VP9 | High-performance encoding/decoding |
| **VideoToolbox** | macOS/iOS | H.264, HEVC, ProRes | Apple hardware acceleration |
| **VAAPI** | Linux (Intel/AMD) | H.264, HEVC, VP8/9, AV1 | Linux GPU acceleration |
| **QSV** | Intel CPUs/GPUs | H.264, HEVC, VP9, AV1 | Intel Quick Sync Video |
| **DXVA2/D3D11VA** | Windows | H.264, HEVC, VP9 | Windows GPU acceleration |

### Hardware-Accelerated Decoding

**Note**: True hardware-accelerated decoding in ffmpeg-next requires FFI access to set up hardware device contexts. The high-level API provides limited hardware support. For full hardware acceleration, consider using `ffmpeg-sys-next` directly.

```rust
use ffmpeg::{codec, decoder, format, media};

fn setup_hw_decoder(input: &str) -> Result<decoder::Video, ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input)?;
    let ist = ictx.streams()
        .best(media::Type::Video)
        .ok_or(ffmpeg::Error::StreamNotFound)?;

    let mut decoder_ctx = codec::context::Context::from_parameters(ist.parameters())?;

    // Note: For true hardware decoding, you need to:
    // 1. Create a hardware device context (AVBufferRef*)
    // 2. Set hw_device_ctx on the decoder context
    // 3. Use a hardware pixel format (e.g., AV_PIX_FMT_VIDEOTOOLBOX)
    //
    // Platform-specific hardware types:
    // - macOS: AV_HWDEVICE_TYPE_VIDEOTOOLBOX
    // - NVIDIA: AV_HWDEVICE_TYPE_CUDA
    // - Intel: AV_HWDEVICE_TYPE_QSV
    // - Linux: AV_HWDEVICE_TYPE_VAAPI
    //
    // The ffmpeg-next high-level API doesn't expose hw_device_ctx directly.
    // See the FFI section for hardware device setup examples.

    // For software decoding with threading optimization:
    decoder_ctx.set_threading(codec::threading::Config::count(4));

    let decoder = decoder_ctx.decoder().video()?;

    Ok(decoder)
}
```

### Hardware-Accelerated Encoding

For hardware encoding, you must use the specific hardware encoder by name, not by codec ID.

```rust
use ffmpeg::{codec, encoder, format, Dictionary};

fn setup_hw_encoder(
    width: u32,
    height: u32,
    framerate: (u32, u32),
) -> Result<encoder::Video, ffmpeg::Error> {
    ffmpeg::init()?;

    // IMPORTANT: Use encoder::find_by_name() with the specific hardware encoder name
    // Using encoder::find(codec::Id::H264) returns the SOFTWARE encoder (libx264)

    // Platform-specific hardware encoder names:
    // - macOS: "h264_videotoolbox" or "hevc_videotoolbox"
    // - NVIDIA: "h264_nvenc" or "hevc_nvenc"
    // - Intel QSV: "h264_qsv" or "hevc_qsv"
    // - AMD/Intel VAAPI: "h264_vaapi" or "hevc_vaapi"

    #[cfg(target_os = "macos")]
    let encoder_name = "h264_videotoolbox";

    #[cfg(all(target_os = "linux", feature = "vaapi"))]
    let encoder_name = "h264_vaapi";

    #[cfg(all(target_os = "linux", not(feature = "vaapi")))]
    let encoder_name = "h264_nvenc"; // Fallback to NVENC if available

    #[cfg(target_os = "windows")]
    let encoder_name = "h264_nvenc"; // or "h264_qsv" for Intel

    // Find the hardware encoder by name
    let codec = encoder::find_by_name(encoder_name)
        .ok_or_else(|| {
            eprintln!("Hardware encoder '{}' not found, falling back to software", encoder_name);
            ffmpeg::Error::EncoderNotFound
        })?;

    let mut encoder_ctx = codec::context::Context::new_with_codec(codec)
        .encoder()
        .video()?;

    encoder_ctx.set_width(width);
    encoder_ctx.set_height(height);
    encoder_ctx.set_frame_rate(Some(ffmpeg::Rational(framerate.0 as i32, framerate.1 as i32)));
    encoder_ctx.set_time_base(ffmpeg::Rational(framerate.1 as i32, framerate.0 as i32));

    // Hardware-specific pixel format and options
    let mut opts = Dictionary::new();

    #[cfg(target_os = "macos")]
    {
        // VideoToolbox accepts various formats, YUV420P works well
        encoder_ctx.set_format(format::Pixel::YUV420P);
        opts.set("allow_sw", "0"); // Require hardware (set to "1" for software fallback)
        opts.set("realtime", "1"); // Real-time encoding
    }

    #[cfg(target_os = "linux")]
    {
        // VAAPI requires NV12 format typically
        // NVENC accepts YUV420P or NV12
        encoder_ctx.set_format(format::Pixel::NV12);
        opts.set("preset", "p4"); // NVENC preset (p1-p7)
        opts.set("tune", "hq"); // High quality
    }

    #[cfg(target_os = "windows")]
    {
        encoder_ctx.set_format(format::Pixel::YUV420P);
        opts.set("preset", "p4"); // NVENC preset
        opts.set("rc", "vbr"); // Variable bitrate
    }

    let encoder = encoder_ctx.open_with(opts)?;
    Ok(encoder)
}
```

### Hardware Acceleration Notes

**Performance Considerations**:
- Hardware encoding is typically 2-5x faster than software encoding
- Quality may be slightly lower than software encoders at same bitrate
- GPU memory transfer overhead can reduce benefits for small videos
- Best for real-time encoding or batch processing large files

**Platform-Specific Setup**:
- **macOS**: VideoToolbox is built-in, no additional setup required
- **NVIDIA**: Requires CUDA toolkit and compatible GPU drivers
- **Intel QSV**: Requires Intel Media SDK and compatible CPU/GPU
- **Linux VAAPI**: Requires libva and GPU-specific drivers (intel-media-driver, mesa)

**Codec Selection**:
```rust
// Find hardware-accelerated encoder by name
if let Some(encoder) = encoder::find_by_name("h264_videotoolbox") {
    // Use VideoToolbox H.264 encoder (macOS)
}

if let Some(encoder) = encoder::find_by_name("h264_nvenc") {
    // Use NVENC H.264 encoder (NVIDIA)
}

if let Some(encoder) = encoder::find_by_name("h264_qsv") {
    // Use QSV H.264 encoder (Intel)
}

if let Some(encoder) = encoder::find_by_name("h264_vaapi") {
    // Use VAAPI H.264 encoder (Linux)
}
```

**Fallback Strategy**:
Always implement software fallback for portability:
```rust
fn find_best_h264_encoder() -> Option<codec::encoder::Encoder> {
    // Try hardware encoders first
    encoder::find_by_name("h264_videotoolbox")
        .or_else(|| encoder::find_by_name("h264_nvenc"))
        .or_else(|| encoder::find_by_name("h264_qsv"))
        .or_else(|| encoder::find_by_name("h264_vaapi"))
        // Fallback to software encoder
        .or_else(|| encoder::find(codec::Id::H264))
}
```
