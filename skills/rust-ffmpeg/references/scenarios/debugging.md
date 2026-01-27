# Debugging & Troubleshooting

**Detection Keywords**: ffprobe, inspect video, metadata probe, debug ffmpeg, log levels, error messages, timebase issues, codec errors, hanging pipes, probe timeout, file integrity, corrupt file, damaged header, validate file
**Aliases**: debug, troubleshoot, inspect, probe, diagnose, error handling, timeout, validation

Quick patterns for debugging FFmpeg operations, inspecting media files, and troubleshooting common issues.

## Related Scenarios

| Scenario | Content |
|----------|---------|
| [audio_extraction.md](audio_extraction.md) | Metadata extraction patterns |
| [testing.md](testing.md) | Validation and testing |
| [video_transcoding.md](video_transcoding.md) | Simple operations |

---

## Quick Start

### Inspect Media File (ffprobe)

**Using ez-ffmpeg**:
```rust
use ez_ffmpeg::container_info::{get_duration_us, get_format, get_metadata};
use ez_ffmpeg::stream_info::{find_video_stream_info, find_audio_stream_info, StreamInfo};

// Get duration
let duration_us = get_duration_us("video.mp4")?;
println!("Duration: {:.2}s", duration_us as f64 / 1_000_000.0);

// Get format
let format = get_format("video.mp4")?;
println!("Format: {}", format);

// Get metadata tags (title, artist, album, etc.)
let metadata = get_metadata("video.mp4")?;
for (key, value) in metadata {
    println!("{}: {}", key, value);
}

// Get video stream info
if let Some(StreamInfo::Video { width, height, fps, codec_name, .. }) =
    find_video_stream_info("video.mp4")?
{
    println!("Video: {}x{} @ {:.2} fps ({})", width, height, fps, codec_name);
}

// Get audio stream info
if let Some(StreamInfo::Audio { sample_rate, nb_channels, codec_name, .. }) =
    find_audio_stream_info("video.mp4")?
{
    println!("Audio: {} Hz, {} ch ({})", sample_rate, nb_channels, codec_name);
}
```
**See also**: [ez_ffmpeg/query.md](../ez_ffmpeg/query.md)

**Using ffmpeg-sidecar**:
```rust
use ffmpeg_sidecar::command::FfmpegCommand;

let mut child = FfmpegCommand::new()
    .input("video.mp4")
    .rawvideo()
    .spawn()?;

let mut iter = child.iter()?;
let metadata = iter.collect_metadata()?;

// Duration and stream count
println!("Duration: {:?}", metadata.duration());
println!("Input streams: {}", metadata.input_streams.len());

// Stream details (codec, type, etc.)
for stream in &metadata.input_streams {
    println!("Stream {}: {} ({})", stream.index, stream.codec_type, stream.codec_name);
}
```
**See also**: [ffmpeg_sidecar/monitoring.md](../ffmpeg_sidecar/monitoring.md)

---

### Enable Debug Logging

**Using ez-ffmpeg**:
```rust
use ez_ffmpeg::FfmpegContext;

FfmpegContext::builder()
    .input("input.mp4")
    .output("output.mp4")
    .set_log_level("debug")  // trace, debug, verbose, info, warning, error
    .build()?.start()?.wait()?;
```
**See also**: [ez_ffmpeg/advanced.md](../ez_ffmpeg/advanced.md)

**Using ffmpeg-sidecar**:
```rust
FfmpegCommand::new()
    .arg("-loglevel")
    .arg("debug")
    .input("input.mp4")
    .output("output.mp4")
    .spawn()?.wait()?;
```
**See also**: [ffmpeg_sidecar/troubleshooting.md](../ffmpeg_sidecar/troubleshooting.md)

---

### Capture Error Messages

**Using ez-ffmpeg**:
```rust
match FfmpegContext::builder()
    .input("input.mp4")
    .output("output.mp4")
    .build()?.start()?.wait() {
    Ok(_) => println!("Success"),
    Err(e) => eprintln!("Error: {}", e),
}
```
**See also**: [ez_ffmpeg/advanced.md](../ez_ffmpeg/advanced.md)

**Using ffmpeg-sidecar**:
```rust
let iter = FfmpegCommand::new()
    .input("input.mp4")
    .output("output.mp4")
    .spawn()?.iter()?;

for event in iter {
    if let FfmpegEvent::Error(msg) = event {
        eprintln!("Error: {}", msg);
    }
}
```
**See also**: [ffmpeg_sidecar/core.md](../ffmpeg_sidecar/core.md)

---

### Check Codec Support

**Using ez-ffmpeg**:
```rust
use ez_ffmpeg::codec::{get_decoders, get_encoders};

// List all available encoders
let encoders = get_encoders();
for encoder in &encoders {
    println!("Encoder: {} - {}", encoder.codec_name, encoder.codec_long_name);
}

// Check if specific codec is available
let has_h264 = encoders.iter().any(|e| e.codec_name == "libx264");
if has_h264 {
    println!("H.264 encoder available");
}
```
**See also**: [ez_ffmpeg/query.md](../ez_ffmpeg/query.md)

**Using ffmpeg-sidecar**:
```rust
use ffmpeg_sidecar::command::FfmpegCommand;

// List available codecs
let output = FfmpegCommand::new()
    .args(["-codecs"])
    .spawn()?.iter()?.collect_output();

if output.contains("libx264") {
    println!("H.264 encoder available");
}
```
**See also**: [ffmpeg_sidecar/core.md](../ffmpeg_sidecar/core.md)

---

### Validate Output

**Using ez-ffmpeg**:
```rust
use ez_ffmpeg::container_info::get_duration_us;

// After encoding, verify output
let duration = get_duration_us("output.mp4")?;
assert!(duration > 0, "Output has no duration");
println!("Output duration: {:.2}s", duration as f64 / 1_000_000.0);
```
**See also**: [ez_ffmpeg/query.md](../ez_ffmpeg/query.md)

**Using ffmpeg-sidecar**:
```rust
use ffmpeg_sidecar::command::FfmpegCommand;

// After encoding, verify output
let iter = FfmpegCommand::new()
    .input("output.mp4")
    .spawn()?.iter()?;
let metadata = iter.collect_metadata()?;
assert!(metadata.duration().is_some());
```
**See also**: [testing.md](testing.md)

---

## Common Issues & Solutions

### Issue: "No such file or directory"
**Cause**: Input file path incorrect or file doesn't exist
**Solution**: Verify file path with `std::path::Path::exists()`

### Issue: "Unknown encoder 'libx264'"
**Cause**: FFmpeg not compiled with x264 support
**Solution**: Check codec availability with `ffmpeg -codecs`

### Issue: "Conversion failed" or hanging
**Cause**: Incompatible codec/format combination
**Solution**: Enable debug logging to see detailed error messages

### Issue: "Invalid data found when processing input"
**Cause**: Corrupted input file or unsupported format
**Solution**: Use ffprobe to inspect file: `ffprobe input.mp4`

### Issue: Timebase/timestamp errors
**Cause**: Frame rate or timebase mismatch
**Solution**: Explicitly set frame rate with `.filter_desc("fps=30")`

---

## Decision Guide

**Choose ez-ffmpeg if**:
- Need structured error handling
- Want type-safe query API (container_info, stream_info, codec modules)
- Production debugging required
- Async error handling needed

**Choose ffmpeg-sidecar if**:
- Need raw FFmpeg output
- Want event-driven error handling
- CLI-style debugging preferred
- Need to capture all log messages

## Common Debugging Patterns

| Task | ez-ffmpeg | ffmpeg-sidecar |
|------|-----------|----------------|
| Inspect file | `container_info`, `stream_info` | `.collect_metadata()` |
| Get metadata tags | `get_metadata()` | Parse from stream info |
| Debug logging | `.set_log_level("debug")` | `.arg("-loglevel").arg("debug")` |
| Error handling | `Result<T, Error>` | `FfmpegEvent::Error` |
| Codec check | `codec::get_encoders()` | `.args(["-codecs"])` |
| Progress tracking | Callback-based | `FfmpegEvent::Progress` |

## Probe with Timeout

Implement timeout for probing operations to handle unresponsive or slow network sources.

### ez-ffmpeg with Tokio Timeout

```rust
use ez_ffmpeg::container_info::get_duration_us;
use std::time::Duration;
use tokio::time::timeout;

async fn probe_with_timeout(path: &str, timeout_secs: u64) -> Result<i64, String> {
    let path = path.to_string();

    let result = timeout(
        Duration::from_secs(timeout_secs),
        tokio::task::spawn_blocking(move || get_duration_us(&path))
    ).await;

    match result {
        Ok(Ok(Ok(duration))) => Ok(duration),
        Ok(Ok(Err(e))) => Err(format!("FFmpeg error: {:?}", e)),
        Ok(Err(e)) => Err(format!("Task error: {}", e)),
        Err(_) => Err(format!("Probe timeout after {}s", timeout_secs)),
    }
}

#[tokio::main]
async fn main() {
    match probe_with_timeout("rtmp://slow-server/stream", 5).await {
        Ok(duration) => println!("Duration: {}us", duration),
        Err(e) => eprintln!("Error: {}", e),
    }
}
```

### ffmpeg-sidecar with Process Timeout

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use std::time::{Duration, Instant};
use std::io::{BufRead, BufReader};

fn probe_with_timeout(path: &str, timeout_secs: u64) -> Result<String, String> {
    let mut child = FfmpegCommand::new()
        .args(["-i", path])
        .args(["-f", "null", "-"])
        .spawn()
        .map_err(|e| format!("Spawn error: {}", e))?;

    let start = Instant::now();
    let timeout = Duration::from_secs(timeout_secs);

    // Poll for completion with timeout
    loop {
        match child.inner_mut().try_wait() {
            Ok(Some(_status)) => {
                // Process completed
                return Ok("Probe completed".to_string());
            }
            Ok(None) => {
                // Still running
                if start.elapsed() > timeout {
                    child.quit().ok();
                    return Err(format!("Probe timeout after {}s", timeout_secs));
                }
                std::thread::sleep(Duration::from_millis(100));
            }
            Err(e) => return Err(format!("Wait error: {}", e)),
        }
    }
}
```

### ffmpeg-next with Thread Timeout

```rust
extern crate ffmpeg_next as ffmpeg;

use std::sync::mpsc;
use std::thread;
use std::time::Duration;

fn probe_with_timeout(path: &str, timeout_secs: u64) -> Result<i64, String> {
    let (tx, rx) = mpsc::channel();
    let path = path.to_string();

    thread::spawn(move || {
        ffmpeg::init().ok();
        let result = ffmpeg::format::input(&path)
            .map(|ctx| ctx.duration());
        tx.send(result).ok();
    });

    match rx.recv_timeout(Duration::from_secs(timeout_secs)) {
        Ok(Ok(duration)) => Ok(duration),
        Ok(Err(e)) => Err(format!("FFmpeg error: {}", e)),
        Err(mpsc::RecvTimeoutError::Timeout) => {
            Err(format!("Probe timeout after {}s", timeout_secs))
        }
        Err(e) => Err(format!("Channel error: {}", e)),
    }
}
```

## File Integrity Validation

Check file integrity before processing to handle corrupted or incomplete files gracefully.

### Basic Integrity Check

```rust
use ez_ffmpeg::container_info::{get_duration_us, get_format};
use ez_ffmpeg::stream_info::{find_video_stream_info, find_audio_stream_info, StreamInfo};

#[derive(Debug)]
pub enum IntegrityError {
    CannotOpen(String),
    NoDuration,
    NoStreams,
    InvalidCodec(String),
    CorruptHeader(String),
}

pub struct FileIntegrity {
    pub is_valid: bool,
    pub duration_us: Option<i64>,
    pub has_video: bool,
    pub has_audio: bool,
    pub warnings: Vec<String>,
}

pub fn check_file_integrity(path: &str) -> Result<FileIntegrity, IntegrityError> {
    let mut result = FileIntegrity {
        is_valid: true,
        duration_us: None,
        has_video: false,
        has_audio: false,
        warnings: Vec::new(),
    };

    // Check if file can be opened and parsed
    let format = get_format(path)
        .map_err(|e| IntegrityError::CannotOpen(format!("{:?}", e)))?;

    if format.is_empty() {
        return Err(IntegrityError::CorruptHeader("Unknown format".to_string()));
    }

    // Check duration
    match get_duration_us(path) {
        Ok(d) if d > 0 => result.duration_us = Some(d),
        Ok(_) => result.warnings.push("Zero or negative duration".to_string()),
        Err(_) => result.warnings.push("Cannot determine duration".to_string()),
    }

    // Check video stream
    match find_video_stream_info(path) {
        Ok(Some(StreamInfo::Video { width, height, codec_name, .. })) => {
            result.has_video = true;
            if width == 0 || height == 0 {
                result.warnings.push("Invalid video dimensions".to_string());
            }
            if codec_name.is_empty() {
                result.warnings.push("Unknown video codec".to_string());
            }
        }
        Ok(_) => {}
        Err(e) => result.warnings.push(format!("Video stream error: {:?}", e)),
    }

    // Check audio stream
    match find_audio_stream_info(path) {
        Ok(Some(StreamInfo::Audio { sample_rate, nb_channels, codec_name, .. })) => {
            result.has_audio = true;
            if sample_rate == 0 {
                result.warnings.push("Invalid sample rate".to_string());
            }
            if nb_channels == 0 {
                result.warnings.push("Invalid channel count".to_string());
            }
            if codec_name.is_empty() {
                result.warnings.push("Unknown audio codec".to_string());
            }
        }
        Ok(_) => {}
        Err(e) => result.warnings.push(format!("Audio stream error: {:?}", e)),
    }

    // Must have at least one stream
    if !result.has_video && !result.has_audio {
        return Err(IntegrityError::NoStreams);
    }

    result.is_valid = result.warnings.is_empty();
    Ok(result)
}
```

### Deep Integrity Check (Scan Packets)

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{format, Error};

#[derive(Debug)]
pub struct DeepIntegrityResult {
    pub total_packets: usize,
    pub corrupt_packets: usize,
    pub pts_discontinuities: usize,
    pub is_truncated: bool,
}

pub fn deep_integrity_check(path: &str) -> Result<DeepIntegrityResult, Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(path)?;
    let expected_duration = ictx.duration();

    let mut result = DeepIntegrityResult {
        total_packets: 0,
        corrupt_packets: 0,
        pts_discontinuities: 0,
        is_truncated: false,
    };

    let mut last_pts: Option<i64> = None;
    let mut max_pts: i64 = 0;

    for (stream, packet) in ictx.packets() {
        result.total_packets += 1;

        // Check for corrupt packet (no data)
        if packet.size() == 0 && !packet.is_key() {
            result.corrupt_packets += 1;
        }

        // Check PTS continuity
        if let Some(pts) = packet.pts() {
            if let Some(last) = last_pts {
                // Large backward jump indicates discontinuity
                if pts < last - 90000 { // ~1 second in 90kHz timebase
                    result.pts_discontinuities += 1;
                }
            }
            max_pts = max_pts.max(pts);
            last_pts = Some(pts);
        }
    }

    // Check if file appears truncated (actual duration much less than header)
    if expected_duration > 0 && max_pts > 0 {
        let actual_ratio = max_pts as f64 / expected_duration as f64;
        if actual_ratio < 0.9 {
            result.is_truncated = true;
        }
    }

    Ok(result)
}
```

### Usage Example

```rust
fn process_file_safely(path: &str) -> Result<(), String> {
    // Quick integrity check first
    let integrity = check_file_integrity(path)
        .map_err(|e| format!("Integrity check failed: {:?}", e))?;

    if !integrity.is_valid {
        eprintln!("Warnings: {:?}", integrity.warnings);
    }

    if !integrity.has_video && !integrity.has_audio {
        return Err("No media streams found".to_string());
    }

    // Optional: deep check for critical files
    let deep = deep_integrity_check(path)
        .map_err(|e| format!("Deep check failed: {}", e))?;

    if deep.corrupt_packets > 0 {
        eprintln!("Warning: {} corrupt packets found", deep.corrupt_packets);
    }

    if deep.is_truncated {
        return Err("File appears truncated".to_string());
    }

    // File is valid, proceed with processing
    println!("File validated: {} packets, duration {:?}us",
        deep.total_packets, integrity.duration_us);

    Ok(())
}
```

## Advanced Topics

For advanced debugging scenarios, see:
- [ez-ffmpeg error handling](../ez_ffmpeg/advanced.md)
- [ffmpeg-sidecar monitoring](../ffmpeg_sidecar/monitoring.md)
- [ffmpeg-sidecar troubleshooting](../ffmpeg_sidecar/troubleshooting.md)
- [Testing strategies](testing.md)
