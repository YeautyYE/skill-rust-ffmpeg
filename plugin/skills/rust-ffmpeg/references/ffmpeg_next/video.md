# ffmpeg-next: Video Operations

**Detection Keywords**: seeking, seek, position, scaling, scaler, pixel format, timestamp, pts, dts, time base, keyframe, key frame, is_key, GOP, gop size, keyframe interval, I-frame
**Aliases**: video seek, scale video, timestamp convert, time base, keyframe detection, gop analysis

Core video processing operations: seeking, scaling context, and timestamp management.

## Table of Contents

- [Seeking](#seeking)
- [Scaling Context (Video Format Conversion)](#scaling-context-video-format-conversion)
- [Timestamp Management (PTS/DTS)](#timestamp-management-ptsdts)

## Related Guides

| Guide | Content |
|-------|---------|
| [transcoding.md](transcoding.md) | Video transcoding, frame extraction, thumbnail generation |
| [output.md](output.md) | PNG/JPEG saving, container remuxing, hardware acceleration |

## Seeking

Seeking allows jumping to a specific position in a media file. FFmpeg seeking works with timestamps in `TIME_BASE` units (microseconds).

### Basic Seeking

```rust
use ffmpeg::{format, rescale, Rescale};

fn seek_to_position(ictx: &mut format::context::Input, position_secs: i64) -> Result<(), ffmpeg::Error> {
    // Convert seconds to TIME_BASE units (microseconds)
    let position = position_secs.rescale((1, 1), rescale::TIME_BASE);

    // Seek to position (..position creates an unbounded range ending at position)
    ictx.seek(position, ..position)?;

    Ok(())
}

fn main() -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input("input.mp4")?;

    // Seek to 30 seconds
    seek_to_position(&mut ictx, 30)?;

    // Continue processing from seek position
    for (stream, packet) in ictx.packets() {
        // Packets start from around the seek position
        println!("Stream {}: pts={:?}", stream.index(), packet.pts());
    }

    Ok(())
}
```

### Seeking with Range

For more precise seeking, specify a range:

```rust
use ffmpeg::{format, rescale, Rescale};

fn seek_with_range(
    ictx: &mut format::context::Input,
    min_ts: i64,
    target_ts: i64,
    max_ts: i64,
) -> Result<(), ffmpeg::Error> {
    // Convert all timestamps to TIME_BASE
    let min = min_ts.rescale((1, 1), rescale::TIME_BASE);
    let target = target_ts.rescale((1, 1), rescale::TIME_BASE);
    let max = max_ts.rescale((1, 1), rescale::TIME_BASE);

    // Seek with bounded range
    ictx.seek(target, min..max)?;

    Ok(())
}
```

### Seek to Keyframe

By default, seeking goes to the nearest keyframe before the target position. This is important for video because decoding must start from a keyframe:

```rust
use ffmpeg::{format, rescale, Rescale};

fn seek_and_decode_from(
    ictx: &mut format::context::Input,
    target_secs: i64,
) -> Result<(), ffmpeg::Error> {
    let position = target_secs.rescale((1, 1), rescale::TIME_BASE);

    // Seek (will land on keyframe at or before target)
    ictx.seek(position, ..position)?;

    // After seeking, packets may start slightly before the target
    // because FFmpeg seeks to the previous keyframe
    for (stream, packet) in ictx.packets() {
        if let Some(pts) = packet.pts() {
            let packet_time_base = stream.time_base();
            let pts_in_seconds = pts as f64 * packet_time_base.numerator() as f64
                / packet_time_base.denominator() as f64;

            // Skip packets before our actual target
            if pts_in_seconds < target_secs as f64 {
                continue;
            }

            // Process packets at or after target
            println!("Processing packet at {:.2}s", pts_in_seconds);
        }
    }

    Ok(())
}
```

### Seeking in Audio Transcoding

From the `transcode-audio` example - seeking before transcoding:

```rust
use ffmpeg::{format, rescale, Rescale};

fn transcode_audio_from_position(
    input_path: &str,
    output_path: &str,
    seek_position: Option<i64>,
) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input_path)?;
    let mut octx = format::output(output_path)?;

    // Seek before starting transcoding
    if let Some(position) = seek_position {
        let position = position.rescale((1, 1), rescale::TIME_BASE);
        ictx.seek(position, ..position)?;
    }

    // Setup transcoding (encoder, decoder, etc.)
    // ... (see Audio Transcoding example for full implementation)

    // Process packets from seek position
    for (stream, packet) in ictx.packets() {
        // Handle packet...
    }

    Ok(())
}
```

### Important Notes

1. **Seeking is approximate**: FFmpeg seeks to the nearest keyframe, which may be before your target timestamp
2. **Time base conversion**: Always use `rescale()` to convert between time bases
3. **Seek after open**: Call `seek()` after opening the input but before reading packets
4. **Flush decoders**: After seeking, you may need to flush decoders to clear buffered frames

## Scaling Context (Video Format Conversion)

The `software::scaling::Context` handles pixel format conversion and resizing.

### Basic Usage

```rust
use ffmpeg::software::scaling::{Context, Flags};
use ffmpeg::format::Pixel;
use ffmpeg::frame::Video;

// Create scaler: YUV420P -> RGB24, same resolution
let mut scaler = Context::get(
    Pixel::YUV420P,    // source format
    1920, 1080,        // source dimensions
    Pixel::RGB24,      // destination format
    1920, 1080,        // destination dimensions
    Flags::BILINEAR,   // scaling algorithm
)?;

// Process frames
let mut src_frame = Video::empty();
let mut dst_frame = Video::empty();

while decoder.receive_frame(&mut src_frame).is_ok() {
    scaler.run(&src_frame, &mut dst_frame)?;
    // dst_frame now contains RGB24 data
}
```

### Scaling Flags

| Flag | Use Case |
|------|----------|
| `Flags::FAST_BILINEAR` | Fastest, acceptable quality |
| `Flags::BILINEAR` | Good balance of speed and quality |
| `Flags::BICUBIC` | Higher quality, slower |
| `Flags::LANCZOS` | Highest quality downscaling |
| `Flags::BITEXACT` | Deterministic output |

### Production Pattern: Lazy Initialization

From production code - initialize scaler on first frame when dimensions are known:

```rust
use ffmpeg_next::software::scaling::{Context as ScalingContext, Flags};
use ffmpeg_next::format::Pixel;

struct VideoProcessor {
    to_scaler: Option<ScalingContext>,
    target_format: Pixel,
}

impl VideoProcessor {
    fn process_frame(&mut self, frame: &ffmpeg_next::frame::Video) -> Result<ffmpeg_next::frame::Video, ffmpeg_next::Error> {
        // Lazy initialization on first frame
        if self.to_scaler.is_none() {
            self.to_scaler = Some(ScalingContext::get(
                frame.format(),
                frame.width(),
                frame.height(),
                self.target_format,
                frame.width(),
                frame.height(),
                Flags::FAST_BILINEAR | Flags::BITEXACT,
            )?);
        }

        let mut output = ffmpeg_next::frame::Video::empty();
        self.to_scaler.as_mut().unwrap().run(frame, &mut output)?;
        Ok(output)
    }
}
```

## Timestamp Management (PTS/DTS)

### Time Base Conversion

Convert between time bases when working with multiple streams:

```rust
use ffmpeg::Rational;

/// Convert stream time to microseconds
fn stream_time_to_us(time_base: Rational, value: i64) -> Option<i64> {
    if value == i64::MIN || time_base.denominator() == 0 {
        return None;
    }

    let numerator = i128::from(value) * i128::from(time_base.numerator()) * 1_000_000i128;
    let denominator = i128::from(time_base.denominator());

    Some((numerator / denominator) as i64)
}

/// Format timestamp for display
fn format_timestamp(time_us: i64) -> String {
    let seconds = time_us / 1_000_000;
    let millis = (time_us % 1_000_000).abs() / 1_000;
    format!("{}.{:03}", seconds, millis)
}
```

### PTS Gap Detection

Detect gaps in audio streams (common in live recordings):

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::format;
use ffmpeg::media::Type;

struct PtsGap {
    position_us: i64,
    gap_duration_us: i64,
}

fn detect_audio_pts_gaps(path: &str) -> Result<Vec<PtsGap>, ffmpeg::Error> {
    ffmpeg::init()?;

    let mut context = format::input(path)?;

    // Find audio stream
    let audio_stream_index = context
        .streams()
        .best(Type::Audio)
        .map(|s| s.index());

    let audio_stream_index = match audio_stream_index {
        Some(idx) => idx,
        None => return Ok(vec![]),
    };

    let time_base = context
        .stream(audio_stream_index)
        .map(|s| s.time_base())
        .ok_or(ffmpeg::Error::StreamNotFound)?;

    let tb_num = time_base.numerator() as i128;
    let tb_den = time_base.denominator() as i128;

    if tb_den == 0 {
        return Ok(vec![]);
    }

    let mut gaps = Vec::new();
    let mut prev_pts: Option<i64> = None;
    let mut prev_duration: Option<i64> = None;
    let mut cumulative_gap_us: i64 = 0;

    const GAP_THRESHOLD_TB: i64 = 100;  // Ignore tiny gaps

    for (stream, packet) in context.packets() {
        if stream.index() != audio_stream_index {
            continue;
        }

        let pts = match packet.pts() {
            Some(p) => p,
            None => continue,
        };

        let duration = packet.duration();

        if let (Some(prev), Some(dur)) = (prev_pts, prev_duration) {
            let expected_pts = prev + dur;
            let gap_tb = pts - expected_pts;

            if gap_tb > GAP_THRESHOLD_TB {
                let gap_us = (i128::from(gap_tb) * tb_num * 1_000_000i128 / tb_den) as i64;
                let prev_end_us = (i128::from(prev + dur) * tb_num * 1_000_000i128 / tb_den) as i64;
                let position_us = prev_end_us - cumulative_gap_us;

                gaps.push(PtsGap {
                    position_us,
                    gap_duration_us: gap_us,
                });

                cumulative_gap_us += gap_us;
            }
        }

        prev_pts = Some(pts);
        prev_duration = Some(duration);
    }

    Ok(gaps)
}
```

### Reading First Packet Timestamp

Get the starting timestamp of a media file:

```rust
fn read_first_packet_time_us(path: &str) -> Result<i64, ffmpeg::Error> {
    ffmpeg::init()?;

    let mut context = ffmpeg::format::input(path)?;

    let (stream, packet) = context
        .packets()
        .next()
        .ok_or(ffmpeg::Error::InvalidData)?;

    let pts = packet.pts().unwrap_or(0);
    let time_base = stream.time_base();
    let numerator = time_base.numerator();
    let denominator = time_base.denominator();

    if denominator == 0 {
        return Ok(0);
    }

    let timestamp = (i128::from(pts) * i128::from(numerator) * 1_000_000i128) / i128::from(denominator);

    Ok(timestamp as i64)
}
```

## Keyframe Detection

Detect whether a packet is a keyframe (I-frame) for seeking, segmentation, or analysis.

### Check Packet Keyframe Flag

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{format, media, Packet};

fn is_keyframe(packet: &Packet) -> bool {
    packet.is_key()
}

fn find_keyframes(path: &str) -> Result<Vec<i64>, ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(path)?;
    let video_stream_index = ictx
        .streams()
        .best(media::Type::Video)
        .map(|s| s.index())
        .ok_or(ffmpeg::Error::StreamNotFound)?;

    let mut keyframe_pts = Vec::new();

    for (stream, packet) in ictx.packets() {
        if stream.index() != video_stream_index {
            continue;
        }

        if packet.is_key() {
            if let Some(pts) = packet.pts() {
                keyframe_pts.push(pts);
            }
        }
    }

    Ok(keyframe_pts)
}

fn main() -> Result<(), ffmpeg::Error> {
    let keyframes = find_keyframes("input.mp4")?;
    println!("Found {} keyframes", keyframes.len());
    for (i, pts) in keyframes.iter().enumerate().take(10) {
        println!("  Keyframe {}: PTS {}", i, pts);
    }
    Ok(())
}
```

### Keyframe Statistics

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{format, media};

struct KeyframeStats {
    total_frames: usize,
    keyframe_count: usize,
    min_gop_size: usize,
    max_gop_size: usize,
    avg_gop_size: f64,
}

fn analyze_keyframes(path: &str) -> Result<KeyframeStats, ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(path)?;
    let video_stream_index = ictx
        .streams()
        .best(media::Type::Video)
        .map(|s| s.index())
        .ok_or(ffmpeg::Error::StreamNotFound)?;

    let mut total_frames = 0usize;
    let mut keyframe_count = 0usize;
    let mut gop_sizes = Vec::new();
    let mut frames_since_keyframe = 0usize;

    for (stream, packet) in ictx.packets() {
        if stream.index() != video_stream_index {
            continue;
        }

        total_frames += 1;

        if packet.is_key() {
            keyframe_count += 1;
            if frames_since_keyframe > 0 {
                gop_sizes.push(frames_since_keyframe);
            }
            frames_since_keyframe = 1;
        } else {
            frames_since_keyframe += 1;
        }
    }

    // Add last GOP
    if frames_since_keyframe > 0 {
        gop_sizes.push(frames_since_keyframe);
    }

    let (min_gop, max_gop, avg_gop) = if gop_sizes.is_empty() {
        (0, 0, 0.0)
    } else {
        let min = *gop_sizes.iter().min().unwrap();
        let max = *gop_sizes.iter().max().unwrap();
        let avg = gop_sizes.iter().sum::<usize>() as f64 / gop_sizes.len() as f64;
        (min, max, avg)
    };

    Ok(KeyframeStats {
        total_frames,
        keyframe_count,
        min_gop_size: min_gop,
        max_gop_size: max_gop,
        avg_gop_size: avg_gop,
    })
}

fn main() -> Result<(), ffmpeg::Error> {
    let stats = analyze_keyframes("input.mp4")?;
    println!("Total frames: {}", stats.total_frames);
    println!("Keyframes: {}", stats.keyframe_count);
    println!("GOP size: min={}, max={}, avg={:.1}",
        stats.min_gop_size, stats.max_gop_size, stats.avg_gop_size);
    Ok(())
}
```

## GOP (Group of Pictures) Analysis

Analyze GOP structure for streaming optimization or quality assessment.

### GOP Size Distribution

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{format, media};
use std::collections::HashMap;

fn analyze_gop_distribution(path: &str) -> Result<HashMap<usize, usize>, ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(path)?;
    let video_stream_index = ictx
        .streams()
        .best(media::Type::Video)
        .map(|s| s.index())
        .ok_or(ffmpeg::Error::StreamNotFound)?;

    let mut gop_distribution: HashMap<usize, usize> = HashMap::new();
    let mut current_gop_size = 0usize;

    for (stream, packet) in ictx.packets() {
        if stream.index() != video_stream_index {
            continue;
        }

        if packet.is_key() {
            if current_gop_size > 0 {
                *gop_distribution.entry(current_gop_size).or_insert(0) += 1;
            }
            current_gop_size = 1;
        } else {
            current_gop_size += 1;
        }
    }

    // Add last GOP
    if current_gop_size > 0 {
        *gop_distribution.entry(current_gop_size).or_insert(0) += 1;
    }

    Ok(gop_distribution)
}

fn main() -> Result<(), ffmpeg::Error> {
    let distribution = analyze_gop_distribution("input.mp4")?;

    println!("GOP Size Distribution:");
    let mut sizes: Vec<_> = distribution.iter().collect();
    sizes.sort_by_key(|(size, _)| *size);

    for (size, count) in sizes {
        println!("  GOP size {}: {} occurrences", size, count);
    }

    Ok(())
}
```

### Validate GOP for Streaming

```rust
/// Check if video GOP structure is suitable for HLS/DASH streaming
fn validate_gop_for_streaming(
    path: &str,
    target_segment_duration: f64,
    fps: f64,
) -> Result<bool, ffmpeg::Error> {
    let expected_gop = (target_segment_duration * fps) as usize;
    let tolerance = expected_gop / 10; // 10% tolerance

    let stats = analyze_keyframes(path)?;

    let is_valid = stats.avg_gop_size >= (expected_gop - tolerance) as f64
        && stats.avg_gop_size <= (expected_gop + tolerance) as f64
        && stats.max_gop_size <= expected_gop * 2;

    if !is_valid {
        eprintln!("GOP validation failed:");
        eprintln!("  Expected GOP: ~{} frames", expected_gop);
        eprintln!("  Actual avg GOP: {:.1} frames", stats.avg_gop_size);
        eprintln!("  Max GOP: {} frames", stats.max_gop_size);
    }

    Ok(is_valid)
}
```
