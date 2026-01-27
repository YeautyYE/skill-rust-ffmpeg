# ffmpeg-sys-next: Frame and Codec

**Detection Keywords**: av_frame_alloc, sws_scale, swr_convert, frame buffer, video scaling, audio resampling, decode loop, encode loop, AVPacket, packet free, av_packet_unref, memory management, NALU, NAL unit, bitstream, annex b, h264 parse
**Aliases**: frame ops, scaling sys, resampling sys, packet management, nalu extraction

Frame allocation, manipulation, video scaling, audio resampling, and encode/decode workflows.

## Table of Contents

- [Related Guides](#related-guides)
- [Frame Allocation](#frame-allocation)
- [Video Scaling (swscale)](#video-scaling-swscale)
- [Audio Resampling (swresample)](#audio-resampling-swresample)
- [Decode Loop](#decode-loop)
- [Encode Loop](#encode-loop)
- [Frame Copy and Reference](#frame-copy-and-reference)
- [Best Practices](#best-practices)

## Related Guides

| Guide | Content |
|-------|---------|
| [types.md](types.md) | Pixel formats, sample formats |
| [hwaccel.md](hwaccel.md) | Hardware acceleration |
| [custom_io.md](custom_io.md) | Custom I/O callbacks |

> **Dependencies**:
> - Core constants from [ffmpeg_sys_next.md](../ffmpeg_sys_next.md)
> - Type definitions from [types.md](types.md)

> **When to use ffmpeg-sys-next frame operations**:
> - Direct control over frame buffer allocation and layout
> - Custom scaling/resampling pipelines with specific algorithms
> - Zero-copy frame manipulation for performance-critical scenarios
> - Integration with existing C/FFI code
>
> For safe APIs, see [ez-ffmpeg](../ez_ffmpeg/advanced.md) or [ffmpeg-next](../ffmpeg_next/video.md).

## Frame Allocation

### Video Frame

```rust
use ffmpeg_sys_next::{
    av_frame_alloc, av_frame_free, av_frame_get_buffer,
    AVFrame, AVPixelFormat,
};

/// Allocate video frame with buffer
unsafe fn alloc_video_frame(
    width: i32,
    height: i32,
    format: AVPixelFormat,
) -> Result<*mut AVFrame, &'static str> {
    let frame = av_frame_alloc();
    if frame.is_null() {
        return Err("Failed to allocate frame");
    }

    (*frame).width = width;
    (*frame).height = height;
    (*frame).format = format as i32;

    // Allocate buffer with default alignment (0 = auto)
    let ret = av_frame_get_buffer(frame, 0);
    if ret < 0 {
        let mut frame_mut = frame;
        av_frame_free(&mut frame_mut);
        return Err("Failed to allocate frame buffer");
    }

    Ok(frame)
}
```

### Audio Frame

```rust
use ffmpeg_sys_next::{
    av_frame_alloc, av_frame_free, av_frame_get_buffer,
    av_channel_layout_default, AVFrame, AVSampleFormat,
};

/// Allocate audio frame with buffer
/// Uses av_channel_layout_default for proper channel layout initialization
unsafe fn alloc_audio_frame(
    nb_samples: i32,
    format: AVSampleFormat,
    channels: i32,
    sample_rate: i32,
) -> Result<*mut AVFrame, &'static str> {
    if channels <= 0 || channels > 64 {
        return Err("Invalid channel count");
    }

    let frame = av_frame_alloc();
    if frame.is_null() {
        return Err("Failed to allocate frame");
    }

    (*frame).nb_samples = nb_samples;
    (*frame).format = format as i32;
    (*frame).sample_rate = sample_rate;

    // Use av_channel_layout_default for proper channel layout
    av_channel_layout_default(&mut (*frame).ch_layout, channels);

    let ret = av_frame_get_buffer(frame, 0);
    if ret < 0 {
        let mut frame_mut = frame;
        av_frame_free(&mut frame_mut);
        return Err("Failed to allocate audio frame buffer");
    }

    Ok(frame)
}
```

## Frame Property Operations

```rust
use ffmpeg_sys_next::{
    av_frame_copy_props, av_frame_ref, av_frame_unref,
    av_frame_make_writable, AVFrame,
};

/// Copy frame properties (timestamps, metadata) without data
unsafe fn copy_frame_props(
    dst: *mut AVFrame,
    src: *const AVFrame,
) -> Result<(), &'static str> {
    let ret = av_frame_copy_props(dst, src);
    if ret < 0 {
        return Err("Failed to copy frame properties");
    }
    Ok(())
}

/// Create reference to frame (increments refcount, shares data)
unsafe fn ref_frame(
    dst: *mut AVFrame,
    src: *const AVFrame,
) -> Result<(), &'static str> {
    let ret = av_frame_ref(dst, src);
    if ret < 0 {
        return Err("Failed to reference frame");
    }
    Ok(())
}

/// Release frame reference
unsafe fn unref_frame(frame: *mut AVFrame) {
    av_frame_unref(frame);
}

/// Ensure frame is writable (may copy if shared)
/// Call this before modifying frame data that may be shared with other references.
/// If the frame is already writable, this is a no-op.
/// If the frame data is shared (refcount > 1), this allocates new buffers and copies data.
unsafe fn make_frame_writable(frame: *mut AVFrame) -> Result<(), &'static str> {
    let ret = av_frame_make_writable(frame);
    if ret < 0 {
        return Err("Failed to make frame writable");
    }
    Ok(())
}
```

## Timestamp Manipulation

```rust
use ffmpeg_sys_next::{AVFrame, AVRational, AV_NOPTS_VALUE};

/// Adjust frame timestamps for looping playback
unsafe fn adjust_loop_timestamps(
    frame: *mut AVFrame,
    base_pts: i64,
    base_dts: i64,
) {
    if base_pts != AV_NOPTS_VALUE && (*frame).pts != AV_NOPTS_VALUE {
        (*frame).pts += base_pts;
    }

    if base_dts != AV_NOPTS_VALUE && (*frame).pkt_dts != AV_NOPTS_VALUE {
        (*frame).pkt_dts += base_dts;
    }
}

/// Extract timing info from frame
unsafe fn get_frame_timing(frame: *const AVFrame) -> FrameTiming {
    FrameTiming {
        pts: (*frame).pts,
        dts: (*frame).pkt_dts,
        duration: (*frame).duration,
        time_base: (*frame).time_base,
    }
}

struct FrameTiming {
    pts: i64,
    dts: i64,
    duration: i64,
    time_base: AVRational,
}
```

## Video Scaling (sws_scale)

### Scaling Algorithm Selection

| Algorithm | Flag | Speed | Quality | Use Case |
|-----------|------|-------|---------|----------|
| Fast Bilinear | `SWS_FAST_BILINEAR` | Fastest | Low | Real-time preview, thumbnails |
| Bilinear | `SWS_BILINEAR` | Fast | Medium | General purpose, live streaming |
| Bicubic | `SWS_BICUBIC` | Medium | High | Transcoding, archival |
| Lanczos | `SWS_LANCZOS` | Slow | Highest | Professional quality, final output |
| Point | `SWS_POINT` | Fastest | Lowest | Pixel art, integer scaling |

```rust
use ffmpeg_sys_next::{
    sws_getContext, sws_scale, sws_freeContext,
    SwsContext, AVFrame, AVPixelFormat,
    SWS_FAST_BILINEAR, SWS_BILINEAR, SWS_BICUBIC, SWS_LANCZOS,
};

/// Create scaler context
unsafe fn create_scaler(
    src_w: i32, src_h: i32, src_fmt: AVPixelFormat,
    dst_w: i32, dst_h: i32, dst_fmt: AVPixelFormat,
    flags: i32,  // SWS_FAST_BILINEAR, SWS_BILINEAR, SWS_BICUBIC
) -> Result<*mut SwsContext, &'static str> {
    let ctx = sws_getContext(
        src_w, src_h, src_fmt,
        dst_w, dst_h, dst_fmt,
        flags,
        std::ptr::null_mut(),  // src filter
        std::ptr::null_mut(),  // dst filter
        std::ptr::null(),      // param
    );

    if ctx.is_null() {
        return Err("Failed to create scaler context");
    }

    Ok(ctx)
}

/// Scale video frame
unsafe fn scale_video_frame(
    scaler: *mut SwsContext,
    src: *const AVFrame,
    dst: *mut AVFrame,
) -> Result<i32, &'static str> {
    let ret = sws_scale(
        scaler,
        (*src).data.as_ptr() as *const *const u8,
        (*src).linesize.as_ptr(),
        0,                    // Source slice Y position
        (*src).height,        // Source slice height
        (*dst).data.as_mut_ptr(),
        (*dst).linesize.as_mut_ptr(),
    );

    if ret <= 0 {
        return Err("sws_scale failed");
    }

    Ok(ret)  // Returns number of output lines
}

/// Complete video scaling pipeline example
unsafe fn scale_frame_complete(
    src: *const AVFrame,
    dst_w: i32,
    dst_h: i32,
    dst_fmt: AVPixelFormat,
) -> Result<*mut AVFrame, &'static str> {
    // Create destination frame
    let dst = alloc_video_frame(dst_w, dst_h, dst_fmt)?;

    // Create scaler
    let scaler = create_scaler(
        (*src).width, (*src).height,
        std::mem::transmute((*src).format),
        dst_w, dst_h, dst_fmt,
        SWS_BICUBIC,
    )?;

    // Scale
    let ret = scale_video_frame(scaler, src, dst);
    sws_freeContext(scaler);

    if ret.is_err() {
        let mut dst_mut = dst;
        av_frame_free(&mut dst_mut);
        return Err("Scaling failed");
    }

    // Copy timestamps from source
    (*dst).pts = (*src).pts;
    (*dst).pkt_dts = (*src).pkt_dts;
    (*dst).duration = (*src).duration;

    Ok(dst)
}
```

## Audio Resampling (swr_convert)

### Resampler Setup

```rust
use ffmpeg_sys_next::{
    swr_alloc, swr_alloc_set_opts2, swr_init, swr_free,
    av_channel_layout_default,
    SwrContext, AVSampleFormat, AVChannelLayout,
};

/// Create and configure audio resampler
/// Uses av_channel_layout_default for proper channel layout initialization (FFmpeg 5.1+)
unsafe fn create_resampler(
    in_sample_rate: i32,
    in_format: AVSampleFormat,
    in_channels: i32,
    out_sample_rate: i32,
    out_format: AVSampleFormat,
    out_channels: i32,
) -> Result<*mut SwrContext, &'static str> {
    // Create channel layouts using av_channel_layout_default
    let mut in_ch_layout = std::mem::zeroed::<AVChannelLayout>();
    let mut out_ch_layout = std::mem::zeroed::<AVChannelLayout>();
    av_channel_layout_default(&mut in_ch_layout, in_channels);
    av_channel_layout_default(&mut out_ch_layout, out_channels);

    let mut swr_ctx: *mut SwrContext = std::ptr::null_mut();

    let ret = swr_alloc_set_opts2(
        &mut swr_ctx,
        &out_ch_layout,
        out_format,
        out_sample_rate,
        &in_ch_layout,
        in_format,
        in_sample_rate,
        0,  // log_offset
        std::ptr::null_mut(),  // log_ctx
    );

    if ret < 0 || swr_ctx.is_null() {
        return Err("Failed to allocate resampler");
    }

    let ret = swr_init(swr_ctx);
    if ret < 0 {
        swr_free(&mut swr_ctx);
        return Err("Failed to initialize resampler");
    }

    Ok(swr_ctx)
}
```

### Resampling Operations

```rust
use ffmpeg_sys_next::{
    swr_alloc_set_opts2, swr_init, swr_convert, swr_free,
    swr_get_delay, swr_get_out_samples, swr_drop_output,
    SwrContext,
};

/// Resample audio
unsafe fn resample_audio(
    resampler: *mut SwrContext,
    output: *mut *mut u8,
    out_samples: i32,
    input: *const *const u8,
    in_samples: i32,
) -> Result<i32, &'static str> {
    let ret = swr_convert(
        resampler,
        output,
        out_samples,
        input,
        in_samples,
    );

    if ret < 0 {
        return Err("swr_convert failed");
    }

    Ok(ret)  // Returns number of samples output
}

/// Query internal delay in resampler (samples buffered)
/// Use swr_get_delay with the input sample rate to get delay in input samples
unsafe fn get_resampler_delay(resampler: *mut SwrContext, in_sample_rate: i64) -> i64 {
    swr_get_delay(resampler, in_sample_rate)
}

/// Estimate output samples for given input
/// More accurate than swr_get_delay for output buffer sizing
unsafe fn get_estimated_output_samples(resampler: *mut SwrContext, in_samples: i32) -> i32 {
    swr_get_out_samples(resampler, in_samples)
}

/// Flush buffered samples without input
unsafe fn flush_resampler(
    resampler: *mut SwrContext,
    output: *mut *mut u8,
    out_samples: i32,
) -> i32 {
    swr_convert(
        resampler,
        output,
        out_samples,
        std::ptr::null(),  // No input
        0,                 // Zero input samples
    )
}

/// Drop samples from resampler buffer (for sync adjustment)
unsafe fn drop_resampler_samples(resampler: *mut SwrContext, count: i32) -> i32 {
    swr_drop_output(resampler, count)
}
```

## Decode Workflow

```rust
use ffmpeg_sys_next::{
    avcodec_send_packet, avcodec_receive_frame,
    av_frame_alloc, av_frame_free, av_frame_unref,
    AVCodecContext, AVPacket, AVFrame, AVERROR_EOF,
};
use libc::EAGAIN;

/// Decode packet to frames
///
/// # Safety
/// The callback receives a frame pointer that is only valid during the callback.
/// Do NOT store the pointer or use it after the callback returns.
/// If you need the frame data later, copy it or use av_frame_ref to create a reference.
unsafe fn decode_packet(
    ctx: *mut AVCodecContext,
    packet: *const AVPacket,
    mut on_frame: impl FnMut(*const AVFrame),
) -> Result<(), i32> {
    // Send packet to decoder
    let ret = avcodec_send_packet(ctx, packet);
    if ret < 0 {
        return Err(ret);
    }

    let frame = av_frame_alloc();
    if frame.is_null() {
        return Err(ffmpeg_sys_next::AVERROR(libc::ENOMEM));
    }

    // Receive all available frames
    loop {
        let ret = avcodec_receive_frame(ctx, frame);

        if ret == ffmpeg_sys_next::AVERROR(EAGAIN) {
            // Need more packets
            break;
        }
        if ret == AVERROR_EOF {
            // Decoder flushed
            break;
        }
        if ret < 0 {
            let mut frame_mut = frame;
            av_frame_free(&mut frame_mut);
            return Err(ret);
        }

        on_frame(frame);
        av_frame_unref(frame);
    }

    let mut frame_mut = frame;
    av_frame_free(&mut frame_mut);
    Ok(())
}

/// Flush decoder (call with NULL packet at end)
unsafe fn flush_decoder(
    ctx: *mut AVCodecContext,
    mut on_frame: impl FnMut(*const AVFrame),
) -> Result<(), i32> {
    decode_packet(ctx, std::ptr::null(), on_frame)
}
```

## Encode Workflow

```rust
use ffmpeg_sys_next::{
    avcodec_send_frame, avcodec_receive_packet,
    av_packet_alloc, av_packet_free, av_packet_unref,
    AVCodecContext, AVPacket, AVFrame, AVERROR_EOF,
};
use libc::EAGAIN;

/// Encode frame to packets
///
/// # Safety
/// The callback receives a packet pointer that is only valid during the callback.
/// Do NOT store the pointer or use it after the callback returns.
/// If you need the packet data later, copy it or use av_packet_ref to create a reference.
unsafe fn encode_frame(
    ctx: *mut AVCodecContext,
    frame: *const AVFrame,  // NULL to flush
    mut on_packet: impl FnMut(*const AVPacket),
) -> Result<(), i32> {
    // Send frame to encoder
    let ret = avcodec_send_frame(ctx, frame);
    if ret < 0 {
        return Err(ret);
    }

    let packet = av_packet_alloc();
    if packet.is_null() {
        return Err(ffmpeg_sys_next::AVERROR(libc::ENOMEM));
    }

    // Receive all available packets
    loop {
        let ret = avcodec_receive_packet(ctx, packet);

        if ret == ffmpeg_sys_next::AVERROR(EAGAIN) {
            break;
        }
        if ret == AVERROR_EOF {
            break;
        }
        if ret < 0 {
            let mut packet_mut = packet;
            av_packet_free(&mut packet_mut);
            return Err(ret);
        }

        on_packet(packet);
        av_packet_unref(packet);
    }

    let mut packet_mut = packet;
    av_packet_free(&mut packet_mut);
    Ok(())
}

/// Flush encoder (call with NULL frame at end)
unsafe fn flush_encoder(
    ctx: *mut AVCodecContext,
    mut on_packet: impl FnMut(*const AVPacket),
) -> Result<(), i32> {
    encode_frame(ctx, std::ptr::null(), on_packet)
}
```

## RAII Wrappers

### FrameGuard

```rust
use ffmpeg_sys_next::{av_frame_alloc, av_frame_free, AVFrame};

struct FrameGuard(*mut AVFrame);

impl FrameGuard {
    fn new() -> Option<Self> {
        let frame = unsafe { av_frame_alloc() };
        if frame.is_null() { None } else { Some(Self(frame)) }
    }

    fn as_ptr(&self) -> *const AVFrame { self.0 }
    fn as_mut_ptr(&mut self) -> *mut AVFrame { self.0 }
}

impl Drop for FrameGuard {
    fn drop(&mut self) {
        unsafe { av_frame_free(&mut self.0) }
    }
}
```

### PacketGuard

```rust
use ffmpeg_sys_next::{av_packet_alloc, av_packet_free, AVPacket};

struct PacketGuard(*mut AVPacket);

impl PacketGuard {
    fn new() -> Option<Self> {
        let packet = unsafe { av_packet_alloc() };
        if packet.is_null() { None } else { Some(Self(packet)) }
    }

    fn as_ptr(&self) -> *const AVPacket { self.0 }
    fn as_mut_ptr(&mut self) -> *mut AVPacket { self.0 }
}

impl Drop for PacketGuard {
    fn drop(&mut self) {
        unsafe { av_packet_free(&mut self.0) }
    }
}
```

### ScalerGuard

```rust
use ffmpeg_sys_next::{sws_freeContext, SwsContext};

struct ScalerGuard(*mut SwsContext);

impl ScalerGuard {
    fn new(ctx: *mut SwsContext) -> Option<Self> {
        if ctx.is_null() { None } else { Some(Self(ctx)) }
    }

    fn as_ptr(&self) -> *mut SwsContext { self.0 }
}

impl Drop for ScalerGuard {
    fn drop(&mut self) {
        unsafe { sws_freeContext(self.0) }
    }
}
```

### ResamplerGuard

```rust
use ffmpeg_sys_next::{swr_free, SwrContext};

struct ResamplerGuard(*mut SwrContext);

impl ResamplerGuard {
    fn new(ctx: *mut SwrContext) -> Option<Self> {
        if ctx.is_null() { None } else { Some(Self(ctx)) }
    }

    fn as_ptr(&self) -> *mut SwrContext { self.0 }
}

impl Drop for ResamplerGuard {
    fn drop(&mut self) {
        unsafe { swr_free(&mut self.0) }
    }
}
```

## Frame Data Access

### Video Frame Data Access

```rust
use ffmpeg_sys_next::{AVFrame, AVPixelFormat};

/// Access video frame plane data
/// Video frames have multiple planes depending on pixel format:
/// - YUV420P: Y (plane 0), U (plane 1), V (plane 2) - chroma half height
/// - YUV422P: Y (plane 0), U (plane 1), V (plane 2) - chroma full height
/// - YUV444P: Y (plane 0), U (plane 1), V (plane 2) - chroma full height
/// - NV12: Y (plane 0), UV interleaved (plane 1) - chroma half height
/// - RGB24/BGR24: Single plane (plane 0)
unsafe fn get_video_plane(
    frame: *const AVFrame,
    plane: usize,
) -> Option<&[u8]> {
    if plane >= 8 || (*frame).data[plane].is_null() {
        return None;
    }

    let format: AVPixelFormat = std::mem::transmute((*frame).format);
    let height = get_plane_height(format, (*frame).height as usize, plane);
    let linesize = (*frame).linesize[plane] as usize;
    let size = height * linesize;

    Some(std::slice::from_raw_parts((*frame).data[plane], size))
}

/// Access mutable video frame plane data
unsafe fn get_video_plane_mut(
    frame: *mut AVFrame,
    plane: usize,
) -> Option<&mut [u8]> {
    if plane >= 8 || (*frame).data[plane].is_null() {
        return None;
    }

    let format: AVPixelFormat = std::mem::transmute((*frame).format);
    let height = get_plane_height(format, (*frame).height as usize, plane);
    let linesize = (*frame).linesize[plane] as usize;
    let size = height * linesize;

    Some(std::slice::from_raw_parts_mut((*frame).data[plane], size))
}

/// Get plane height based on pixel format
/// Chroma subsampling affects plane heights:
/// - 4:2:0 (YUV420P, NV12): chroma height = luma height / 2
/// - 4:2:2 (YUV422P): chroma height = luma height
/// - 4:4:4 (YUV444P): chroma height = luma height
fn get_plane_height(format: AVPixelFormat, luma_height: usize, plane: usize) -> usize {
    if plane == 0 {
        return luma_height;
    }

    match format {
        // 4:2:0 formats - chroma half height
        AVPixelFormat::AV_PIX_FMT_YUV420P
        | AVPixelFormat::AV_PIX_FMT_YUVA420P
        | AVPixelFormat::AV_PIX_FMT_NV12
        | AVPixelFormat::AV_PIX_FMT_NV21 => (luma_height + 1) / 2,

        // 4:2:2 formats - chroma full height
        AVPixelFormat::AV_PIX_FMT_YUV422P
        | AVPixelFormat::AV_PIX_FMT_YUVA422P => luma_height,

        // 4:4:4 formats - chroma full height
        AVPixelFormat::AV_PIX_FMT_YUV444P
        | AVPixelFormat::AV_PIX_FMT_YUVA444P => luma_height,

        // Single plane formats (RGB, etc.) - no chroma planes
        _ => luma_height,
    }
}
```

### Audio Frame Data Access

```rust
use ffmpeg_sys_next::{AVFrame, AVSampleFormat};

/// Access audio frame samples for planar formats
/// Each channel is in a separate plane (data[0], data[1], etc.)
unsafe fn get_audio_plane_planar(
    frame: *const AVFrame,
    channel: usize,
) -> Option<&[u8]> {
    let nb_channels = (*frame).ch_layout.nb_channels as usize;
    if channel >= nb_channels || (*frame).data[channel].is_null() {
        return None;
    }

    let bytes_per_sample = match std::mem::transmute::<i32, AVSampleFormat>((*frame).format) {
        AVSampleFormat::AV_SAMPLE_FMT_U8P => 1,
        AVSampleFormat::AV_SAMPLE_FMT_S16P => 2,
        AVSampleFormat::AV_SAMPLE_FMT_S32P | AVSampleFormat::AV_SAMPLE_FMT_FLTP => 4,
        AVSampleFormat::AV_SAMPLE_FMT_DBLP | AVSampleFormat::AV_SAMPLE_FMT_S64P => 8,
        _ => return None,  // Not a planar format
    };

    let size = (*frame).nb_samples as usize * bytes_per_sample;
    Some(std::slice::from_raw_parts((*frame).data[channel], size))
}

/// Access audio frame samples for interleaved formats
/// All channels are interleaved in data[0]
unsafe fn get_audio_interleaved(frame: *const AVFrame) -> Option<&[u8]> {
    if (*frame).data[0].is_null() {
        return None;
    }

    let bytes_per_sample = match std::mem::transmute::<i32, AVSampleFormat>((*frame).format) {
        AVSampleFormat::AV_SAMPLE_FMT_U8 => 1,
        AVSampleFormat::AV_SAMPLE_FMT_S16 => 2,
        AVSampleFormat::AV_SAMPLE_FMT_S32 | AVSampleFormat::AV_SAMPLE_FMT_FLT => 4,
        AVSampleFormat::AV_SAMPLE_FMT_DBL | AVSampleFormat::AV_SAMPLE_FMT_S64 => 8,
        _ => return None,  // Not an interleaved format
    };

    let nb_channels = (*frame).ch_layout.nb_channels as usize;
    let size = (*frame).nb_samples as usize * nb_channels * bytes_per_sample;
    Some(std::slice::from_raw_parts((*frame).data[0], size))
}
```

## Error Conversion

```rust
use ffmpeg_sys_next::av_strerror;

fn averror_to_string(code: i32) -> String {
    let mut buf = [0i8; 256];
    unsafe {
        av_strerror(code, buf.as_mut_ptr(), buf.len());
        std::ffi::CStr::from_ptr(buf.as_ptr())
            .to_string_lossy()
            .into_owned()
    }
}
```

## NALU Extraction (H.264/H.265 Bitstream Parsing)

Extract NAL units from H.264/HEVC bitstreams for low-level analysis or custom processing.

### Parse Annex B NAL Units

```rust
use ffmpeg_sys_next::{
    av_bsf_alloc, av_bsf_free, av_bsf_get_by_name,
    av_bsf_init, av_bsf_receive_packet, av_bsf_send_packet,
    av_packet_alloc, av_packet_free, av_packet_unref,
    AVBSFContext, AVPacket,
};
use std::ffi::CString;

/// NALU type for H.264
#[derive(Debug, Clone, Copy)]
pub enum H264NaluType {
    Slice = 1,
    SliceA = 2,
    SliceB = 3,
    SliceC = 4,
    Idr = 5,        // Keyframe
    Sei = 6,
    Sps = 7,
    Pps = 8,
    Aud = 9,
    EndSeq = 10,
    EndStream = 11,
    FillerData = 12,
    Unknown(u8),
}

impl From<u8> for H264NaluType {
    fn from(val: u8) -> Self {
        match val & 0x1F {
            1 => H264NaluType::Slice,
            2 => H264NaluType::SliceA,
            3 => H264NaluType::SliceB,
            4 => H264NaluType::SliceC,
            5 => H264NaluType::Idr,
            6 => H264NaluType::Sei,
            7 => H264NaluType::Sps,
            8 => H264NaluType::Pps,
            9 => H264NaluType::Aud,
            10 => H264NaluType::EndSeq,
            11 => H264NaluType::EndStream,
            12 => H264NaluType::FillerData,
            n => H264NaluType::Unknown(n),
        }
    }
}

/// Parse NAL units from Annex B bitstream (00 00 00 01 or 00 00 01 start codes)
pub fn parse_annex_b_nalus(data: &[u8]) -> Vec<(usize, usize, H264NaluType)> {
    let mut nalus = Vec::new();
    let mut i = 0;

    while i < data.len() {
        // Find start code (00 00 00 01 or 00 00 01)
        let start_code_len = if i + 4 <= data.len()
            && data[i] == 0 && data[i + 1] == 0 && data[i + 2] == 0 && data[i + 3] == 1
        {
            4
        } else if i + 3 <= data.len()
            && data[i] == 0 && data[i + 1] == 0 && data[i + 2] == 1
        {
            3
        } else {
            i += 1;
            continue;
        };

        let nalu_start = i + start_code_len;

        // Find next start code or end of data
        let mut nalu_end = data.len();
        for j in nalu_start..data.len().saturating_sub(2) {
            if data[j] == 0 && data[j + 1] == 0
                && (data[j + 2] == 1 || (j + 3 < data.len() && data[j + 2] == 0 && data[j + 3] == 1))
            {
                nalu_end = j;
                break;
            }
        }

        if nalu_start < nalu_end {
            let nalu_type = H264NaluType::from(data[nalu_start]);
            nalus.push((nalu_start, nalu_end - nalu_start, nalu_type));
        }

        i = nalu_end;
    }

    nalus
}

/// Extract NALUs from packet using FFmpeg bitstream filter
unsafe fn extract_nalus_with_bsf(
    packet: *mut AVPacket,
) -> Result<Vec<Vec<u8>>, &'static str> {
    let filter_name = CString::new("h264_mp4toannexb").unwrap();
    let filter = av_bsf_get_by_name(filter_name.as_ptr());
    if filter.is_null() {
        return Err("BSF filter not found");
    }

    let mut bsf_ctx: *mut AVBSFContext = std::ptr::null_mut();
    if av_bsf_alloc(filter, &mut bsf_ctx) < 0 {
        return Err("Failed to allocate BSF context");
    }

    // Initialize BSF (in real code, set codecpar from input stream)
    if av_bsf_init(bsf_ctx) < 0 {
        av_bsf_free(&mut bsf_ctx);
        return Err("Failed to init BSF");
    }

    let mut nalus = Vec::new();
    let out_pkt = av_packet_alloc();

    if av_bsf_send_packet(bsf_ctx, packet) >= 0 {
        while av_bsf_receive_packet(bsf_ctx, out_pkt) >= 0 {
            let data = std::slice::from_raw_parts((*out_pkt).data, (*out_pkt).size as usize);
            for (start, len, _nalu_type) in parse_annex_b_nalus(data) {
                nalus.push(data[start..start + len].to_vec());
            }
            av_packet_unref(out_pkt);
        }
    }

    av_packet_free(&mut (out_pkt as *mut _));
    av_bsf_free(&mut bsf_ctx);
    Ok(nalus)
}
```

### Analyze NALU Types in Video

```rust
use ffmpeg_sys_next::{
    avformat_open_input, avformat_find_stream_info, avformat_close_input,
    av_read_frame, av_packet_unref, AVFormatContext, AVPacket, AVMEDIA_TYPE_VIDEO,
};
use std::collections::HashMap;
use std::ffi::CString;

unsafe fn analyze_nalu_distribution(path: &str) -> Result<HashMap<String, usize>, String> {
    let c_path = CString::new(path).map_err(|_| "Invalid path")?;
    let mut fmt_ctx: *mut AVFormatContext = std::ptr::null_mut();

    if avformat_open_input(&mut fmt_ctx, c_path.as_ptr(), std::ptr::null_mut(), std::ptr::null_mut()) < 0 {
        return Err("Failed to open input".to_string());
    }

    if avformat_find_stream_info(fmt_ctx, std::ptr::null_mut()) < 0 {
        avformat_close_input(&mut fmt_ctx);
        return Err("Failed to find stream info".to_string());
    }

    // Find video stream
    let mut video_stream_idx = -1i32;
    for i in 0..(*fmt_ctx).nb_streams {
        let stream = *(*fmt_ctx).streams.offset(i as isize);
        if (*(*stream).codecpar).codec_type == AVMEDIA_TYPE_VIDEO {
            video_stream_idx = i as i32;
            break;
        }
    }

    if video_stream_idx < 0 {
        avformat_close_input(&mut fmt_ctx);
        return Err("No video stream found".to_string());
    }

    let mut pkt: AVPacket = std::mem::zeroed();
    let mut nalu_counts: HashMap<String, usize> = HashMap::new();

    while av_read_frame(fmt_ctx, &mut pkt) >= 0 {
        if pkt.stream_index == video_stream_idx {
            let data = std::slice::from_raw_parts(pkt.data, pkt.size as usize);
            for (_start, _len, nalu_type) in parse_annex_b_nalus(data) {
                let type_name = format!("{:?}", nalu_type);
                *nalu_counts.entry(type_name).or_insert(0) += 1;
            }
        }
        av_packet_unref(&mut pkt);
    }

    avformat_close_input(&mut fmt_ctx);
    Ok(nalu_counts)
}
```

## Memory Management Best Practices

### Packet Lifecycle Management

```rust
use ffmpeg_sys_next::{
    av_packet_alloc, av_packet_free, av_packet_unref, av_packet_clone,
    av_packet_ref, av_packet_move_ref, AVPacket,
};

/// RAII wrapper for AVPacket
pub struct PacketGuard {
    ptr: *mut AVPacket,
}

impl PacketGuard {
    pub fn new() -> Option<Self> {
        let ptr = unsafe { av_packet_alloc() };
        if ptr.is_null() {
            None
        } else {
            Some(PacketGuard { ptr })
        }
    }

    pub fn as_ptr(&self) -> *mut AVPacket {
        self.ptr
    }

    /// Unreference packet data (release buffer, keep struct)
    pub fn unref(&mut self) {
        unsafe { av_packet_unref(self.ptr) };
    }

    /// Clone packet (deep copy)
    pub fn clone_packet(&self) -> Option<Self> {
        let cloned = unsafe { av_packet_clone(self.ptr) };
        if cloned.is_null() {
            None
        } else {
            Some(PacketGuard { ptr: cloned })
        }
    }
}

impl Drop for PacketGuard {
    fn drop(&mut self) {
        unsafe {
            av_packet_free(&mut self.ptr);
        }
    }
}

/// Efficient packet processing without memory leaks
unsafe fn process_packets_efficiently(fmt_ctx: *mut ffmpeg_sys_next::AVFormatContext) {
    let mut pkt = PacketGuard::new().expect("Failed to alloc packet");

    loop {
        // Read frame into packet
        let ret = ffmpeg_sys_next::av_read_frame(fmt_ctx, pkt.as_ptr());
        if ret < 0 {
            break;
        }

        // Process packet...

        // CRITICAL: Unref packet data before next read
        // This releases the buffer but keeps the packet struct
        pkt.unref();
    }
    // PacketGuard automatically frees on drop
}
```

### Context Reuse Pattern

```rust
use ffmpeg_sys_next::{
    avformat_open_input, avformat_close_input, avformat_find_stream_info,
    avcodec_alloc_context3, avcodec_free_context, avcodec_open2,
    avcodec_parameters_to_context, avcodec_flush_buffers,
    AVFormatContext, AVCodecContext, AVCodec,
};
use std::ffi::CString;

/// Reusable decoder context for processing multiple segments
pub struct ReusableDecoder {
    codec_ctx: *mut AVCodecContext,
    codec: *const AVCodec,
}

impl ReusableDecoder {
    /// Create decoder once, reuse for multiple files
    pub unsafe fn new(codec: *const AVCodec) -> Option<Self> {
        let codec_ctx = avcodec_alloc_context3(codec);
        if codec_ctx.is_null() {
            return None;
        }
        Some(ReusableDecoder { codec_ctx, codec })
    }

    /// Reset decoder for new input without reallocating
    pub unsafe fn reset_for_input(&mut self, fmt_ctx: *mut AVFormatContext, stream_idx: usize) -> Result<(), &'static str> {
        // Flush any buffered frames
        avcodec_flush_buffers(self.codec_ctx);

        // Copy parameters from new stream
        let stream = *(*fmt_ctx).streams.offset(stream_idx as isize);
        if avcodec_parameters_to_context(self.codec_ctx, (*stream).codecpar) < 0 {
            return Err("Failed to copy codec params");
        }

        // Reopen codec with new parameters
        if avcodec_open2(self.codec_ctx, self.codec, std::ptr::null_mut()) < 0 {
            return Err("Failed to open codec");
        }

        Ok(())
    }

    pub fn as_ptr(&self) -> *mut AVCodecContext {
        self.codec_ctx
    }
}

impl Drop for ReusableDecoder {
    fn drop(&mut self) {
        unsafe {
            avcodec_free_context(&mut self.codec_ctx);
        }
    }
}

/// Process multiple files efficiently by reusing contexts
unsafe fn process_multiple_files(paths: &[&str]) {
    // Find decoder once
    let codec = ffmpeg_sys_next::avcodec_find_decoder(ffmpeg_sys_next::AVCodecID::AV_CODEC_ID_H264);
    if codec.is_null() {
        return;
    }

    let mut decoder = ReusableDecoder::new(codec).expect("Failed to create decoder");

    for path in paths {
        let c_path = CString::new(*path).unwrap();
        let mut fmt_ctx: *mut AVFormatContext = std::ptr::null_mut();

        if avformat_open_input(&mut fmt_ctx, c_path.as_ptr(), std::ptr::null_mut(), std::ptr::null_mut()) < 0 {
            continue;
        }

        avformat_find_stream_info(fmt_ctx, std::ptr::null_mut());

        // Reset decoder for this file (no reallocation)
        if decoder.reset_for_input(fmt_ctx, 0).is_ok() {
            // Process frames...
        }

        avformat_close_input(&mut fmt_ctx);
    }
    // Decoder freed once at end
}
```

## Best Practices

1. **Always use RAII wrappers**: Use `FrameGuard`, `PacketGuard`, `ScalerGuard`, `ResamplerGuard` to prevent memory leaks
2. **Check writable before modify**: Call `av_frame_make_writable` before modifying shared frames
3. **Preserve timestamps**: Copy PTS/DTS when scaling or resampling to maintain sync
4. **Flush at end**: Call flush functions with NULL input at stream end to get buffered data
5. **Unref packets in loops**: Always call `av_packet_unref()` before reading next packet
6. **Reuse contexts when possible**: For batch processing, reuse codec contexts instead of reallocating
7. **Check return values**: All FFmpeg functions return negative values on error
5. **Reuse contexts**: Create scaler/resampler once and reuse for all frames with same parameters
6. **Check return values**: All FFmpeg functions return negative on error
7. **Handle EAGAIN**: Decoders/encoders may need multiple packets/frames before producing output
8. **Match formats**: Ensure input format matches what encoder/scaler/resampler expects
9. **Use appropriate alignment**: Default alignment (0) is usually best; use 1 for no alignment
10. **Free in reverse order**: Free frames/packets before their parent contexts

## Common Pitfalls

| Issue | Cause | Solution |
|-------|-------|----------|
| Memory leak | Not freeing frame/packet | Use RAII wrappers or ensure `av_*_free` called |
| Crash on write | Modifying shared frame | Call `av_frame_make_writable` first |
| Audio desync | Not flushing resampler | Call `flush_resampler` at stream end |
| Video artifacts | Wrong linesize | Use frame's linesize, not width × bytes_per_pixel |
| Decoder hang | Missing flush | Send NULL packet at end to flush decoder |
| Encoder hang | Missing flush | Send NULL frame at end to flush encoder |
| Wrong colors | Mismatched pixel format | Verify source and destination formats match |
| Silence gaps | Ignoring resampler delay | Use `swr_get_delay` to account for buffered samples |
| Timestamp jumps | Not copying timestamps | Copy PTS/DTS from source after processing |
| Use after free | Storing callback pointers | Copy frame data or use `av_frame_ref` |
| Channel mismatch | Wrong channel layout | Use `av_channel_layout_default` for channel count |
| Scaling quality | Using SWS_FAST_BILINEAR | Use SWS_BICUBIC or SWS_LANCZOS for quality |
