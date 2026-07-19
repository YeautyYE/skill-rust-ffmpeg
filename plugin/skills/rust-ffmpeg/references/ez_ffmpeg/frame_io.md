# ez-ffmpeg: In-Memory Frame I/O (Export & Push)

**Detection Keywords**: frame export, extract frames to memory, decode to rgb, whisper pcm, ai frame ingest, frame push, generate video from frames, in-memory mp4, procedural video
**Aliases**: FrameExtractor, SampleExtractor, VideoWriter, frames to video

> **Experimental (new in 0.14)** — both APIs on this page are new in ez-ffmpeg 0.14
> and marked experimental upstream; the surface may be reshaped in a future minor
> release. Neither needs a Cargo feature flag — they are in the default build.

Two symmetric capabilities, both moving raw frames across the Rust ↔ FFmpeg
boundary with **no intermediate files and no hand-rolled byte plumbing**:

| Direction | Type | Turns … into … | Use for |
|-----------|------|----------------|---------|
| **Read** (decode → memory) | `frame_export::FrameExtractor` / `SampleExtractor` | a media file → owned packed pixel buffers / `f32` PCM | AI/CV/ASR ingest (tensors, Whisper) |
| **Write** (memory → encode) | `VideoWriter` | Rust-rendered frames → a full encode/mux/stream pipeline | procedural video, in-memory MP4, live targets |

---

## Frame & Sample Export (decode → memory)

Decode straight into owned Rust buffers. Import from `ez_ffmpeg::frame_export`.

### FrameExtractor (video → packed pixels)

```rust
use ez_ffmpeg::frame_export::{FrameExtractor, Sampling, PixelLayout};

fn main() -> Result<(), ez_ffmpeg::error::Error> {
    // One 224-wide RGB frame per second — ready for a tensor / image encoder.
    for frame in FrameExtractor::new("input.mp4")
        .sampling(Sampling::EverySec(1.0))
        .width(224)                    // aspect-preserving resize (height auto)
        .pixel(PixelLayout::Rgb24)     // default; Rgba32 / Gray8 also available
        .frames()?                     // -> FrameIter, yields Result<VideoFrame>
    {
        let frame = frame?;
        let _bytes: &[u8] = frame.as_bytes(); // tightly packed, no row padding, top-down
        let (_w, _h) = (frame.width(), frame.height());
        let _pts_us = frame.pts_us();         // Option<i64>
    }
    Ok(())
}
```

**Builder knobs** (`FrameExtractor::new(input)` → chain → `.frames()?` or `.collect_frames()?`):

| Method | Effect |
|--------|--------|
| `.sampling(Sampling)` | Which frames — see table below (default `All`) |
| `.width(u32)` / `.height(u32)` | Resize; set one for aspect-preserving scale |
| `.pixel(PixelLayout)` | `Rgb24` (default), `Rgba32`, `Gray8` |
| `.color(ColorPolicy)` | YUV→RGB matrix policy (see below) |
| `.max_frames(u64)` | Hard cap on emitted frames |
| `.start_time_us(i64)` / `.duration_us(i64)` | Time window (trim) |
| `.duration_hint_us(i64)` | Total duration for `UniformN` when it can't be probed (live/piped input) |
| `.video_stream_index(usize)` | Pick a stream when the file has several video streams |
| `.channel_capacity(usize)` | Bounded decode-ahead queue depth |

**`Sampling` modes:**

| Variant | Emits | Cost |
|---------|-------|------|
| `All` | every decoded frame | full decode |
| `EveryNth(u64)` | every Nth frame | full decode, filtered |
| `EverySec(f64)` | one frame per N seconds | full decode, filtered |
| `KeyframesOnly` | only keyframes | **fast** sparse path (seek-friendly) |
| `UniformN(u32)` | **exactly** N frames evenly spread over the (trimmed) duration | single sequential decode — no seek-per-target |

`UniformN(n)` is the fixed frame budget VLM/CLIP-style pipelines expect; it pads
short inputs by repeating nearby frames, and yields fewer than `n` only if a
lower `max_frames` wins. It is a **single sequential decode** (no seek fast path),
so budget accordingly on long files — reach for `KeyframesOnly` when you want the
cheap sparse-thumbnail path instead.

### Color policy (tag-aware by default)

`ColorPolicy` controls YUV → RGB conversion. Getting this wrong visibly shifts
saturated colors on HD sources (the classic BT.601-coefficients-on-BT.709-content bug).

| `ColorPolicy` | Behavior |
|---------------|----------|
| `Tagged` *(default)* | Honor each frame's colorspace tags; untagged frames fall through to swscale's documented default (BT.601 / limited) |
| `TaggedOrResolutionGuess` | Like `Tagged`, but untagged frames get a per-frame guess: BT.709 when height ≥ 720, else BT.601 (tagged frames never overridden) |
| `Force { matrix, range }` | Pin `YuvMatrix::{Bt601,Bt709}` + `YuvRange::{Limited,Full}` for ALL frames when the tags are known wrong |

Input flagged **HDR** in its stream metadata (BT.2020 / PQ / HLG) **fails fast with
a typed error** rather than being silently mis-converted to 8-bit RGB.

### SampleExtractor (audio → interleaved f32 PCM)

```rust
use ez_ffmpeg::frame_export::{SampleExtractor, Channels};

// 16 kHz mono f32 — the whisper-rs / candle handoff shape.
let pcm: Vec<f32> = SampleExtractor::for_whisper("input.mp4").collect_samples()?;

// Or configure explicitly:
let pcm: Vec<f32> = SampleExtractor::new("input.mp4")
    .sample_rate(48_000)
    .channels(Channels::Stereo)      // Mono downmixes; ASR models want Mono
    .start_time_us(0)
    .duration_us(30_000_000)         // first 30 s
    .collect_samples()?;
```

- `for_whisper(input)` presets 16 kHz **mono** — the shape ASR models consume.
- `.collect_samples()? -> Vec<f32>` buffers everything; `.samples()? -> SampleIter`
  streams chunks for long inputs without holding the whole track in memory.
- `Channels::{Mono, Stereo}`; interleaved layout for stereo.

---

## Frame Push: VideoWriter (memory → encode)

The write-side sibling of frame export: render frames in Rust and push them into
a full FFmpeg pipeline — filters, any encoder/container the linked build offers,
or a streaming target — with **no demuxer**. Constant frame rate, **video only**.
Import from the crate root: `ez_ffmpeg::{VideoWriter, Output}`.

```rust
use ez_ffmpeg::{Output, VideoWriter};

fn render(_i: usize) -> Vec<u8> {
    vec![0u8; 640 * 360 * 4] // one tightly packed RGBA frame (default pixel format)
}

fn main() -> Result<(), ez_ffmpeg::error::Error> {
    // Pick an encoder explicitly: a bare "out.mp4" lets the linked FFmpeg build
    // choose the container default (H.264 via libx264, else mpeg4).
    let out = Output::from("out.mp4").set_video_codec("mpeg4").set_video_qscale(5);

    let mut writer = VideoWriter::builder(640, 360)
        .fps(30, 1)            // default (30, 1); NTSC like fps(30000, 1001) works
        .open(out)?;

    for i in 0..90 {
        writer.write_owned(render(i))?;   // or writer.write(&bytes)
    }
    writer.finish()?;          // drains the encoder, finalizes the container
    Ok(())
}
```

**Builder** — `VideoWriter::builder(width, height)`:

| Method | Effect |
|--------|--------|
| `.pixel_format(name)` | Any non-hardware `AVPixelFormat` name. Default `"rgba"`; e.g. `"rgb24"`, `"yuv420p"` (planes concatenated in descriptor order) |
| `.fps(num, den)` | CFR rate; every written frame advances exactly `den/num` seconds |
| `.queue_capacity(frames)` | Backpressure queue depth (derived from a memory budget by default) |
| `.filter_desc(desc)` | A filter graph the pushed frames flow through before encoding — must consume exactly **one** video input and produce **one** video output |
| `.open(output) -> Result<VideoWriter>` | Validate + start the pipeline |

**Writer** — the live handle:

| Method | Effect |
|--------|--------|
| `.frame_size() -> usize` | Exact bytes each pushed frame must be (`w * h * bytes_per_pixel`, packed) |
| `.write(&[u8])` / `.write_owned(Vec<u8>)` | Push one frame; applies backpressure through the bounded queue, returns `Result<(), PushError>` |
| `.finish() -> Result<()>` | **Authoritative** result — drains/flushes the encoder, writes the trailer, surfaces the pipeline's first error |
| `.abort()` | Discard the export (no valid output) |

Notes:
- **`finish()` is where errors surface.** A `write()` that returns
  `PushError::PipelineClosed` means a worker failed or an `Output` limit (e.g.
  `set_max_video_frames`) ended the job early — call `finish()` for the real cause.
- **Frame size is exact**: a wrong-length buffer is rejected as `PushError::WrongSize`.
  Query `frame_size()` after `open()` rather than computing it yourself.
- Build/validation problems (zero dimensions, unknown/hardware pixel format,
  a graph that never consumes the pushed video, stream maps on the single stream)
  fail at `.open()` as `error::Error::Writer(WriterError::…)`.

### In-memory MP4 (encode into a `Vec<u8>`)

Combine `VideoWriter` with ez-ffmpeg's custom output I/O (write/seek callbacks —
see [advanced.md](advanced.md)) to keep the encoded container in memory instead of
on disk. The upstream `examples/in_memory_mp4` shows the full wiring;
`examples/bouncing_balls` and `examples/frames_to_video` show procedural render loops.

---

## When to use this vs. alternatives

- **Extracting frames for a model?** `FrameExtractor` — owned packed RGB, correct
  colorspace, uniform sampling. Don't hand-roll `sws_scale` (BT.601 default bug) or
  shell out to the CLI and re-read PNGs.
- **Extracting audio for ASR?** `SampleExtractor::for_whisper` — one call to the
  16 kHz mono `f32` shape; skip the manual resample/downmix.
- **Generating video from scratch (no input file)?** `VideoWriter` — procedural
  animation, data-viz frames, synthetic test media. If you instead have an input
  file and want to *transform* it, use the normal `FfmpegContext` pipeline with a
  `FrameFilter` (see [filters.md](filters.md)).
- **Need per-frame codec structs (AVFrame) or zero-copy?** Drop to `ffmpeg-next`
  ([ffmpeg_next.md](../ffmpeg_next.md)) — `VideoWriter`/`FrameExtractor` deal in
  packed byte buffers, not refcounted `AVFrame`s.
