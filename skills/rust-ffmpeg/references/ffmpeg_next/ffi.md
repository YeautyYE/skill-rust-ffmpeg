# ffmpeg-next: Low-Level FFI

**Detection Keywords**: ffi access, sys next, unsafe, raw pointer, av_frame, direct api, c api
**Aliases**: ffi, low level, unsafe access

Direct access to FFmpeg's C API through `ffmpeg_sys_next` for advanced operations.

## Related Guides

| Guide | Content |
|-------|---------|
| [video.md](video.md) | Seeking, scaling context, timestamp management |
| [audio.md](audio.md) | Audio resampling, format conversion |
| [../ffmpeg_sys_next.md](../ffmpeg_sys_next.md) | Raw FFI bindings reference |

## Overview

For operations requiring direct FFI access, use `ffmpeg_sys_next` alongside `ffmpeg_next`. This is useful when:
- You need fixed-size output buffers (audio FIFO)
- You need reference-counted frame sharing
- You need to copy properties atomically
- Performance profiling shows FFI is faster for your use case

## Basic FFI Usage

```rust
use ffmpeg_next::ffi::av_frame_get_buffer;
use ffmpeg_next::frame;

// Create a video frame and allocate buffer directly
let mut video_frame = frame::Video::empty();
video_frame.set_width(1920);
video_frame.set_height(1080);
video_frame.set_format(ffmpeg_next::format::Pixel::YUV420P);

unsafe {
    let frame_ptr = video_frame.as_mut_ptr();
    let ret = av_frame_get_buffer(frame_ptr, 0);  // 0 = default alignment
    if ret < 0 {
        return Err(ffmpeg_next::Error::from(ret));
    }
}
```

## Audio Frame Data Access

Access raw audio sample data for processing:

```rust
use ffmpeg_next::format::Sample;

fn process_audio_samples(frame: &ffmpeg_next::frame::Audio) {
    let format = frame.format();
    let channels = frame.channels() as usize;
    let samples = frame.samples();

    // Guard on sample format before casting
    match format {
        Sample::F32(_) => {
            // For planar formats (e.g., F32P), each channel is in separate plane
            if format.is_planar() {
                for ch in 0..channels {
                    let plane_data = frame.data(ch);
                    let samples_slice: &[f32] = unsafe {
                        std::slice::from_raw_parts(
                            plane_data.as_ptr() as *const f32,
                            samples
                        )
                    };
                    // Process samples_slice...
                }
            } else {
                // For packed formats, all channels interleaved in plane 0
                let plane_data = frame.data(0);
                let total_samples = samples * channels;
                let samples_slice: &[f32] = unsafe {
                    std::slice::from_raw_parts(
                        plane_data.as_ptr() as *const f32,
                        total_samples
                    )
                };
                // Process interleaved samples...
            }
        }
        Sample::I16(_) => {
            // Handle S16 format similarly with i16 slices
            let plane_data = frame.data(0);
            let total_samples = if format.is_planar() { samples } else { samples * channels };
            let samples_slice: &[i16] = unsafe {
                std::slice::from_raw_parts(
                    plane_data.as_ptr() as *const i16,
                    total_samples
                )
            };
            // Process i16 samples...
        }
        _ => {
            // Handle other formats or return error
            eprintln!("Unsupported sample format: {:?}", format);
        }
    }
}
```

## Advanced FFI Patterns

For scenarios requiring direct control over FFmpeg's C API, use `ffmpeg_sys_next` alongside `ffmpeg_next`.

### Frame Reference Copying (av_frame_ref)

Clone a frame by reference (increments refcount, shares underlying buffer):

```rust
use ffmpeg_next::frame::Frame;
use ffmpeg_sys_next::av_frame_ref;

/// Clone a frame by reference (efficient, shared buffer)
fn clone_frame_ref(src: &Frame) -> Result<Frame, String> {
    unsafe {
        let mut dst = Frame::empty();
        let ret = av_frame_ref(dst.as_mut_ptr(), src.as_ptr());
        if ret < 0 {
            return Err(format!("av_frame_ref failed: {}", ret));
        }
        Ok(dst)
    }
}
```

### Frame Property Copying (av_frame_copy_props)

Copy frame metadata without copying pixel/sample data:

```rust
use ffmpeg_next::frame::Frame;
use ffmpeg_sys_next::av_frame_copy_props;

/// Copy properties (pts, duration, etc.) from src to dst
fn copy_frame_properties(dst: &mut Frame, src: &Frame) -> Result<(), String> {
    unsafe {
        let ret = av_frame_copy_props(dst.as_mut_ptr(), src.as_ptr());
        if ret < 0 {
            return Err(format!("av_frame_copy_props failed: {}", ret));
        }
        Ok(())
    }
}
```

### Direct sws_scale for Custom Scaling

When you need more control than `scaler.run()` provides:

```rust
use ffmpeg_next::software::scaling::{Context as Scaler, Flags};
use ffmpeg_next::frame::Video;
use ffmpeg_sys_next::{sws_scale, av_frame_get_buffer, av_frame_copy_props, AVPixelFormat};

/// Scale frame with direct FFI control
fn scale_frame_ffi(
    scaler: &mut Scaler,
    src: &Video,
    dst_format: AVPixelFormat,
) -> Result<Video, String> {
    unsafe {
        let mut dst = Video::empty();

        // Copy properties from source
        let ret = av_frame_copy_props(dst.as_mut_ptr(), src.as_ptr());
        if ret < 0 {
            return Err(format!("Failed to copy props: {}", ret));
        }

        // Set output frame parameters
        (*dst.as_mut_ptr()).width = (*src.as_ptr()).width;
        (*dst.as_mut_ptr()).height = (*src.as_ptr()).height;
        (*dst.as_mut_ptr()).format = dst_format as i32;

        // Allocate buffer
        let ret = av_frame_get_buffer(dst.as_mut_ptr(), 0);
        if ret < 0 {
            return Err(format!("Failed to allocate buffer: {}", ret));
        }

        // Perform scaling
        let ret = sws_scale(
            scaler.as_mut_ptr(),
            (*src.as_ptr()).data.as_ptr() as *const *const _,
            (*src.as_ptr()).linesize.as_ptr(),
            0,
            (*src.as_ptr()).height,
            (*dst.as_mut_ptr()).data.as_mut_ptr(),  // Use as_mut_ptr() for output
            (*dst.as_mut_ptr()).linesize.as_mut_ptr(),
        );
        if ret <= 0 {
            return Err(format!("sws_scale failed: {}", ret));
        }

        Ok(dst)
    }
}
```

### Direct swr_convert for Audio Resampling

For fixed-size output buffers or FIFO-style resampling:

```rust
use ffmpeg_next::software::resampling::Context as Resampler;
use ffmpeg_next::frame::Frame;
use ffmpeg_sys_next::{swr_convert, swr_get_out_samples, av_frame_get_buffer, av_channel_layout_copy, AVSampleFormat, AVChannelLayout};

/// Resample with fixed output buffer size (FIFO-style)
/// IMPORTANT: target_layout is passed by reference to avoid copy issues
fn resample_fixed_output(
    resampler: &mut Resampler,
    src: &Frame,
    target_nb_samples: i32,
    target_format: AVSampleFormat,
    target_layout: &AVChannelLayout,  // Pass by reference
    target_rate: i32,
) -> Result<Vec<Frame>, String> {
    let mut output_frames = Vec::new();

    unsafe {
        // Feed input to resampler (output to null)
        let ret = swr_convert(
            resampler.as_mut_ptr(),
            std::ptr::null_mut(),
            0,
            (*src.as_ptr()).data.as_ptr() as *const *const _,
            (*src.as_ptr()).nb_samples,
        );
        if ret < 0 {
            return Err(format!("swr_convert input failed: {}", ret));
        }

        // Drain output in fixed-size chunks
        loop {
            let available = swr_get_out_samples(resampler.as_mut_ptr(), 0);
            if available < target_nb_samples {
                break;
            }

            let mut dst = Frame::empty();
            (*dst.as_mut_ptr()).sample_rate = target_rate;
            (*dst.as_mut_ptr()).format = target_format as i32;
            (*dst.as_mut_ptr()).nb_samples = target_nb_samples;
            // IMPORTANT: Use av_channel_layout_copy() to properly copy channel layout
            // Direct assignment can leak or double-free internal allocations
            let ret = av_channel_layout_copy(
                &mut (*dst.as_mut_ptr()).ch_layout,
                target_layout,
            );
            if ret < 0 {
                return Err(format!("av_channel_layout_copy failed: {}", ret));
            }

            let ret = av_frame_get_buffer(dst.as_mut_ptr(), 0);
            if ret < 0 {
                return Err(format!("av_frame_get_buffer failed: {}", ret));
            }

            let ret = swr_convert(
                resampler.as_mut_ptr(),
                (*dst.as_mut_ptr()).data.as_mut_ptr(),  // Use as_mut_ptr() for output
                target_nb_samples,
                std::ptr::null(),
                0,
            );
            if ret < 0 {
                return Err(format!("swr_convert output failed: {}", ret));
            }

            output_frames.push(dst);
        }
    }

    Ok(output_frames)
}
```

### Time Base Conversion with av_q2d

Convert FFmpeg Rational to floating-point seconds:

```rust
use ffmpeg_sys_next::av_q2d;
use ffmpeg_next::Rational;

/// Convert PTS to seconds using time_base
fn pts_to_seconds(pts: i64, time_base: Rational) -> f64 {
    unsafe {
        let tb = ffmpeg_sys_next::AVRational {
            num: time_base.numerator(),
            den: time_base.denominator(),
        };
        pts as f64 * av_q2d(tb)
    }
}

/// Get frame presentation time in seconds
/// IMPORTANT: Use the stream's time_base, NOT the frame's internal time_base
/// The frame's time_base field is often unset (0/0) or unreliable
fn frame_time_seconds(frame: &ffmpeg_next::frame::Frame, stream_time_base: Rational) -> Option<f64> {
    let pts = frame.pts()?;
    unsafe {
        let tb = ffmpeg_sys_next::AVRational {
            num: stream_time_base.numerator(),
            den: stream_time_base.denominator(),
        };
        Some(pts as f64 * av_q2d(tb))
    }
}

// Example usage:
// let stream = ictx.stream(stream_index)?;
// let time_in_seconds = frame_time_seconds(&frame, stream.time_base());
```

## Comparison: High-Level vs FFI Approaches

| Operation | High-Level API | FFI Approach | When to Use FFI |
|-----------|---------------|--------------|-----------------|
| Frame scaling | `scaler.run(&src, &mut dst)` | `sws_scale()` | Need custom buffer management |
| Audio resampling | `resampler.run(&src, &mut dst)` | `swr_convert()` | Fixed-size output buffers, FIFO control |
| Frame cloning | Clone trait (if available) | `av_frame_ref()` | Reference-counted sharing |
| Property copy | Manual field copy | `av_frame_copy_props()` | Copy all metadata atomically |
| Buffer alloc | `frame::Video::new()` | `av_frame_get_buffer()` | Custom format/dimensions |

## FFI Safety Guidelines

1. **Always check return values**: Negative values indicate errors
2. **Use unsafe blocks judiciously**: Only wrap the minimum necessary code
3. **Validate pointers**: Ensure frames are properly initialized before FFI calls
4. **Handle lifetime carefully**: FFI doesn't track Rust lifetimes
5. **Document unsafe code**: Explain why each unsafe block is necessary

## Common FFI Functions Reference

| Function | Purpose | Returns |
|----------|---------|---------|
| `av_frame_ref` | Reference-counted frame copy | 0 on success, <0 on error |
| `av_frame_copy_props` | Copy frame properties | 0 on success, <0 on error |
| `av_frame_get_buffer` | Allocate frame buffer | 0 on success, <0 on error |
| `sws_scale` | Perform video scaling | Height of output slice, <=0 on error |
| `swr_convert` | Perform audio resampling | Samples output, <0 on error |
| `swr_get_out_samples` | Get available output samples | Sample count |
| `av_q2d` | Convert Rational to double | Floating-point value |

## Best Practices

**Recommendation**: Use the high-level API when possible. Resort to FFI when:
- You need fixed-size output buffers (audio FIFO)
- You need reference-counted frame sharing
- You need to copy properties atomically
- Performance profiling shows FFI is faster for your use case
- You need custom I/O callbacks for special input sources

## Custom I/O Callbacks

For reading from non-standard sources (memory buffers, custom protocols, encrypted streams):

```rust
use ffmpeg_sys_next::{
    avio_alloc_context, avformat_open_input, avformat_alloc_context,
    AVSEEK_SIZE, AVFormatContext, AVIOContext,
};
use std::os::raw::{c_int, c_void};
use std::io::{Read, Seek, SeekFrom};

const BUFFER_SIZE: usize = 32768;

/// Read callback for custom I/O
unsafe extern "C" fn read_callback<R: Read>(
    opaque: *mut c_void,
    buf: *mut u8,
    buf_size: c_int,
) -> c_int {
    let reader = &mut *(opaque as *mut R);
    let buffer = std::slice::from_raw_parts_mut(buf, buf_size as usize);

    match reader.read(buffer) {
        Ok(0) => ffmpeg_sys_next::AVERROR_EOF,  // End of file
        Ok(n) => n as c_int,
        Err(_) => ffmpeg_sys_next::AVERROR(libc::EIO),
    }
}

/// Seek callback for custom I/O
unsafe extern "C" fn seek_callback<S: Seek>(
    opaque: *mut c_void,
    offset: i64,
    whence: c_int,
) -> i64 {
    let seeker = &mut *(opaque as *mut S);

    // Handle AVSEEK_SIZE: return total stream size
    if whence == AVSEEK_SIZE as c_int {
        // Get current position, seek to end, get position, restore
        let current = seeker.stream_position().unwrap_or(0);
        let end = seeker.seek(SeekFrom::End(0)).unwrap_or(0);
        let _ = seeker.seek(SeekFrom::Start(current));
        return end as i64;
    }

    let seek_from = match whence {
        0 => SeekFrom::Start(offset as u64),  // SEEK_SET
        1 => SeekFrom::Current(offset),       // SEEK_CUR
        2 => SeekFrom::End(offset),           // SEEK_END
        _ => return -1,
    };

    match seeker.seek(seek_from) {
        Ok(pos) => pos as i64,
        Err(_) => -1,
    }
}

/// Open input from custom Read+Seek source
fn open_custom_input<RS: Read + Seek + 'static>(
    mut source: RS,
) -> Result<*mut AVFormatContext, String> {
    unsafe {
        // Allocate buffer for AVIO context
        let buffer = ffmpeg_sys_next::av_malloc(BUFFER_SIZE) as *mut u8;
        if buffer.is_null() {
            return Err("Failed to allocate AVIO buffer".to_string());
        }

        // Box the source to get stable pointer
        let source_ptr = Box::into_raw(Box::new(source)) as *mut c_void;

        // Create AVIO context with callbacks
        let avio_ctx = avio_alloc_context(
            buffer,
            BUFFER_SIZE as c_int,
            0,  // write_flag = 0 (read-only)
            source_ptr,
            Some(read_callback::<RS>),
            None,  // write_packet (not needed for input)
            Some(seek_callback::<RS>),
        );

        if avio_ctx.is_null() {
            ffmpeg_sys_next::av_free(buffer as *mut c_void);
            let _ = Box::from_raw(source_ptr as *mut RS);
            return Err("Failed to create AVIO context".to_string());
        }

        // Create format context
        let mut fmt_ctx = avformat_alloc_context();
        if fmt_ctx.is_null() {
            ffmpeg_sys_next::av_free(buffer as *mut c_void);
            let _ = Box::from_raw(source_ptr as *mut RS);
            return Err("Failed to allocate format context".to_string());
        }

        // Assign custom AVIO to format context
        (*fmt_ctx).pb = avio_ctx;
        (*fmt_ctx).flags |= ffmpeg_sys_next::AVFMT_FLAG_CUSTOM_IO as c_int;

        // Open input
        let ret = avformat_open_input(
            &mut fmt_ctx,
            std::ptr::null(),  // No URL needed with custom I/O
            std::ptr::null_mut(),
            std::ptr::null_mut(),
        );

        if ret < 0 {
            // Cleanup on failure
            ffmpeg_sys_next::avformat_close_input(&mut fmt_ctx);
            let _ = Box::from_raw(source_ptr as *mut RS);
            return Err(format!("avformat_open_input failed: {}", ret));
        }

        Ok(fmt_ctx)
    }
}

/// CRITICAL: Proper cleanup for custom I/O contexts
/// When using custom AVIO, you MUST manually clean up resources
fn close_custom_input<RS>(fmt_ctx: *mut AVFormatContext) {
    unsafe {
        if fmt_ctx.is_null() {
            return;
        }

        // Get the AVIO context before closing
        let avio_ctx = (*fmt_ctx).pb;

        // Close the format context (does NOT free AVIO buffer with custom I/O)
        let mut fmt_ctx = fmt_ctx;
        ffmpeg_sys_next::avformat_close_input(&mut fmt_ctx);

        // Manually clean up AVIO resources
        if !avio_ctx.is_null() {
            // Recover the source from opaque pointer
            let source_ptr = (*avio_ctx).opaque;
            if !source_ptr.is_null() {
                // Drop the boxed source to release the Read+Seek resource
                let _ = Box::from_raw(source_ptr as *mut RS);
            }

            // Free the AVIO buffer (av_freep sets pointer to null)
            // Note: buffer may already be freed if avio_context_free is called
            // but with custom I/O, we're responsible for cleanup
            let buffer = (*avio_ctx).buffer;
            if !buffer.is_null() {
                ffmpeg_sys_next::av_free(buffer as *mut c_void);
            }

            // Free the AVIO context itself
            ffmpeg_sys_next::av_free(avio_ctx as *mut c_void);
        }
    }
}
```

**IMPORTANT Cleanup Notes for Custom I/O**:
- `avformat_close_input()` does NOT free AVIO buffer/context when using custom I/O
- You MUST track and free: the AVIO buffer, the AVIO context, and the opaque source
- Call cleanup in reverse order of allocation
- Consider using RAII wrapper to ensure cleanup on all exit paths

**Use Cases**:
- Reading from memory buffers (embedded resources)
- Encrypted or DRM-protected content
- Custom network protocols
- Virtualized file systems

## PTS/DTS Correction for Loop Playback

When looping video/audio, timestamps must be corrected to maintain continuity:

```rust
use ffmpeg_next::frame::Frame;
use ffmpeg_sys_next::AV_NOPTS_VALUE;
use std::sync::atomic::{AtomicI64, Ordering};

struct LoopTimestampCorrector {
    /// Base PTS offset for current loop iteration
    base_pts: AtomicI64,
    /// Base DTS offset for current loop iteration
    base_dts: AtomicI64,
    /// Last seen PTS (to detect loop boundary)
    last_pts: AtomicI64,
    /// Last seen DTS
    last_dts: AtomicI64,
    /// Duration of one loop iteration
    loop_duration: i64,
}

impl LoopTimestampCorrector {
    fn new(loop_duration: i64) -> Self {
        Self {
            base_pts: AtomicI64::new(0),
            base_dts: AtomicI64::new(0),
            last_pts: AtomicI64::new(0),
            last_dts: AtomicI64::new(0),
            loop_duration,
        }
    }

    /// Call when loop restarts (e.g., EOF detected and seeking back to start)
    fn on_loop_restart(&self) {
        // Add the loop duration to base offsets
        let new_base_pts = self.last_pts.load(Ordering::SeqCst) + 1;
        let new_base_dts = self.last_dts.load(Ordering::SeqCst) + 1;

        self.base_pts.store(new_base_pts, Ordering::SeqCst);
        self.base_dts.store(new_base_dts, Ordering::SeqCst);
    }

    /// Correct frame timestamps for seamless loop playback
    fn correct_frame(&self, frame: &mut Frame) {
        unsafe {
            let frame_ptr = frame.as_mut_ptr();

            // Correct PTS
            if (*frame_ptr).pts != AV_NOPTS_VALUE {
                (*frame_ptr).pts += self.base_pts.load(Ordering::SeqCst);
                self.last_pts.store((*frame_ptr).pts, Ordering::SeqCst);
            }

            // Correct DTS (pkt_dts for decoded frames)
            if (*frame_ptr).pkt_dts != AV_NOPTS_VALUE {
                (*frame_ptr).pkt_dts += self.base_dts.load(Ordering::SeqCst);
                self.last_dts.store((*frame_ptr).pkt_dts, Ordering::SeqCst);
            }
        }
    }
}

// Usage in a loop playback scenario
fn process_looped_frames(
    decoder: &mut ffmpeg_next::decoder::Video,
    corrector: &LoopTimestampCorrector,
) {
    let mut frame = ffmpeg_next::frame::Video::empty();

    loop {
        match decoder.receive_frame(&mut frame) {
            Ok(_) => {
                // IMPORTANT: Correct timestamps by directly modifying the raw frame
                // DO NOT use Frame::from_raw() as it takes ownership and would double-free
                unsafe {
                    let frame_ptr = frame.as_mut_ptr();

                    // Correct PTS
                    if (*frame_ptr).pts != AV_NOPTS_VALUE {
                        (*frame_ptr).pts += corrector.base_pts.load(Ordering::SeqCst);
                        corrector.last_pts.store((*frame_ptr).pts, Ordering::SeqCst);
                    }

                    // Correct DTS (pkt_dts for decoded frames)
                    if (*frame_ptr).pkt_dts != AV_NOPTS_VALUE {
                        (*frame_ptr).pkt_dts += corrector.base_dts.load(Ordering::SeqCst);
                        corrector.last_dts.store((*frame_ptr).pkt_dts, Ordering::SeqCst);
                    }
                }
                // Process frame with corrected timestamps...
            }
            Err(ffmpeg_next::Error::Eof) => {
                // Loop restart: seek back to beginning
                corrector.on_loop_restart();
                // decoder.flush() and seek back to start...
                continue;
            }
            Err(ffmpeg_next::Error::Other { errno: ffmpeg_sys_next::EAGAIN }) => {
                // Need more input packets
                break;
            }
            Err(e) => {
                eprintln!("Decode error: {:?}", e);
                break;
            }
        }
    }
}
```

**Key Points**:
- Track last PTS/DTS before loop boundary
- Add cumulative offset when loop restarts
- Handle `AV_NOPTS_VALUE` (-1) to avoid corrupting undefined timestamps
- Use atomic operations for thread-safe access in multi-threaded pipelines
