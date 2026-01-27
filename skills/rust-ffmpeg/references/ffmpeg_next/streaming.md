# ffmpeg-next: Network Streaming

**Detection Keywords**: rtmp input, hls input, network stream, rtmp read, stream pull, network protocol, http input
**Aliases**: network streaming, stream input, rtmp source

Network protocol support for streaming media over RTMP, HLS, and other protocols.

## Related Guides

| Guide | Content |
|-------|---------|
| [transcoding.md](transcoding.md) | Video transcoding, frame extraction |
| [output.md](output.md) | Container remuxing, hardware acceleration |
| [metadata.md](metadata.md) | Metadata reading, codec info |

## Overview

ffmpeg-next supports network protocols through FFmpeg's URL-based I/O. This enables reading from and writing to network streams.

**Important**: For network protocols (RTMP, HTTP, etc.), call `format::network::init()` once before opening network URLs.

## Reading from RTMP Stream

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{format, media, codec, frame};

fn read_rtmp_stream(rtmp_url: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;
    format::network::init();

    // Open RTMP input (e.g., "rtmp://server/app/stream")
    let mut ictx = format::input(rtmp_url)?;

    let video_stream = ictx.streams()
        .best(media::Type::Video)
        .ok_or(ffmpeg::Error::StreamNotFound)?;
    let video_index = video_stream.index();

    let context = codec::context::Context::from_parameters(video_stream.parameters())?;
    let mut decoder = context.decoder().video()?;

    let mut decoded = frame::Video::empty();

    for (stream, packet) in ictx.packets() {
        if stream.index() != video_index {
            continue;
        }

        decoder.send_packet(&packet)?;

        while decoder.receive_frame(&mut decoded).is_ok() {
            let pts = decoded.timestamp().unwrap_or(0);
            println!("Received frame at PTS: {}", pts);
            // Process live frame...
        }
    }

    Ok(())
}
```

## Writing to RTMP Stream

**⚠️ Codec Compatibility Warning**: RTMP/FLV format requires specific codecs:
- **Video**: H.264 (AVC) only
- **Audio**: AAC, MP3, or Speex

Stream copying (shown below) will **fail** if the input uses incompatible codecs (e.g., HEVC, VP9, Opus, FLAC). For production use, check codec compatibility and transcode if needed (see transcode example in video.md).

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{format, codec, encoder, media, frame, Dictionary, Packet, Rational};

fn push_to_rtmp(input_path: &str, rtmp_url: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;
    format::network::init();

    let mut ictx = format::input(input_path)?;
    // Force FLV format for RTMP output
    let mut octx = format::output_as(rtmp_url, "flv")?;

    let mut stream_mapping = vec![-1i32; ictx.nb_streams() as usize];
    let mut ist_time_bases = vec![Rational(0, 1); ictx.nb_streams() as usize];
    let mut ost_index = 0;

    for (ist_index, ist) in ictx.streams().enumerate() {
        let medium = ist.parameters().medium();
        if medium != media::Type::Video && medium != media::Type::Audio {
            continue;
        }

        // Check codec compatibility with FLV/RTMP
        let codec_id = ist.parameters().id();
        let is_compatible = match medium {
            media::Type::Video => codec_id == codec::Id::H264,
            media::Type::Audio => matches!(codec_id, codec::Id::AAC | codec::Id::MP3),
            _ => false,
        };

        if !is_compatible {
            eprintln!("Warning: Codec {:?} is not compatible with RTMP/FLV. Transcoding required.", codec_id);
            // In production, you should transcode here instead of stream copying
            // See the video transcoding examples for how to set up encoders
            return Err(ffmpeg::Error::InvalidData);
        }

        stream_mapping[ist_index] = ost_index;
        ist_time_bases[ist_index] = ist.time_base();
        ost_index += 1;

        // Stream copy (no transcoding) - only works with compatible codecs
        let mut ost = octx.add_stream(encoder::find(codec::Id::None))?;
        ost.set_parameters(ist.parameters());
        unsafe { (*ost.parameters().as_mut_ptr()).codec_tag = 0; }
    }

    octx.write_header()?;

    for (stream, mut packet) in ictx.packets() {
        let ist_index = stream.index();
        let ost_index = stream_mapping[ist_index];
        if ost_index < 0 { continue; }

        let ost = octx.stream(ost_index as usize).ok_or(ffmpeg::Error::StreamNotFound)?;
        packet.rescale_ts(ist_time_bases[ist_index], ost.time_base());
        packet.set_position(-1);
        packet.set_stream(ost_index as usize);
        packet.write_interleaved(&mut octx)?;
    }

    octx.write_trailer()?;
    Ok(())
}
```

## Writing HLS Output

**⚠️ Codec Compatibility Warning**: HLS format works best with specific codecs:
- **Video**: H.264 (AVC) or HEVC (H.265) - H.264 has widest compatibility
- **Audio**: AAC (most compatible), MP3, or AC-3

Stream copying (shown below) will **fail** if the input uses incompatible codecs (e.g., VP9, Opus, FLAC). For production use, check codec compatibility and transcode if needed (see transcode example in video.md).

```rust
extern crate ffmpeg_next as ffmpeg;

use ffmpeg::{format, codec, encoder, media, Rational, Dictionary};

fn create_hls_output(input_path: &str, output_playlist: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;

    let mut ictx = format::input(input_path)?;
    // Force HLS format
    let mut octx = format::output_as(output_playlist, "hls")?;

    // Set HLS options
    let mut opts = Dictionary::new();
    opts.set("hls_time", "10");           // Segment duration
    opts.set("hls_list_size", "6");       // Playlist entries
    opts.set("hls_flags", "delete_segments");

    let mut stream_mapping = vec![-1i32; ictx.nb_streams() as usize];
    let mut ist_time_bases = vec![Rational(0, 1); ictx.nb_streams() as usize];
    let mut ost_index = 0;

    for (ist_index, ist) in ictx.streams().enumerate() {
        let medium = ist.parameters().medium();
        if medium != media::Type::Video && medium != media::Type::Audio {
            continue;
        }

        // Check codec compatibility with HLS
        let codec_id = ist.parameters().id();
        let is_compatible = match medium {
            media::Type::Video => matches!(codec_id, codec::Id::H264 | codec::Id::HEVC),
            media::Type::Audio => matches!(codec_id, codec::Id::AAC | codec::Id::MP3 | codec::Id::AC3),
            _ => false,
        };

        if !is_compatible {
            eprintln!("Warning: Codec {:?} may not be compatible with HLS. Transcoding recommended.", codec_id);
            // In production, you should transcode here instead of stream copying
            // See the video transcoding examples for how to set up encoders
            return Err(ffmpeg::Error::InvalidData);
        }

        stream_mapping[ist_index] = ost_index;
        ist_time_bases[ist_index] = ist.time_base();
        ost_index += 1;

        // Stream copy (no transcoding) - only works with compatible codecs
        let mut ost = octx.add_stream(encoder::find(codec::Id::None))?;
        ost.set_parameters(ist.parameters());
        unsafe { (*ost.parameters().as_mut_ptr()).codec_tag = 0; }
    }

    octx.write_header_with(opts)?;

    for (stream, mut packet) in ictx.packets() {
        let ist_index = stream.index();
        let ost_index = stream_mapping[ist_index];
        if ost_index < 0 { continue; }

        let ost = octx.stream(ost_index as usize).ok_or(ffmpeg::Error::StreamNotFound)?;
        packet.rescale_ts(ist_time_bases[ist_index], ost.time_base());
        packet.set_position(-1);
        packet.set_stream(ost_index as usize);
        packet.write_interleaved(&mut octx)?;
    }

    octx.write_trailer()?;
    Ok(())
}
```

## Network Protocol Reference

| Protocol | URL Format | Common Options |
|----------|-----------|----------------|
| RTMP | `rtmp://server:1935/app/stream` | `-f flv` required |
| RTMPS | `rtmps://server/app/stream` | SSL enabled RTMP |
| HLS | `http://server/playlist.m3u8` (read) or file path (write) | `hls_time`, `hls_list_size` |
| HTTP | `http://server/video.mp4` | Supports range requests |
| UDP | `udp://host:port` | Low latency streaming |
| RTP | `rtp://host:port` | Real-time protocol |
| SRT | `srt://host:port` | Secure reliable transport |

## HLS Options Reference

| Option | Description | Example |
|--------|-------------|---------|
| `hls_time` | Segment duration in seconds | `"10"` |
| `hls_list_size` | Max playlist entries (0 = unlimited) | `"6"` |
| `hls_flags` | HLS-specific flags | `"delete_segments"` |
| `hls_segment_filename` | Segment filename pattern | `"segment_%03d.ts"` |
| `hls_base_url` | Base URL for segments | `"http://cdn.example.com/"` |
| `hls_playlist_type` | Playlist type (event/vod) | `"vod"` |

## RTMP Options Reference

| Option | Description | Example |
|--------|-------------|---------|
| `rtmp_live` | Live stream mode | `"live"` |
| `rtmp_buffer` | Buffer time in ms | `"3000"` |
| `rtmp_conn` | Connection parameters | AMF encoded |
| `rtmp_flashver` | Flash version string | `"LNX 9,0,124,2"` |
| `rtmp_swfurl` | SWF player URL | URL string |
| `rtmp_tcurl` | Target stream URL | URL string |

## Error Handling for Network Streams

```rust
fn handle_network_errors(url: &str) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;
    format::network::init();

    match format::input(url) {
        Ok(mut ictx) => {
            // Process stream...
            for (stream, packet) in ictx.packets() {
                // Handle packet
            }
            Ok(())
        }
        Err(ffmpeg::Error::Io) => {
            eprintln!("Network I/O error - check connection");
            Err(ffmpeg::Error::Io)
        }
        Err(ffmpeg::Error::InvalidData) => {
            eprintln!("Invalid stream data - check URL format");
            Err(ffmpeg::Error::InvalidData)
        }
        Err(e) => {
            eprintln!("Stream error: {}", e);
            Err(e)
        }
    }
}
```

## Reconnection Pattern

For robust streaming, implement reconnection logic:

```rust
fn stream_with_reconnect(url: &str, max_retries: u32) -> Result<(), ffmpeg::Error> {
    ffmpeg::init()?;
    format::network::init();

    let mut retries = 0;

    loop {
        match format::input(url) {
            Ok(mut ictx) => {
                retries = 0;  // Reset on successful connection

                for (stream, packet) in ictx.packets() {
                    // Process packet...
                }

                // Stream ended normally
                break Ok(());
            }
            Err(e) => {
                retries += 1;
                if retries > max_retries {
                    return Err(e);
                }

                eprintln!("Connection failed, retry {}/{}: {}", retries, max_retries, e);
                std::thread::sleep(std::time::Duration::from_secs(2));
            }
        }
    }
}
```

## Best Practices

1. **Always call `format::network::init()`**: Required before any network URL operations
2. **Use appropriate format**: RTMP requires FLV format (`output_as(url, "flv")`)
3. **Handle disconnections**: Implement reconnection logic for live streams
4. **Monitor latency**: For live streaming, monitor PTS/DTS for drift
5. **Buffer management**: Adjust buffer sizes for network conditions

## See Also

- [ez-ffmpeg streaming](../ez_ffmpeg/streaming.md) - Higher-level streaming APIs with embedded RTMP server
- [ffmpeg-sidecar streaming](../ffmpeg_sidecar/streaming.md) - CLI-style streaming without FFmpeg library installation
