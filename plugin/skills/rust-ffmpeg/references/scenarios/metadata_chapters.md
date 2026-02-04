# Metadata and Chapters

**Detection Keywords**: metadata, chapter, tag, media info, title, artist, album, read metadata, write metadata, chapter marker, chapter navigation
**Aliases**: media metadata, file info, chapter handling, ID3 tags

Cross-library guide for reading, writing, and manipulating media metadata and chapters.

## Quick Reference

| Operation | ez-ffmpeg | ffmpeg-next | ffmpeg-sidecar |
|-----------|-----------|-------------|----------------|
| Read metadata | `get_metadata()` | `ctx.metadata()` | `ffprobe` JSON |
| Write metadata | `.add_metadata()` | `octx.set_metadata()` | `-metadata` args |
| Read chapters | Not yet supported | `ctx.chapters()` | `ffprobe` JSON |
| Write chapters | Not yet supported | `octx.add_chapter()` | `-map_chapters` |

## Reading Metadata

### ez-ffmpeg

```rust
use ez_ffmpeg::container_info::get_metadata;

fn read_metadata(path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let metadata = get_metadata(path)?;

    for (key, value) in metadata {
        println!("{}: {}", key, value);
    }

    Ok(())
}
```

### ffmpeg-next

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{format, media};

fn read_metadata(path: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;
    let ctx = format::input(path)?;

    // Container-level metadata
    println!("=== Container Metadata ===");
    for (key, value) in ctx.metadata().iter() {
        println!("{}: {}", key, value);
    }

    // Duration
    let duration_secs = ctx.duration() as f64 / f64::from(ffmpeg::ffi::AV_TIME_BASE);
    println!("Duration: {:.2}s", duration_secs);

    // Stream-level metadata
    for stream in ctx.streams() {
        println!("\nStream #{}:", stream.index());
        for (key, value) in stream.metadata().iter() {
            println!("  {}: {}", key, value);
        }
    }

    Ok(())
}
```

### ffmpeg-sidecar

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use std::process::Command;

fn read_metadata_ffprobe(path: &str) -> Result<String, std::io::Error> {
    let output = Command::new("ffprobe")
        .args([
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            path,
        ])
        .output()?;

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

// Parse with serde_json for structured access
// use serde_json::Value;
// let info: Value = serde_json::from_str(&json)?;
// let title = info["format"]["tags"]["title"].as_str();
```

## Writing Metadata

### ez-ffmpeg

```rust
use ez_ffmpeg::{FfmpegContext, Output};
use std::collections::HashMap;

// Single metadata entry
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .add_metadata("title", "My Video")
        .add_metadata("artist", "Author Name")
        .add_metadata("album", "My Album")
        .add_metadata("date", "2024")
        .add_metadata("comment", "Processed with ez-ffmpeg"))
    .build()?.start()?.wait()?;

// Batch metadata with HashMap
let mut metadata = HashMap::new();
metadata.insert("title".to_string(), "Complete Example".to_string());
metadata.insert("artist".to_string(), "ez-ffmpeg".to_string());
metadata.insert("year".to_string(), "2024".to_string());

FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .add_metadata_map(metadata)
        .set_video_codec("libx264"))
    .build()?.start()?.wait()?;
```

### ffmpeg-next

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{format, Dictionary};

fn write_metadata(input: &str, output: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let ictx = format::input(input)?;
    let mut octx = format::output(output)?;

    // Copy streams (simplified - see remuxing guide for full example)
    for ist in ictx.streams() {
        let mut ost = octx.add_stream(ffmpeg::encoder::find(ffmpeg::codec::Id::None))?;
        ost.set_parameters(ist.parameters());
        unsafe { (*ost.parameters().as_mut_ptr()).codec_tag = 0; }
    }

    // Set custom metadata
    let metadata = Dictionary::from_iter([
        ("title", "My Video"),
        ("artist", "Author Name"),
        ("album", "My Album"),
        ("date", "2024"),
    ]);
    octx.set_metadata(metadata);

    octx.write_header()?;
    // ... copy packets ...
    octx.write_trailer()?;

    Ok(())
}
```

### ffmpeg-sidecar

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

FfmpegCommand::new()
    .input("input.mp4")
    .args(["-metadata", "title=My Video"])
    .args(["-metadata", "artist=Author Name"])
    .args(["-metadata", "album=My Album"])
    .args(["-metadata", "date=2024"])
    .args(["-c", "copy"])  // Stream copy (no re-encode)
    .output("output.mp4")
    .spawn()?.wait()?;
```

## Copying Metadata from Input

### ez-ffmpeg

```rust
use ez_ffmpeg::{FfmpegContext, Output};

// Copy all global metadata from input
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .map_metadata_from_input(0, "g", "g").unwrap())  // Copy global metadata from input 0
    .build()?.start()?.wait()?;

// Copy with specifiers (advanced)
FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .map_metadata_from_input(0, "g", "g").unwrap()      // global to global
        .map_metadata_from_input(0, "s:v:0", "s:v:0").unwrap()  // video stream
        .map_metadata_from_input(0, "s:a:0", "s:a:0").unwrap()) // audio stream
    .build()?.start()?.wait()?;
```

### ffmpeg-next

```rust
// Copy existing metadata
octx.set_metadata(ictx.metadata().to_owned());
```

### ffmpeg-sidecar

```rust
FfmpegCommand::new()
    .input("input.mp4")
    .args(["-map_metadata", "0"])  // Copy all metadata from input 0
    .args(["-c", "copy"])
    .output("output.mp4")
    .spawn()?.wait()?;
```

## Stripping Metadata

### ez-ffmpeg

```rust
use ez_ffmpeg::{FfmpegContext, Output};

FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .disable_auto_copy_metadata()  // Remove all metadata
        .add_stream_map_with_copy("0:v")
        .add_stream_map_with_copy("0:a"))
    .build()?.start()?.wait()?;
```

### ffmpeg-sidecar

```rust
FfmpegCommand::new()
    .input("input.mp4")
    .args(["-map_metadata", "-1"])  // Strip all metadata
    .args(["-c", "copy"])
    .output("output.mp4")
    .spawn()?.wait()?;
```

## Stream-Specific Metadata

### ez-ffmpeg

```rust
use ez_ffmpeg::{FfmpegContext, Output};

FfmpegContext::builder()
    .input("input.mp4")
    .output(Output::from("output.mp4")
        .add_stream_metadata("v:0", "title", "Main Video").unwrap()
        .add_stream_metadata("a:0", "language", "eng").unwrap()
        .add_stream_metadata("a:1", "language", "jpn").unwrap())
    .build()?.start()?.wait()?;
```

### ffmpeg-sidecar

```rust
FfmpegCommand::new()
    .input("input.mp4")
    .args(["-metadata:s:v:0", "title=Main Video"])
    .args(["-metadata:s:a:0", "language=eng"])
    .args(["-metadata:s:a:1", "language=jpn"])
    .output("output.mp4")
    .spawn()?.wait()?;
```

## Reading Chapters

### ffmpeg-next

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::format;

fn read_chapters(path: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;
    let ctx = format::input(path)?;

    println!("Found {} chapters", ctx.nb_chapters());

    for chapter in ctx.chapters() {
        let time_base = chapter.time_base();
        let scale = time_base.numerator() as f64 / time_base.denominator() as f64;

        let start_secs = chapter.start() as f64 * scale;
        let end_secs = chapter.end() as f64 * scale;

        let title = chapter.metadata()
            .get("title")
            .unwrap_or("Untitled");

        println!("[{:.2}s - {:.2}s] {}", start_secs, end_secs, title);
    }

    Ok(())
}
```

### ffmpeg-sidecar

```rust
use std::process::Command;

fn read_chapters_ffprobe(path: &str) -> Result<String, std::io::Error> {
    let output = Command::new("ffprobe")
        .args([
            "-v", "quiet",
            "-print_format", "json",
            "-show_chapters",
            path,
        ])
        .output()?;

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

// JSON structure:
// {
//   "chapters": [
//     {
//       "id": 0,
//       "time_base": "1/1000",
//       "start": 0,
//       "start_time": "0.000000",
//       "end": 300000,
//       "end_time": "300.000000",
//       "tags": { "title": "Introduction" }
//     }
//   ]
// }
```

## Writing Chapters

### ffmpeg-next

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{format, Rational};

fn add_chapters(octx: &mut format::context::Output) -> Result<(), ffmpeg::Error> {
    // Chapter 1: 0:00 - 5:00
    octx.add_chapter(
        0,                      // ID
        Rational(1, 1000),      // time_base (milliseconds)
        0,                      // start (0ms)
        300000,                 // end (300000ms = 5 minutes)
        "Introduction",
    )?;

    // Chapter 2: 5:00 - 15:00
    octx.add_chapter(
        1,
        Rational(1, 1000),
        300000,                 // start (5 minutes)
        900000,                 // end (15 minutes)
        "Main Content",
    )?;

    // Chapter 3: 15:00 - 20:00
    octx.add_chapter(
        2,
        Rational(1, 1000),
        900000,                 // start (15 minutes)
        1200000,                // end (20 minutes)
        "Conclusion",
    )?;

    Ok(())
}
```

### ffmpeg-sidecar (via metadata file)

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use std::fs::File;
use std::io::Write;

// Create FFMETADATA file
fn create_chapters_file(path: &str) -> std::io::Result<()> {
    let mut file = File::create(path)?;
    writeln!(file, ";FFMETADATA1")?;
    writeln!(file, "title=My Video")?;
    writeln!(file, "")?;
    writeln!(file, "[CHAPTER]")?;
    writeln!(file, "TIMEBASE=1/1000")?;
    writeln!(file, "START=0")?;
    writeln!(file, "END=300000")?;
    writeln!(file, "title=Introduction")?;
    writeln!(file, "")?;
    writeln!(file, "[CHAPTER]")?;
    writeln!(file, "TIMEBASE=1/1000")?;
    writeln!(file, "START=300000")?;
    writeln!(file, "END=900000")?;
    writeln!(file, "title=Main Content")?;
    Ok(())
}

// Apply chapters
FfmpegCommand::new()
    .args(["-i", "input.mp4"])
    .args(["-i", "chapters.txt"])
    .args(["-map_metadata", "1"])
    .args(["-map_chapters", "1"])
    .args(["-c", "copy"])
    .output("output.mp4")
    .spawn()?.wait()?;
```

## Copying Chapters Between Files

### ffmpeg-next

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, encoder, format, media};

fn copy_chapters(input: &str, output: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input)?;
    let mut octx = format::output(output)?;

    // Copy streams
    let mut stream_mapping: Vec<i32> = vec![-1; ictx.nb_streams() as usize];
    let mut ost_index = 0i32;

    for (ist_index, ist) in ictx.streams().enumerate() {
        let medium = ist.parameters().medium();
        if medium != media::Type::Audio
            && medium != media::Type::Video
            && medium != media::Type::Subtitle {
            continue;
        }
        stream_mapping[ist_index] = ost_index;
        ost_index += 1;

        let mut ost = octx.add_stream(encoder::find(codec::Id::None))?;
        ost.set_parameters(ist.parameters());
        unsafe { (*ost.parameters().as_mut_ptr()).codec_tag = 0; }
    }

    // Copy chapters
    for chapter in ictx.chapters() {
        let title = chapter.metadata()
            .get("title")
            .map(String::from)
            .unwrap_or_default();

        octx.add_chapter(
            chapter.id(),
            chapter.time_base(),
            chapter.start(),
            chapter.end(),
            &title,
        )?;
    }

    octx.write_header()?;

    // Copy packets
    for (stream, mut packet) in ictx.packets() {
        let ist_index = stream.index();
        let ost_index = stream_mapping[ist_index];
        if ost_index < 0 {
            continue;
        }

        let ost = octx.stream(ost_index as usize).unwrap();
        packet.rescale_ts(stream.time_base(), ost.time_base());
        packet.set_position(-1);
        packet.set_stream(ost_index as usize);
        packet.write_interleaved(&mut octx)?;
    }

    octx.write_trailer()?;
    Ok(())
}
```

### ffmpeg-sidecar

```rust
FfmpegCommand::new()
    .input("input.mp4")
    .args(["-map_chapters", "0"])  // Copy chapters from input 0
    .args(["-c", "copy"])
    .output("output.mp4")
    .spawn()?.wait()?;
```

## Common Metadata Keys

| Key | Description | Example |
|-----|-------------|---------|
| `title` | Media title | "My Video" |
| `artist` | Creator/artist | "John Doe" |
| `album` | Album name | "Collection" |
| `album_artist` | Album artist | "Various Artists" |
| `date` | Creation date | "2024-01-15" |
| `year` | Year | "2024" |
| `track` | Track number | "1/10" |
| `genre` | Genre | "Documentary" |
| `comment` | Comments | "Encoded with..." |
| `description` | Description | "A video about..." |
| `copyright` | Copyright info | "© 2024 Company" |
| `encoder` | Encoding software | "Lavf60.3.100" |
| `language` | Language code | "eng", "jpn" |
| `handler_name` | Handler name | "VideoHandler" |

## Library Selection Guide

| Use Case | Recommended | Reason |
|----------|-------------|--------|
| Simple metadata read/write | ez-ffmpeg | Clean API, minimal code |
| Chapter manipulation | ffmpeg-next | Full chapter API support |
| Batch metadata operations | ez-ffmpeg | HashMap support |
| Complex metadata workflows | ffmpeg-next | Fine-grained control |
| CLI-like operations | ffmpeg-sidecar | Direct FFmpeg access |
| JSON metadata output | ffmpeg-sidecar | ffprobe integration |

## Related Guides

| Guide | Content |
|-------|---------|
| [video_transcoding.md](video_transcoding.md) | Video format conversion |
| [subtitles.md](subtitles.md) | Subtitle handling |
| [batch_processing.md](batch_processing.md) | Processing multiple files |
