# Subtitle Processing

**Detection Keywords**: subtitles, srt, ass, vtt, burn subtitles, embed subtitles, extract subtitles, hardcode subs
**Aliases**: closed captions, subtitle overlay, text track, caption

Patterns for subtitle extraction, embedding, and burning.

## Related Scenarios

| Scenario | Content |
|----------|---------|
| [transcoding.md](transcoding.md) | Video transcoding with subtitle streams |
| [audio_extraction.md](audio_extraction.md) | Stream extraction patterns |

---

## Quick Start

### Extract Subtitles

**Using ez-ffmpeg**:
```rust
use ez_ffmpeg::{FfmpegContext, Output};

FfmpegContext::builder()
    .input("video.mkv")
    .output(Output::from("subs.srt")
        .add_stream_map("0:s:0"))
    .build()?.start()?.wait()
```

**Using ffmpeg-sidecar**:
```rust
FfmpegCommand::new()
    .input("video.mkv")
    .args(["-map", "0:s:0"])
    .output("subs.srt")
    .spawn()?.wait()
```

### Burn Subtitles (Hardcode)

**Using ez-ffmpeg**:
```rust
let escaped_srt = srt_file.replace("\\", "/").replace(":", "\\:");

FfmpegContext::builder()
    .input("video.mp4")
    .filter_desc(&format!("subtitles='{}'", escaped_srt))
    .output(Output::from("output.mp4")
        .set_video_codec("libx264"))
    .build()?.start()?.wait()
```

**Using ffmpeg-sidecar**:
```rust
FfmpegCommand::new()
    .input("video.mp4")
    .args(["-vf", &format!("subtitles={}", srt_file)])
    .codec_video("libx264")
    .output("output.mp4")
    .spawn()?.wait()
```

### Embed Soft Subtitles

**Using ez-ffmpeg**:
```rust
FfmpegContext::builder()
    .input("video.mp4")
    .input("subs.srt")
    .output(Output::from("output.mp4")
        .add_stream_map("0:v")
        .add_stream_map("0:a")
        .add_stream_map("1:0")
        .set_subtitle_codec("mov_text")
        .set_video_codec("copy"))
    .build()?.start()?.wait()
```

**Using ffmpeg-sidecar**:
```rust
FfmpegCommand::new()
    .input("video.mp4")
    .input("subs.srt")
    .args(["-map", "0:v", "-map", "0:a", "-map", "1:0"])
    .args(["-c:v", "copy", "-c:s", "mov_text"])
    .output("output.mp4")
    .spawn()?.wait()
```

### ffmpeg-next Subtitle Stream Copy

ffmpeg-next can extract or remux subtitle streams at the packet level (no decoding needed):

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, encoder, format, media};

fn extract_subtitle(
    input_path: &str,
    output_path: &str,
    sub_index: usize,  // 0 = first subtitle track
) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input_path)?;
    let mut octx = format::output(output_path)?;

    // Find the Nth subtitle stream
    let sub_streams: Vec<usize> = ictx.streams()
        .filter(|s| s.parameters().medium() == media::Type::Subtitle)
        .map(|s| s.index())
        .collect();
    let ist_index = *sub_streams.get(sub_index)
        .ok_or(ffmpeg::Error::StreamNotFound)?;

    let ist = ictx.stream(ist_index).unwrap();
    let ist_time_base = ist.time_base();

    let mut ost = octx.add_stream(encoder::find(codec::Id::None))?;
    ost.set_parameters(ist.parameters());

    octx.write_header()?;

    for (stream, mut packet) in ictx.packets() {
        if stream.index() != ist_index { continue; }
        let ost = octx.stream(0).unwrap();
        packet.rescale_ts(ist_time_base, ost.time_base());
        packet.set_position(-1);
        packet.set_stream(0);
        packet.write_interleaved(&mut octx)?;
    }

    octx.write_trailer()?;
    Ok(())
}
```

This is a packet-level operation (stream copy), so it runs near-instantly with no quality loss.

### Convert Format

**Using ez-ffmpeg**:
```rust
FfmpegContext::builder()
    .input("subs.srt")
    .output("subs.vtt")
    .build()?.start()?.wait()
```

**Using ffmpeg-sidecar**:
```rust
FfmpegCommand::new()
    .input("subs.srt")
    .output("subs.vtt")
    .spawn()?.wait()
```

**See also**: [ez_ffmpeg/filters.md](../ez_ffmpeg/filters.md) for subtitle styling options

---

## Decision Guide

```
IF need permanent subtitles → Burn with subtitles filter
ELIF need toggleable subtitles → Embed as soft subtitle
ELIF MP4 container → Use mov_text codec
ELIF MKV container → Use srt or ass codec
ELIF extract from video → Map subtitle stream with -map 0:s:0
ELSE → Convert format by changing extension
```

---

## Common Patterns

| Pattern | ez-ffmpeg | ffmpeg-sidecar |
|---------|-----------|----------------|
| Extract first sub | `.add_stream_map("0:s:0")` | `.args(["-map", "0:s:0"])` |
| Burn external SRT | `.filter_desc("subtitles='file.srt'")` | `.args(["-vf", "subtitles=file.srt"])` |
| Burn embedded | `.filter_desc("subtitles=input.mkv:si=0")` | `.args(["-vf", "subtitles=input.mkv:si=0"])` |
| Embed soft (MP4) | `.set_subtitle_codec("mov_text")` | `.args(["-c:s", "mov_text"])` |
| Embed soft (MKV) | `.set_subtitle_codec("srt")` | `.args(["-c:s", "srt"])` |
| Style subtitles | `.filter_desc("subtitles='f.srt':force_style='FontSize=24'")` | `.args(["-vf", "subtitles=f.srt:force_style='FontSize=24'"])` |

---

## Advanced Topics

### Subtitle Format Reference

| Format | Extension | Container | Notes |
|--------|-----------|-----------|-------|
| SRT | `.srt` | MKV, MP4 | Most compatible |
| ASS/SSA | `.ass` | MKV | Styled subtitles |
| WebVTT | `.vtt` | WebM | Web standard |
| PGS | N/A | Blu-ray, MKV | Bitmap |

### Codec Names

| Container | Codec | Notes |
|-----------|-------|-------|
| MP4 | `mov_text` | Text only |
| MKV | `srt`, `ass` | All formats |
| WebM | `webvtt` | VTT only |

### Multiple Subtitle Tracks

```rust
// Embed multiple subtitles with language metadata
let output = Output::from("output.mkv")
    .add_stream_map("0:v").add_stream_map("0:a")
    .add_stream_map("1:0").add_stream_map("2:0")
    .add_stream_metadata("s:0", "language", "eng")
    .add_stream_metadata("s:1", "language", "spa");

FfmpegContext::builder()
    .input("video.mp4").input("en.srt").input("es.srt")
    .output(output).build()?.start()?.wait()
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Subtitle codec not compatible" | Use `mov_text` for MP4, `srt` for MKV |
| Path not found in filter | Escape `:` as `\:`, use forward slashes |
| Subtitles not showing | Use burn method for guaranteed display |
| Wrong encoding | Convert subtitle file to UTF-8 first |
