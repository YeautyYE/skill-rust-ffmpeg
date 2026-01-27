# Testing & Validation

**Detection Keywords**: test ffmpeg, unit test, integration test, golden file, checksum validation, duration check, verify output, test video processing, frame rate check, verify fps, frame count, nb_frames
**Aliases**: testing, validation, verify, quality assurance, test automation

Quick patterns for testing FFmpeg operations, validating outputs, and ensuring quality.

## Test Environment Setup

> **Important**: Before writing tests, check if local `ffmpeg` and `ffprobe` are available. They can generate test videos and verify outputs.

### Check Local Tools

```bash
# Check ffmpeg availability
ffmpeg -version

# Check ffprobe availability
ffprobe -version
```

### Generate Test Videos with ffmpeg

Use `lavfi` virtual sources - no real video files needed:

```bash
# Generate 10-second 1080p test video with audio (H.264 + AAC)
ffmpeg -f lavfi -i testsrc=size=1920x1080:rate=30:duration=10 \
       -f lavfi -i sine=frequency=440:duration=10 \
       -c:v libx264 -preset ultrafast -c:a aac \
       test_input.mp4

# Generate 720p test video (5 seconds, no audio)
ffmpeg -f lavfi -i testsrc=size=1280x720:rate=30:duration=5 \
       -c:v libx264 -preset ultrafast \
       test_720p.mp4

# Generate audio-only test file
ffmpeg -f lavfi -i sine=frequency=440:duration=10 \
       -c:a aac test_audio.aac

# Generate silent video (for audio extraction tests)
ffmpeg -f lavfi -i testsrc=size=640x480:rate=30:duration=5 \
       -f lavfi -i anullsrc=r=44100:cl=stereo:d=5 \
       -c:v libx264 -c:a aac silent_video.mp4
```

### Verify Output with ffprobe

```bash
# Check video resolution and codec
ffprobe -v error -select_streams v:0 \
        -show_entries stream=width,height,codec_name \
        -of csv=p=0 output.mp4
# Output: 1280,720,h264

# Check duration (in seconds)
ffprobe -v error -show_entries format=duration \
        -of default=noprint_wrappers=1:nokey=1 output.mp4
# Output: 10.000000

# Check audio properties
ffprobe -v error -select_streams a:0 \
        -show_entries stream=codec_name,sample_rate,channels \
        -of csv=p=0 output.mp4
# Output: aac,44100,2

# Check frame rate
ffprobe -v error -select_streams v:0 \
        -show_entries stream=r_frame_rate \
        -of default=noprint_wrappers=1:nokey=1 output.mp4
# Output: 30/1

# Check frame count
ffprobe -v error -select_streams v:0 \
        -show_entries stream=nb_frames \
        -of default=noprint_wrappers=1:nokey=1 output.mp4
# Output: 150

# Full format info (JSON)
ffprobe -v quiet -print_format json -show_format -show_streams output.mp4
```

### Integration in Rust Tests

```rust
use std::process::Command;

/// Check if ffmpeg is available
fn ffmpeg_available() -> bool {
    Command::new("ffmpeg").arg("-version").output().is_ok()
}

/// Generate test video using ffmpeg CLI
fn generate_test_video(output: &str, width: u32, height: u32, duration: u32) -> std::io::Result<()> {
    let status = Command::new("ffmpeg")
        .args(["-y", "-f", "lavfi"])
        .args(["-i", &format!("testsrc=size={}x{}:rate=30:duration={}", width, height, duration)])
        .args(["-c:v", "libx264", "-preset", "ultrafast"])
        .arg(output)
        .status()?;
    assert!(status.success());
    Ok(())
}

/// Verify video resolution using ffprobe
fn verify_resolution(path: &str) -> std::io::Result<(u32, u32)> {
    let output = Command::new("ffprobe")
        .args(["-v", "error", "-select_streams", "v:0"])
        .args(["-show_entries", "stream=width,height"])
        .args(["-of", "csv=p=0"])
        .arg(path)
        .output()?;
    let s = String::from_utf8_lossy(&output.stdout);
    let parts: Vec<&str> = s.trim().split(',').collect();
    Ok((parts[0].parse().unwrap(), parts[1].parse().unwrap()))
}

/// Verify video frame rate using ffprobe
fn verify_framerate(path: &str) -> std::io::Result<(u32, u32)> {
    let output = Command::new("ffprobe")
        .args(["-v", "error", "-select_streams", "v:0"])
        .args(["-show_entries", "stream=r_frame_rate"])
        .args(["-of", "default=noprint_wrappers=1:nokey=1"])
        .arg(path)
        .output()?;
    let s = String::from_utf8_lossy(&output.stdout);
    let parts: Vec<&str> = s.trim().split('/').collect();
    Ok((parts[0].parse().unwrap(), parts[1].parse().unwrap()))
}

/// Verify video frame count using ffprobe
fn verify_frame_count(path: &str) -> std::io::Result<u64> {
    let output = Command::new("ffprobe")
        .args(["-v", "error", "-select_streams", "v:0"])
        .args(["-show_entries", "stream=nb_frames"])
        .args(["-of", "default=noprint_wrappers=1:nokey=1"])
        .arg(path)
        .output()?;
    let s = String::from_utf8_lossy(&output.stdout);
    Ok(s.trim().parse().unwrap())
}

#[test]
fn test_resize_1080p_to_720p() -> Result<(), Box<dyn std::error::Error>> {
    // Skip if ffmpeg not available
    if !ffmpeg_available() { return Ok(()); }

    // Generate test input
    generate_test_video("test_input.mp4", 1920, 1080, 5)?;

    // Run your Rust code here
    // resize_video("test_input.mp4", "test_output.mp4", 1280, 720)?;

    // Verify output
    let (w, h) = verify_resolution("test_output.mp4")?;
    assert_eq!((w, h), (1280, 720));

    // Cleanup
    std::fs::remove_file("test_input.mp4")?;
    std::fs::remove_file("test_output.mp4")?;
    Ok(())
}
```

---

## Related Scenarios

| Scenario | Content |
|----------|---------|
| [debugging.md](debugging.md) | Error handling, inspection |
| [video_transcoding.md](video_transcoding.md) | Simple operations to test |
| [batch_processing.md](batch_processing.md) | Batch testing patterns |

---

## Quick Start

### Basic Output Validation

**Using ez-ffmpeg**:
```rust
use ez_ffmpeg::{FfmpegContext};
use ez_ffmpeg::container_info::get_duration_us;
use std::path::Path;

FfmpegContext::builder()
    .input("input.mp4")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Verify output exists
assert!(Path::new("output.mp4").exists());

// Verify output has valid duration
let duration = get_duration_us("output.mp4")?;
assert!(duration > 0, "Output has no duration");
```
**See also**: [ez_ffmpeg/query.md](../ez_ffmpeg/query.md)

**Using ffmpeg-sidecar for validation**:
```rust
use ffmpeg_sidecar::command::FfmpegCommand;

let mut child = FfmpegCommand::new()
    .input("output.mp4")
    .spawn()?;
let metadata = child.iter()?.collect_metadata()?;
assert!(metadata.duration().is_some());
```
**See also**: [ffmpeg_sidecar/core.md](../ffmpeg_sidecar/core.md)

---

### Golden File Testing

**Using ez-ffmpeg**:
```rust
use ez_ffmpeg::FfmpegContext;
use ez_ffmpeg::container_info::get_duration_us;

FfmpegContext::builder()
    .input("test_input.mp4")
    .output("test_output.mp4")
    .build()?.start()?.wait()?;

// Compare durations
let output_duration = get_duration_us("test_output.mp4")?;
let golden_duration = get_duration_us("golden_output.mp4")?;

// Allow 1% tolerance
let tolerance = golden_duration / 100;
let diff = (output_duration as i64 - golden_duration as i64).abs() as u64;
assert!(diff <= tolerance, "Duration mismatch");
```
**See also**: [ez_ffmpeg/query.md](../ez_ffmpeg/query.md)

**Using ffmpeg-sidecar**:
```rust
use ffmpeg_sidecar::command::FfmpegCommand;

let output_meta = FfmpegCommand::new().input("test_output.mp4").spawn()?.iter()?.collect_metadata()?;
let golden_meta = FfmpegCommand::new().input("golden_output.mp4").spawn()?.iter()?.collect_metadata()?;
// Compare metadata...
```
**See also**: [ffmpeg_sidecar/core.md](../ffmpeg_sidecar/core.md)

---

### Checksum Validation

**Using standard Rust**:
```rust
use sha2::{Sha256, Digest};

fn calculate_checksum(path: &str) -> Result<String, std::io::Error> {
    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0; 8192];
    loop { let n = file.read(&mut buffer)?; if n == 0 { break; } hasher.update(&buffer[..n]); }
    Ok(format!("{:x}", hasher.finalize()))
}
```

---

### Test with Temporary Files

**Using tempfile crate**:
```rust
use tempfile::NamedTempFile;
use ez_ffmpeg::FfmpegContext;

#[test]
fn test_video_processing() -> Result<(), Box<dyn std::error::Error>> {
    let temp = NamedTempFile::new()?;
    FfmpegContext::builder().input("test_input.mp4")
        .output(temp.path().to_str().unwrap())
        .build()?.start()?.wait()?;
    assert!(temp.path().exists());
    Ok(())
}
```
**See also**: [Rust tempfile crate](https://docs.rs/tempfile)

---

### Integration Test with ffmpeg-sidecar

**Using ffmpeg-sidecar**:
```rust
#[test]
fn test_thumbnail_extraction() -> Result<(), Box<dyn std::error::Error>> {
    let mut child = FfmpegCommand::new()
        .input("test_video.mp4").frames(1).output("test_thumb.jpg")
        .spawn()?;

    assert!(child.wait()?.success());
    assert!(Path::new("test_thumb.jpg").exists());
    std::fs::remove_file("test_thumb.jpg")?;
    Ok(())
}
```
**See also**: [ffmpeg_sidecar/core.md](../ffmpeg_sidecar/core.md)

---

### Mock FFmpeg for Unit Tests

**Using ffmpeg-sidecar with test fixtures**:
```rust
#[cfg(test)]
mod tests {
    #[test]
    fn test_with_mock_input() {
        let test_video = "tests/fixtures/sample.mp4";
        let result = process_video(test_video);
        assert!(result.is_ok());
    }
}
```

---

## Testing Patterns

### Unit Testing
```rust
#[cfg(test)]
mod tests {
    #[test]
    fn test_format_conversion() {
        let result = convert_format("input.mp4", "output.webm");
        assert!(result.is_ok());
    }
}
```

### Integration Testing
```rust
#[test]
fn test_full_pipeline() {
    // Test complete workflow
    let result = extract_thumbnail("video.mp4")
        .and_then(|thumb| resize_image(thumb, 320, 180))
        .and_then(|resized| save_to_disk(resized, "output.jpg"));

    assert!(result.is_ok());
}
```

### Property-Based Testing
```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn test_any_valid_resolution(w in 100u32..3840, h in 100u32..2160) {
        let result = resize_video("input.mp4", w, h);
        assert!(result.is_ok());
    }
}
```

---

## Decision Guide

**Choose ez-ffmpeg if**:
- Need structured query API (container_info, stream_info modules)
- Want type-safe validation
- Testing async workflows
- Production test suites

**Choose ffmpeg-sidecar if**:
- Testing CLI-style operations
- Need event-driven validation
- Testing with mock inputs
- Simple integration tests

## Common Testing Patterns

| Task | Pattern | Tools |
|------|---------|-------|
| Output validation | Duration check + file exists | ez-ffmpeg container_info |
| Golden file testing | Duration/metadata comparison | Both libraries |
| Temporary files | NamedTempFile | tempfile crate |
| Integration tests | Full pipeline testing | Both libraries |
| Mock testing | Test fixtures | Standard Rust |

## Advanced Topics

For advanced testing scenarios, see:
- [Batch testing](batch_processing.md)
- [Performance benchmarking](hardware_acceleration.md)
- [Batch testing](batch_processing.md)
- [Error handling tests](debugging.md)
