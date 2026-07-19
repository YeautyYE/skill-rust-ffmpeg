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

**Native burn-in with `SubtitleFilter` (preferred, ez-ffmpeg)** — a pure-Rust
renderer runs inside the frame pipeline, so this needs **no `--enable-libass`
FFmpeg build flag, no system libass, and no temporary subtitle files**. It works
with any FFmpeg build configuration in the supported 7.1–8.x range and accepts
in-memory subtitle content (e.g. ASR output).

Enable the feature in `Cargo.toml`:
```toml
[dependencies]
ez-ffmpeg = { version = "0.14.0", features = ["subtitle"] }
```

```rust
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ez_ffmpeg::subtitle::SubtitleFilter;
use ez_ffmpeg::{AVMediaType, FfmpegContext, Output};

// Subtitles straight from memory; .srt/.ass/.vtt files work too via
// `.file("subs.srt")`, and full in-memory ASS scripts via `.ass_content(script)`.
let srt = "\
1
00:00:00,500 --> 00:00:02,500
Hello from ez-ffmpeg!

2
00:00:02,500 --> 00:00:04,800
<i>Native pure-Rust burn-in</i> - no FFmpeg build flags needed.
";

let filter = SubtitleFilter::builder()
    .srt_content(srt)
    // Style overrides use FFmpeg `force_style` semantics:
    .force_style("FontSize=28,Outline=1")
    // For reproducible fonts (e.g. app-shipped ones):
    // .fonts_dir("assets/fonts")
    // .default_font_file("assets/fonts/NotoSansSC-Regular.otf")
    // .font_provider(ez_ffmpeg::subtitle::FontProvider::None)
    .build()?;

// Attach on the output side: subtitles render against the final,
// post-filter-graph geometry, right before encoding.
let pipeline: FramePipelineBuilder = AVMediaType::AVMEDIA_TYPE_VIDEO.into();
FfmpegContext::builder()
    .input("video.mp4")
    .output(
        Output::from("output.mp4")
            .add_frame_pipeline(pipeline.filter("subtitles", Box::new(filter))),
    )
    .build()?.start()?.wait()?;
```

Source options on the builder (pick one): `.file(path)` (.srt/.ass/.vtt),
`.srt_content(s)`, `.ass_content(s)` (full ASS/SSA script), `.stream_index(i)`
(burn an embedded subtitle stream). Styling/fonts: `.force_style(s)`,
`.fonts_dir(dir)`, `.default_font_file(f)`, `.default_family(name)`,
`.font_provider(FontProvider)` (`Autodetect` default, or `None` for
deterministic explicit-fonts-only), `.font_scale(f64)`, `.shaping(TextShaping)`.
`build()` validates up front, so a bad option logs and skips the attach instead
of aborting mid-transcode.

**Fallback — FFmpeg native `subtitles` filter (only when the linked FFmpeg was
built with `--enable-libass`)**:
```rust
let escaped_srt = srt_file.replace("\\", "/").replace(":", "\\:");

FfmpegContext::builder()
    .input("video.mp4")
    .filter_desc(&format!("subtitles='{}'", escaped_srt))
    .output(Output::from("output.mp4")
        .set_video_codec("libx264"))
    .build()?.start()?.wait()
```

**Using ffmpeg-sidecar** (invokes the ffmpeg binary's `subtitles` filter — also requires libass):
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

**MKV with ASS subs + embedded fonts** (ez-ffmpeg 0.13+, FFmpeg `-attach` parity) —
attach the fonts the ASS script references so any player renders it correctly:
```rust
FfmpegContext::builder()
    .input("video.mp4")
    .input("subs.ass")
    .output(Output::from("output.mkv")
        .add_stream_map("0:v")
        .add_stream_map("0:a")
        .add_stream_map("1:0")
        .set_subtitle_codec("ass")
        .set_video_codec("copy")
        .add_attachment("fonts/NotoSansSC-Regular.otf")  // mimetype inferred for common font types
        .add_attachment_with_mimetype("fonts/custom.ttf", "font/ttf"))
    .build()?.start()?.wait()
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
IF need permanent subtitles → Native SubtitleFilter burn-in (no libass), or subtitles filter if FFmpeg has libass
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
| Native burn (no libass) | `SubtitleFilter::builder().srt_content(..).build()` + `.add_frame_pipeline(..)` | N/A (needs libass) |
| Burn external SRT (needs libass) | `.filter_desc("subtitles='file.srt'")` | `.args(["-vf", "subtitles=file.srt"])` |
| Burn embedded (needs libass) | `.filter_desc("subtitles=input.mkv:si=0")` | `.args(["-vf", "subtitles=input.mkv:si=0"])` |
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
