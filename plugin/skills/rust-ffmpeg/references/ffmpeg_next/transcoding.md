# ffmpeg-next: Video Transcoding

**Detection Keywords**: transcode, transcoding, h264, x264, encode, encoder, frame extraction, dump frames, thumbnail, first frame, preview, poster
**Aliases**: video encode, convert video, extract frame, video thumbnail

Complete video processing examples: transcoding, frame extraction, and thumbnail generation.

## Table of Contents

- [Running the Examples](#running-the-examples)
- [Video Transcoding (H.264)](#1-video-transcoding-h264)
- [Frame Extraction](#2-frame-extraction-dump-frames)
- [High-Performance Thumbnail](#21-high-performance-first-frame-extraction-thumbnail)

## Related Guides

| Guide | Content |
|-------|---------|
| [video.md](video.md) | Seeking, scaling context, timestamp management |
| [output.md](output.md) | PNG/JPEG saving, container remuxing, hardware acceleration |

## Running the Examples

The following examples are complete, runnable programs. To run them:

1. Create a new Rust project: `cargo new ffmpeg_example && cd ffmpeg_example`
2. Add dependency: `cargo add ffmpeg-next`
3. Replace `src/main.rs` with the example code
4. Run with: `cargo run -- input.mp4 output.mp4` (adjust arguments per example)

## 1. Video Transcoding (H.264)

Full transcoding pipeline with encoder configuration:

**Usage**: `cargo run -- input.mp4 output.mp4`

**Expected Output**: Creates `output.mp4` with H.264 encoding, printing progress to stdout.

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{codec, decoder, encoder, format, frame, media, picture, Dictionary, Packet, Rational};
use ffmpeg::software::scaling::{Context as Scaler, Flags as ScalerFlags};
use std::collections::HashMap;

struct Transcoder {
    ost_index: usize,
    decoder: decoder::Video,
    encoder: encoder::Video,
    scaler: Option<Scaler>,
    input_time_base: Rational,
    encoder_time_base: Rational,  // Encoder's time base for proper rescaling
}

impl Transcoder {
    fn new(
        ist: &format::stream::Stream,
        octx: &mut format::context::Output,
        ost_index: usize,
        x264_opts: Dictionary,
    ) -> Result<Self, ffmpeg::Error> {
        let global_header = octx.format().flags().contains(format::Flags::GLOBAL_HEADER);

        // Setup decoder
        let decoder = codec::context::Context::from_parameters(ist.parameters())?
            .decoder()
            .video()?;

        // Setup encoder - H.264 requires YUV420P
        let codec = encoder::find(codec::Id::H264).ok_or(ffmpeg::Error::EncoderNotFound)?;
        let mut ost = octx.add_stream(codec)?;

        let mut enc = codec::context::Context::new_with_codec(codec)
            .encoder()
            .video()?;

        // H.264 typically requires YUV420P pixel format
        let encoder_format = format::Pixel::YUV420P;
        enc.set_height(decoder.height());
        enc.set_width(decoder.width());
        enc.set_aspect_ratio(decoder.aspect_ratio());
        enc.set_format(encoder_format);
        enc.set_frame_rate(decoder.frame_rate());
        // IMPORTANT: For video encoders, time_base should be the inverse of frame_rate
        // Using input stream time_base directly can cause timestamp issues
        let frame_rate = decoder.frame_rate().unwrap_or(Rational(30, 1));
        enc.set_time_base(Rational(frame_rate.1, frame_rate.0)); // 1/fps

        if global_header {
            enc.set_flags(codec::Flags::GLOBAL_HEADER);
        }

        let encoder = enc.open_with(x264_opts)?;
        ost.set_parameters(&encoder);

        // Create scaler if pixel format conversion is needed
        let scaler = if decoder.format() != encoder_format {
            Some(Scaler::get(
                decoder.format(),
                decoder.width(),
                decoder.height(),
                encoder_format,
                decoder.width(),
                decoder.height(),
                ScalerFlags::BILINEAR,
            )?)
        } else {
            None
        };

        Ok(Self {
            ost_index,
            decoder,
            encoder,
            scaler,
            input_time_base: ist.time_base(),
            encoder_time_base: Rational(frame_rate.1, frame_rate.0),
        })
    }

    fn transcode_packet(
        &mut self,
        packet: &Packet,
        octx: &mut format::context::Output,
        ost_time_base: Rational,
    ) -> Result<(), ffmpeg::Error> {
        self.decoder.send_packet(packet)?;

        let mut decoded = frame::Video::empty();
        while self.decoder.receive_frame(&mut decoded).is_ok() {
            let timestamp = decoded.timestamp();
            // Rescale timestamp from input stream time base to encoder time base
            let encoder_pts = timestamp.map(|pts| {
                pts.rescale(self.input_time_base, self.encoder_time_base)
            });

            // Convert pixel format if scaler exists
            let frame_to_encode = if let Some(ref mut scaler) = self.scaler {
                let mut converted = frame::Video::empty();
                scaler.run(&decoded, &mut converted)?;
                converted.set_pts(encoder_pts);
                converted
            } else {
                decoded.set_pts(encoder_pts);
                decoded.clone()
            };

            frame_to_encode.set_kind(picture::Type::None);
            self.encoder.send_frame(&frame_to_encode)?;
            self.write_encoded_packets(octx, ost_time_base)?;
        }
        Ok(())
    }

    fn flush(&mut self, octx: &mut format::context::Output, ost_time_base: Rational) -> Result<(), ffmpeg::Error> {
        self.decoder.send_eof()?;

        let mut decoded = frame::Video::empty();
        while self.decoder.receive_frame(&mut decoded).is_ok() {
            let timestamp = decoded.timestamp();
            // Rescale timestamp from input stream time base to encoder time base
            let encoder_pts = timestamp.map(|pts| {
                pts.rescale(self.input_time_base, self.encoder_time_base)
            });

            let frame_to_encode = if let Some(ref mut scaler) = self.scaler {
                let mut converted = frame::Video::empty();
                scaler.run(&decoded, &mut converted)?;
                converted.set_pts(encoder_pts);
                converted
            } else {
                decoded.set_pts(encoder_pts);
                decoded.clone()
            };

            frame_to_encode.set_kind(picture::Type::None);
            self.encoder.send_frame(&frame_to_encode)?;
            self.write_encoded_packets(octx, ost_time_base)?;
        }

        self.encoder.send_eof()?;
        self.write_encoded_packets(octx, ost_time_base)?;
        Ok(())
    }

    fn write_encoded_packets(
        &mut self,
        octx: &mut format::context::Output,
        ost_time_base: Rational,
    ) -> Result<(), ffmpeg::Error> {
        let mut encoded = Packet::empty();
        while self.encoder.receive_packet(&mut encoded).is_ok() {
            encoded.set_stream(self.ost_index);
            // IMPORTANT: Rescale from encoder time base (not input stream time base)
            encoded.rescale_ts(self.encoder_time_base, ost_time_base);
            encoded.write_interleaved(octx)?;
        }
        Ok(())
    }
}

fn transcode(input: &str, output: &str, preset: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input)?;
    let mut octx = format::output(output)?;

    // Parse x264 options
    let mut x264_opts = Dictionary::new();
    x264_opts.set("preset", preset);

    // Setup transcoders for video, copy other streams
    let mut transcoders = HashMap::new();
    let mut stream_mapping = vec![-1i32; ictx.nb_streams() as usize];
    let mut ost_index = 0usize;

    for (ist_index, ist) in ictx.streams().enumerate() {
        let medium = ist.parameters().medium();
        if medium != media::Type::Video && medium != media::Type::Audio {
            continue;
        }

        stream_mapping[ist_index] = ost_index as i32;

        if medium == media::Type::Video {
            transcoders.insert(
                ist_index,
                Transcoder::new(&ist, &mut octx, ost_index, x264_opts.clone())?,
            );
        } else {
            // Stream copy for audio
            let mut ost = octx.add_stream(encoder::find(codec::Id::None))?;
            ost.set_parameters(ist.parameters());
            unsafe { (*ost.parameters().as_mut_ptr()).codec_tag = 0; }
        }
        ost_index += 1;
    }

    octx.write_header()?;

    // Get output time bases after write_header
    let ost_time_bases: Vec<_> = octx.streams()
        .map(|s| s.time_base())
        .collect();

    // Process packets
    for (stream, packet) in ictx.packets() {
        let ist_index = stream.index();
        let ost_idx = stream_mapping[ist_index];
        if ost_idx < 0 { continue; }

        let ost_time_base = ost_time_bases[ost_idx as usize];

        if let Some(transcoder) = transcoders.get_mut(&ist_index) {
            transcoder.transcode_packet(&packet, &mut octx, ost_time_base)?;
        } else {
            // Stream copy
            let mut pkt = packet;
            pkt.rescale_ts(stream.time_base(), ost_time_base);
            pkt.set_stream(ost_idx as usize);
            pkt.write_interleaved(&mut octx)?;
        }
    }

    // Flush transcoders
    for (&ist_index, transcoder) in &mut transcoders {
        let ost_idx = stream_mapping[ist_index] as usize;
        transcoder.flush(&mut octx, ost_time_bases[ost_idx])?;
    }

    octx.write_trailer()?;
    Ok(())
}
```

## 2. Frame Extraction (Dump Frames)

Extract video frames and save as images:

**Usage**: `cargo run -- input.mp4 output_dir`

**Expected Output**: Creates PPM image files in output directory (frame1.ppm, frame2.ppm, etc.).

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::format::{input, Pixel};
use ffmpeg::media::Type;
use ffmpeg::software::scaling::{Context, Flags};
use ffmpeg::frame::Video;
use std::fs::File;
use std::io::Write;

fn extract_frames(input_path: &str, output_dir: &str) -> Result<usize, ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = input(input_path)?;
    let video_stream = ictx.streams()
        .best(Type::Video)
        .ok_or(ffmpeg::Error::StreamNotFound)?;
    let video_index = video_stream.index();

    let context = ffmpeg::codec::context::Context::from_parameters(video_stream.parameters())?;
    let mut decoder = context.decoder().video()?;

    // Create scaler for RGB output
    let mut scaler = Context::get(
        decoder.format(),
        decoder.width(),
        decoder.height(),
        Pixel::RGB24,
        decoder.width(),
        decoder.height(),
        Flags::BILINEAR,
    )?;

    let mut frame_index = 0;
    let mut decoded = Video::empty();
    let mut rgb_frame = Video::empty();

    for (stream, packet) in ictx.packets() {
        if stream.index() != video_index {
            continue;
        }

        decoder.send_packet(&packet)?;

        while decoder.receive_frame(&mut decoded).is_ok() {
            scaler.run(&decoded, &mut rgb_frame)?;

            // Save as PPM (simple uncompressed format)
            let path = format!("{}/frame{:04}.ppm", output_dir, frame_index);
            save_ppm(&rgb_frame, &path)?;

            frame_index += 1;
        }
    }

    // Flush decoder
    decoder.send_eof()?;
    while decoder.receive_frame(&mut decoded).is_ok() {
        scaler.run(&decoded, &mut rgb_frame)?;
        let path = format!("{}/frame{:04}.ppm", output_dir, frame_index);
        save_ppm(&rgb_frame, &path)?;
        frame_index += 1;
    }

    Ok(frame_index)
}

fn save_ppm(frame: &Video, path: &str) -> Result<(), std::io::Error> {
    let mut file = File::create(path)?;
    writeln!(file, "P6\n{} {}\n255", frame.width(), frame.height())?;

    // Write RGB data line by line (handle stride)
    let data = frame.data(0);
    let stride = frame.stride(0);
    let width = frame.width() as usize * 3;  // RGB24 = 3 bytes per pixel

    for y in 0..frame.height() as usize {
        let start = y * stride;
        file.write_all(&data[start..start + width])?;
    }

    Ok(())
}
```

## 2.1 High-Performance First Frame Extraction (Thumbnail)

Optimized for extracting only the first frame (thumbnail generation):

**Usage**: `cargo run -- input.mp4 thumbnail.ppm`

**Expected Output**: Creates a single thumbnail image from the first video frame.

**Performance Optimizations**:
- Stops immediately after first frame is decoded
- Uses `FAST_BILINEAR` for speed over quality
- Returns raw frame data for flexible output handling

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::format::{input, Pixel};
use ffmpeg::media::Type;
use ffmpeg::software::scaling::{Context as Scaler, Flags};
use ffmpeg::frame::Video;

/// Extract first frame from video with maximum performance
/// Returns RGB24 frame data, width, and height
pub fn extract_first_frame(input_path: &str) -> Result<(Vec<u8>, u32, u32), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = input(input_path)?;
    let video_stream = ictx.streams()
        .best(Type::Video)
        .ok_or(ffmpeg::Error::StreamNotFound)?;
    let video_index = video_stream.index();

    let context = ffmpeg::codec::context::Context::from_parameters(video_stream.parameters())?;
    let mut decoder = context.decoder().video()?;

    // Use FAST_BILINEAR for maximum speed
    let mut scaler = Scaler::get(
        decoder.format(),
        decoder.width(),
        decoder.height(),
        Pixel::RGB24,
        decoder.width(),
        decoder.height(),
        Flags::FAST_BILINEAR,
    )?;

    let mut decoded = Video::empty();
    let mut rgb_frame = Video::empty();

    // Process packets until first frame is decoded
    for (stream, packet) in ictx.packets() {
        if stream.index() != video_index {
            continue;
        }

        decoder.send_packet(&packet)?;

        // Check if we got a decoded frame
        if decoder.receive_frame(&mut decoded).is_ok() {
            scaler.run(&decoded, &mut rgb_frame)?;

            // Extract RGB data (handle stride)
            let width = rgb_frame.width() as usize;
            let height = rgb_frame.height() as usize;
            let stride = rgb_frame.stride(0);
            let data = rgb_frame.data(0);

            let mut rgb_data = Vec::with_capacity(width * height * 3);
            for y in 0..height {
                let start = y * stride;
                rgb_data.extend_from_slice(&data[start..start + width * 3]);
            }

            return Ok((rgb_data, rgb_frame.width(), rgb_frame.height()));
        }
    }

    Err(ffmpeg::Error::Eof)
}

/// Extract first frame with custom output dimensions (for smaller thumbnails)
pub fn extract_thumbnail(
    input_path: &str,
    target_width: u32,
    target_height: u32,
) -> Result<(Vec<u8>, u32, u32), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = input(input_path)?;
    let video_stream = ictx.streams()
        .best(Type::Video)
        .ok_or(ffmpeg::Error::StreamNotFound)?;
    let video_index = video_stream.index();

    let context = ffmpeg::codec::context::Context::from_parameters(video_stream.parameters())?;
    let mut decoder = context.decoder().video()?;

    // Scale down for thumbnail - FAST_BILINEAR is fastest
    let mut scaler = Scaler::get(
        decoder.format(),
        decoder.width(),
        decoder.height(),
        Pixel::RGB24,
        target_width,
        target_height,
        Flags::FAST_BILINEAR,
    )?;

    let mut decoded = Video::empty();
    let mut rgb_frame = Video::empty();

    for (stream, packet) in ictx.packets() {
        if stream.index() != video_index {
            continue;
        }

        decoder.send_packet(&packet)?;

        if decoder.receive_frame(&mut decoded).is_ok() {
            scaler.run(&decoded, &mut rgb_frame)?;

            let width = rgb_frame.width() as usize;
            let height = rgb_frame.height() as usize;
            let stride = rgb_frame.stride(0);
            let data = rgb_frame.data(0);

            let mut rgb_data = Vec::with_capacity(width * height * 3);
            for y in 0..height {
                let start = y * stride;
                rgb_data.extend_from_slice(&data[start..start + width * 3]);
            }

            return Ok((rgb_data, rgb_frame.width(), rgb_frame.height()));
        }
    }

    Err(ffmpeg::Error::Eof)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 {
        eprintln!("Usage: {} <input> <output.ppm>", args[0]);
        std::process::exit(1);
    }

    // Full resolution first frame
    let (rgb_data, width, height) = extract_first_frame(&args[1])?;

    // Save as PPM
    use std::io::Write;
    let mut file = std::fs::File::create(&args[2])?;
    writeln!(file, "P6\n{} {}\n255", width, height)?;
    file.write_all(&rgb_data)?;

    println!("Saved thumbnail: {}x{} -> {}", width, height, args[2]);
    Ok(())
}
```

**Performance Tips for Thumbnail Generation**:

| Technique | Benefit |
|-----------|---------|
| `Flags::FAST_BILINEAR` | Fastest scaling algorithm |
| Stop after first frame | No unnecessary decoding |
| Scale to smaller size | Less data to process |
| Reuse frame buffers | Avoid allocations |

**For batch thumbnail generation**, consider:
1. Reuse `ffmpeg::init()` (call once)
2. Process files in parallel with `rayon`
3. Use smaller target dimensions (e.g., 320x180)
