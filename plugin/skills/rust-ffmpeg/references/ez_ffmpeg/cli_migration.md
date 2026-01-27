# ez-ffmpeg: CLI Migration Guide

**Detection Keywords**: cli to rust, convert ffmpeg command, migration guide, ffmpeg options, command line equivalent
**Aliases**: cli migration, ffmpeg to rust, command conversion

## Table of Contents

- [Related Guides](#related-guides)
- [Core Pattern](#core-pattern)
- [Common Conversions](#common-conversions)
- [CLI Option Mapping](#cli-option-mapping)
- [Time Conversion](#time-conversion)
- [Async Support](#async-support)

## Related Guides

| Guide | Content |
|-------|---------|
| [video.md](video.md) | Video transcoding, format conversion |
| [audio.md](audio.md) | Audio extraction and processing |
| [filters.md](filters.md) | FFmpeg filters (scale, crop, etc.) |

Quick reference for converting FFmpeg CLI commands to ez-ffmpeg Rust code.

## Core Pattern

**FFmpeg CLI structure:**
```bash
ffmpeg [input_options] -i input [output_options] output
```

**ez-ffmpeg Rust equivalent:**
```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

FfmpegContext::builder()
    .input(Input::from("input").set_input_opt("option", "value"))
    .output(Output::from("output").set_video_codec("codec"))
    .build()?.start()?.wait()?;
```

## Common Conversions

### Format Conversion

```bash
ffmpeg -i input.mp4 output.avi
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output("output.avi")
    .build()?.start()?.wait()?;
```

### Extract Audio

```bash
ffmpeg -i input.mp4 -vn -acodec copy output.aac
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.aac")
        .add_stream_map("0:a"))  // Select audio only
    .build()?.start()?.wait()?;
```

### Extract Video (No Audio)

```bash
ffmpeg -i input.mp4 -an -c:v copy output.mp4
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .add_stream_map_with_copy("0:v"))  // Video only, stream copy
    .build()?.start()?.wait()?;
```

### Clip Video (Seek + Duration)

```bash
ffmpeg -i input.mp4 -ss 00:00:10 -t 00:00:05 -c copy output.mp4
```

```rust
// Time in microseconds: 10s = 10_000_000us, 5s = 5_000_000us
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_start_time_us(10_000_000)      // -ss 10s
        .set_recording_time_us(5_000_000))  // -t 5s
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

### Video to GIF

```bash
ffmpeg -i input.mp4 -vf "fps=10,scale=320:-1:flags=lanczos" output.gif
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("fps=10,scale=320:-1:flags=lanczos")
    .output("output.gif")
    .build()?.start()?.wait()?;
```

### Scale Video

```bash
ffmpeg -i input.mp4 -vf "scale=1280:720" output.mp4
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("scale=1280:720")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

### Change Codec

```bash
ffmpeg -i input.mp4 -c:v libx264 -c:a aac output.mp4
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .set_video_codec("libx264")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;
```

### Set Bitrate

```bash
ffmpeg -i input.mp4 -b:v 2M -b:a 128k output.mp4
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .set_video_codec_opt("b", "2M")
        .set_audio_codec_opt("b", "128k"))
    .build()?.start()?.wait()?;
```

### Extract Thumbnail

```bash
ffmpeg -i input.mp4 -vframes 1 -q:v 2 thumbnail.jpg
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("thumbnail.jpg")
        .set_max_video_frames(1)
        .set_video_qscale(2))
    .build()?.start()?.wait()?;
```

### Concatenate Videos

```bash
ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4
```

```rust
// Direct input method (for simple cases)
FfmpegContext::builder()
    .input("file1.mp4")
    .input("file2.mp4")
    .filter_desc("[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]")
    .output(Output::from("output.mp4")
        .add_stream_map("outv")
        .add_stream_map("outa"))
    .build()?.start()?.wait()?;
```

### Overlay (Watermark)

```bash
ffmpeg -i main.mp4 -i watermark.png -filter_complex "overlay=10:10" output.mp4
```

```rust
FfmpegContext::builder()
    .input("main.mp4")
    .input("watermark.png")
    .filter_desc("[0:v][1:v]overlay=10:10")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

### Picture-in-Picture

```bash
ffmpeg -i main.mp4 -i pip.mp4 -filter_complex "[1:v]scale=320:180[pip];[0:v][pip]overlay=W-w-10:H-h-10" output.mp4
```

```rust
FfmpegContext::builder()
    .input("main.mp4")
    .input("pip.mp4")
    .filter_desc("[1:v]scale=320:180[pip];[0:v][pip]overlay=W-w-10:H-h-10")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

### RTMP Streaming

```bash
ffmpeg -i input.mp4 -c:v libx264 -preset veryfast -f flv rtmp://server/live/stream
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("rtmp://server/live/stream")
        .set_format("flv")
        .set_video_codec("libx264")
        .set_video_codec_opt("preset", "veryfast"))
    .build()?.start()?.wait()?;
```

### HLS Generation

```bash
ffmpeg -i input.mp4 -f hls -hls_time 4 -hls_list_size 0 playlist.m3u8
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("playlist.m3u8")
        .set_format("hls")
        .set_format_opt("hls_time", "4")
        .set_format_opt("hls_list_size", "0"))
    .build()?.start()?.wait()?;
```

### Hardware Acceleration (macOS)

```bash
ffmpeg -hwaccel videotoolbox -i input.mp4 -c:v h264_videotoolbox output.mp4
```

```rust
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_hwaccel("videotoolbox"))
    .output(Output::from("output.mp4")
        .set_video_codec("h264_videotoolbox"))
    .build()?.start()?.wait()?;
```

### Hardware Acceleration (NVIDIA)

```bash
ffmpeg -hwaccel cuda -i input.mp4 -c:v h264_nvenc output.mp4
```

```rust
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_hwaccel("cuda"))
    .output(Output::from("output.mp4")
        .set_video_codec("h264_nvenc"))
    .build()?.start()?.wait()?;
```

### Loop Input Video

```bash
ffmpeg -stream_loop 3 -i input.mp4 -c copy output.mp4
```

```rust
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_stream_loop(3))  // Loop 3 times
    .output(Output::from("output.mp4")
        .add_stream_map_with_copy("0:v")
        .add_stream_map_with_copy("0:a"))
    .build()?.start()?.wait()?;
```

### Audio Resampling

```bash
ffmpeg -i input.mp4 -ar 48000 -ac 2 -sample_fmt s16 output.wav
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.wav")
        .set_audio_sample_rate(48000)
        .set_audio_channels(2)
        .set_audio_sample_fmt("s16"))
    .build()?.start()?.wait()?;
```

### High-Quality x264 Encoding

```bash
ffmpeg -i input.mp4 -c:v libx264 -preset slow -crf 18 -profile:v high -level 4.1 output.mp4
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .set_video_codec("libx264")
        .set_video_codec_opt("preset", "slow")
        .set_video_codec_opt("crf", "18")
        .set_video_codec_opt("profile", "high")
        .set_video_codec_opt("level", "4.1"))
    .build()?.start()?.wait()?;
```

### Add Metadata

```bash
ffmpeg -i input.mp4 -metadata title="My Video" -metadata artist="Author" -c copy output.mp4
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .add_metadata("title", "My Video")
        .add_metadata("artist", "Author")
        .add_stream_map_with_copy("0:v")
        .add_stream_map_with_copy("0:a"))
    .build()?.start()?.wait()?;
```

### MP4 Fast Start (Web Streaming)

```bash
ffmpeg -i input.mp4 -c copy -movflags +faststart output.mp4
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .set_format_opt("movflags", "+faststart")
        .add_stream_map_with_copy("0:v")
        .add_stream_map_with_copy("0:a"))
    .build()?.start()?.wait()?;
```

### Extract Multiple Thumbnails

```bash
ffmpeg -i input.mp4 -vf "fps=1/10" -q:v 2 thumb_%03d.jpg
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("fps=1/10")  // 1 frame every 10 seconds
    .output(Output::from("thumb_%03d.jpg")
        .set_video_qscale(2))
    .build()?.start()?.wait()?;
```

### Audio Quality Control (VBR)

```bash
ffmpeg -i input.mp4 -c:a libmp3lame -q:a 2 output.mp3
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp3")
        .set_audio_codec("libmp3lame")
        .set_audio_qscale(2))  // MP3: 0 (best) to 9 (worst)
    .build()?.start()?.wait()?;
```

### Hardware Acceleration with Device Selection

```bash
ffmpeg -hwaccel cuda -hwaccel_device 0 -hwaccel_output_format cuda -i input.mp4 -c:v h264_nvenc output.mp4
```

```rust
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_hwaccel("cuda")
        .set_hwaccel_device("0")
        .set_hwaccel_output_format("cuda"))
    .output(Output::from("output.mp4")
        .set_video_codec("h264_nvenc"))
    .build()?.start()?.wait()?;
```

### Intel QSV Hardware Acceleration

```bash
ffmpeg -hwaccel qsv -i input.mp4 -c:v h264_qsv -preset fast output.mp4
```

```rust
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_hwaccel("qsv"))
    .output(Output::from("output.mp4")
        .set_video_codec("h264_qsv")
        .set_video_codec_opt("preset", "fast"))
    .build()?.start()?.wait()?;
```

### Copy Metadata from Input

```bash
ffmpeg -i input.mp4 -map_metadata 0 -c copy output.mp4
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .map_metadata_from_input(0)
        .add_stream_map_with_copy("0:v")
        .add_stream_map_with_copy("0:a"))
    .build()?.start()?.wait()?;
```

### Strip All Metadata

```bash
ffmpeg -i input.mp4 -map_metadata -1 -c copy output.mp4
```

```rust
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .disable_auto_copy_metadata()
        .add_stream_map_with_copy("0:v")
        .add_stream_map_with_copy("0:a"))
    .build()?.start()?.wait()?;
```

## CLI Option Mapping

### Input Options

| CLI Option | ez-ffmpeg Method | Notes |
|------------|------------------|-------|
| `-i input` | `.input("input")` | Input file |
| `-f format` | `Input::from(...).set_format("format")` | Force input format |
| `-ss TIME` | `.set_start_time_us(us)` | Seek position (microseconds) |
| `-t TIME` | `.set_recording_time_us(us)` | Duration (microseconds) |
| `-to TIME` | `.set_stop_time_us(us)` | Stop time (microseconds) |
| `-re` | `.set_readrate(1.0)` | Real-time read rate |
| `-stream_loop n` | `.set_stream_loop(n)` | Loop input n times (-1 = infinite) |
| `-c:v codec` | `Input::from(...).set_video_codec("codec")` | Video decoder |
| `-c:a codec` | `Input::from(...).set_audio_codec("codec")` | Audio decoder |
| `-c:s codec` | `Input::from(...).set_subtitle_codec("codec")` | Subtitle decoder |
| `-hwaccel type` | `.set_hwaccel("type")` | Hardware acceleration |
| `-hwaccel_device dev` | `.set_hwaccel_device("dev")` | HW accel device |
| `-hwaccel_output_format fmt` | `.set_hwaccel_output_format("fmt")` | HW output format |
| `-xerror` | `.set_exit_on_error(true)` | Exit on error |
| `-option value` | `.set_input_opt("option", "value")` | Generic input option |

### Output Options

| CLI Option | ez-ffmpeg Method | Notes |
|------------|------------------|-------|
| `-f format` | `.set_format("format")` | Output format |
| `-c:v codec` | `.set_video_codec("codec")` | Video encoder |
| `-c:a codec` | `.set_audio_codec("codec")` | Audio encoder |
| `-c:s codec` | `.set_subtitle_codec("codec")` | Subtitle encoder |
| `-b:v bitrate` | `.set_video_codec_opt("b", "rate")` | Video bitrate |
| `-b:a bitrate` | `.set_audio_codec_opt("b", "rate")` | Audio bitrate |
| `-r fps` | `.set_framerate(AVRational{num,den})` | Output frame rate |
| `-ar rate` | `.set_audio_sample_rate(rate)` | Audio sample rate (Hz) |
| `-ac channels` | `.set_audio_channels(channels)` | Audio channel count |
| `-sample_fmt fmt` | `.set_audio_sample_fmt("fmt")` | Audio sample format |
| `-vsync method` | `.set_vsync_method("method")` | Video sync method |
| `-bits_per_raw_sample n` | `.set_bits_per_raw_sample(n)` | Bits per raw sample |

### Quality & Frame Limits

| CLI Option | ez-ffmpeg Method | Notes |
|------------|------------------|-------|
| `-q:v n` | `.set_video_qscale(n)` | Video quality (VBR) |
| `-q:a n` | `.set_audio_qscale(n)` | Audio quality (codec-specific) |
| `-frames:v n` | `.set_max_video_frames(n)` | Limit video frames |
| `-frames:a n` | `.set_max_audio_frames(n)` | Limit audio frames |
| `-frames:s n` | `.set_max_subtitle_frames(n)` | Limit subtitle frames |
| `-vframes n` | `.set_max_video_frames(n)` | Alias for -frames:v |

### Stream Mapping

| CLI Option | ez-ffmpeg Method | Notes |
|------------|------------------|-------|
| `-map stream` | `.add_stream_map("stream")` | Map stream (re-encode) |
| `-map stream -c copy` | `.add_stream_map_with_copy("stream")` | Map stream (copy) |
| `-vn` | `.add_stream_map("0:a")` | No video (audio only) |
| `-an` | `.add_stream_map("0:v")` | No audio (video only) |

### Metadata

| CLI Option | ez-ffmpeg Method | Notes |
|------------|------------------|-------|
| `-metadata k=v` | `.add_metadata("k", "v")` | Global metadata |
| `-metadata:s:v:0 k=v` | `.add_stream_metadata("v:0", "k", "v")` | Stream metadata |
| `-metadata:c:0 k=v` | `.add_chapter_metadata(0, "k", "v")` | Chapter metadata |
| `-metadata:p:0 k=v` | `.add_program_metadata(0, "k", "v")` | Program metadata |
| `-map_metadata input` | `.map_metadata_from_input(input)` | Copy metadata from input |
| `-map_metadata -1` | `.disable_auto_copy_metadata()` | Disable metadata copy |

### Filters

| CLI Option | ez-ffmpeg Method | Notes |
|------------|------------------|-------|
| `-vf filter` | `.filter_desc("filter")` | Video filter |
| `-af filter` | `.filter_desc("filter")` | Audio filter |
| `-filter_complex graph` | `.filter_desc("graph")` | Complex filter graph |

### Encoder Options

| CLI Option | ez-ffmpeg Method | Notes |
|------------|------------------|-------|
| `-preset value` | `.set_video_codec_opt("preset", "value")` | Encoder preset |
| `-crf value` | `.set_video_codec_opt("crf", "value")` | Constant rate factor |
| `-tune value` | `.set_video_codec_opt("tune", "value")` | Encoder tuning |
| `-profile:v value` | `.set_video_codec_opt("profile", "value")` | Video profile |
| `-level value` | `.set_video_codec_opt("level", "value")` | Codec level |
| `-g value` | `.set_video_codec_opt("g", "value")` | GOP size |
| `-bf value` | `.set_video_codec_opt("bf", "value")` | B-frames |
| `-rc mode` | `.set_video_codec_opt("rc", "mode")` | Rate control mode |

### Format Options

| CLI Option | ez-ffmpeg Method | Notes |
|------------|------------------|-------|
| `-movflags flags` | `.set_format_opt("movflags", "flags")` | MOV/MP4 flags |
| `-flvflags flags` | `.set_format_opt("flvflags", "flags")` | FLV flags |
| `-hls_time secs` | `.set_format_opt("hls_time", "secs")` | HLS segment duration |
| `-hls_list_size n` | `.set_format_opt("hls_list_size", "n")` | HLS playlist size |
| `-hls_segment_filename` | `.set_format_opt("hls_segment_filename", "pattern")` | HLS segment naming |

## Time Conversion

FFmpeg uses various time formats. ez-ffmpeg uses microseconds:

| FFmpeg Format | Microseconds | Example |
|---------------|--------------|---------|
| `00:00:10` | 10_000_000 | 10 seconds |
| `00:01:30` | 90_000_000 | 1 min 30 sec |
| `10.5` | 10_500_000 | 10.5 seconds |

**Helper function:**
```rust
fn time_to_us(hours: i64, minutes: i64, seconds: i64) -> i64 {
    (hours * 3600 + minutes * 60 + seconds) * 1_000_000
}

// Usage: set_start_time_us(time_to_us(0, 1, 30)) // 1:30
```

## Async Support

For async operations, enable the `async` feature and use `.await`:

```rust
// CLI: ffmpeg -i input.mp4 output.mp4
// Async Rust:
FfmpegContext::builder()
    .input("input.mp4")
    .output("output.mp4")
    .build()?.start()?.await?;
```
