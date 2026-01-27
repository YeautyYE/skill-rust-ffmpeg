# ffmpeg-sys-next Reference

**Detection Keywords**: unsafe bindings, raw FFmpeg, direct C API, zero-copy, FFI access, low-level control
**Aliases**: sys, ffi, unsafe ffmpeg, raw bindings

Raw FFI bindings providing direct access to FFmpeg C libraries for Rust applications.

**Crate**: https://crates.io/crates/ffmpeg-sys-next
**Documentation**: https://docs.rs/ffmpeg-sys-next

## Related Guides

| Guide | Content |
|-------|---------|
| [ez_ffmpeg.md](ez_ffmpeg.md) | High-level safe API (sync and async) |
| [ffmpeg_next.md](ffmpeg_next.md) | Medium-level safe bindings |
| [installation.md](installation.md) | Platform-specific setup |

## Overview

ffmpeg-sys-next provides low-level, unsafe bindings to FFmpeg's C API. Use this crate when you need:

- **Zero-copy operations** for maximum performance
- **Direct access** to FFmpeg internals not exposed by higher-level wrappers
- **Custom I/O callbacks** for streaming from non-file sources
- **Hardware acceleration** integration (NVIDIA, VideoToolbox, VA-API, QSV)
- **Fine-grained control** over frame/packet manipulation

> **Trade-off**: ffmpeg-sys-next requires `unsafe` code and manual memory management. Higher-level alternatives ([ez-ffmpeg](ez_ffmpeg.md), [ffmpeg-next](ffmpeg_next.md)) provide safe Rust APIs with some abstraction overhead.

## Sub-References

| File | Content |
|------|---------|
| [types.md](ffmpeg_sys_next/types.md) | Pixel formats, sample formats, channel layouts, media types |
| [custom_io.md](ffmpeg_sys_next/custom_io.md) | Custom I/O callbacks (read, write, seek, non-blocking) |
| [frame_codec.md](ffmpeg_sys_next/frame_codec.md) | Frame operations, scaling, resampling, encode/decode workflows |
| [hwaccel.md](ffmpeg_sys_next/hwaccel.md) | Hardware acceleration (NVIDIA, VideoToolbox, VA-API, QSV) |

## Initialization

```rust
use ffmpeg_sys_next::{avformat_network_init, avformat_network_deinit};

/// Initialize FFmpeg for network operations (required before using URLs)
unsafe fn init_ffmpeg() {
    avformat_network_init();
}

/// Cleanup network resources (call once at program end)
unsafe fn cleanup_ffmpeg() {
    avformat_network_deinit();
}
```

## Core Constants

### Error Handling

```rust
use ffmpeg_sys_next::{AVERROR, AVERROR_EOF, AVERROR_INVALIDDATA, av_strerror};

/// Convert POSIX errno to FFmpeg error code
fn to_averror(errno: i32) -> i32 {
    ffmpeg_sys_next::AVERROR(errno)
}

/// Common error codes
const EOF_ERROR: i32 = AVERROR_EOF;              // End of file/stream
const INVALID_DATA: i32 = AVERROR_INVALIDDATA;  // Invalid data found

/// Error codes from errno (re-exported by ffmpeg-sys-next)
const EAGAIN_ERROR: i32 = ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EAGAIN);  // Need more data
const EIO_ERROR: i32 = ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO);        // I/O error
const ESPIPE_ERROR: i32 = ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::ESPIPE);  // Illegal seek
const ENOMEM_ERROR: i32 = ffmpeg_sys_next::AVERROR(libc::ENOMEM);             // Out of memory

/// Check if operation should be retried (common in decode/encode loops)
fn should_retry(ret: i32) -> bool {
    ret == ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EAGAIN)
}

/// Check if end of stream reached
fn is_eof(ret: i32) -> bool {
    ret == AVERROR_EOF
}

/// Convert FFmpeg error code to human-readable string
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

### Time Constants

```rust
use ffmpeg_sys_next::{AV_NOPTS_VALUE, AV_TIME_BASE, AV_TIME_BASE_Q, AVRational};

/// No presentation timestamp available (0x8000000000000000)
const NO_PTS: i64 = AV_NOPTS_VALUE;

/// Default time base: 1/1000000 (microseconds)
const TIME_BASE: i32 = AV_TIME_BASE;  // 1000000

/// Time base as rational: {num: 1, den: 1000000}
fn time_base_rational() -> AVRational {
    AV_TIME_BASE_Q
}

/// Check if timestamp is valid
fn has_valid_pts(pts: i64) -> bool {
    pts != AV_NOPTS_VALUE
}

/// Convert PTS to seconds
unsafe fn pts_to_seconds(pts: i64, time_base: AVRational) -> f64 {
    if pts == AV_NOPTS_VALUE { return 0.0; }
    pts as f64 * ffmpeg_sys_next::av_q2d(time_base)
}
```

### Seek Constants

```rust
use ffmpeg_sys_next::{AVSEEK_SIZE, SEEK_SET, SEEK_CUR, SEEK_END};

/// Seek operations for custom I/O (see [custom_io.md](ffmpeg_sys_next/custom_io.md))
const SEEK_TO_START: i32 = SEEK_SET;      // Seek from beginning (0)
const SEEK_FROM_CURRENT: i32 = SEEK_CUR;  // Seek from current position (1)
const SEEK_FROM_END: i32 = SEEK_END;      // Seek from end (2)
const QUERY_SIZE: i32 = AVSEEK_SIZE;      // Query total size (0x10000)
```

## Rational Number Operations

FFmpeg uses rational numbers for time bases, frame rates, and aspect ratios.

```rust
use ffmpeg_sys_next::{AVRational, av_make_q, av_cmp_q, av_q2d, av_inv_q, av_rescale_q};

/// Create rational from numerator/denominator
fn create_rational(num: i32, den: i32) -> AVRational {
    AVRational { num, den }
}

/// Convert rational to double
unsafe fn rational_to_double(r: AVRational) -> f64 {
    av_q2d(r)
}

/// Invert rational (swap num/den)
unsafe fn invert_rational(r: AVRational) -> AVRational {
    av_inv_q(r)
}

/// Compare two rationals: returns -1, 0, or 1
unsafe fn compare_rationals(a: AVRational, b: AVRational) -> i32 {
    av_cmp_q(a, b)
}

/// Rescale timestamp between time bases
unsafe fn rescale_timestamp(pts: i64, src_tb: AVRational, dst_tb: AVRational) -> i64 {
    av_rescale_q(pts, src_tb, dst_tb)
}
```

## Stream Information

```rust
use ffmpeg_sys_next::{
    avformat_open_input, avformat_find_stream_info, avformat_close_input,
    av_find_best_stream, AVFormatContext, AVMediaType, AVCodecParameters,
};

/// Extract stream information from media file
unsafe fn get_stream_info(path: &str) -> Result<StreamInfo, &'static str> {
    let c_path = std::ffi::CString::new(path).map_err(|_| "Invalid path")?;
    let mut fmt_ctx: *mut AVFormatContext = std::ptr::null_mut();

    // Open input
    let ret = avformat_open_input(
        &mut fmt_ctx,
        c_path.as_ptr(),
        std::ptr::null_mut(),
        std::ptr::null_mut(),
    );
    if ret < 0 {
        return Err("Failed to open input");
    }

    // Read stream info
    let ret = avformat_find_stream_info(fmt_ctx, std::ptr::null_mut());
    if ret < 0 {
        avformat_close_input(&mut fmt_ctx);
        return Err("Failed to find stream info");
    }

    // Find best streams
    let video_idx = av_find_best_stream(
        fmt_ctx, AVMediaType::AVMEDIA_TYPE_VIDEO,
        -1, -1, std::ptr::null_mut(), 0,
    );
    let audio_idx = av_find_best_stream(
        fmt_ctx, AVMediaType::AVMEDIA_TYPE_AUDIO,
        -1, -1, std::ptr::null_mut(), 0,
    );

    let info = StreamInfo {
        duration_us: (*fmt_ctx).duration,
        nb_streams: (*fmt_ctx).nb_streams as i32,
        video_stream_idx: if video_idx >= 0 { Some(video_idx) } else { None },
        audio_stream_idx: if audio_idx >= 0 { Some(audio_idx) } else { None },
    };

    avformat_close_input(&mut fmt_ctx);
    Ok(info)
}

struct StreamInfo {
    duration_us: i64,
    nb_streams: i32,
    video_stream_idx: Option<i32>,
    audio_stream_idx: Option<i32>,
}
```

## Packet Reading Loop

```rust
use ffmpeg_sys_next::{
    av_read_frame, av_packet_alloc, av_packet_free, av_packet_unref,
    AVFormatContext, AVPacket, AVERROR_EOF,
};

/// Read packets from input (core decode loop pattern)
unsafe fn read_packets(
    fmt_ctx: *mut AVFormatContext,
    mut on_packet: impl FnMut(*const AVPacket, i32),  // packet, stream_index
) -> Result<(), i32> {
    let packet = av_packet_alloc();
    if packet.is_null() {
        return Err(ffmpeg_sys_next::AVERROR(libc::ENOMEM));
    }

    loop {
        let ret = av_read_frame(fmt_ctx, packet);
        if ret == AVERROR_EOF {
            break;  // End of file
        }
        if ret < 0 {
            av_packet_free(&mut (packet as *mut _));
            return Err(ret);
        }

        on_packet(packet, (*packet).stream_index);
        av_packet_unref(packet);
    }

    av_packet_free(&mut (packet as *mut _));
    Ok(())
}
```

## Safety Guidelines

### Memory Management

1. **Allocation pairs**: Every `av_*_alloc` needs corresponding `av_*_free`
2. **Reference counting**: Use `av_frame_ref`/`av_frame_unref` for shared frames
3. **Buffer ownership**: `av_frame_get_buffer` allocates, frame owns the buffer
4. **Null checks**: Always validate pointers returned from allocation functions
5. **Cleanup order**: Free in reverse allocation order on error paths

### Error Handling

1. **Check all return codes**: FFmpeg functions return negative on error
2. **Use AVERROR macros**: `AVERROR(errno)` for POSIX errors, `AVERROR_EOF` for end-of-stream
3. **Cleanup on error**: Free resources in reverse allocation order
4. **Propagate errors**: Don't silently ignore failures
5. **Use av_strerror**: Convert error codes to readable messages for debugging

### Thread Safety

1. **Context isolation**: Each thread should have its own codec context
2. **Shared frames**: Use reference counting for cross-thread frame sharing
3. **Global init**: FFmpeg internal structures are thread-safe after initialization
4. **Network init**: Call `avformat_network_init()` once before using network URLs
5. **Avoid global state**: Don't share codec contexts between threads

## When to Use vs Alternatives

| Task | ffmpeg-sys-next | ffmpeg-next | ez-ffmpeg |
|------|-----------------|-------------|-----------|
| Basic decode/encode | ❌ | ✅ | ✅ |
| Custom I/O callbacks | ✅ | Partial | ✅ |
| Zero-copy frame access | ✅ | ❌ | ❌ |
| Hardware acceleration | ✅ | Limited | ✅ |
| Audio resampling | ✅ | ✅ | ✅ |
| Video scaling | ✅ | ✅ | ✅ |
| Timestamp manipulation | ✅ | Partial | ✅ |
| Filter graphs | ❌ | ✅ | ✅ |
| Ease of use | ❌ | Moderate | ✅ |

**Decision guide**:
- **ez-ffmpeg**: Safe API, comprehensive features, async support
- **ffmpeg-next**: Safe API with FFmpeg semantics, frame-level control
- **ffmpeg-sys-next**: Direct FFI access, zero-copy operations, unavailable features

## Troubleshooting

### Common Issues

**Linker errors (undefined reference to av_*)**:
- FFmpeg development libraries not installed
- Wrong FFmpeg version (requires FFmpeg 7.x)
- Set `PKG_CONFIG_PATH` correctly for FFmpeg location

**Segfaults in unsafe code**:
- Null pointer dereference - always check allocation returns
- Use-after-free - ensure proper cleanup order
- Buffer overrun - validate sizes before writing
- Use Valgrind or AddressSanitizer to detect memory issues

**ABI mismatch panics**:
- FFmpeg version mismatch between compile and runtime
- Rebuild with matching FFmpeg headers and libraries
- Check `ffmpeg -version` matches expected version

**"Function not found" at runtime**:
- Dynamic linking issue - FFmpeg libs not in library path
- Set `LD_LIBRARY_PATH` (Linux) or `DYLD_LIBRARY_PATH` (macOS)
- On Windows, ensure FFmpeg DLLs are in PATH or app directory

**Memory leaks**:
- Missing `av_*_free` calls - use RAII wrappers
- Unref packets after processing: `av_packet_unref`
- Free frames properly: `av_frame_free`
