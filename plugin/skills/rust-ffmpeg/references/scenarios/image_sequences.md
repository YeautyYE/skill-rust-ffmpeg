# Image Sequences

**Detection Keywords**: image sequence, frame extraction, video to images, images to video, image2, png sequence, jpg sequence, timelapse, frame by frame
**Aliases**: frame sequence, image series, video frames, slideshow

Cross-library guide for converting between video and image sequences.

## Quick Reference

| Operation | ez-ffmpeg | ffmpeg-next | ffmpeg-sidecar |
|-----------|-----------|-------------|----------------|
| Video → Images | `.output("frame_%04d.png")` | Decode loop + image encoder | `-f image2` args |
| Images → Video | `.input()` + `image2` format | Image decoder + encode loop | `-f image2` args |
| Frame rate control | `.filter_desc("fps=...")` | Manual timing | `-r` argument |
| Quality control | `.set_video_qscale()` | Encoder options | `-q:v` argument |

## Video to Image Sequence

### ez-ffmpeg

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Extract all frames as PNG (lossless)
FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("frames/frame_%04d.png")
        .set_video_codec("png"))
    .build()?.start()?.wait()?;

// Extract as JPEG with quality control
FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("frames/frame_%04d.jpg")
        .set_video_qscale(2))  // Quality: 2-31, lower is better
    .build()?.start()?.wait()?;

// Extract at specific frame rate (1 frame per second)
FfmpegContext::builder()
    .input("video.mp4")
    .filter_desc("fps=1")
    .output("frames/frame_%04d.png")
    .build()?.start()?.wait()?;

// Extract frames from specific time range
FfmpegContext::builder()
    .input(Input::from("video.mp4")
        .set_start_time_us(10_000_000))  // Start at 10 seconds
    .output(Output::from("frames/frame_%04d.png")
        .set_recording_time_us(5_000_000))  // Extract for 5 seconds
    .build()?.start()?.wait()?;

// Extract with scaling
FfmpegContext::builder()
    .input("video.mp4")
    .filter_desc("scale=640:-1,fps=10")  // Scale + 10 fps
    .output("frames/thumb_%04d.jpg")
    .build()?.start()?.wait()?;

// Extract every Nth frame (e.g., every 30th frame)
FfmpegContext::builder()
    .input("video.mp4")
    .filter_desc("select='not(mod(n,30))'")
    .output(Output::from("frames/frame_%04d.png")
        .set_format_opt("vsync", "vfr"))  // Variable frame rate
    .build()?.start()?.wait()?;

// Extract keyframes only (I-frames)
FfmpegContext::builder()
    .input("video.mp4")
    .filter_desc("select='eq(pict_type,I)'")
    .output(Output::from("keyframes/key_%04d.png")
        .set_format_opt("vsync", "vfr"))
    .build()?.start()?.wait()?;
```

### ffmpeg-next

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, decoder, encoder, format, frame, media, software::scaling};
use std::fs::File;
use std::io::Write;
use std::path::Path;

fn extract_frames(input: &str, output_dir: &str, format: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input)?;
    let video_stream = ictx
        .streams()
        .best(media::Type::Video)
        .ok_or(ffmpeg::Error::StreamNotFound)?;
    let video_index = video_stream.index();

    let context = codec::context::Context::from_parameters(video_stream.parameters())?;
    let mut decoder = context.decoder().video()?;

    // Create scaler for RGB conversion (needed for image encoding)
    let mut scaler = scaling::Context::get(
        decoder.format(),
        decoder.width(),
        decoder.height(),
        format::Pixel::RGB24,
        decoder.width(),
        decoder.height(),
        scaling::Flags::BILINEAR,
    )?;

    let mut frame_index = 0;

    for (stream, packet) in ictx.packets() {
        if stream.index() != video_index {
            continue;
        }

        decoder.send_packet(&packet)?;

        let mut decoded = frame::Video::empty();
        while decoder.receive_frame(&mut decoded).is_ok() {
            let mut rgb_frame = frame::Video::empty();
            scaler.run(&decoded, &mut rgb_frame)?;

            // Save frame as image
            let filename = format!("{}/frame_{:04}.{}", output_dir, frame_index, format);
            save_frame_as_image(&rgb_frame, &filename)?;

            frame_index += 1;
        }
    }

    // Flush decoder
    decoder.send_eof()?;
    let mut decoded = frame::Video::empty();
    while decoder.receive_frame(&mut decoded).is_ok() {
        let mut rgb_frame = frame::Video::empty();
        scaler.run(&decoded, &mut rgb_frame)?;

        let filename = format!("{}/frame_{:04}.{}", output_dir, frame_index, format);
        save_frame_as_image(&rgb_frame, &filename)?;

        frame_index += 1;
    }

    println!("Extracted {} frames", frame_index);
    Ok(())
}

fn save_frame_as_image(frame: &frame::Video, path: &str) -> Result<(), ffmpeg::Error> {
    // For PNG/JPEG encoding, use image crate or write raw PPM
    // Simple PPM format (can be converted to PNG/JPEG externally)
    let mut file = File::create(path).map_err(|_| ffmpeg::Error::Unknown)?;

    let width = frame.width();
    let height = frame.height();

    // Write PPM header
    writeln!(file, "P6\n{} {}\n255", width, height)
        .map_err(|_| ffmpeg::Error::Unknown)?;

    // Write RGB data
    let data = frame.data(0);
    let stride = frame.stride(0);

    for y in 0..height {
        let row_start = y as usize * stride;
        let row_end = row_start + (width as usize * 3);
        file.write_all(&data[row_start..row_end])
            .map_err(|_| ffmpeg::Error::Unknown)?;
    }

    Ok(())
}
```

### ffmpeg-sidecar

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

// Extract all frames as PNG
FfmpegCommand::new()
    .input("video.mp4")
    .output("frames/frame_%04d.png")
    .spawn()?.wait()?;

// Extract as JPEG with quality
FfmpegCommand::new()
    .input("video.mp4")
    .args(["-q:v", "2"])  // Quality: 2-31
    .output("frames/frame_%04d.jpg")
    .spawn()?.wait()?;

// Extract at 1 fps
FfmpegCommand::new()
    .input("video.mp4")
    .args(["-vf", "fps=1"])
    .output("frames/frame_%04d.png")
    .spawn()?.wait()?;

// Extract from time range
FfmpegCommand::new()
    .args(["-ss", "00:00:10"])  // Start at 10s
    .input("video.mp4")
    .args(["-t", "5"])  // Duration 5s
    .output("frames/frame_%04d.png")
    .spawn()?.wait()?;

// Extract keyframes only
FfmpegCommand::new()
    .input("video.mp4")
    .args(["-vf", "select='eq(pict_type,I)'"])
    .args(["-vsync", "vfr"])
    .output("keyframes/key_%04d.png")
    .spawn()?.wait()?;

// Extract with scaling
FfmpegCommand::new()
    .input("video.mp4")
    .args(["-vf", "scale=320:-1,fps=5"])
    .output("thumbs/thumb_%04d.jpg")
    .spawn()?.wait()?;
```

## Image Sequence to Video

### ez-ffmpeg

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};
use ffmpeg_sys_next::AVRational;

// Basic image sequence to video
FfmpegContext::builder()
    .input(Input::from("frames/frame_%04d.png")
        .set_format("image2")
        .set_framerate(30, 1))  // 30 fps
    .output(Output::from("output.mp4")
        .set_video_codec("libx264")
        .set_pix_fmt("yuv420p"))  // Required for compatibility
    .build()?.start()?.wait()?;

// JPEG sequence with quality encoding
FfmpegContext::builder()
    .input(Input::from("frames/frame_%04d.jpg")
        .set_format("image2")
        .set_framerate(24, 1))
    .output(Output::from("output.mp4")
        .set_video_codec("libx264")
        .set_video_codec_opt("crf", "18")
        .set_video_codec_opt("preset", "medium")
        .set_pix_fmt("yuv420p"))
    .build()?.start()?.wait()?;

// Timelapse from photos (variable naming with glob)
FfmpegContext::builder()
    .input(Input::from("photos/*.jpg")
        .set_format("image2")
        .set_input_opt("pattern_type", "glob")
        .set_framerate(30, 1))
    .output(Output::from("timelapse.mp4")
        .set_video_codec("libx264")
        .set_pix_fmt("yuv420p"))
    .build()?.start()?.wait()?;

// With scaling and padding for consistent size
FfmpegContext::builder()
    .input(Input::from("frames/frame_%04d.png")
        .set_format("image2")
        .set_framerate(30, 1))
    .filter_desc("scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2")
    .output(Output::from("output.mp4")
        .set_video_codec("libx264")
        .set_pix_fmt("yuv420p"))
    .build()?.start()?.wait()?;

// Slideshow with duration per image
FfmpegContext::builder()
    .input(Input::from("slides/slide_%02d.png")
        .set_format("image2")
        .set_framerate(1, 3))  // 3 seconds per image (1/3 fps)
    .output(Output::from("slideshow.mp4")
        .set_video_codec("libx264")
        .set_pix_fmt("yuv420p")
        .set_framerate(AVRational { num: 30, den: 1 }))  // Output at 30fps
    .build()?.start()?.wait()?;

// Start from specific frame number
FfmpegContext::builder()
    .input(Input::from("frames/frame_%04d.png")
        .set_format("image2")
        .set_input_opt("start_number", "100")  // Start from frame_0100.png
        .set_framerate(30, 1))
    .output(Output::from("output.mp4")
        .set_video_codec("libx264")
        .set_pix_fmt("yuv420p"))
    .build()?.start()?.wait()?;
```

### ffmpeg-next

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, encoder, format, frame, media, software::scaling, Dictionary, Rational};
use std::fs;
use std::path::Path;

fn images_to_video(
    input_pattern: &str,
    output_path: &str,
    fps: i32,
) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    // Get list of image files
    let dir = Path::new(input_pattern).parent().unwrap();
    let mut images: Vec<_> = fs::read_dir(dir)
        .map_err(|_| ffmpeg::Error::Unknown)?
        .filter_map(|e| e.ok())
        .filter(|e| {
            e.path()
                .extension()
                .map(|ext| ext == "png" || ext == "jpg")
                .unwrap_or(false)
        })
        .collect();
    images.sort_by_key(|e| e.path());

    if images.is_empty() {
        return Err(ffmpeg::Error::StreamNotFound);
    }

    // Read first image to get dimensions
    let first_image = format::input(&images[0].path())?;
    let video_stream = first_image.streams().best(media::Type::Video).unwrap();
    let params = video_stream.parameters();

    let width = unsafe { (*params.as_ptr()).width as u32 };
    let height = unsafe { (*params.as_ptr()).height as u32 };

    // Create output context
    let mut octx = format::output(output_path)?;

    // Find H.264 encoder
    let codec = encoder::find(codec::Id::H264).unwrap();
    let mut ost = octx.add_stream(codec)?;

    let mut encoder = codec::context::Context::new_with_codec(codec)
        .encoder()
        .video()?;

    encoder.set_width(width);
    encoder.set_height(height);
    encoder.set_format(format::Pixel::YUV420P);
    encoder.set_time_base(Rational(1, fps));
    encoder.set_frame_rate(Some(Rational(fps, 1)));

    let mut opts = Dictionary::new();
    opts.set("preset", "medium");
    opts.set("crf", "23");

    let encoder = encoder.open_with(opts)?;
    ost.set_parameters(&encoder);

    octx.write_header()?;

    // Process each image
    let mut pts = 0i64;
    for entry in images {
        let mut ictx = format::input(&entry.path())?;
        let ist = ictx.streams().best(media::Type::Video).unwrap();
        let ist_index = ist.index();

        let context = codec::context::Context::from_parameters(ist.parameters())?;
        let mut decoder = context.decoder().video()?;

        // Create scaler for format conversion
        let mut scaler = scaling::Context::get(
            decoder.format(),
            decoder.width(),
            decoder.height(),
            format::Pixel::YUV420P,
            width,
            height,
            scaling::Flags::BILINEAR,
        )?;

        for (stream, packet) in ictx.packets() {
            if stream.index() != ist_index {
                continue;
            }

            decoder.send_packet(&packet)?;

            let mut decoded = frame::Video::empty();
            while decoder.receive_frame(&mut decoded).is_ok() {
                let mut yuv_frame = frame::Video::empty();
                scaler.run(&decoded, &mut yuv_frame)?;

                yuv_frame.set_pts(Some(pts));
                pts += 1;

                encoder.send_frame(&yuv_frame)?;

                let mut encoded = ffmpeg::Packet::empty();
                while encoder.receive_packet(&mut encoded).is_ok() {
                    encoded.set_stream(0);
                    encoded.rescale_ts(Rational(1, fps), ost.time_base());
                    encoded.write_interleaved(&mut octx)?;
                }
            }
        }
    }

    // Flush encoder
    encoder.send_eof()?;
    let mut encoded = ffmpeg::Packet::empty();
    while encoder.receive_packet(&mut encoded).is_ok() {
        encoded.set_stream(0);
        encoded.rescale_ts(Rational(1, fps), ost.time_base());
        encoded.write_interleaved(&mut octx)?;
    }

    octx.write_trailer()?;
    Ok(())
}
```

### ffmpeg-sidecar

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

// Basic image sequence to video
FfmpegCommand::new()
    .args(["-framerate", "30"])
    .args(["-i", "frames/frame_%04d.png"])
    .args(["-c:v", "libx264"])
    .args(["-pix_fmt", "yuv420p"])
    .output("output.mp4")
    .spawn()?.wait()?;

// JPEG sequence with quality
FfmpegCommand::new()
    .args(["-framerate", "24"])
    .args(["-i", "frames/frame_%04d.jpg"])
    .args(["-c:v", "libx264"])
    .args(["-crf", "18"])
    .args(["-pix_fmt", "yuv420p"])
    .output("output.mp4")
    .spawn()?.wait()?;

// Glob pattern for variable naming
FfmpegCommand::new()
    .args(["-framerate", "30"])
    .args(["-pattern_type", "glob"])
    .args(["-i", "photos/*.jpg"])
    .args(["-c:v", "libx264"])
    .args(["-pix_fmt", "yuv420p"])
    .output("timelapse.mp4")
    .spawn()?.wait()?;

// Start from specific frame number
FfmpegCommand::new()
    .args(["-framerate", "30"])
    .args(["-start_number", "100"])
    .args(["-i", "frames/frame_%04d.png"])
    .args(["-c:v", "libx264"])
    .args(["-pix_fmt", "yuv420p"])
    .output("output.mp4")
    .spawn()?.wait()?;

// Slideshow with duration per image
FfmpegCommand::new()
    .args(["-framerate", "1/3"])  // 3 seconds per image
    .args(["-i", "slides/slide_%02d.png"])
    .args(["-c:v", "libx264"])
    .args(["-r", "30"])  // Output framerate
    .args(["-pix_fmt", "yuv420p"])
    .output("slideshow.mp4")
    .spawn()?.wait()?;

// With scaling
FfmpegCommand::new()
    .args(["-framerate", "30"])
    .args(["-i", "frames/frame_%04d.png"])
    .args(["-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"])
    .args(["-c:v", "libx264"])
    .args(["-pix_fmt", "yuv420p"])
    .output("output.mp4")
    .spawn()?.wait()?;
```

## Advanced Operations

### Frame Interpolation (Slow Motion)

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Extract frames, then create slow-motion video
// Step 1: Extract at original rate
FfmpegContext::builder()
    .input("video.mp4")
    .output("frames/frame_%04d.png")
    .build()?.start()?.wait()?;

// Step 2: Create video at lower framerate (2x slower)
FfmpegContext::builder()
    .input(Input::from("frames/frame_%04d.png")
        .set_format("image2")
        .set_framerate(15, 1))  // Half the original 30fps
    .output(Output::from("slow_motion.mp4")
        .set_video_codec("libx264")
        .set_pix_fmt("yuv420p"))
    .build()?.start()?.wait()?;
```

### Batch Frame Processing

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};
use std::fs;

// Process multiple videos to frame sequences
fn batch_extract_frames(input_dir: &str, output_dir: &str) -> Result<(), Box<dyn std::error::Error>> {
    for entry in fs::read_dir(input_dir)? {
        let entry = entry?;
        let path = entry.path();

        if path.extension().map(|e| e == "mp4").unwrap_or(false) {
            let stem = path.file_stem().unwrap().to_str().unwrap();
            let output_pattern = format!("{}/{}/frame_%04d.png", output_dir, stem);

            // Create output directory
            fs::create_dir_all(format!("{}/{}", output_dir, stem))?;

            FfmpegContext::builder()
                .input(path.to_str().unwrap())
                .filter_desc("fps=10")  // 10 frames per second
                .output(&output_pattern)
                .build()?.start()?.wait()?;
        }
    }
    Ok(())
}
```

### Alpha Channel (Transparent) Sequences

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Extract with alpha channel (PNG only)
FfmpegContext::builder()
    .input("video_with_alpha.mov")  // ProRes 4444 or similar
    .output(Output::from("frames/frame_%04d.png")
        .set_pix_fmt("rgba"))  // Preserve alpha
    .build()?.start()?.wait()?;

// Create video with alpha from PNG sequence
FfmpegContext::builder()
    .input(Input::from("frames/frame_%04d.png")
        .set_format("image2")
        .set_framerate(30, 1))
    .output(Output::from("output.mov")
        .set_video_codec("prores_ks")
        .set_video_codec_opt("profile", "4444")  // ProRes 4444 with alpha
        .set_pix_fmt("yuva444p10le"))
    .build()?.start()?.wait()?;

// WebM with alpha (VP9)
FfmpegContext::builder()
    .input(Input::from("frames/frame_%04d.png")
        .set_format("image2")
        .set_framerate(30, 1))
    .output(Output::from("output.webm")
        .set_video_codec("libvpx-vp9")
        .set_pix_fmt("yuva420p"))
    .build()?.start()?.wait()?;
```

### Scene Detection and Extraction

```rust
use ez_ffmpeg::{FfmpegContext, Output};

// Extract frames at scene changes
FfmpegContext::builder()
    .input("video.mp4")
    .filter_desc("select='gt(scene,0.3)',showinfo")  // Scene change threshold 0.3
    .output(Output::from("scenes/scene_%04d.png")
        .set_format_opt("vsync", "vfr"))
    .build()?.start()?.wait()?;
```

## Common Patterns

### Naming Conventions

| Pattern | Description | Example Files |
|---------|-------------|---------------|
| `%d` | Sequential number | 1, 2, 3... |
| `%02d` | 2-digit padded | 01, 02, 03... |
| `%04d` | 4-digit padded | 0001, 0002... |
| `%06d` | 6-digit padded | 000001, 000002... |

### Image Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| PNG | `.png` | Lossless, supports alpha |
| JPEG | `.jpg` | Smaller files, lossy |
| TIFF | `.tiff` | Professional workflows |
| BMP | `.bmp` | Uncompressed, large |
| WebP | `.webp` | Modern, good compression |

### Quality Settings

| Format | Quality Parameter | Range | Recommendation |
|--------|-------------------|-------|----------------|
| JPEG | `-q:v` / `set_video_qscale()` | 2-31 | 2-5 for high quality |
| PNG | N/A | Lossless | Always lossless |
| WebP | `-quality` | 0-100 | 80-95 for good quality |

## Library Selection Guide

| Use Case | Recommended | Reason |
|----------|-------------|--------|
| Simple extraction | ez-ffmpeg | Clean API, minimal code |
| Batch processing | ez-ffmpeg | Easy iteration |
| Custom frame processing | ffmpeg-next | Direct frame access |
| CLI-like operations | ffmpeg-sidecar | Direct FFmpeg access |
| Timelapse creation | ez-ffmpeg | Glob pattern support |
| Alpha channel handling | ez-ffmpeg | Simple codec options |

## Troubleshooting

### Common Issues

**"No such file or directory"**:
- Ensure output directory exists before extraction
- Check pattern matches actual filenames

**"Invalid frame rate"**:
- Use `set_framerate(num, den)` format (e.g., `set_framerate(30, 1)`)
- For fractional rates: `set_framerate(24000, 1001)` for 23.976fps

**"Discarding frame with invalid format"**:
- Add `.set_pix_fmt("yuv420p")` for H.264 compatibility
- Use `.filter_desc("format=yuv420p")` as alternative

**"Pattern not matching files"**:
- Check digit padding matches (`%04d` needs 4 digits)
- Use `start_number` option if sequence doesn't start at 0 or 1
- Try glob pattern with `pattern_type=glob`

**Large output file size**:
- Use JPEG instead of PNG for smaller files
- Add quality settings: `.set_video_qscale(5)`
- Reduce frame rate with `fps` filter

## Related Guides

| Guide | Content |
|-------|---------|
| [video_transcoding.md](video_transcoding.md) | Video format conversion |
| [filters_effects.md](filters_effects.md) | Video filters and effects |
| [batch_processing.md](batch_processing.md) | Processing multiple files |
| [gif_creation.md](gif_creation.md) | Creating animated GIFs |
