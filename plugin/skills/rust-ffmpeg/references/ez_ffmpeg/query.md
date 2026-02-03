# ez-ffmpeg: Media Query

**Detection Keywords**: get duration, media info, codec info, video properties, probe, file metadata, stream info
**Aliases**: media query, video info, file info

## Related Guides

| Guide | Content |
|-------|---------|
| [video.md](video.md) | Video transcoding, format conversion |
| [audio.md](audio.md) | Audio extraction and processing |
| [cli_migration.md](cli_migration.md) | CLI to Rust migration guide |

## Get Duration

```rust
use ez_ffmpeg::container_info::get_duration_us;

// Get duration in microseconds
let duration_us = get_duration_us("video.mp4")?;
let duration_secs = duration_us as f64 / 1_000_000.0;
println!("Duration: {:.2} seconds", duration_secs);
```

## Get Format

```rust
use ez_ffmpeg::container_info::get_format;

// Get container format name
let format = get_format("video.mp4")?;
println!("Format: {}", format);  // e.g., "mov,mp4,m4a,3gp,3g2,mj2"
```

## Get Metadata

```rust
use ez_ffmpeg::container_info::get_metadata;

// Get container metadata
let metadata = get_metadata("video.mp4")?;
for (key, value) in metadata {
    println!("{}: {}", key, value);
}
// Common keys: title, artist, album, date, encoder, etc.
```

## Query Media Info

```rust
use ez_ffmpeg::stream_info::{find_video_stream_info, find_audio_stream_info, find_all_stream_infos, StreamInfo};

// Get video stream information
if let Some(StreamInfo::Video { width, height, fps, codec_name, bit_rate, .. }) =
    find_video_stream_info("video.mp4")?
{
    println!("Video: {}x{} @ {:.2} fps", width, height, fps);
    println!("Codec: {}, Bitrate: {} bps", codec_name, bit_rate);
}

// Get audio stream information
if let Some(StreamInfo::Audio { sample_rate, nb_channels, codec_name, bit_rate, .. }) =
    find_audio_stream_info("video.mp4")?
{
    println!("Audio: {} Hz, {} channels", sample_rate, nb_channels);
    println!("Codec: {}, Bitrate: {} bps", codec_name, bit_rate);
}

// Get all streams information
let streams = find_all_stream_infos("video.mp4")?;
for stream in streams {
    match stream {
        StreamInfo::Video { index, width, height, fps, codec_name, .. } => {
            println!("Stream #{}: Video {}x{} @ {:.2} fps ({})",
                index, width, height, fps, codec_name);
        }
        StreamInfo::Audio { index, sample_rate, nb_channels, codec_name, .. } => {
            println!("Stream #{}: Audio {} Hz, {} ch ({})",
                index, sample_rate, nb_channels, codec_name);
        }
        StreamInfo::Subtitle { index, codec_name, .. } => {
            println!("Stream #{}: Subtitle ({})", index, codec_name);
        }
        _ => {}
    }
}
```

## List Available Codecs

```rust
use ez_ffmpeg::codec::{get_decoders, get_encoders};

// List all available decoders
let decoders = get_decoders();
for decoder in decoders {
    println!("Decoder: {} - {}", decoder.codec_name, decoder.codec_long_name);
}

// List all available encoders
let encoders = get_encoders();
for encoder in encoders {
    println!("Encoder: {} - {}", encoder.codec_name, encoder.codec_long_name);
}

// Check if specific codec is available
let has_h264 = encoders.iter().any(|e| e.codec_name == "libx264");
```

## List Available Filters

```rust
use ez_ffmpeg::filter::get_filters;

// List all available FFmpeg filters
let filters = get_filters();
for filter in filters {
    println!("Filter: {} - {}", filter.name, filter.description);
}

// Common filters: scale, overlay, crop, pad, fps, volume, etc.
```

## List Capture Devices

For capture usage examples, see [capture.md](capture.md).

```rust
use ez_ffmpeg::device::{get_input_video_devices, get_input_audio_devices};

// List video input devices (cameras, capture cards)
let video_devices = get_input_video_devices()?;
for device in video_devices {
    println!("Video Device: {}", device);
}

// List audio input devices (microphones)
let audio_devices = get_input_audio_devices()?;
for device in audio_devices {
    println!("Audio Device: {}", device);
}
```

## List Hardware Accelerators

```rust
use ez_ffmpeg::hwaccel::get_hwaccels;

// List available hardware acceleration methods
let hwaccels = get_hwaccels();
for hw in hwaccels {
    println!("HW Accel: {}", hw.name);
}
// Common: videotoolbox (macOS), cuda/nvenc (NVIDIA),
//         vaapi/qsv (Intel), dxva2/d3d11va (Windows)
```

## Packet-Level Scanning

Scan media files at the packet level without decoding. Useful for inspecting timestamps, keyframes, and packet metadata.

```rust
use ez_ffmpeg::packet_scanner::PacketScanner;

// Open file and iterate packets
let mut scanner = PacketScanner::open("video.mp4")?;
for packet in scanner.packets() {
    let info = packet?;
    println!(
        "Stream #{}: pts={:?} dts={:?} size={} keyframe={}",
        info.stream_index(),
        info.pts(),
        info.dts(),
        info.size(),
        info.is_keyframe(),
    );
}

// Seek to specific timestamp (microseconds) and scan from there
let mut scanner = PacketScanner::open("video.mp4")?;
scanner.seek(5_000_000)?;  // Seek to 5 seconds
let packet = scanner.next_packet()?;
if let Some(info) = packet {
    println!("First packet after seek: pts={:?}", info.pts());
}

// PacketInfo fields:
// - stream_index(): usize - which stream this packet belongs to
// - pts(): Option<i64> - presentation timestamp (stream time-base)
// - dts(): Option<i64> - decompression timestamp (stream time-base)
// - duration(): i64 - packet duration (stream time-base)
// - size(): usize - packet data size in bytes
// - pos(): i64 - byte position in file (-1 if unknown)
// - is_keyframe(): bool - whether this is a keyframe
// - is_corrupt(): bool - whether packet is flagged as corrupt
```

**Use cases**:
- Analyze GOP structure and keyframe distribution
- Verify timestamp continuity
- Detect corrupt packets
- Build custom seek logic
- Media file integrity checking

## Probe with FFprobe (Alternative)

For comprehensive media analysis, use ffprobe via command:

```rust
// Requires: serde_json = "1.0" in Cargo.toml
use std::process::Command;

let output = Command::new("ffprobe")
    .args([
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "video.mp4"
    ])
    .output()?;

let info: serde_json::Value = serde_json::from_slice(&output.stdout)?;
println!("{}", serde_json::to_string_pretty(&info)?);
```
