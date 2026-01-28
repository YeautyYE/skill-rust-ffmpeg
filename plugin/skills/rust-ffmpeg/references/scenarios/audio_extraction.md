# Audio Extraction

**Detection Keywords**: extract audio, audio only, how to extract audio from video, separate audio track, audio track, video to audio, mp3 extract, audio conversion, separate audio, loudness normalization, normalize audio, loudnorm, lufs, ebur128, volume normalize
**Aliases**: audio extract, get audio, audio only, audio separation, audio normalization

Extract audio tracks from video files across all Rust FFmpeg libraries.

## Quick Example (30 seconds)

```rust
// ez-ffmpeg
use ez_ffmpeg::{FfmpegContext, Output};

FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("audio.mp3")
        .add_stream_map("0:a"))  // Map only audio stream
    .build()?.start()?.wait()?;
```

```rust
// ffmpeg-sidecar
use ffmpeg_sidecar::command::FfmpegCommand;

FfmpegCommand::new()
    .input("video.mp4")
    .no_video()
    .codec_audio("libmp3lame")
    .output("audio.mp3")
    .spawn()?.wait()?;
```

## Library Comparison

| Aspect | ez-ffmpeg | ffmpeg-next | ffmpeg-sys-next | ffmpeg-sidecar |
|--------|-----------|-------------|-----------------|----------------|
| **Async support** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Code complexity** | Low | Medium | High | Low |
| **Type safety** | ✅ Full | ✅ Full | ⚠️ Unsafe | ✅ Full |
| **Use when** | General tasks | Codec control | Max performance | No install |

## Detailed Examples

For detailed audio extraction examples, see library-specific guides:
- **ez-ffmpeg**: [ez_ffmpeg/audio.md](../ez_ffmpeg/audio.md) - format conversion, codec selection, bitrate control, resampling, channel mapping
- **ffmpeg-next**: [ffmpeg_next/audio.md](../ffmpeg_next/audio.md) - stream-level audio processing
- **ffmpeg-sys-next**: [ffmpeg_sys_next/frame_codec.md](../ffmpeg_sys_next/frame_codec.md) - low-level audio operations
- **ffmpeg-sidecar**: [ffmpeg_sidecar/audio.md](../ffmpeg_sidecar/audio.md) - CLI wrapper audio extraction

## When to Choose

See [Library Selection Guide](../library_selection.md) for detailed criteria.

## Common Patterns

### Extract audio to different formats
```rust
// ez-ffmpeg
.output(Output::from("audio.mp3").add_stream_map("0:a"))
.output(Output::from("audio.aac").add_stream_map("0:a"))

// ffmpeg-sidecar
.no_video()
.codec_audio("libmp3lame")
```

### Control audio quality
```rust
// ez-ffmpeg
.output(Output::from("audio.mp3")
    .add_stream_map("0:a")
    .set_audio_codec_opt("b", "192k"))

// ffmpeg-sidecar
.no_video()
.args(["-b:a", "192k"])
```

### Extract specific audio track
```rust
// ez-ffmpeg
.output(Output::from("audio.mp3")
    .add_stream_map("0:a:1"))  // Second audio track

// ffmpeg-sidecar
.args(["-map", "0:a:1"])
```

### ffmpeg-next Audio Transcoding

ffmpeg-next provides frame-level control over audio processing via a decode-filter-encode pipeline. Based on the upstream `transcode-audio` example:

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, filter, format, frame, media};

/// Transcode the best audio stream with an optional filter.
/// Pass "anull" for direct copy, or a filter like "atempo=1.2" for speed change.
fn transcode_audio(
    input_path: &str,
    output_path: &str,
    filter_spec: &str,
) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input_path)?;
    let mut octx = format::output(output_path)?;

    // Find best audio stream and set up decoder
    let input_stream = ictx.streams().best(media::Type::Audio)
        .ok_or(ffmpeg::Error::StreamNotFound)?;
    let stream_index = input_stream.index();
    let in_time_base = input_stream.time_base();

    let context = codec::context::Context::from_parameters(input_stream.parameters())?;
    let mut decoder = context.decoder().audio()?;
    decoder.set_parameters(input_stream.parameters())?;

    // Set up encoder based on output format
    let codec = ffmpeg::encoder::find(
        octx.format().codec(output_path, media::Type::Audio)
    ).ok_or(ffmpeg::Error::EncoderNotFound)?.audio()?;

    let mut ost = octx.add_stream(codec)?;
    let enc_context = codec::context::Context::from_parameters(ost.parameters())?;
    let mut encoder = enc_context.encoder().audio()?;

    let channel_layout = codec.channel_layouts()
        .map(|cls| cls.best(decoder.channel_layout().channels()))
        .unwrap_or(ffmpeg::channel_layout::ChannelLayout::STEREO);

    encoder.set_rate(decoder.rate() as i32);
    encoder.set_channel_layout(channel_layout);
    encoder.set_format(codec.formats().expect("unknown formats").next().unwrap());
    encoder.set_bit_rate(decoder.bit_rate());
    encoder.set_time_base((1, decoder.rate() as i32));
    ost.set_time_base((1, decoder.rate() as i32));

    if octx.format().flags().contains(format::Flags::GLOBAL_HEADER) {
        encoder.set_flags(codec::Flags::GLOBAL_HEADER);
    }

    let encoder = encoder.open_as(codec)?;
    ost.set_parameters(&encoder);

    // Set up filter graph (e.g., "anull" for passthrough, "loudnorm" for normalization)
    let mut graph = filter::Graph::new();
    let args = format!(
        "time_base={}:sample_rate={}:sample_fmt={}:channel_layout=0x{:x}",
        decoder.time_base(), decoder.rate(),
        decoder.format().name(), decoder.channel_layout().bits()
    );
    graph.add(&filter::find("abuffer").unwrap(), "in", &args)?;
    graph.add(&filter::find("abuffersink").unwrap(), "out", "")?;
    {
        let mut out = graph.get("out").unwrap();
        out.set_sample_format(encoder.format());
        out.set_channel_layout(encoder.channel_layout());
        out.set_sample_rate(encoder.rate());
    }
    graph.output("in", 0)?.input("out", 0)?.parse(filter_spec)?;
    graph.validate()?;

    octx.write_header()?;
    let out_time_base = octx.stream(0).unwrap().time_base();

    // Decode → Filter → Encode loop
    for (stream, mut packet) in ictx.packets() {
        if stream.index() != stream_index { continue; }
        packet.rescale_ts(stream.time_base(), decoder.time_base());
        decoder.send_packet(&packet)?;

        let mut decoded = frame::Audio::empty();
        while decoder.receive_frame(&mut decoded).is_ok() {
            decoded.set_pts(decoded.timestamp());
            graph.get("in").unwrap().source().add(&decoded)?;

            let mut filtered = frame::Audio::empty();
            while graph.get("out").unwrap().sink().frame(&mut filtered).is_ok() {
                encoder.send_frame(&filtered)?;
                let mut encoded = ffmpeg::Packet::empty();
                while encoder.receive_packet(&mut encoded).is_ok() {
                    encoded.set_stream(0);
                    encoded.rescale_ts(decoder.time_base(), out_time_base);
                    encoded.write_interleaved(&mut octx)?;
                }
            }
        }
    }

    // Flush
    decoder.send_eof()?;
    // ... flush decoder, filter, encoder (same pattern)

    octx.write_trailer()?;
    Ok(())
}
```

Key points:
- The filter graph bridges decoder output format to encoder input format.
- Use `"anull"` filter for passthrough, `"loudnorm"` for normalization, `"atempo=1.2"` for speed change.
- `set_frame_size` on the sink may be needed for codecs without `VARIABLE_FRAME_SIZE` capability.
- Proper flush sequence: decoder EOF → filter flush → encoder EOF.

For the complete working example, see [ffmpeg_next/audio.md](../ffmpeg_next/audio.md).

### Loudness Normalization (EBU R128)

Normalize audio to broadcast standards (-16 LUFS for streaming, -24 LUFS for TV).

```rust
// ez-ffmpeg - Basic normalization
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("loudnorm")
    .output("normalized.mp3")
    .build()?.start()?.wait()?;

// ez-ffmpeg - With target parameters (streaming standard)
FfmpegContext::builder()
    .input("input.mp4")
    .filter_desc("loudnorm=I=-16:TP=-1.5:LRA=11")
    .output("normalized.mp3")
    .build()?.start()?.wait()?;
// I=-16: Target integrated loudness -16 LUFS
// TP=-1.5: True peak limit -1.5 dBTP
// LRA=11: Loudness range target 11 LU
```

```rust
// ffmpeg-sidecar - Basic normalization
FfmpegCommand::new()
    .input("input.mp4")
    .args(["-af", "loudnorm"])
    .output("normalized.mp3")
    .spawn()?.wait()?;

// ffmpeg-sidecar - Two-pass for precise normalization
// Pass 1: Analyze
let output = FfmpegCommand::new()
    .input("input.mp4")
    .args(["-af", "loudnorm=print_format=json", "-f", "null", "-"])
    .spawn()?.iter()?.collect_output();
// Parse JSON output to get measured_I, measured_TP, measured_LRA, measured_thresh

// Pass 2: Apply with measured values
FfmpegCommand::new()
    .input("input.mp4")
    .args(["-af", &format!(
        "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={}:measured_TP={}:measured_LRA={}:measured_thresh={}:linear=true",
        measured_i, measured_tp, measured_lra, measured_thresh
    )])
    .output("normalized.mp3")
    .spawn()?.wait()?;
```

```rust
// ffmpeg-next - Filter graph approach
let filter_spec = "loudnorm=I=-16:TP=-1.5:LRA=11";
// See ffmpeg_next/filters.md for complete filter graph setup
```

**Common Target Standards**:
| Standard | Integrated | True Peak | Use Case |
|----------|------------|-----------|----------|
| `-16 LUFS` | -16 | -1.5 dBTP | Streaming (Spotify, YouTube) |
| `-14 LUFS` | -14 | -1.0 dBTP | Podcasts |
| `-24 LUFS` | -24 | -2.0 dBTP | TV broadcast (EBU R128) |
| `-24 LKFS` | -24 | -2.0 dBTP | US broadcast (ATSC A/85) |

## Related Scenarios

| Scenario | Guide |
|----------|-------|
| Video transcoding | [video_transcoding.md](video_transcoding.md) |
| Batch processing | [batch_processing.md](batch_processing.md) |
| Streaming | [streaming_rtmp_hls.md](streaming_rtmp_hls.md) |
