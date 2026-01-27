# ffmpeg-next: Metadata Operations

**Detection Keywords**: metadata read, codec info, chapter, media info, tag, stream info, container info
**Aliases**: metadata, media metadata, file info

Reading and manipulating media metadata, codec information, and chapter data.

## Related Guides

| Guide | Content |
|-------|---------|
| [video.md](video.md) | Seeking, scaling context, timestamp management |
| [streaming.md](streaming.md) | Network streaming, RTMP/HLS |
| [output.md](output.md) | Container remuxing, PNG/JPEG saving |

## Table of Contents

- [Metadata Reading](#metadata-reading)
- [Codec Information Query](#codec-information-query)
- [Chapter Handling](#chapter-handling)

## Metadata Reading

Extract comprehensive media information:

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{format, media};

fn read_metadata(path: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let ctx = format::input(path)?;

    // Container metadata
    println!("=== Container Metadata ===");
    for (key, value) in ctx.metadata().iter() {
        println!("{}: {}", key, value);
    }

    // Duration
    let duration_secs = ctx.duration() as f64 / f64::from(ffmpeg::ffi::AV_TIME_BASE);
    println!("\nDuration: {:.2} seconds", duration_secs);

    // Best streams
    if let Some(s) = ctx.streams().best(media::Type::Video) {
        println!("Best video stream: {}", s.index());
    }
    if let Some(s) = ctx.streams().best(media::Type::Audio) {
        println!("Best audio stream: {}", s.index());
    }

    // Stream details
    println!("\n=== Streams ===");
    for stream in ctx.streams() {
        println!("\nStream {}:", stream.index());
        println!("  time_base: {}", stream.time_base());
        println!("  duration: {} (stream units)", stream.duration());
        println!("  frames: {}", stream.frames());

        let codec = ffmpeg::codec::context::Context::from_parameters(stream.parameters())?;
        println!("  medium: {:?}", codec.medium());
        println!("  codec: {:?}", codec.id());

        match codec.medium() {
            media::Type::Video => {
                if let Ok(video) = codec.decoder().video() {
                    println!("  dimensions: {}x{}", video.width(), video.height());
                    println!("  format: {:?}", video.format());
                    println!("  bit_rate: {}", video.bit_rate());
                    println!("  aspect_ratio: {}", video.aspect_ratio());
                    println!("  color_space: {:?}", video.color_space());
                }
            }
            media::Type::Audio => {
                if let Ok(audio) = codec.decoder().audio() {
                    println!("  sample_rate: {}", audio.rate());
                    println!("  channels: {}", audio.channels());
                    println!("  format: {:?}", audio.format());
                    println!("  bit_rate: {}", audio.bit_rate());
                    println!("  channel_layout: {:?}", audio.channel_layout());
                }
            }
            _ => {}
        }
    }

    Ok(())
}
```

## Common Metadata Keys

| Key | Description | Example |
|-----|-------------|---------|
| `title` | Media title | "My Video" |
| `artist` | Creator/artist | "John Doe" |
| `album` | Album name | "Collection" |
| `date` | Creation date | "2024-01-15" |
| `comment` | Comments | "Encoded with..." |
| `genre` | Genre | "Documentary" |
| `track` | Track number | "1/10" |
| `encoder` | Encoding software | "Lavf60.3.100" |
| `duration` | Duration string | "00:05:30.000000" |

## Metadata Writing

```rust
fn copy_with_metadata(input: &str, output: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let ictx = format::input(input)?;
    let mut octx = format::output(output)?;

    // Copy streams...
    // (stream setup code here)

    // Copy existing metadata
    octx.set_metadata(ictx.metadata().to_owned());

    // Or set custom metadata
    // octx.set_metadata(ffmpeg::Dictionary::from([
    //     ("title", "New Title"),
    //     ("artist", "New Artist"),
    // ]));

    octx.write_header()?;
    // ... process packets ...
    octx.write_trailer()?;

    Ok(())
}
```

## Codec Information Query

Query encoder/decoder capabilities:

```rust
extern crate ffmpeg_next as ffmpeg;

fn query_codec(name: &str) {
    ffmpeg::init().unwrap();

    // Check decoder
    if let Some(codec) = ffmpeg::decoder::find_by_name(name) {
        println!("=== Decoder: {} ===", name);
        println!("  ID: {:?}", codec.id());
        println!("  Description: {}", codec.description());
        println!("  Medium: {:?}", codec.medium());
        println!("  Capabilities: {:?}", codec.capabilities());

        if let Some(profiles) = codec.profiles() {
            println!("  Profiles: {:?}", profiles.collect::<Vec<_>>());
        }

        if let Ok(video) = codec.video() {
            if let Some(formats) = video.formats() {
                println!("  Pixel formats: {:?}", formats.collect::<Vec<_>>());
            }
        }

        if let Ok(audio) = codec.audio() {
            if let Some(rates) = audio.rates() {
                println!("  Sample rates: {:?}", rates.collect::<Vec<_>>());
            }
            if let Some(formats) = audio.formats() {
                println!("  Sample formats: {:?}", formats.collect::<Vec<_>>());
            }
        }
    }

    // Check encoder
    if let Some(codec) = ffmpeg::encoder::find_by_name(name) {
        println!("\n=== Encoder: {} ===", name);
        println!("  ID: {:?}", codec.id());
        println!("  Description: {}", codec.description());
        println!("  Capabilities: {:?}", codec.capabilities());

        if let Ok(video) = codec.video() {
            if let Some(formats) = video.formats() {
                println!("  Pixel formats: {:?}", formats.collect::<Vec<_>>());
            }
        }
    }
}
```

## List All Codecs

```rust
fn list_codecs() {
    ffmpeg::init().unwrap();

    println!("=== Video Decoders ===");
    for codec in ffmpeg::codec::decoder::video() {
        println!("  {} - {}", codec.name(), codec.description());
    }

    println!("\n=== Video Encoders ===");
    for codec in ffmpeg::codec::encoder::video() {
        println!("  {} - {}", codec.name(), codec.description());
    }

    println!("\n=== Audio Decoders ===");
    for codec in ffmpeg::codec::decoder::audio() {
        println!("  {} - {}", codec.name(), codec.description());
    }

    println!("\n=== Audio Encoders ===");
    for codec in ffmpeg::codec::encoder::audio() {
        println!("  {} - {}", codec.name(), codec.description());
    }
}
```

## Codec Lookup by ID

```rust
fn find_codec_by_id() {
    ffmpeg::init().unwrap();

    // Find by codec ID
    if let Some(decoder) = ffmpeg::decoder::find(ffmpeg::codec::Id::H264) {
        println!("H264 decoder: {}", decoder.name());
    }

    if let Some(encoder) = ffmpeg::encoder::find(ffmpeg::codec::Id::AAC) {
        println!("AAC encoder: {}", encoder.name());
    }
}
```

## Chapter Handling

Read and copy chapter metadata to a new file:

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, encoder, format, media};

fn copy_chapters_with_streams(input: &str, output: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input)?;
    let mut octx = format::output(output)?;

    println!("Input has {} chapters", ictx.nb_chapters());

    // First, copy streams (required for valid output file)
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

    // Copy chapters from input
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

        println!("Copied chapter {}: {}", chapter.id(), title);
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

    println!("\nOutput has {} chapters", octx.nb_chapters());
    Ok(())
}
```

## Chapter Time Conversion

```rust
fn chapter_to_seconds(chapter: &ffmpeg::format::chapter::Chapter) -> (f64, f64) {
    let time_base = chapter.time_base();
    let scale = time_base.numerator() as f64 / time_base.denominator() as f64;

    let start_secs = chapter.start() as f64 * scale;
    let end_secs = chapter.end() as f64 * scale;

    (start_secs, end_secs)
}

fn list_chapters_with_times(path: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;
    let ctx = format::input(path)?;

    for chapter in ctx.chapters() {
        let (start, end) = chapter_to_seconds(&chapter);
        let title = chapter.metadata().get("title").unwrap_or("Untitled");

        println!("[{:.2}s - {:.2}s] {}", start, end, title);
    }

    Ok(())
}
```

## Creating Chapters

```rust
fn add_custom_chapters(octx: &mut format::context::Output) -> Result<(), ffmpeg::Error> {
    use ffmpeg::Rational;

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

## Stream Information Summary

```rust
fn print_stream_summary(path: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;
    let ctx = format::input(path)?;

    println!("File: {}", path);
    println!("Format: {}", ctx.format().name());
    println!("Duration: {:.2}s", ctx.duration() as f64 / f64::from(ffmpeg::ffi::AV_TIME_BASE));
    println!("Bit rate: {} kbps", ctx.bit_rate() / 1000);
    println!("Streams: {}", ctx.nb_streams());
    println!("Chapters: {}", ctx.nb_chapters());

    for stream in ctx.streams() {
        let params = stream.parameters();
        let medium = params.medium();

        print!("  Stream #{}: {:?}", stream.index(), medium);

        if medium == media::Type::Video {
            println!(" {}x{}", params.width(), params.height());
        } else if medium == media::Type::Audio {
            println!(" {}Hz {} channels", params.rate(), params.channels());
        } else {
            println!();
        }
    }

    Ok(())
}
```

## Subtitle Stream Handling

Subtitle streams can be extracted, remuxed, or converted between formats.

### Extract Subtitle Streams

```rust
use ffmpeg::{codec, format, media};

fn extract_subtitles(input: &str, output: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input)?;
    let mut octx = format::output(output)?;

    // Find subtitle streams
    let subtitle_streams: Vec<_> = ictx.streams()
        .filter(|s| s.parameters().medium() == media::Type::Subtitle)
        .collect();

    if subtitle_streams.is_empty() {
        return Err(ffmpeg::Error::StreamNotFound);
    }

    println!("Found {} subtitle streams", subtitle_streams.len());

    // Copy subtitle streams to output
    let mut stream_mapping: Vec<i32> = vec![-1; ictx.nb_streams() as usize];
    let mut ost_index = 0i32;

    for ist in subtitle_streams {
        let ist_index = ist.index();
        stream_mapping[ist_index] = ost_index;
        ost_index += 1;

        let mut ost = octx.add_stream(codec::encoder::find(codec::Id::None))?;
        ost.set_parameters(ist.parameters());
        unsafe { (*ost.parameters().as_mut_ptr()).codec_tag = 0; }

        // Print subtitle stream info
        if let Some(lang) = ist.metadata().get("language") {
            println!("  Stream #{}: {} ({})", ist_index, ist.parameters().id(), lang);
        }
    }

    octx.write_header()?;

    // Copy subtitle packets
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

### List Subtitle Streams with Language

```rust
fn list_subtitle_streams(input: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;
    let ictx = format::input(input)?;

    println!("Subtitle streams in {}:", input);

    for stream in ictx.streams() {
        if stream.parameters().medium() != media::Type::Subtitle {
            continue;
        }

        let codec_id = stream.parameters().id();
        let language = stream.metadata()
            .get("language")
            .unwrap_or("unknown");
        let title = stream.metadata()
            .get("title")
            .unwrap_or("");

        println!("  Stream #{}: {:?}", stream.index(), codec_id);
        println!("    Language: {}", language);
        if !title.is_empty() {
            println!("    Title: {}", title);
        }
        println!("    Time base: {}", stream.time_base());
    }

    Ok(())
}
```

### Copy Specific Subtitle Stream by Language

```rust
fn copy_subtitle_by_language(
    input: &str,
    output: &str,
    target_lang: &str,
) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input)?;
    let mut octx = format::output(output)?;

    // Find subtitle stream with target language
    let subtitle_stream = ictx.streams()
        .find(|s| {
            s.parameters().medium() == media::Type::Subtitle
                && s.metadata().get("language").map_or(false, |lang| lang == target_lang)
        })
        .ok_or(ffmpeg::Error::StreamNotFound)?;

    let ist_index = subtitle_stream.index();
    println!("Found {} subtitle at stream #{}", target_lang, ist_index);

    // Add output stream
    let mut ost = octx.add_stream(codec::encoder::find(codec::Id::None))?;
    ost.set_parameters(subtitle_stream.parameters());
    unsafe { (*ost.parameters().as_mut_ptr()).codec_tag = 0; }

    // Copy language metadata
    if let Some(lang) = subtitle_stream.metadata().get("language") {
        ost.set_metadata(subtitle_stream.metadata().to_owned());
    }

    octx.write_header()?;

    // Copy packets from target subtitle stream only
    for (stream, mut packet) in ictx.packets() {
        if stream.index() != ist_index {
            continue;
        }

        let ost = octx.stream(0).unwrap();
        packet.rescale_ts(stream.time_base(), ost.time_base());
        packet.set_position(-1);
        packet.set_stream(0);
        packet.write_interleaved(&mut octx)?;
    }

    octx.write_trailer()?;
    Ok(())
}
```

### Subtitle Format Notes

**Common Subtitle Codecs**:
- **SubRip (SRT)**: Text-based, widely supported (`codec::Id::SUBRIP`)
- **ASS/SSA**: Advanced SubStation Alpha, supports styling (`codec::Id::ASS`)
- **WebVTT**: Web Video Text Tracks (`codec::Id::WEBVTT`)
- **DVD Subtitles (VOB)**: Bitmap-based (`codec::Id::DVD_SUBTITLE`)
- **PGS**: Blu-ray subtitles, bitmap-based (`codec::Id::HDMV_PGS_SUBTITLE`)

**Container Support**:
- **MP4/MOV**: Supports text subtitles (tx3g, WebVTT)
- **MKV**: Supports all subtitle formats
- **WebM**: Supports WebVTT
- **AVI**: Limited subtitle support

**Subtitle Extraction Tips**:
- Use `.srt` extension for SubRip text subtitles
- Use `.ass` extension for Advanced SubStation Alpha
- Bitmap subtitles (DVD, PGS) require OCR for text conversion
- Check `stream.metadata().get("language")` for language codes (ISO 639-2)

