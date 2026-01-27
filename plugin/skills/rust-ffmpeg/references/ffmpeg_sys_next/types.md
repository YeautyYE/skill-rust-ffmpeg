# ffmpeg-sys-next: Types

**Detection Keywords**: pixel format, sample format, channel layout, yuv420p, rgb24, media type
**Aliases**: types, formats, pixel fmt

Type definitions for pixel formats, sample formats, channel layouts, and media types.

## Related Guides

| Guide | Content |
|-------|---------|
| [frame_codec.md](frame_codec.md) | Frame allocation, scaling, resampling |
| [hwaccel.md](hwaccel.md) | Hardware acceleration, GPU formats |
| [custom_io.md](custom_io.md) | Custom I/O callbacks |

> **Dependencies**: Core constants from [ffmpeg_sys_next.md](../ffmpeg_sys_next.md)

## Pixel Formats

```rust
use ffmpeg_sys_next::AVPixelFormat;

/// Common video pixel formats
const YUV420P: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_YUV420P;   // Most common, H.264/HEVC default
const YUV422P: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_YUV422P;   // Professional video
const YUV444P: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_YUV444P;   // Highest quality YUV
const NV12: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_NV12;         // Hardware decoder output
const NV21: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_NV21;         // Android camera format
const RGB24: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_RGB24;       // 8-bit RGB
const BGR24: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_BGR24;       // OpenCV compatible
const RGBA: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_RGBA;         // 8-bit RGBA with alpha
const BGRA: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_BGRA;         // Windows bitmap format
const GRAY8: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_GRAY8;       // Grayscale

/// Hardware-accelerated pixel formats (see [hwaccel.md](hwaccel.md))
const CUDA: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_CUDA;
const VAAPI: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_VAAPI;
const VIDEOTOOLBOX: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_VIDEOTOOLBOX;
const D3D11: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_D3D11;
const QSV: AVPixelFormat = AVPixelFormat::AV_PIX_FMT_QSV;

/// Check if format is hardware accelerated
fn is_hwaccel_format(fmt: AVPixelFormat) -> bool {
    matches!(fmt,
        AVPixelFormat::AV_PIX_FMT_CUDA |
        AVPixelFormat::AV_PIX_FMT_VAAPI |
        AVPixelFormat::AV_PIX_FMT_VIDEOTOOLBOX |
        AVPixelFormat::AV_PIX_FMT_D3D11 |
        AVPixelFormat::AV_PIX_FMT_DXVA2_VLD |
        AVPixelFormat::AV_PIX_FMT_QSV
    )
}

/// Check if format has alpha channel
fn has_alpha(fmt: AVPixelFormat) -> bool {
    matches!(fmt,
        AVPixelFormat::AV_PIX_FMT_RGBA |
        AVPixelFormat::AV_PIX_FMT_BGRA |
        AVPixelFormat::AV_PIX_FMT_ARGB |
        AVPixelFormat::AV_PIX_FMT_ABGR |
        AVPixelFormat::AV_PIX_FMT_YUVA420P |
        AVPixelFormat::AV_PIX_FMT_YUVA422P |
        AVPixelFormat::AV_PIX_FMT_YUVA444P
    )
}

/// Check if format is planar (separate planes for each component)
fn is_planar_video(fmt: AVPixelFormat) -> bool {
    matches!(fmt,
        AVPixelFormat::AV_PIX_FMT_YUV420P |
        AVPixelFormat::AV_PIX_FMT_YUV422P |
        AVPixelFormat::AV_PIX_FMT_YUV444P |
        AVPixelFormat::AV_PIX_FMT_YUVA420P |
        AVPixelFormat::AV_PIX_FMT_YUVA422P |
        AVPixelFormat::AV_PIX_FMT_YUVA444P
    )
}
```

## Sample Formats

```rust
use ffmpeg_sys_next::AVSampleFormat;

/// Common audio sample formats (interleaved)
const U8: AVSampleFormat = AVSampleFormat::AV_SAMPLE_FMT_U8;     // Unsigned 8-bit
const S16: AVSampleFormat = AVSampleFormat::AV_SAMPLE_FMT_S16;   // Signed 16-bit (CD quality)
const S32: AVSampleFormat = AVSampleFormat::AV_SAMPLE_FMT_S32;   // Signed 32-bit
const FLT: AVSampleFormat = AVSampleFormat::AV_SAMPLE_FMT_FLT;   // 32-bit float [-1.0, 1.0]
const DBL: AVSampleFormat = AVSampleFormat::AV_SAMPLE_FMT_DBL;   // 64-bit double
const S64: AVSampleFormat = AVSampleFormat::AV_SAMPLE_FMT_S64;   // Signed 64-bit

/// Planar formats (separate buffer per channel) - common codec output
const U8P: AVSampleFormat = AVSampleFormat::AV_SAMPLE_FMT_U8P;
const S16P: AVSampleFormat = AVSampleFormat::AV_SAMPLE_FMT_S16P;
const S32P: AVSampleFormat = AVSampleFormat::AV_SAMPLE_FMT_S32P;
const FLTP: AVSampleFormat = AVSampleFormat::AV_SAMPLE_FMT_FLTP;  // AAC, MP3 decoder output
const DBLP: AVSampleFormat = AVSampleFormat::AV_SAMPLE_FMT_DBLP;
const S64P: AVSampleFormat = AVSampleFormat::AV_SAMPLE_FMT_S64P;

/// Check if format is planar (separate planes per channel)
fn is_planar_audio(fmt: AVSampleFormat) -> bool {
    matches!(fmt,
        AVSampleFormat::AV_SAMPLE_FMT_U8P |
        AVSampleFormat::AV_SAMPLE_FMT_S16P |
        AVSampleFormat::AV_SAMPLE_FMT_S32P |
        AVSampleFormat::AV_SAMPLE_FMT_FLTP |
        AVSampleFormat::AV_SAMPLE_FMT_DBLP |
        AVSampleFormat::AV_SAMPLE_FMT_S64P
    )
}

/// Get bytes per sample for any format
fn bytes_per_sample(fmt: AVSampleFormat) -> usize {
    match fmt {
        AVSampleFormat::AV_SAMPLE_FMT_U8 | AVSampleFormat::AV_SAMPLE_FMT_U8P => 1,
        AVSampleFormat::AV_SAMPLE_FMT_S16 | AVSampleFormat::AV_SAMPLE_FMT_S16P => 2,
        AVSampleFormat::AV_SAMPLE_FMT_S32 | AVSampleFormat::AV_SAMPLE_FMT_S32P |
        AVSampleFormat::AV_SAMPLE_FMT_FLT | AVSampleFormat::AV_SAMPLE_FMT_FLTP => 4,
        AVSampleFormat::AV_SAMPLE_FMT_DBL | AVSampleFormat::AV_SAMPLE_FMT_DBLP |
        AVSampleFormat::AV_SAMPLE_FMT_S64 | AVSampleFormat::AV_SAMPLE_FMT_S64P => 8,
        _ => 0,
    }
}

/// Get packed equivalent of planar format
fn get_packed_format(fmt: AVSampleFormat) -> AVSampleFormat {
    match fmt {
        AVSampleFormat::AV_SAMPLE_FMT_U8P => AVSampleFormat::AV_SAMPLE_FMT_U8,
        AVSampleFormat::AV_SAMPLE_FMT_S16P => AVSampleFormat::AV_SAMPLE_FMT_S16,
        AVSampleFormat::AV_SAMPLE_FMT_S32P => AVSampleFormat::AV_SAMPLE_FMT_S32,
        AVSampleFormat::AV_SAMPLE_FMT_FLTP => AVSampleFormat::AV_SAMPLE_FMT_FLT,
        AVSampleFormat::AV_SAMPLE_FMT_DBLP => AVSampleFormat::AV_SAMPLE_FMT_DBL,
        AVSampleFormat::AV_SAMPLE_FMT_S64P => AVSampleFormat::AV_SAMPLE_FMT_S64,
        other => other,  // Already packed
    }
}
```

## Channel Layouts

FFmpeg 5.1+ uses `AVChannelLayout` instead of deprecated channel masks. Use `av_channel_layout_default` for standard configurations.

```rust
use ffmpeg_sys_next::{AVChannelLayout, AVChannelOrder, av_channel_layout_default, av_channel_layout_copy, av_channel_layout_uninit};

/// Create channel layout using FFmpeg's default for given channel count
/// This is the recommended approach for FFmpeg 5.1+
unsafe fn create_default_channel_layout(channels: i32) -> Result<AVChannelLayout, &'static str> {
    if channels <= 0 || channels > 64 {
        return Err("Invalid channel count (must be 1-64)");
    }

    let mut layout = std::mem::zeroed::<AVChannelLayout>();
    av_channel_layout_default(&mut layout, channels);

    // Verify layout was created successfully
    if layout.nb_channels != channels {
        return Err("Failed to create channel layout");
    }

    Ok(layout)
}

/// Copy channel layout (for passing to codec contexts)
unsafe fn copy_channel_layout(
    dst: *mut AVChannelLayout,
    src: *const AVChannelLayout,
) -> Result<(), &'static str> {
    let ret = av_channel_layout_copy(dst, src);
    if ret < 0 {
        return Err("Failed to copy channel layout");
    }
    Ok(())
}

/// Free channel layout resources
unsafe fn free_channel_layout(layout: *mut AVChannelLayout) {
    av_channel_layout_uninit(layout);
}

/// Common channel layout masks (for manual creation)
const MONO: u64 = ffmpeg_sys_next::AV_CH_LAYOUT_MONO;
const STEREO: u64 = ffmpeg_sys_next::AV_CH_LAYOUT_STEREO;
const SURROUND_2_1: u64 = ffmpeg_sys_next::AV_CH_LAYOUT_2POINT1;
const SURROUND_5_1: u64 = ffmpeg_sys_next::AV_CH_LAYOUT_5POINT1;
const SURROUND_7_1: u64 = ffmpeg_sys_next::AV_CH_LAYOUT_7POINT1;

/// Create channel layout from known mask (for specific configurations)
/// WARNING: Caller must ensure channels matches the popcount of mask
unsafe fn create_channel_layout_from_mask(mask: u64, channels: i32) -> Result<AVChannelLayout, &'static str> {
    if mask == 0 {
        return Err("Invalid channel mask");
    }

    // Validate that channels matches the number of bits set in mask
    let mask_channels = mask.count_ones() as i32;
    if channels != mask_channels {
        return Err("Channel count does not match mask");
    }

    Ok(AVChannelLayout {
        order: AVChannelOrder::AV_CHANNEL_ORDER_NATIVE,
        nb_channels: channels,
        u: ffmpeg_sys_next::AVChannelLayout__bindgen_ty_1 { mask },
        opaque: std::ptr::null_mut(),
    })
}

/// Example: Create stereo layout
unsafe fn create_stereo_layout() -> AVChannelLayout {
    create_channel_layout_from_mask(STEREO, 2).unwrap()
}

/// Example: Create mono layout
unsafe fn create_mono_layout() -> AVChannelLayout {
    create_channel_layout_from_mask(MONO, 1).unwrap()
}
```

### Channel Layout Comparison

| Approach | Use Case | Pros | Cons |
|----------|----------|------|------|
| `av_channel_layout_default` | Standard configs (stereo, 5.1) | Always valid, future-proof | Less control |
| Manual mask creation | Custom channel configurations | Full control | Must ensure mask/count match |

## Media Types

```rust
use ffmpeg_sys_next::AVMediaType;

/// Stream type identification
const VIDEO: AVMediaType = AVMediaType::AVMEDIA_TYPE_VIDEO;
const AUDIO: AVMediaType = AVMediaType::AVMEDIA_TYPE_AUDIO;
const SUBTITLE: AVMediaType = AVMediaType::AVMEDIA_TYPE_SUBTITLE;
const DATA: AVMediaType = AVMediaType::AVMEDIA_TYPE_DATA;
const ATTACHMENT: AVMediaType = AVMediaType::AVMEDIA_TYPE_ATTACHMENT;
const UNKNOWN: AVMediaType = AVMediaType::AVMEDIA_TYPE_UNKNOWN;

fn is_video_stream(media_type: AVMediaType) -> bool {
    media_type == AVMediaType::AVMEDIA_TYPE_VIDEO
}

fn is_audio_stream(media_type: AVMediaType) -> bool {
    media_type == AVMediaType::AVMEDIA_TYPE_AUDIO
}

fn is_subtitle_stream(media_type: AVMediaType) -> bool {
    media_type == AVMediaType::AVMEDIA_TYPE_SUBTITLE
}

fn media_type_name(media_type: AVMediaType) -> &'static str {
    match media_type {
        AVMediaType::AVMEDIA_TYPE_VIDEO => "video",
        AVMediaType::AVMEDIA_TYPE_AUDIO => "audio",
        AVMediaType::AVMEDIA_TYPE_SUBTITLE => "subtitle",
        AVMediaType::AVMEDIA_TYPE_DATA => "data",
        AVMediaType::AVMEDIA_TYPE_ATTACHMENT => "attachment",
        _ => "unknown",
    }
}
```

## Codec IDs

```rust
use ffmpeg_sys_next::AVCodecID;

/// Common video codecs
const H264: AVCodecID = AVCodecID::AV_CODEC_ID_H264;
const HEVC: AVCodecID = AVCodecID::AV_CODEC_ID_HEVC;  // H.265
const VP8: AVCodecID = AVCodecID::AV_CODEC_ID_VP8;
const VP9: AVCodecID = AVCodecID::AV_CODEC_ID_VP9;
const AV1: AVCodecID = AVCodecID::AV_CODEC_ID_AV1;
const MJPEG: AVCodecID = AVCodecID::AV_CODEC_ID_MJPEG;
const PNG: AVCodecID = AVCodecID::AV_CODEC_ID_PNG;
const RAWVIDEO: AVCodecID = AVCodecID::AV_CODEC_ID_RAWVIDEO;

/// Common audio codecs
const AAC: AVCodecID = AVCodecID::AV_CODEC_ID_AAC;
const MP3: AVCodecID = AVCodecID::AV_CODEC_ID_MP3;
const OPUS: AVCodecID = AVCodecID::AV_CODEC_ID_OPUS;
const VORBIS: AVCodecID = AVCodecID::AV_CODEC_ID_VORBIS;
const FLAC: AVCodecID = AVCodecID::AV_CODEC_ID_FLAC;
const PCM_S16LE: AVCodecID = AVCodecID::AV_CODEC_ID_PCM_S16LE;
const PCM_S24LE: AVCodecID = AVCodecID::AV_CODEC_ID_PCM_S24LE;
const PCM_F32LE: AVCodecID = AVCodecID::AV_CODEC_ID_PCM_F32LE;

/// Common subtitle codecs
const ASS: AVCodecID = AVCodecID::AV_CODEC_ID_ASS;
const SRT: AVCodecID = AVCodecID::AV_CODEC_ID_SUBRIP;
const WEBVTT: AVCodecID = AVCodecID::AV_CODEC_ID_WEBVTT;
```

## Buffer Size Calculation

```rust
use ffmpeg_sys_next::{av_samples_get_buffer_size, av_image_get_buffer_size, AVSampleFormat, AVPixelFormat};

/// Calculate required buffer size for audio samples
unsafe fn get_audio_buffer_size(
    channels: i32,
    nb_samples: i32,
    format: AVSampleFormat,
    align: i32,  // 0 for default, 1 for no alignment
) -> Result<i32, &'static str> {
    let mut linesize: i32 = 0;
    let size = av_samples_get_buffer_size(
        &mut linesize,
        channels,
        nb_samples,
        format,
        align,
    );

    if size < 0 {
        return Err("Failed to calculate audio buffer size");
    }

    Ok(size)
}

/// Calculate required buffer size for video frame
unsafe fn get_video_buffer_size(
    width: i32,
    height: i32,
    format: AVPixelFormat,
    align: i32,  // 1 for no alignment, 32 for SIMD
) -> Result<i32, &'static str> {
    let size = av_image_get_buffer_size(format, width, height, align);

    if size < 0 {
        return Err("Failed to calculate video buffer size");
    }

    Ok(size)
}
```

## Format Conversion Reference

### Pixel Format Conversion

| Source Format | Target Format | Common Use Case |
|---------------|---------------|-----------------|
| YUV420P | RGB24/RGBA | Display, image processing |
| NV12 | YUV420P | Hardware decoder → software encoder |
| RGB24 | YUV420P | Camera input → video encoding |
| RGBA | YUV420P/YUVA420P | Graphics overlay with alpha |
| BGR24 | RGB24 | OpenCV → FFmpeg |
| GRAY8 | YUV420P | Grayscale to video |

### Sample Format Conversion

| Source Format | Target Format | Common Use Case |
|---------------|---------------|-----------------|
| FLTP | S16 | AAC/MP3 decoder → PCM playback |
| S16 | FLTP | PCM input → AAC encoder |
| S32 | FLTP | High-quality audio processing |
| Any planar | Any interleaved | Audio playback APIs |
| Any interleaved | Any planar | Codec input requirements |
