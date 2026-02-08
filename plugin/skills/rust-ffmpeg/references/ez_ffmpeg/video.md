# ez-ffmpeg: Video Processing

**Detection Keywords**: video transcode, format conversion, resize video, change container, clip video, trim, cut
**Aliases**: video processing, convert video, video encoding

## Table of Contents

- [Related Guides](#related-guides)
- [Transcoding (Format Conversion)](#transcoding-format-conversion)
- [Video Clipping](#video-clipping)
- [Video Merging](#video-merging)
- [Resolution & FPS](#resolution--fps)
- [Thumbnail Extraction](#thumbnail-extraction)
- [Watermark & Overlay](#watermark--overlay)
- [Multi-Input Processing](#multi-input-processing)
- [Image to Video](#image-to-video)
- [Test Pattern Generation](#test-pattern-generation)
- [Metadata Operations](#metadata-operations)
- [Loop Input Video](#loop-input-video)

## Related Guides

| Guide | Content |
|-------|---------|
| [audio.md](audio.md) | Audio extraction and processing |
| [filters.md](filters.md) | FFmpeg filters (scale, crop, etc.) |
| [advanced.md](advanced.md) | Hardware acceleration, async processing |

## Transcoding (Format Conversion)

```rust
use ez_ffmpeg::{FfmpegContext, Output};

// Simple container change
FfmpegContext::builder()
    .input("input.mp4")
    .output("output.mov")
    .build()?.start()?.wait()?;

// With codec specification
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.webm")
        .set_video_codec("libvpx-vp9")
        .set_audio_codec("libopus"))
    .build()?.start()?.wait()?;

// High-quality H.264 encoding
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .set_video_codec("libx264")
        .set_video_codec_opt("preset", "medium")
        .set_video_codec_opt("crf", "18")
        .set_audio_codec("aac")
        .set_audio_codec_opt("b", "192k"))
    .build()?.start()?.wait()?;
```

## Video Clipping

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Cut from 00:01:00, duration 60 seconds
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_start_time_us(60_000_000))  // 60 seconds in microseconds
    .output(Output::from("clip.mp4")
        .set_recording_time_us(60_000_000))  // 60 seconds
    .build()?.start()?.wait()?;

// Precise clipping with microseconds
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_start_time_us(60_000_000))  // 60 seconds in microseconds
    .output(Output::from("clip.mp4")
        .set_recording_time_us(30_000_000))  // 30 seconds
    .build()?.start()?.wait()?;

// Input clipping methods
Input::from("input.mp4")
    .set_start_time_us(1_000_000)      // Start at 1 second
    .set_recording_time_us(5_000_000)  // Record for 5 seconds
    .set_stop_time_us(6_000_000);      // Stop at 6 seconds

// Output clipping methods
Output::from("output.mp4")
    .set_start_time_us(2_000_000)      // Start writing at 2 seconds
    .set_recording_time_us(5_000_000)  // Record for 5 seconds
    .set_stop_time_us(7_000_000);      // Stop at 7 seconds

// Stream copy (fast, no re-encoding)
FfmpegContext::builder()
    .input(Input::from("input.mp4")
        .set_start_time_us(60_000_000))  // 60 seconds in microseconds
    .output(Output::from("clip.mp4")
        .set_recording_time_us(60_000_000)  // 60 seconds
        .add_stream_map_with_copy("0:v")
        .add_stream_map_with_copy("0:a"))
    .build()?.start()?.wait()?;
```

## Video Merging

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};
use std::fs::File;
use std::io::Write;

// Method 1: Concat demuxer (same codec, fast)
let mut file = File::create("list.txt")?;
writeln!(file, "file 'video1.mp4'")?;
writeln!(file, "file 'video2.mp4'")?;

FfmpegContext::builder()
    .input(Input::from("list.txt")
        .set_format("concat")
        .set_input_opt("safe", "0"))
    .output(Output::from("merged.mp4")
        .set_video_codec("copy")
        .set_audio_codec("copy"))
    .build()?.start()?.wait()?;

// Method 2: Filter concat (different codecs, re-encode)
FfmpegContext::builder()
    .input("video1.mp4")
    .input("video2.mp4")
    .filter_desc("[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]")
    .output(Output::from("merged.mp4")
        .add_stream_map("outv")
        .add_stream_map("outa"))
    .build()?.start()?.wait()?;
```

## Resolution & FPS

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};
use ez_ffmpeg::AVRational;

// Scale to 1280x720
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("scale=1280:720")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Preserve aspect ratio
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("scale=1280:-1")  // -1 = auto calculate
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Change FPS via filter
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("fps=30")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Change FPS via Output method
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .set_framerate(AVRational { num: 30, den: 1 }))
    .build()?.start()?.wait()?;

// Set input framerate (for DTS estimation or raw streams)
// Useful for streams without proper timestamps or when forcing a specific input rate
FfmpegContext::builder()
    .input(Input::from("raw_video.yuv")
        .set_framerate(30, 1))  // Force 30fps input
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Set input framerate for 23.976fps (NTSC film)
FfmpegContext::builder()
    .input(Input::from("video.mp4")
        .set_framerate(24000, 1001))  // 23.976fps
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Combined: scale + fps
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("scale=1920:1080,fps=60")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

## Thumbnail Extraction

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// First frame as JPEG
FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("thumb.jpg")
        .set_max_video_frames(1)
        .set_video_qscale(2))  // Quality: 2-31, lower is better
    .build()?.start()?.wait()?;

// Frame at specific time
FfmpegContext::builder()
    .input(Input::from("video.mp4")
        .set_start_time_us(10_000_000))  // 10 seconds in microseconds
    .output(Output::from("thumb_10s.jpg")
        .set_max_video_frames(1))
    .build()?.start()?.wait()?;

// Scaled thumbnail
FfmpegContext::builder()
    .input("video.mp4")
    .filter_desc("scale=320:-1")
    .output(Output::from("thumb_small.jpg")
        .set_max_video_frames(1))
    .build()?.start()?.wait()?;
```

## Watermark & Overlay

```rust
use ez_ffmpeg::FfmpegContext;

// Image watermark at top-left
FfmpegContext::builder()
    .input("video.mp4")
    .input("watermark.png")
    .filter_desc("overlay=10:10")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Bottom-right corner
FfmpegContext::builder()
    .input("video.mp4")
    .input("watermark.png")
    .filter_desc("overlay=main_w-overlay_w-10:main_h-overlay_h-10")
    .output("output.mp4")
    .build()?.start()?.wait()?;

// Picture-in-picture
FfmpegContext::builder()
    .input("main.mp4")
    .input("pip.mp4")
    .filter_desc("[1:v]scale=320:180[pip];[0:v][pip]overlay=W-w-10:H-h-10")
    .output("output.mp4")
    .build()?.start()?.wait()?;
```

## Multi-Input Processing

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Side-by-side video (hstack)
FfmpegContext::builder()
    .input(Input::from("left.mp4").set_readrate(1.0))
    .input(Input::from("right.mp4").set_readrate(1.0))
    .independent_readrate()  // Sync multiple inputs
    .filter_desc("[0:v][1:v]hstack[outv]")
    .output(Output::from("side_by_side.mp4")
        .add_stream_map("outv")
        .set_video_codec("libx264"))
    .build()?.start()?.wait()?;

// Dynamic multi-input with hardware acceleration
// Note: Input::set_video_codec() specifies the DECODER (e.g., "h264" for hw decoding)
//       Output::set_video_codec() specifies the ENCODER (e.g., "libx264" for encoding)
let video_paths: Vec<(&str, &str, &str)> = vec![
    ("video1.mp4", "videotoolbox", "h264"),  // hwaccel + decoder
    ("video2.mp4", "", ""),  // No hwaccel
];

let inputs: Vec<Input> = video_paths.iter()
    .map(|(path, hwaccel, codec)| {
        let mut input = Input::from(*path).set_readrate(1.0);
        if !hwaccel.is_empty() {
            input = input.set_hwaccel(hwaccel);
        }
        if !codec.is_empty() {
            input = input.set_video_codec(codec);
        }
        input
    })
    .collect();

FfmpegContext::builder()
    .independent_readrate()
    .inputs(inputs)
    .filter_desc("[0:v][1:v]hstack[outv]")
    .output(Output::from("output.mp4")
        .add_stream_map("outv")
        .set_video_codec("libx264"))
    .build()?.start()?.wait()?;
```

## Image to Video

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Still image to 10-second video
FfmpegContext::builder()
    .input(Input::from("image.jpg")
        .set_input_opt("loop", "1")
        .set_input_opt("framerate", "1"))
    .filter_desc("format=yuv420p")  // Set pixel format via filter
    .output(Output::from("video.mp4")
        .set_recording_time_us(10_000_000)  // 10 seconds
        .set_video_codec("libx264"))
    .build()?.start()?.wait()?;
```

## Test Pattern Generation

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Black video with silent audio
FfmpegContext::builder()
    .input(Input::from("color=c=black:s=1920x1080:r=30")
        .set_format("lavfi"))
    .input(Input::from("anullsrc=r=44100:cl=stereo")
        .set_format("lavfi"))
    .output(Output::from("black.mp4")
        .set_recording_time_us(10_000_000)  // 10 seconds
        .set_video_codec("libx264")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;
```

## Metadata Operations

```rust
use ez_ffmpeg::{FfmpegContext, Output};
use ez_ffmpeg::container_info::get_metadata;
use std::collections::HashMap;

// Add metadata to output
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .set_video_codec("libx264")
        .add_metadata("title", "My Video")
        .add_metadata("artist", "Author Name")
        .add_metadata("album", "My Album")
        .add_metadata("date", "2024")
        .add_metadata("comment", "Processed with ez-ffmpeg")
        .add_metadata("location", "+48.8584+002.2945/"))
    .build()?.start()?.wait()?;

// Batch metadata with HashMap
let mut global_metadata = HashMap::new();
global_metadata.insert("title".to_string(), "Complete Example".to_string());
global_metadata.insert("artist".to_string(), "ez-ffmpeg".to_string());
global_metadata.insert("album".to_string(), "Demo Album".to_string());
global_metadata.insert("year".to_string(), "2024".to_string());

FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .add_metadata_map(global_metadata)
        .set_video_codec("libx264"))
    .build()?.start()?.wait()?;

// Copy metadata from input (simple)
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .map_metadata_from_input(0)  // Copy all metadata from input 0
        .set_video_codec("libx264"))
    .build()?.start()?.wait()?;

// Copy metadata with specifiers (advanced)
// Specifiers: "g" = global, "s:v:0" = video stream 0, "s:a:0" = audio stream 0
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .map_metadata_from_input(0, "g", "g").unwrap()      // global to global
        .map_metadata_from_input(0, "s:v:0", "s:v:0").unwrap()  // video stream
        .map_metadata_from_input(0, "s:a:0", "s:a:0").unwrap()  // audio stream
        .set_video_codec("libx264"))
    .build()?.start()?.wait()?;

// Strip all metadata
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .disable_auto_copy_metadata()  // Remove all metadata
        .add_stream_map_with_copy("0:v")
        .add_stream_map_with_copy("0:a"))
    .build()?.start()?.wait()?;

// Add stream-specific metadata (returns Result)
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .add_stream_metadata("v:0", "title", "Main Video").unwrap()
        .add_stream_metadata("a:0", "language", "eng").unwrap()
        .set_video_codec("libx264"))
    .build()?.start()?.wait()?;

// Read metadata from file
let metadata = get_metadata("video.mp4")?;
for (key, value) in metadata {
    println!("{}: {}", key, value);
}
```

## Loop Input Video

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Loop video 3 times
FfmpegContext::builder()
    .input(Input::from("short_clip.mp4")
        .set_stream_loop(3))  // Loop 3 times (total 4 plays)
    .output(Output::from("looped.mp4")
        .add_stream_map_with_copy("0:v")
        .add_stream_map_with_copy("0:a"))
    .build()?.start()?.wait()?;

// Infinite loop (for streaming)
FfmpegContext::builder()
    .input(Input::from("intro.mp4")
        .set_stream_loop(-1)  // -1 = infinite loop
        .set_readrate(1.0))   // Real-time playback
    .output(Output::from("rtmp://server/live/stream")
        .set_format("flv")
        .set_video_codec("libx264")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;
```
