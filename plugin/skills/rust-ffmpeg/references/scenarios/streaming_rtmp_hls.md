# Streaming (RTMP & HLS)

**Detection Keywords**: rtmp stream, hls generation, how to stream video, live streaming tutorial, live streaming, real-time encoding, broadcast, stream output, network streaming, jitter buffer, network jitter, buffer management, packet loss, stream buffer, latency buffer, playout buffer
**Aliases**: live stream, broadcast, streaming output, RTMP push, HLS output, jitter management, buffer control

Stream video to RTMP servers and generate HLS playlists across all Rust FFmpeg libraries.

## Table of Contents

- [Quick Example](#quick-example-30-seconds)
- [Library Comparison](#library-comparison)
- [Detailed Examples](#detailed-examples)
- [When to Choose](#when-to-choose)
- [Common Patterns](#common-patterns)
- [Streaming Best Practices](#streaming-best-practices)
- [Related Scenarios](#related-scenarios)

## Quick Example (30 seconds)

```rust
// ez-ffmpeg
use ez_ffmpeg::{FfmpegContext, Output};

FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("rtmp://server/live/stream")
        .set_format("flv")
        .set_video_codec("libx264")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;
```

```rust
// ffmpeg-sidecar
use ffmpeg_sidecar::command::FfmpegCommand;

FfmpegCommand::new()
    .input("video.mp4")
    .args(["-f", "flv"])
    .codec_video("libx264")
    .codec_audio("aac")
    .output("rtmp://server/live/stream")
    .spawn()?.wait()?;
```

## Library Comparison

| Aspect | ez-ffmpeg | ffmpeg-next | ffmpeg-sys-next | ffmpeg-sidecar |
|--------|-----------|-------------|-----------------|----------------|
| **Async support** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Code complexity** | Low | Medium | High | Low |
| **Type safety** | ✅ Full | ✅ Full | ⚠️ Unsafe | ✅ Full |
| **RTMP server** | ✅ Yes (embedded, high-concurrency) | ❌ No | ❌ No | ❌ No |
| **Use when** | General tasks | Protocol control | Max performance | No install |

## Detailed Examples

For detailed streaming examples, see library-specific guides:
- **ez-ffmpeg**: [ez_ffmpeg/streaming.md](../ez_ffmpeg/streaming.md) - RTMP push, HLS generation, re-streaming, embedded high-concurrency RTMP server, real-time encoding
- **ffmpeg-next**: [ffmpeg_next/streaming.md](../ffmpeg_next/streaming.md) - protocol-level streaming control
- **ffmpeg-sys-next**: [ffmpeg_sys_next/frame_codec.md](../ffmpeg_sys_next/frame_codec.md) - low-level streaming operations
- **ffmpeg-sidecar**: [ffmpeg_sidecar/streaming.md](../ffmpeg_sidecar/streaming.md) - CLI wrapper streaming

## When to Choose

See [Library Selection Guide](../library_selection.md) for detailed criteria.

## Common Patterns

### HLS generation
```rust
// ez-ffmpeg
.output(Output::from("stream.m3u8")
    .set_format("hls")
    .set_format_opt("hls_time", "4")
    .set_format_opt("hls_list_size", "5"))

// ffmpeg-sidecar
.args(["-f", "hls", "-hls_time", "4", "-hls_list_size", "5"])
.output("stream.m3u8")
```

### Low-latency streaming
```rust
// ez-ffmpeg
.output(Output::from("rtmp://server/live/stream")
    .set_video_codec("libx264")
    .set_video_codec_opt("preset", "ultrafast")
    .set_video_codec_opt("tune", "zerolatency"))

// ffmpeg-sidecar
.codec_video("libx264")
.args(["-preset", "ultrafast", "-tune", "zerolatency"])
```

## Streaming Best Practices

### Keyframe Alignment (Critical for HLS/DASH)

Keyframes (I-frames) must align with segment boundaries for smooth playback:

```rust
// ez-ffmpeg: Force keyframe every 2 seconds (for 30fps video)
.output(Output::from("stream.m3u8")
    .set_format("hls")
    .set_format_opt("hls_time", "2")
    .set_video_codec("libx264")
    .set_video_codec_opt("g", "60")           // GOP size = fps * segment_duration
    .set_video_codec_opt("keyint_min", "60")  // Minimum keyframe interval
    .set_video_codec_opt("sc_threshold", "0") // Disable scene change detection
    .set_video_codec_opt("force_key_frames", "expr:gte(t,n_forced*2)")) // Force keyframe every 2s

// ffmpeg-sidecar
.args(["-g", "60", "-keyint_min", "60", "-sc_threshold", "0"])
.args(["-force_key_frames", "expr:gte(t,n_forced*2)"])
```

**Why this matters**: Without keyframe alignment, players may experience buffering or seek issues.

### Real-time Input Rate Control

When streaming from files (not live sources), control input rate to prevent buffer overflow:

```rust
// ez-ffmpeg: Read at 1x speed (real-time)
use ez_ffmpeg::Input;

FfmpegContext::builder()
    .input(Input::from("video.mp4")
        .set_readrate(1.0))  // Equivalent to -re flag
    .output(Output::from("rtmp://server/live/stream")
        .set_format("flv"))
    .build()?.start()?.wait()?;

// ffmpeg-sidecar
FfmpegCommand::new()
    .args(["-re"])  // Real-time input
    .input("video.mp4")
    .output("rtmp://server/live/stream")
    .spawn()?.wait()?;
```

### Constant Bitrate (CBR) for Stable Streaming

Use CBR for consistent bandwidth usage:

```rust
// ez-ffmpeg: CBR at 2.5 Mbps
.output(Output::from("rtmp://server/live/stream")
    .set_video_codec("libx264")
    .set_video_codec_opt("b", "2500k")      // Target bitrate
    .set_video_codec_opt("maxrate", "2500k") // Max bitrate = target for CBR
    .set_video_codec_opt("bufsize", "5000k") // Buffer size = 2x bitrate
    .set_video_codec_opt("nal-hrd", "cbr"))  // Signal CBR to decoder

// ffmpeg-sidecar
.args(["-b:v", "2500k", "-maxrate", "2500k", "-bufsize", "5000k"])
```

### HLS Segment Naming and Cleanup

```rust
// ez-ffmpeg: Production HLS configuration
.output(Output::from("live/playlist.m3u8")
    .set_format("hls")
    .set_format_opt("hls_time", "4")                    // 4-second segments
    .set_format_opt("hls_list_size", "5")              // Keep 5 segments in playlist
    .set_format_opt("hls_flags", "delete_segments")    // Auto-delete old segments
    .set_format_opt("hls_segment_filename", "live/segment_%03d.ts"))
```

### Audio/Video Sync for Live Streams

```rust
// ez-ffmpeg: Ensure A/V sync with async audio resampling
FfmpegContext::builder()
    .input(Input::from("rtmp://source/live/stream"))
    .filter_desc("aresample=async=1")  // Resample audio to maintain sync
    .output(Output::from("rtmp://dest/live/stream")
        .set_format("flv")
        .set_video_codec("copy")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;
```

### Reconnection for Unstable Networks

```rust
// ez-ffmpeg: Input with reconnection options
.input(Input::from("rtmp://source/live/stream")
    .set_input_opt("reconnect", "1")
    .set_input_opt("reconnect_streamed", "1")
    .set_input_opt("reconnect_delay_max", "5"))

// ffmpeg-sidecar
.args(["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5"])
.input("rtmp://source/live/stream")
```

### Summary: Production Streaming Checklist

| Setting | Purpose | Typical Value |
|---------|---------|---------------|
| `-g` (GOP size) | Keyframe interval | fps × segment_duration |
| `-sc_threshold 0` | Disable scene detection | Always for HLS/DASH |
| `-re` / `set_readrate(1.0)` | Real-time input | File-to-stream only |
| `-b:v` / `-maxrate` / `-bufsize` | CBR encoding | 2.5M / 2.5M / 5M |
| `-hls_time` | Segment duration | 2-6 seconds |
| `-hls_flags delete_segments` | Cleanup old segments | Live streams |
| `-tune zerolatency` | Minimize latency | Low-latency streams |

### Network Jitter Buffer Management

Handle network instability in live streaming scenarios:

```rust
// ffmpeg-next: Implement a packet jitter buffer
use ffmpeg_next::{codec, format, Packet};
use std::collections::BinaryHeap;
use std::cmp::Reverse;
use std::time::{Duration, Instant};

struct TimestampedPacket {
    packet: Packet,
    pts: i64,
    arrival_time: Instant,
}

impl Ord for TimestampedPacket {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.pts.cmp(&other.pts)
    }
}

impl PartialOrd for TimestampedPacket {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for TimestampedPacket {
    fn eq(&self, other: &Self) -> bool {
        self.pts == other.pts
    }
}

impl Eq for TimestampedPacket {}

struct JitterBuffer {
    buffer: BinaryHeap<Reverse<TimestampedPacket>>,
    target_latency: Duration,
    max_size: usize,
    last_output_pts: i64,
}

impl JitterBuffer {
    fn new(target_latency_ms: u64, max_size: usize) -> Self {
        Self {
            buffer: BinaryHeap::new(),
            target_latency: Duration::from_millis(target_latency_ms),
            max_size,
            last_output_pts: i64::MIN,
        }
    }

    fn push(&mut self, packet: Packet) {
        let pts = packet.pts().unwrap_or(0);

        // Drop if buffer is full and this packet is older than oldest buffered
        if self.buffer.len() >= self.max_size {
            if let Some(Reverse(oldest)) = self.buffer.peek() {
                if pts < oldest.pts {
                    return; // Drop old packet
                }
            }
            self.buffer.pop(); // Remove oldest to make room
        }

        self.buffer.push(Reverse(TimestampedPacket {
            packet,
            pts,
            arrival_time: Instant::now(),
        }));
    }

    fn pop(&mut self) -> Option<Packet> {
        // Only output if we have enough buffered
        if let Some(Reverse(oldest)) = self.buffer.peek() {
            if oldest.arrival_time.elapsed() >= self.target_latency {
                if let Some(Reverse(pkt)) = self.buffer.pop() {
                    // Skip out-of-order packets
                    if pkt.pts > self.last_output_pts {
                        self.last_output_pts = pkt.pts;
                        return Some(pkt.packet);
                    }
                }
            }
        }
        None
    }

    fn is_ready(&self) -> bool {
        if let Some(Reverse(oldest)) = self.buffer.peek() {
            oldest.arrival_time.elapsed() >= self.target_latency
        } else {
            false
        }
    }
}

// Usage example
fn stream_with_jitter_buffer(
    input_url: &str,
    output_url: &str,
) -> Result<(), ffmpeg_next::Error> {
    ffmpeg_next::init()?;

    let mut ictx = format::input(&input_url)?;
    let mut octx = format::output(&output_url)?;

    // Create jitter buffer: 200ms latency, max 100 packets
    let mut video_buffer = JitterBuffer::new(200, 100);
    let mut audio_buffer = JitterBuffer::new(200, 100);

    for (stream, _) in ictx.streams().enumerate() {
        let mut out_stream = octx.add_stream(codec::encoder::find(codec::Id::None))?;
        out_stream.set_parameters(ictx.stream(stream).unwrap().parameters());
    }

    octx.write_header()?;

    let video_idx = ictx.streams().best(ffmpeg_next::media::Type::Video)
        .map(|s| s.index());
    let audio_idx = ictx.streams().best(ffmpeg_next::media::Type::Audio)
        .map(|s| s.index());

    for (stream, packet) in ictx.packets() {
        let idx = stream.index();

        // Add to appropriate buffer
        if Some(idx) == video_idx {
            video_buffer.push(packet);
        } else if Some(idx) == audio_idx {
            audio_buffer.push(packet);
        }

        // Output buffered packets
        while let Some(pkt) = video_buffer.pop() {
            pkt.write_interleaved(&mut octx)?;
        }
        while let Some(pkt) = audio_buffer.pop() {
            pkt.write_interleaved(&mut octx)?;
        }
    }

    octx.write_trailer()?;
    Ok(())
}
```

```rust
// ez-ffmpeg: Use FFmpeg's built-in buffer options
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Configure input buffering for network streams
FfmpegContext::builder()
    .input(Input::from("rtmp://source/live/stream")
        // Increase buffer size for jitter absorption
        .set_input_opt("buffer_size", "1048576")     // 1MB buffer
        .set_input_opt("max_delay", "500000")        // 500ms max delay
        .set_input_opt("analyzeduration", "5000000") // 5s analyze duration
        .set_input_opt("probesize", "5000000")       // 5MB probe size
        // Reconnection for network issues
        .set_input_opt("reconnect", "1")
        .set_input_opt("reconnect_streamed", "1")
        .set_input_opt("reconnect_delay_max", "5"))
    .output(Output::from("rtmp://dest/live/stream")
        .set_format("flv")
        // Output buffer settings
        .set_format_opt("flush_packets", "0")        // Buffer before writing
        .set_format_opt("max_interleave_delta", "0")) // Disable interleave limit
    .build()?.start()?.wait()?;
```

```rust
// ffmpeg-sidecar: Buffer options via CLI args
use ffmpeg_sidecar::command::FfmpegCommand;

FfmpegCommand::new()
    // Input buffer configuration
    .args(["-buffer_size", "1048576"])     // 1MB input buffer
    .args(["-max_delay", "500000"])        // 500ms max delay
    .args(["-analyzeduration", "5000000"]) // 5s analysis
    .args(["-probesize", "5000000"])       // 5MB probe
    .args(["-fflags", "+genpts"])          // Generate PTS if missing
    // Reconnection
    .args(["-reconnect", "1"])
    .args(["-reconnect_streamed", "1"])
    .args(["-reconnect_delay_max", "5"])
    .input("rtmp://source/live/stream")
    // Output with thread queue
    .args(["-thread_queue_size", "512"])   // Packet queue size
    .output("rtmp://dest/live/stream")
    .spawn()?.wait()?;
```

**Jitter Buffer Guidelines**:
| Network Condition | Buffer Size | Latency Trade-off |
|-------------------|-------------|-------------------|
| Stable LAN | 50-100ms | Ultra-low latency |
| Good Internet | 200-500ms | Low latency |
| Variable 4G/WiFi | 500ms-1s | Medium latency |
| Poor connection | 1-3s | High latency, smooth playback |

**Common Buffer Options**:
| Option | Purpose | Typical Value |
|--------|---------|---------------|
| `buffer_size` | Input read buffer | 1-5MB |
| `max_delay` | Max demux delay | 500000 (500ms) |
| `thread_queue_size` | Packet queue | 512-1024 |
| `flush_packets` | Output buffering | 0 (buffered) |
| `fflags +genpts` | Generate missing PTS | Always for unreliable sources |

## Related Scenarios

| Scenario | Guide |
|----------|-------|
| Video transcoding | [video_transcoding.md](video_transcoding.md) |
| Hardware acceleration | [hardware_acceleration.md](hardware_acceleration.md) |
| Device capture | [capture.md](../ez_ffmpeg/capture.md) |
| Batch processing | [batch_processing.md](batch_processing.md) |
