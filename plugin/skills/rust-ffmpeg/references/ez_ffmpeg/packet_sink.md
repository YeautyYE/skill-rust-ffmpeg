# ez-ffmpeg: Encoded Packet Export (Packet Sink)

**Detection Keywords**: encoded packet export, webcodecs, packet sink, h.264 access units, aac frames, encodeddecoder feed, avcC, audiospecificconfig, rtp packetizer, fmp4 segmenter
**Aliases**: PacketSink, PacketSinkHandler, packet callback, EncodedVideoChunk, EncodedAudioChunk

> **Experimental (new in 0.15)** — marked experimental upstream; the surface may be
> reshaped in a future minor release. No Cargo feature flag needed — it's in the
> default build.

Consume the encoders' output directly through callbacks — **no container is
written, no bytes are demuxed back**. This is a third way to get data out of an
`FfmpegContext` job, alongside a normal muxed `Output` and the frame-level
`frame_export`/`VideoWriter` APIs in [frame_io.md](frame_io.md): packet sink
sits *after* the encoder but *before* any muxer, delivering the exact
access units a `VideoDecoder`/`AudioDecoder`, an RTP/SRT packetizer, or a
hand-rolled fMP4 segmenter would otherwise have to demux back out of a
container.

The strict tier (the only tier that exists today; see [Tier](#tier)) targets
WebCodecs consumption specifically: H.264 arrives as avcC-configured,
length-prefixed access units with a ready-made `avc1.PPCCLL` codec string;
AAC arrives as raw frames with the `AudioSpecificConfig`.

## Table of Contents

- [Building a sink](#building-a-sink)
- [Callback contract](#callback-contract)
- [PacketView / EncodedPacket](#packetview--encodedpacket)
- [Stream configuration](#stream-configuration)
- [Strict-tier constraints](#strict-tier-constraints)
- [Wiring into a pipeline](#wiring-into-a-pipeline)
- [Channel-based consumption](#channel-based-consumption)
- [Backpressure and threading](#backpressure-and-threading)
- [Examples](#examples)
- [When to use this vs. alternatives](#when-to-use-this-vs-alternatives)

## Building a sink

Three constructors, all returning a `PacketSink` (import from
`ez_ffmpeg::packet_sink`):

| Constructor | Shape | Use when |
|-------------|-------|----------|
| `PacketSink::builder(on_packet)` → chain → `.build()` | closures | Quick, stateless-ish consumers |
| `PacketSink::from_handler(handler)` | one `impl PacketSinkHandler` | Stateful consumer, no `Arc<Mutex<_>>` needed |
| `PacketSink::channel(capacity)` → `(sink, receiver)` | bounded channel | Consumer lives on its own thread |
| `PacketSink::discard()` | no-op | Explicitly throw everything away |

**Builder (closures):**

```rust
use ez_ffmpeg::packet_sink::{PacketCallbackError, PacketSink};

let sink = PacketSink::builder(|packet| {
    println!("pts {} us, key {}, {} bytes", packet.pts_us(), packet.is_key(), packet.data().len());
    Ok(())
})
.on_stream_info(|streams| {
    let video = streams.iter().find_map(|s| s.video())
        .ok_or_else(|| PacketCallbackError::new("no video stream"))?;
    println!("codec \"{}\", avcC {} bytes", video.codec_string(), video.codec_config().len());
    Ok(())
})
.on_end(|| println!("delivery finished cleanly"))
.on_delivery_error(|e| eprintln!("delivery failed: {e}"))
.build();
```

`on_packet` is the only required callback — there's no default consumer;
`PacketSink::discard()` exists precisely so "throw it all away" is an explicit
choice, not an accident. `on_stream_info` / `on_end` / `on_delivery_error` are
all optional chain calls; `on_end` and `on_delivery_error` are infallible
(`FnMut(..)`, no `Result`).

**Trait-based handler** (one stateful object instead of several closures —
see the `PacketSinkHandler` trait, whose only required method is `on_packet`):

```rust
use ez_ffmpeg::packet_sink::{PacketCallbackResult, PacketSink, PacketSinkHandler, PacketStreamInfo, PacketView};

struct MyFeed { /* decoder state */ }

impl PacketSinkHandler for MyFeed {
    fn on_packet(&mut self, packet: &PacketView<'_>) -> PacketCallbackResult {
        // required; on_stream_info/on_end/on_delivery_error default to no-ops
        Ok(())
    }
}

let sink = PacketSink::from_handler(MyFeed { /* ... */ });
```

### Tier

`sink.tier() -> PacketSinkTier` always returns `PacketSinkTier::Strict` today —
the enum is `#[non_exhaustive]`, reserved for future tiers (generic
passthrough, HEVC, Annex-B) that would arrive as **new constructors**, never
as a flag toggled on the existing strict bundle.

## Callback contract

All callbacks run **serially on one delivery thread** (the mux worker) — never
concurrently, never reentrantly. Fixed order:

1. **`on_stream_info`** — at most once, after every mapped encoder has
   finalized its parameters, strictly before any packet.
2. **`on_packet`** — zero or more times.
3. **`on_end` XOR `on_delivery_error`** — at most one of the two fires, at
   most once. `on_end` fires only when every output stream reached a
   recognized terminal state and the job settled without error.
   `on_delivery_error` fires for a strict-tier violation, a failing callback,
   or a job failure elsewhere (synthesized as `PacketSinkError::JobFailed`).

Neither `on_end` nor `on_delivery_error` fires for: a build-time configuration
failure (see [Strict-tier constraints](#strict-tier-constraints)), cancellation
(`stop()`/`abort()` with packets still in flight), or a **panicking** delivery
callback — in those cases only the scheduler's `wait()`/`stop()` result is
authoritative.

`on_packet`/`on_stream_info` return `PacketCallbackResult` (`= Result<(),
PacketCallbackError>`); a returned `Err` stops delivery and is what
`on_delivery_error` receives. Build one with `PacketCallbackError::new(msg)`
or `PacketCallbackError::with_source(msg, source)` (preserves a wrapped error
reachable via `std::error::Error::source()`).

**Panic containment**: a panic inside one callback (or one captured value's
destructor) is caught per-callback and does not corrupt an already-settled job
result. Caveat carried over from ordinary Rust unwind semantics: two
panicking destructors inside the *same* captured closure/handler still abort
the process — this isn't a packet-sink-specific guarantee, just don't rely on
double-panic recovery.

## PacketView / EncodedPacket

`on_packet`'s argument is a **borrowed** `PacketView<'a>` — valid only for the
duration of that call; copy out anything you need to keep. The channel
adapter (below) hands you an **owned** `EncodedPacket` with the identical
accessor set plus `into_data(self) -> Vec<u8>`.

| Method | Returns | Notes |
|--------|---------|-------|
| `.stream_index()` | `usize` | |
| `.pts()` / `.dts()` | `i64` | Stream-tick values on the shared zero-based timeline; dts strictly increasing per stream |
| `.duration()` | `i64` | Always > 0 — passed through or derived, never a guessed 0 |
| `.time_base()` | `AVRational` | |
| `.pts_us()` / `.dts_us()` / `.duration_us()` | `i64` | Exact microsecond rescale — prefer these over doing the math yourself |
| `.is_key()` | `bool` | **IDR-NAL presence**, deliberately not the raw `AV_PKT_FLAG_KEY` — open-GOP encoders flag non-IDR recovery points as key, which is unsafe to hand a fresh decoder under the WebCodecs "key" contract. Audio packets are always key |
| `.applied_offset()` / `.applied_offset_us()` | `i64` | Per-stream shift subtracted so all streams share one zero-based origin; `original_ts = delivered_ts + applied_offset` recovers the true (possibly negative) encoder-timeline A/V offset |
| `.data()` | `&[u8]` | H.264: one AVCC access unit (4-byte NAL length prefixes). AAC: one raw frame |

No codec-specific accessor lives on the packet itself — codec identity and
out-of-band configuration arrive once, separately, via `on_stream_info`.

## Stream configuration

`on_stream_info` receives `&[PacketStreamInfo]` — one entry per mapped stream,
delivered once, before any packet:

```rust
#[non_exhaustive]
pub enum PacketStreamInfo {
    Video(VideoPacketConfig),
    Audio(AudioPacketConfig),
}
```

Common accessors (on the enum): `.stream_index()`, `.media_type()`,
`.codec_id()`, `.codec_string()`, `.codec_config()` (alias `.extradata()`),
`.time_base()`, `.video() -> Option<&VideoPacketConfig>`, `.audio() -> Option<&AudioPacketConfig>`.

| `VideoPacketConfig` | Returns | Notes |
|----------------------|---------|-------|
| `.codec_string()` | `&str` | RFC 6381 `"avc1.PPCCLL"` |
| `.profile()` / `.compatibility()` / `.level()` | `u8` | The three avcC header bytes behind `codec_string()` |
| `.codec_config()` | `&[u8]` | Full AVCDecoderConfigurationRecord — the WebCodecs `description` |
| `.width()` / `.height()` | `i32` | Coded dimensions |
| `.sample_aspect_ratio()` | `Option<AVRational>` | |
| `.frame_rate()` | `Option<AVRational>` | `None` for VFR sources / no explicit output rate |

| `AudioPacketConfig` | Returns | Notes |
|-----------------------|---------|-------|
| `.codec_string()` | `&str` | RFC 6381 `"mp4a.40.X"` (X = audioObjectType) |
| `.codec_config()` | `&[u8]` | Raw AudioSpecificConfig — the WebCodecs `description` |
| `.sample_rate()` | `i32` | |
| `.channels()` | `i32` | |
| `.channel_layout()` | `&str` | FFmpeg's textual description (`"stereo"`, `"5.1"`, ...) |

## Strict-tier constraints

Everything below is enforced **before any sink callback runs** — most of it
at `build()` time, encoder validity and extradata at job-start time. Nothing
here is "no container, so it doesn't matter" laxness — filters, bitstream
filters, and subtitle codecs are rejected as deliberate policy, outside the
strict tier's delivery contract, not merely because there's no muxer to carry
them.

| Rule | Fails as | When |
|------|----------|------|
| Video encoder must be **`libx264`** — exact name match, not codec ID (`h264_nvenc` does **not** pass, even though it's also H.264) | `PacketSinkError::EncoderNotWhitelisted` | `build()` |
| Audio encoder must declare `AV_CODEC_ID_AAC` — matched by **codec ID**, so both `"aac"` (built-in) and `"libfdk_aac"` pass | `PacketSinkError::EncoderNotWhitelisted` | `build()` |
| `set_video_codec("copy")` / `set_audio_codec("copy")`, or a stream mapped via `add_stream_map_with_copy` | `PacketSinkError::StreamCopyUnsupported` | `build()` |
| Container-only setters: `set_format`, `set_seek_callback`, `set_io_buffer_size`, `set_video_filter`, `set_video_bsf`/`set_audio_bsf`/`set_subtitle_bsf`, `set_format_opt`, `add_attachment`, `set_subtitle_codec`, `add_metadata`/`add_stream_metadata`/`add_chapter_metadata`/`add_program_metadata`, `map_metadata_from_input`, `disable_auto_copy_metadata`, the `"flags"` codec option | `PacketSinkError::UnsupportedOption` | `build()` |
| No stream mapped to the sink at all | `PacketSinkError::NoStreams` | `build()` |
| A mapped stream isn't audio or video | `PacketSinkError::UnsupportedStream` | `build()` |
| Encoder produced no extradata, or extradata fails strict validation | `PacketSinkError::MissingExtradata` / `InvalidExtradata` | job start, before first callback |

Per-packet delivery is validated too (non-monotonic dts, duplicate pts,
pts-before-dts, missing timestamp, unresolvable duration, mid-stream
config change, in-band SPS/PPS instead of out-of-band avcC, malformed
payload) — each a distinct `PacketSinkError` variant, surfacing through
`on_delivery_error` and as the job's terminal error.

## Wiring into a pipeline

```rust
use ez_ffmpeg::{FfmpegContext, Output};

FfmpegContext::builder()
    .input("input.mp4")
    .output(
        Output::from(sink)             // == Output::new_by_packet_sink(sink); `from` is the
            .set_video_codec("libx264") // crate-conventional spelling used throughout the docs
            .disable_audio(),          // route only video into this sink
    )
    .build()?
    .start()?
    .wait()?;
```

- `disable_audio()` / `disable_video()` work unmodified on a packet-sink
  `Output` and are the recommended way to route a single media type — without
  `disable_audio()`, an input that also carries audio hands AAC packets to the
  same callback.
- To route **two** streams into **one** sink (e.g. an fMP4-segmenter shape),
  use explicit `add_stream_map("0:v")` / `add_stream_map("1:a")` instead —
  packets arrive tagged with `.stream_index()`, with **no cross-stream
  interleaving order promised**, so track state independently per index.
- A single `FfmpegContext` job can mix a packet-sink output with ordinary
  muxed outputs.

## Channel-based consumption

For a consumer that lives on its own thread instead of inline callbacks:

```rust
use ez_ffmpeg::packet_sink::{PacketSink, PacketSinkEvent};
use std::num::NonZeroUsize;

let (sink, receiver) = PacketSink::channel(NonZeroUsize::new(8).unwrap());
// ... build the job with Output::from(sink), .start() it ...

for event in receiver.iter() {
    match event {
        PacketSinkEvent::StreamInfo(streams) => { /* ... */ }
        PacketSinkEvent::Packet(packet) => { /* packet: EncodedPacket, owned */ }
        PacketSinkEvent::End => break,
        PacketSinkEvent::Error(e) => { /* ... */ }
        _ => {} // #[non_exhaustive] — the event set can grow
    }
}
```

`PacketSinkReceiver` methods: `.recv()`, `.try_recv()`,
`.recv_timeout(Duration)`, `.iter()`, and `.into_events(scheduler)` — the last
**consumes the receiver together with the running `FfmpegScheduler`** into one
owned iterator yielding `Result<PacketSinkEvent, error::Error>`, guaranteeing
exactly one `End` on a clean run (synthesized if the raw channel's best-effort
terminal event was lost) and aborting the job cleanly if dropped mid-run.
Passing a scheduler that isn't the one actually driving this receiver's sink
fails with `PacketEventsPairingError` (both handles handed back unchanged).

**The channel is bounded and blocks on send when full — the same backpressure
as the direct callback path.** The consumer *must* drain concurrently with the
job; draining only after `wait()` deadlocks once the channel fills. Correct
order: start the job, drain on a second thread, `scheduler.wait()` **first**,
then join the consumer thread. Dropping the receiver cancels the job with
`PacketSinkError::ChannelDisconnected`.

## Backpressure and threading

> "The callbacks run on the delivery thread. A slow `on_packet` blocks that
> thread, the bounded packet queue behind it fills, and the encoders stall —
> exactly the backpressure a slow container write exerts today. No packet is
> ever silently dropped."

There is no opt-out and no async/non-blocking callback variant. The only
alternative to a slow inline callback is to copy data out and queue it
yourself, or use `PacketSink::channel`, which does that copying for you and
simply moves the blocking point to its own bounded channel.

## Examples

Three runnable examples ship in the crate (`cargo run --example <name>`):

| Example | Demonstrates |
|---------|--------------|
| `packet_sink_avc` | Video-only, `from_handler` with a stateful `PacketSinkHandler`, maps onto a WebCodecs-shaped `VideoDecoderConfig`/`EncodedVideoChunk`; checks `codec::get_encoders()` for libx264 first |
| `packet_sink_aac_channel` | Audio-only (built-in `"aac"`, no GPL dependency), `PacketSink::channel` with a small capacity to exercise backpressure, consumer on a separate thread, correct join order |
| `packet_sink_av_transport` | Both video (libx264) + audio (AAC) into one handler via explicit stream maps, routes by `stream_index()`, uses `applied_offset_us()` to recover each track's original timeline — the shape of an fMP4 segmenter or RTP/SRT session |

## When to use this vs. alternatives

- **Feeding a WebCodecs `VideoDecoder`/`AudioDecoder`, packetizing for
  RTP/SRT, or building fMP4 segments yourself?** Packet sink — you get
  ready-made codec strings and out-of-band config, no container parsing.
- **Need decoded pixels/PCM in memory (AI/CV/ASR)?** That's the opposite
  direction — see `frame_export::{FrameExtractor, SampleExtractor}` in
  [frame_io.md](frame_io.md), which decode *into* memory rather than exporting
  *encoded* output.
- **Just need a file or a standard streaming protocol output?** A normal
  muxed `Output` (`Output::from("out.mp4")` / `rtmp://...` / `srt://...`) —
  packet sink is for when you need the encoder's bytes directly, not
  something FFmpeg's own muxers already solve. See
  [streaming.md](streaming.md).
- **Need HEVC, other codecs, or a passthrough (no validation) tier?** Not
  available in 0.15 — the strict tier is H.264 (libx264 only) + AAC, v1.
