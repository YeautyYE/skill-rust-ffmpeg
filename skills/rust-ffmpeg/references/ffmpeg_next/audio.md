# ffmpeg-next: Audio Operations

**Detection Keywords**: audio resampling, sample rate conversion, channel layout, audio format, audio transcoding, audio filter
**Aliases**: audio resample, audio convert, sample format

Audio processing operations including resampling and transcoding with filters.

## Related Guides

| Guide | Content |
|-------|---------|
| [video.md](video.md) | Seeking, scaling context, timestamp management |
| [filters.md](filters.md) | Filter graph for audio/video processing |
| [transcoding.md](transcoding.md) | Video transcoding, frame extraction |

## Table of Contents

- [Resampling Context (Audio Format Conversion)](#resampling-context-audio-format-conversion)
- [Examples](#examples)
  - [Audio Transcoding with Filters](#audio-transcoding-with-filters)

## Resampling Context (Audio Format Conversion)

The `software::resampling::Context` handles audio sample format, rate, and channel layout conversion.

### Basic Usage

```rust
use ffmpeg::software::resampling::Context;
use ffmpeg::format::Sample;
use ffmpeg::channel_layout::ChannelLayout;
use ffmpeg::frame::Audio;

// Create resampler: 48kHz stereo float -> 44.1kHz stereo S16
let mut resampler = Context::get(
    Sample::F32(ffmpeg::format::sample::Type::Planar),  // source format
    ChannelLayout::STEREO,                              // source layout
    48000,                                              // source rate
    Sample::I16(ffmpeg::format::sample::Type::Packed),  // dest format
    ChannelLayout::STEREO,                              // dest layout
    44100,                                              // dest rate
)?;

// Process a single frame (typically from a decoder)
let mut dst_frame = Audio::empty();
if let Some(delay) = resampler.run(&src_frame, &mut dst_frame)? {
    // delay indicates buffered samples not yet output
    println!("Resampler delay: {:?}", delay);
}
// dst_frame now contains converted audio

// After all input frames processed, flush remaining samples
while resampler.flush(&mut dst_frame)?.is_some() {
    // Process each flushed frame
    // dst_frame contains the remaining buffered samples
}
```

### Usage with Decoder Loop

For processing decoded audio frames through a resampler:

```rust
use ffmpeg::{software::resampling::Context, format::Sample, channel_layout::ChannelLayout};
use ffmpeg::{codec, format, frame, media, error::EAGAIN};

fn resample_decoded_audio(input_path: &str) -> Result<(), ffmpeg::Error> {
    let mut ictx = format::input(input_path)?;
    let audio_stream = ictx.streams().best(media::Type::Audio)
        .ok_or(ffmpeg::Error::StreamNotFound)?;
    let audio_index = audio_stream.index();

    let ctx = codec::context::Context::from_parameters(audio_stream.parameters())?;
    let mut decoder = ctx.decoder().audio()?;

    // Create resampler after decoder is set up (to get actual format)
    let mut resampler = Context::get(
        decoder.format(),
        decoder.channel_layout(),
        decoder.rate(),
        Sample::I16(ffmpeg::format::sample::Type::Packed),
        ChannelLayout::STEREO,
        44100,
    )?;

    let mut src_frame = frame::Audio::empty();
    let mut dst_frame = frame::Audio::empty();

    for (stream, packet) in ictx.packets() {
        if stream.index() != audio_index { continue; }

        decoder.send_packet(&packet)?;

        loop {
            match decoder.receive_frame(&mut src_frame) {
                Ok(()) => {
                    resampler.run(&src_frame, &mut dst_frame)?;
                    // Process resampled dst_frame...
                }
                Err(ffmpeg::Error::Other { errno: EAGAIN }) => break,
                Err(ffmpeg::Error::Eof) => break,
                Err(e) => return Err(e),
            }
        }
    }

    // Flush decoder
    decoder.send_eof()?;
    loop {
        match decoder.receive_frame(&mut src_frame) {
            Ok(()) => { resampler.run(&src_frame, &mut dst_frame)?; }
            Err(ffmpeg::Error::Other { errno: EAGAIN }) => break,
            Err(ffmpeg::Error::Eof) => break,
            Err(e) => return Err(e),
        }
    }

    // Flush resampler
    while resampler.flush(&mut dst_frame)?.is_some() {
        // Process remaining samples
    }

    Ok(())
}
```

### Production Pattern: Dynamic Resampling

From production code - handle varying input formats dynamically:

```rust
use ffmpeg_next::software::resampling::Context as ResamplingContext;
use ffmpeg::channel_layout::ChannelLayout;

struct AudioProcessor {
    resampler: Option<ResamplingContext>,
    target_rate: u32,
    target_layout: ChannelLayout,
}

impl AudioProcessor {
    fn process_frame(&mut self, frame: &ffmpeg_next::frame::Audio) -> Result<ffmpeg_next::frame::Audio, ffmpeg_next::Error> {
        // Initialize resampler based on actual input format
        if self.resampler.is_none() {
            self.resampler = Some(ResamplingContext::get(
                frame.format(),
                frame.channel_layout(),
                frame.rate(),
                ffmpeg_next::format::Sample::F32(ffmpeg_next::format::sample::Type::Planar),
                self.target_layout,
                self.target_rate,
            )?);
        }

        let mut output = ffmpeg_next::frame::Audio::empty();
        self.resampler.as_mut().unwrap().run(frame, &mut output)?;
        Ok(output)
    }
}
```

### Sample Format Reference

| Format | Description | Use Case |
|--------|-------------|----------|
| `Sample::I16(Packed)` | 16-bit signed integer, interleaved | CD quality, compatibility |
| `Sample::I16(Planar)` | 16-bit signed integer, planar | Some encoders |
| `Sample::F32(Packed)` | 32-bit float, interleaved | Processing, mixing |
| `Sample::F32(Planar)` | 32-bit float, planar | Most FFmpeg internal use |
| `Sample::I32(Packed)` | 32-bit signed integer | High-quality audio |

### Channel Layout Reference

| Layout | Channels | Description |
|--------|----------|-------------|
| `ChannelLayout::MONO` | 1 | Single channel |
| `ChannelLayout::STEREO` | 2 | Left + Right |
| `ChannelLayout::_2POINT1` | 3 | Stereo + LFE |
| `ChannelLayout::SURROUND` | 3 | L + R + C |
| `ChannelLayout::_5POINT1` | 6 | 5.1 surround |
| `ChannelLayout::_7POINT1` | 8 | 7.1 surround |

### Advanced Channel Layout (FFmpeg 5.1+)

For FFmpeg 5.1+, use `AVChannelLayout` for more flexible channel configuration:

```rust
use ffmpeg_sys_next::{AVChannelLayout, AVChannelOrder, av_channel_layout_default};

/// Create a default stereo channel layout
fn create_stereo_layout() -> AVChannelLayout {
    unsafe {
        let mut layout = AVChannelLayout {
            order: AVChannelOrder::AV_CHANNEL_ORDER_NATIVE,
            nb_channels: 2,
            u: std::mem::zeroed(),
            opaque: std::ptr::null_mut(),
        };
        av_channel_layout_default(&mut layout, 2);
        layout
    }
}

/// Create a mono channel layout
fn create_mono_layout() -> AVChannelLayout {
    unsafe {
        let mut layout = AVChannelLayout {
            order: AVChannelOrder::AV_CHANNEL_ORDER_NATIVE,
            nb_channels: 1,
            u: std::mem::zeroed(),
            opaque: std::ptr::null_mut(),
        };
        av_channel_layout_default(&mut layout, 1);
        layout
    }
}

/// Get channel count from layout
fn get_channel_count(layout: &AVChannelLayout) -> i32 {
    layout.nb_channels
}

/// Check if layout is valid
fn is_layout_valid(layout: &AVChannelLayout) -> bool {
    layout.nb_channels > 0 && layout.order != AVChannelOrder::AV_CHANNEL_ORDER_UNSPEC
}
```

**Channel Layout Migration Note**:
FFmpeg 5.1+ deprecates `channel_layout` (bitmask) in favor of `AVChannelLayout` struct.
When working with frames:

```rust
// Old style (FFmpeg < 5.1) - deprecated
// frame.set_channel_layout(ChannelLayout::STEREO);

// New style (FFmpeg 5.1+)
unsafe {
    let frame_ptr = frame.as_mut_ptr();
    av_channel_layout_default(&mut (*frame_ptr).ch_layout, 2);
}
```


## Examples

### Audio Transcoding with Filters

Transcode audio with filter processing (e.g., tempo change, volume adjustment):

**Usage**: `cargo run -- input.mp4 output.aac "atempo=1.5"`

**Expected Output**: Creates output audio file with the specified filter applied.

**Common Filter Specs**:
- `atempo=1.5` - Speed up 1.5x
- `volume=0.5` - Reduce volume to 50%
- `aresample=44100` - Resample to 44.1kHz
- `loudnorm` - Normalize loudness

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, filter, format, frame, media, Rescale};

fn transcode_audio_with_filter(
    input: &str,
    output: &str,
    filter_spec: &str,  // e.g., "atempo=1.5", "volume=0.5"
) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input)?;
    let mut octx = format::output(output)?;

    // Setup decoder
    let ist = ictx.streams().best(media::Type::Audio)
        .ok_or(ffmpeg::Error::StreamNotFound)?;
    let ist_index = ist.index();
    let decoder_ctx = codec::context::Context::from_parameters(ist.parameters())?;
    let mut decoder = decoder_ctx.decoder().audio()?;

    // Setup encoder - find codec for the output container format
    // Note: octx.format().codec() returns Option<codec::Id>
    let codec_id = octx.format().codec(output, media::Type::Audio);
    let codec = ffmpeg::encoder::find(codec_id)
        .ok_or(ffmpeg::Error::EncoderNotFound)?
        .audio()?;

    // Create encoder context from the codec (NOT from empty output stream parameters)
    let mut encoder = codec::context::Context::new_with_codec(codec)
        .encoder()
        .audio()?;

    // Configure encoder to match decoder
    let channel_layout = codec.channel_layouts()
        .map(|cls| cls.best(decoder.channel_layout().channels()))
        .unwrap_or(ffmpeg::channel_layout::ChannelLayout::STEREO);

    encoder.set_rate(decoder.rate() as i32);
    encoder.set_channel_layout(channel_layout);
    encoder.set_format(codec.formats().expect("unknown supported formats").next().unwrap());
    encoder.set_bit_rate(decoder.bit_rate());
    encoder.set_time_base((1, decoder.rate() as i32));

    let encoder = encoder.open_as(codec)?;

    // Add output stream AFTER encoder is configured and opened
    let mut ost = octx.add_stream(encoder)?;
    ost.set_time_base((1, decoder.rate() as i32));
    ost.set_parameters(&encoder);

    // Setup filter graph
    let mut graph = filter::Graph::new();
    let args = format!(
        "time_base={}:sample_rate={}:sample_fmt={}:channel_layout=0x{:x}",
        decoder.time_base(),
        decoder.rate(),
        decoder.format().name(),
        decoder.channel_layout().bits()
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

    let encoder_time_base = encoder.time_base();
    let out_time_base = ost.time_base();

    // Process packets
    for (stream, packet) in ictx.packets() {
        if stream.index() != ist_index {
            continue;
        }

        // Note: No need to rescale packets before decoding - decoder context
        // was created from stream parameters and uses the same time_base
        decoder.send_packet(&packet)?;

        let mut decoded = frame::Audio::empty();
        // Drain all available frames from decoder
        // EAGAIN means "need more input", not an error
        loop {
            match decoder.receive_frame(&mut decoded) {
                Ok(()) => {
                    decoded.set_pts(decoded.timestamp());
                    graph.get("in").unwrap().source().add(&decoded)?;

                    let mut filtered = frame::Audio::empty();
                    loop {
                        match graph.get("out").unwrap().sink().frame(&mut filtered) {
                            Ok(()) => {
                                encoder.send_frame(&filtered)?;

                                let mut encoded = ffmpeg::Packet::empty();
                                loop {
                                    match encoder.receive_packet(&mut encoded) {
                                        Ok(()) => {
                                            encoded.set_stream(0);
                                            encoded.rescale_ts(encoder_time_base, out_time_base);
                                            encoded.write_interleaved(&mut octx)?;
                                        }
                                        Err(ffmpeg::Error::Other { errno: ffmpeg::error::EAGAIN }) => break,
                                        Err(ffmpeg::Error::Eof) => break,
                                        Err(e) => return Err(e),
                                    }
                                }
                            }
                            Err(ffmpeg::Error::Other { errno: ffmpeg::error::EAGAIN }) => break,
                            Err(ffmpeg::Error::Eof) => break,
                            Err(e) => return Err(e),
                        }
                    }
                }
                Err(ffmpeg::Error::Other { errno: ffmpeg::error::EAGAIN }) => break,
                Err(ffmpeg::Error::Eof) => break,
                Err(e) => return Err(e),
            }
        }
    }

    // Flush decoder, filter, encoder
    decoder.send_eof()?;
    let mut decoded = frame::Audio::empty();
    loop {
        match decoder.receive_frame(&mut decoded) {
            Ok(()) => {
                decoded.set_pts(decoded.timestamp());
                graph.get("in").unwrap().source().add(&decoded)?;
            }
            Err(ffmpeg::Error::Other { errno: ffmpeg::error::EAGAIN }) => break,
            Err(ffmpeg::Error::Eof) => break,
            Err(e) => return Err(e),
        }
    }

    graph.get("in").unwrap().source().flush()?;
    let mut filtered = frame::Audio::empty();
    loop {
        match graph.get("out").unwrap().sink().frame(&mut filtered) {
            Ok(()) => encoder.send_frame(&filtered)?,
            Err(ffmpeg::Error::Other { errno: ffmpeg::error::EAGAIN }) => break,
            Err(ffmpeg::Error::Eof) => break,
            Err(e) => return Err(e),
        }
    }

    encoder.send_eof()?;
    let mut encoded = ffmpeg::Packet::empty();
    loop {
        match encoder.receive_packet(&mut encoded) {
            Ok(()) => {
                encoded.set_stream(0);
                encoded.rescale_ts(encoder_time_base, out_time_base);
                encoded.write_interleaved(&mut octx)?;
            }
            Err(ffmpeg::Error::Other { errno: ffmpeg::error::EAGAIN }) => break,
            Err(ffmpeg::Error::Eof) => break,
            Err(e) => return Err(e),
        }
    }

    octx.write_trailer()?;
    Ok(())
}
```

### Audio Processing Pipeline Pattern

For complex audio processing, use a pipeline pattern:

```rust
use ffmpeg::Rational;

struct AudioPipeline {
    decoder: ffmpeg::decoder::Audio,
    resampler: Option<ffmpeg::software::resampling::Context>,
    filter_graph: Option<ffmpeg::filter::Graph>,
    encoder: ffmpeg::encoder::Audio,
    // Time base tracking for proper timestamp conversion
    encoder_time_base: Rational,
}

impl AudioPipeline {
    /// Process a packet and return encoded packets ready for muxing
    /// - stream_index: output stream index to set on packets
    /// - out_time_base: output stream's time base for rescaling
    fn process_packet(
        &mut self,
        packet: &ffmpeg::Packet,
        stream_index: usize,
        out_time_base: Rational,
    ) -> Result<Vec<ffmpeg::Packet>, ffmpeg::Error> {
        let mut output_packets = Vec::new();

        self.decoder.send_packet(packet)?;

        let mut decoded = ffmpeg::frame::Audio::empty();
        // Proper error handling: EAGAIN means "need more input", not an error
        loop {
            match self.decoder.receive_frame(&mut decoded) {
                Ok(()) => {
                    // Optional: resample
                    let frame = if let Some(ref mut resampler) = self.resampler {
                        let mut resampled = ffmpeg::frame::Audio::empty();
                        resampler.run(&decoded, &mut resampled)?;
                        resampled
                    } else {
                        decoded.clone()
                    };

                    // Optional: filter
                    let frame = if let Some(ref mut graph) = self.filter_graph {
                        graph.get("in").unwrap().source().add(&frame)?;
                        let mut filtered = ffmpeg::frame::Audio::empty();
                        match graph.get("out").unwrap().sink().frame(&mut filtered) {
                            Ok(()) => filtered,
                            Err(ffmpeg::Error::Other { errno: ffmpeg::error::EAGAIN }) => continue,
                            Err(ffmpeg::Error::Eof) => continue,
                            Err(e) => return Err(e),
                        }
                    } else {
                        frame
                    };

                    // Encode
                    self.encoder.send_frame(&frame)?;

                    let mut encoded = ffmpeg::Packet::empty();
                    loop {
                        match self.encoder.receive_packet(&mut encoded) {
                            Ok(()) => {
                                // Set stream index and rescale timestamps for muxing
                                encoded.set_stream(stream_index);
                                encoded.rescale_ts(self.encoder_time_base, out_time_base);
                                output_packets.push(encoded.clone());
                            }
                            Err(ffmpeg::Error::Other { errno: ffmpeg::error::EAGAIN }) => break,
                            Err(ffmpeg::Error::Eof) => break,
                            Err(e) => return Err(e),
                        }
                    }
                }
                Err(ffmpeg::Error::Other { errno: ffmpeg::error::EAGAIN }) => break,
                Err(ffmpeg::Error::Eof) => break,
                Err(e) => return Err(e),
            }
        }

        Ok(output_packets)
    }
}
```
