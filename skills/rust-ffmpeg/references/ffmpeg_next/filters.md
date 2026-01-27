# ffmpeg-next: Filter Graph

**Detection Keywords**: filter graph, audio filter, video filter, filter chain, complex filter, abuffer, buffer
**Aliases**: filtergraph, filter pipeline, filter complex

FFmpeg filter graph for complex audio and video processing pipelines.

## Related Guides

| Guide | Content |
|-------|---------|
| [audio.md](audio.md) | Audio resampling, format conversion |
| [video.md](video.md) | Seeking, scaling context, timestamp management |
| [transcoding.md](transcoding.md) | Video transcoding, frame extraction |

## Overview

ffmpeg-next provides access to FFmpeg's powerful filter graph system for complex processing pipelines. Filters can be chained together to perform multiple operations in a single pass.

## Audio Filter Example

```rust
use ffmpeg::{filter, codec, frame};

fn create_audio_filter(
    decoder: &codec::decoder::Audio,
    encoder: &codec::encoder::Audio,
    filter_spec: &str,  // e.g., "atempo=1.2" or "volume=0.5"
) -> Result<filter::Graph, ffmpeg::Error> {
    let mut graph = filter::Graph::new();

    // Create input buffer
    let args = format!(
        "time_base={}:sample_rate={}:sample_fmt={}:channel_layout=0x{:x}",
        decoder.time_base(),
        decoder.rate(),
        decoder.format().name(),
        decoder.channel_layout().bits()
    );
    graph.add(&filter::find("abuffer").unwrap(), "in", &args)?;

    // Create output buffer
    graph.add(&filter::find("abuffersink").unwrap(), "out", "")?;

    // Configure output format
    {
        let mut out = graph.get("out").unwrap();
        out.set_sample_format(encoder.format());
        out.set_channel_layout(encoder.channel_layout());
        out.set_sample_rate(encoder.rate());
    }

    // Parse and validate filter
    graph.output("in", 0)?.input("out", 0)?.parse(filter_spec)?;
    graph.validate()?;

    // Set frame size for encoders that require fixed frame sizes
    // Check if encoder supports variable frame size; if not, set the required frame size
    if encoder.frame_size() > 0 {
        graph.get("out").unwrap().sink().set_frame_size(encoder.frame_size());
    }

    Ok(graph)
}

// Usage
let mut filtered = frame::Audio::empty();
graph.get("in").unwrap().source().add(&decoded_frame)?;

while graph.get("out").unwrap().sink().frame(&mut filtered).is_ok() {
    // Process filtered frame
}
```

## Video Filter Example

```rust
fn create_video_filter(
    decoder: &codec::decoder::Video,
    filter_spec: &str,  // e.g., "scale=1280:720" or "fps=30"
) -> Result<filter::Graph, ffmpeg::Error> {
    let mut graph = filter::Graph::new();

    // Get pixel format name safely
    let pix_fmt_name = decoder.format()
        .descriptor()
        .ok_or(ffmpeg::Error::InvalidData)?
        .name();

    // Create input buffer
    let args = format!(
        "video_size={}x{}:pix_fmt={}:time_base={}:pixel_aspect={}",
        decoder.width(),
        decoder.height(),
        pix_fmt_name,
        decoder.time_base(),
        decoder.aspect_ratio()
    );
    graph.add(&filter::find("buffer").unwrap(), "in", &args)?;

    // Create output buffer
    graph.add(&filter::find("buffersink").unwrap(), "out", "")?;

    // Parse and validate filter
    graph.output("in", 0)?.input("out", 0)?.parse(filter_spec)?;
    graph.validate()?;

    Ok(graph)
}
```

## Common Audio Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `volume` | Adjust volume | `volume=0.5` (50% volume) |
| `atempo` | Change tempo | `atempo=1.5` (1.5x speed) |
| `aresample` | Resample audio | `aresample=44100` |
| `loudnorm` | Normalize loudness | `loudnorm` |
| `lowpass` | Low-pass filter | `lowpass=f=3000` |
| `highpass` | High-pass filter | `highpass=f=200` |
| `aecho` | Add echo effect | `aecho=0.8:0.88:60:0.4` |
| `amix` | Mix audio streams | `amix=inputs=2` |
| `apad` | Pad audio with silence | `apad=pad_dur=2` |
| `atrim` | Trim audio | `atrim=start=10:end=20` |

## Common Video Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `scale` | Resize video | `scale=1280:720` |
| `fps` | Change frame rate | `fps=30` |
| `crop` | Crop video | `crop=640:480:0:0` |
| `rotate` | Rotate video | `rotate=PI/2` |
| `hflip` | Horizontal flip | `hflip` |
| `vflip` | Vertical flip | `vflip` |
| `overlay` | Overlay video | `overlay=10:10` |
| `drawtext` | Draw text | `drawtext=text='Hello':x=10:y=10` |
| `trim` | Trim video | `trim=start=10:end=20` |
| `setpts` | Modify timestamps | `setpts=0.5*PTS` (2x speed) |

## Complex Filter Chains

### Audio: Volume + Tempo Change

```rust
let filter_spec = "volume=0.8,atempo=1.25";
```

### Video: Scale + FPS + Crop

```rust
let filter_spec = "scale=1920:1080,fps=30,crop=1280:720:320:180";
```

### Audio Normalization Pipeline

```rust
let filter_spec = "loudnorm=I=-16:TP=-1.5:LRA=11";
```

## Processing Loop Pattern

```rust
use ffmpeg::Rational;

fn process_with_filter(
    decoder: &mut codec::decoder::Audio,
    encoder: &mut codec::encoder::Audio,
    graph: &mut filter::Graph,
    packet: &ffmpeg::Packet,
    stream_index: usize,           // Output stream index
    in_time_base: Rational,        // Encoder time base
    out_time_base: Rational,       // Output stream time base
) -> Result<Vec<ffmpeg::Packet>, ffmpeg::Error> {
    let mut output_packets = Vec::new();

    decoder.send_packet(packet)?;

    let mut decoded = frame::Audio::empty();
    // Proper error handling: EAGAIN means "need more input", not an error
    loop {
        match decoder.receive_frame(&mut decoded) {
            Ok(()) => {
                // Set PTS for filter graph
                decoded.set_pts(decoded.timestamp());

                // Add frame to filter graph
                graph.get("in").unwrap().source().add(&decoded)?;

                // Get filtered frames
                let mut filtered = frame::Audio::empty();
                loop {
                    match graph.get("out").unwrap().sink().frame(&mut filtered) {
                        Ok(()) => {
                            encoder.send_frame(&filtered)?;

                            let mut encoded = ffmpeg::Packet::empty();
                            loop {
                                match encoder.receive_packet(&mut encoded) {
                                    Ok(()) => {
                                        // IMPORTANT: Set stream index and rescale timestamps
                                        encoded.set_stream(stream_index);
                                        encoded.rescale_ts(in_time_base, out_time_base);
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
            }
            Err(ffmpeg::Error::Other { errno: ffmpeg::error::EAGAIN }) => break,
            Err(ffmpeg::Error::Eof) => break,
            Err(e) => return Err(e),
        }
    }

    Ok(output_packets)
}
```

## Flushing the Filter Graph

Always flush the filter graph at the end of processing:

```rust
fn flush_filter_graph(
    graph: &mut filter::Graph,
    encoder: &mut codec::encoder::Audio,
    stream_index: usize,           // Output stream index
    in_time_base: Rational,        // Encoder time base
    out_time_base: Rational,       // Output stream time base
) -> Result<Vec<ffmpeg::Packet>, ffmpeg::Error> {
    let mut output_packets = Vec::new();

    // Flush the source
    graph.get("in").unwrap().source().flush()?;

    // Get remaining filtered frames
    let mut filtered = frame::Audio::empty();
    loop {
        match graph.get("out").unwrap().sink().frame(&mut filtered) {
            Ok(()) => {
                encoder.send_frame(&filtered)?;

                let mut encoded = ffmpeg::Packet::empty();
                loop {
                    match encoder.receive_packet(&mut encoded) {
                        Ok(()) => {
                            // IMPORTANT: Set stream index and rescale timestamps
                            encoded.set_stream(stream_index);
                            encoded.rescale_ts(in_time_base, out_time_base);
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

    // Flush encoder
    encoder.send_eof()?;
    let mut encoded = ffmpeg::Packet::empty();
    loop {
        match encoder.receive_packet(&mut encoded) {
            Ok(()) => {
                // IMPORTANT: Set stream index and rescale timestamps
                encoded.set_stream(stream_index);
                encoded.rescale_ts(in_time_base, out_time_base);
                output_packets.push(encoded.clone());
            }
            Err(ffmpeg::Error::Other { errno: ffmpeg::error::EAGAIN }) => break,
            Err(ffmpeg::Error::Eof) => break,
            Err(e) => return Err(e),
        }
    }

    Ok(output_packets)
}
```

## Filter Graph Inspection

```rust
fn inspect_filter_graph(graph: &filter::Graph) {
    println!("Filter graph:");
    println!("  Inputs: {:?}", graph.get("in"));
    println!("  Outputs: {:?}", graph.get("out"));

    // Get filter graph description
    // graph.dump() - if available
}
```

## Best Practices

1. **Validate Early**: Always call `graph.validate()` after parsing to catch configuration errors
2. **Handle PTS**: Set `frame.set_pts(frame.timestamp())` before adding to filter graph
3. **Flush Properly**: Always flush source and encoder at end of processing
4. **Match Formats**: Ensure encoder format matches filter graph output format
5. **Error Handling**: Check for errors at each step of the pipeline
