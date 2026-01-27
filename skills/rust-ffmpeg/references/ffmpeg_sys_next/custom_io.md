# ffmpeg-sys-next: Custom I/O

**Detection Keywords**: avio_alloc_context, custom io, memory buffer, read callback, write callback, seek callback, non-blocking io
**Aliases**: custom io, avio, memory stream

FFmpeg custom I/O for reading from memory buffers, network streams, or other non-file sources.

## Table of Contents

- [Related Guides](#related-guides)
- [Overview](#overview)
- [Callback Context Pattern](#callback-context-pattern)
- [Read Callback](#read-callback)
- [Write Callback](#write-callback)
- [Seek Callback](#seek-callback)
- [Complete Example: Memory Buffer](#complete-example-memory-buffer)
- [Non-Blocking I/O](#non-blocking-io)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

## Related Guides

| Guide | Content |
|-------|---------|
| [types.md](types.md) | Pixel formats, sample formats |
| [frame_codec.md](frame_codec.md) | Frame allocation, encode/decode |
| [../ffmpeg_sys_next.md](../ffmpeg_sys_next.md) | Core constants and error handling |

> **Dependencies**: Error and seek constants from [ffmpeg_sys_next.md](../ffmpeg_sys_next.md)

## Overview

Custom I/O allows FFmpeg to read/write from any data source by providing callback functions. The key function is `avio_alloc_context` which creates an I/O context with your callbacks.

> **When to use ffmpeg-sys-next custom I/O**:
> - Direct control over FFmpeg's internal buffer management
> - Integration with existing C/FFI code
> - Performance-critical scenarios requiring zero-copy operations
>
> For safe APIs, see [ez-ffmpeg custom I/O](../ez_ffmpeg/advanced.md).

## Callback Context Pattern

Use a concrete struct (not trait objects) for the opaque pointer to ensure correct memory layout:

```rust
use std::io::{Read, Write, Seek, SeekFrom, Cursor};

/// Context struct for custom I/O operations
/// Use concrete types, not trait objects, for FFI safety
struct IOContext {
    cursor: Cursor<Vec<u8>>,
    total_size: u64,
}

impl IOContext {
    fn new(data: Vec<u8>) -> Self {
        let total_size = data.len() as u64;
        Self {
            cursor: Cursor::new(data),
            total_size,
        }
    }
}
```

## Read Callback

```rust
use ffmpeg_sys_next::{AVERROR_EOF, EIO};

/// Custom read callback for FFmpeg I/O
/// Returns: bytes read on success, AVERROR on failure
///
/// # Safety
/// - `opaque` must point to a valid IOContext
/// - `buf` must be valid for writing `buf_size` bytes
unsafe extern "C" fn read_callback(
    opaque: *mut std::ffi::c_void,
    buf: *mut u8,
    buf_size: i32,
) -> i32 {
    if opaque.is_null() || buf.is_null() {
        return ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO);
    }

    let ctx = &mut *(opaque as *mut IOContext);
    let slice = std::slice::from_raw_parts_mut(buf, buf_size as usize);

    match ctx.cursor.read(slice) {
        Ok(0) => ffmpeg_sys_next::AVERROR_EOF,  // End of stream
        Ok(n) => n as i32,                       // Bytes read
        Err(_) => ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO),
    }
}
```

## Write Callback

```rust
use ffmpeg_sys_next::EIO;

/// Custom write callback for FFmpeg I/O
/// Returns: bytes written on success, AVERROR on failure
unsafe extern "C" fn write_callback(
    opaque: *mut std::ffi::c_void,
    buf: *const u8,
    buf_size: i32,
) -> i32 {
    if opaque.is_null() || buf.is_null() {
        return ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO);
    }

    let ctx = &mut *(opaque as *mut IOContext);
    let slice = std::slice::from_raw_parts(buf, buf_size as usize);

    match ctx.cursor.write_all(slice) {
        Ok(_) => buf_size,
        Err(_) => ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO),
    }
}
```

## Seek Callback

```rust
use ffmpeg_sys_next::{AVSEEK_SIZE, SEEK_SET, SEEK_CUR, SEEK_END, EIO, ESPIPE};

/// Custom seek callback for FFmpeg I/O
/// Returns: new position on success, AVERROR on failure
///
/// Important: Handle AVSEEK_SIZE to return total stream size
unsafe extern "C" fn seek_callback(
    opaque: *mut std::ffi::c_void,
    offset: i64,
    whence: i32,
) -> i64 {
    if opaque.is_null() {
        return ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO) as i64;
    }

    let ctx = &mut *(opaque as *mut IOContext);

    // Handle AVSEEK_SIZE: return total stream size
    if whence == ffmpeg_sys_next::AVSEEK_SIZE {
        return ctx.total_size as i64;
    }

    let seek_from = match whence {
        x if x == ffmpeg_sys_next::SEEK_SET => SeekFrom::Start(offset as u64),
        x if x == ffmpeg_sys_next::SEEK_CUR => SeekFrom::Current(offset),
        x if x == ffmpeg_sys_next::SEEK_END => SeekFrom::End(offset),
        _ => return ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::ESPIPE) as i64,
    };

    match ctx.cursor.seek(seek_from) {
        Ok(pos) => pos as i64,
        Err(_) => ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO) as i64,
    }
}
```

## Wiring Callbacks with avio_alloc_context

This is the critical step to connect your callbacks to FFmpeg:

```rust
use ffmpeg_sys_next::{
    avio_alloc_context, avio_context_free,
    avformat_alloc_context, avformat_open_input, avformat_close_input,
    AVFormatContext, AVIOContext, AVFMT_FLAG_CUSTOM_IO,
};

/// Create custom I/O context and wire it to AVFormatContext
unsafe fn setup_custom_io(data: Vec<u8>) -> Result<(*mut AVFormatContext, *mut IOContext), &'static str> {
    // 1. Allocate context struct on heap (must outlive FFmpeg usage)
    let ctx = Box::into_raw(Box::new(IOContext::new(data)));

    // 2. Allocate I/O buffer (FFmpeg takes ownership)
    let buffer_size: i32 = 4096;
    let buffer = ffmpeg_sys_next::av_malloc(buffer_size as usize) as *mut u8;
    if buffer.is_null() {
        let _ = Box::from_raw(ctx);  // Cleanup
        return Err("Failed to allocate I/O buffer");
    }

    // 3. Create AVIO context with callbacks
    let avio_ctx = avio_alloc_context(
        buffer,
        buffer_size,
        0,  // 0 = read-only, 1 = write
        ctx as *mut std::ffi::c_void,
        Some(read_callback),   // Read function
        None,                   // Write function (None for read-only)
        Some(seek_callback),   // Seek function
    );

    if avio_ctx.is_null() {
        ffmpeg_sys_next::av_free(buffer as *mut std::ffi::c_void);
        let _ = Box::from_raw(ctx);
        return Err("Failed to create AVIO context");
    }

    // 4. Create format context and attach custom I/O
    let fmt_ctx = avformat_alloc_context();
    if fmt_ctx.is_null() {
        let mut avio_ctx_mut = avio_ctx;
        avio_context_free(&mut avio_ctx_mut);
        let _ = Box::from_raw(ctx);
        return Err("Failed to allocate format context");
    }

    (*fmt_ctx).pb = avio_ctx;
    (*fmt_ctx).flags |= AVFMT_FLAG_CUSTOM_IO as i32;

    Ok((fmt_ctx, ctx))
}

/// Cleanup custom I/O resources
/// IMPORTANT: Order matters - close format context first, then free AVIO, then free user context last
unsafe fn cleanup_custom_io(mut fmt_ctx: *mut AVFormatContext, ctx: *mut IOContext) {
    if !fmt_ctx.is_null() {
        // Store AVIO context pointer before closing format context
        let mut avio_ctx = (*fmt_ctx).pb;

        // Close format context first (this may access pb internally)
        avformat_close_input(&mut fmt_ctx);

        // Then free AVIO context (buffer is freed automatically)
        if !avio_ctx.is_null() {
            avio_context_free(&mut avio_ctx);
        }
    }
    // Free our context last
    if !ctx.is_null() {
        let _ = Box::from_raw(ctx);
    }
}
```

## Non-Blocking Read Pattern

For async/event-driven sources (e.g., channels, queues):

```rust
use ffmpeg_sys_next::{AVERROR_EOF, EAGAIN};
use std::sync::mpsc::Receiver;

struct AsyncIOContext {
    receiver: Receiver<Vec<u8>>,
    buffer: Vec<u8>,
    position: usize,
}

/// Non-blocking read from channel
/// Returns AVERROR(EAGAIN) when no data available yet
unsafe extern "C" fn async_read_callback(
    opaque: *mut std::ffi::c_void,
    buf: *mut u8,
    buf_size: i32,
) -> i32 {
    if opaque.is_null() {
        return ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO);
    }

    let ctx = &mut *(opaque as *mut AsyncIOContext);

    // Try to get more data if buffer is empty
    if ctx.position >= ctx.buffer.len() {
        match ctx.receiver.try_recv() {
            Ok(data) => {
                ctx.buffer = data;
                ctx.position = 0;
            }
            Err(std::sync::mpsc::TryRecvError::Empty) => {
                // No data available yet, tell FFmpeg to retry
                return ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EAGAIN);
            }
            Err(std::sync::mpsc::TryRecvError::Disconnected) => {
                // Channel closed, signal EOF
                return ffmpeg_sys_next::AVERROR_EOF;
            }
        }
    }

    // Copy available data to output buffer
    let available = ctx.buffer.len() - ctx.position;
    let to_copy = available.min(buf_size as usize);
    std::ptr::copy_nonoverlapping(
        ctx.buffer[ctx.position..].as_ptr(),
        buf,
        to_copy,
    );
    ctx.position += to_copy;

    to_copy as i32
}
```

## Complete Memory Buffer Example

```rust
use std::io::{Cursor, Read, Seek, SeekFrom, Write};

struct MemoryIO {
    cursor: Cursor<Vec<u8>>,
    total_size: u64,
}

impl MemoryIO {
    fn new(data: Vec<u8>) -> Self {
        let total_size = data.len() as u64;
        Self {
            cursor: Cursor::new(data),
            total_size,
        }
    }

    fn new_writable(capacity: usize) -> Self {
        Self {
            cursor: Cursor::new(Vec::with_capacity(capacity)),
            total_size: 0,
        }
    }

    fn into_data(self) -> Vec<u8> {
        self.cursor.into_inner()
    }
}

unsafe extern "C" fn memory_read(
    opaque: *mut std::ffi::c_void,
    buf: *mut u8,
    buf_size: i32,
) -> i32 {
    if opaque.is_null() || buf.is_null() {
        return ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO);
    }

    let io = &mut *(opaque as *mut MemoryIO);
    let slice = std::slice::from_raw_parts_mut(buf, buf_size as usize);

    match io.cursor.read(slice) {
        Ok(0) => ffmpeg_sys_next::AVERROR_EOF,
        Ok(n) => n as i32,
        Err(_) => ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO),
    }
}

unsafe extern "C" fn memory_write(
    opaque: *mut std::ffi::c_void,
    buf: *const u8,
    buf_size: i32,
) -> i32 {
    if opaque.is_null() || buf.is_null() {
        return ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO);
    }

    let io = &mut *(opaque as *mut MemoryIO);
    let slice = std::slice::from_raw_parts(buf, buf_size as usize);

    match io.cursor.write_all(slice) {
        Ok(_) => {
            io.total_size = io.cursor.position().max(io.total_size);
            buf_size
        }
        Err(_) => ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO),
    }
}

unsafe extern "C" fn memory_seek(
    opaque: *mut std::ffi::c_void,
    offset: i64,
    whence: i32,
) -> i64 {
    if opaque.is_null() {
        return ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO) as i64;
    }

    let io = &mut *(opaque as *mut MemoryIO);

    if whence == ffmpeg_sys_next::AVSEEK_SIZE {
        return io.total_size as i64;
    }

    let seek_from = match whence {
        x if x == ffmpeg_sys_next::SEEK_SET => SeekFrom::Start(offset as u64),
        x if x == ffmpeg_sys_next::SEEK_CUR => SeekFrom::Current(offset),
        x if x == ffmpeg_sys_next::SEEK_END => SeekFrom::End(offset),
        _ => return ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::ESPIPE) as i64,
    };

    match io.cursor.seek(seek_from) {
        Ok(pos) => pos as i64,
        Err(_) => ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO) as i64,
    }
}
```

## Best Practices

1. **Use concrete structs**: Avoid `Box<dyn Trait>` for opaque pointers; use concrete structs for FFI safety
2. **Null checks**: Always validate opaque and buffer pointers at callback entry
3. **Error codes**: Return proper AVERROR codes, never raw `-1` or errno values
4. **AVSEEK_SIZE**: Always handle this to enable duration detection and seeking
5. **Buffer ownership**: The buffer passed to `avio_alloc_context` is owned by FFmpeg
6. **Cleanup order**: Close format context first, then free AVIO context, then free your context last
7. **Thread safety**: Ensure context data is thread-safe if callbacks may be called from multiple threads
8. **Non-blocking**: Return `AVERROR(EAGAIN)` for async sources when data isn't ready
9. **Buffer size**: Use 4096-32768 bytes; larger buffers reduce callback overhead

## RAII Wrapper

```rust
use ffmpeg_sys_next::{
    avio_alloc_context, avio_context_free, av_free,
    AVIOContext,
};

/// Safe RAII wrapper for custom I/O context
struct CustomIOGuard<T> {
    avio_ctx: *mut AVIOContext,
    user_ctx: *mut T,
}

impl<T> CustomIOGuard<T> {
    /// Create custom I/O with read-only callbacks
    unsafe fn new_read(
        user_ctx: T,
        buffer_size: i32,
        read_fn: unsafe extern "C" fn(*mut std::ffi::c_void, *mut u8, i32) -> i32,
        seek_fn: Option<unsafe extern "C" fn(*mut std::ffi::c_void, i64, i32) -> i64>,
    ) -> Result<Self, &'static str> {
        let user_ptr = Box::into_raw(Box::new(user_ctx));
        let buffer = ffmpeg_sys_next::av_malloc(buffer_size as usize) as *mut u8;

        if buffer.is_null() {
            let _ = Box::from_raw(user_ptr);
            return Err("Failed to allocate I/O buffer");
        }

        let avio_ctx = avio_alloc_context(
            buffer,
            buffer_size,
            0,  // read-only
            user_ptr as *mut std::ffi::c_void,
            Some(read_fn),
            None,
            seek_fn,
        );

        if avio_ctx.is_null() {
            av_free(buffer as *mut std::ffi::c_void);
            let _ = Box::from_raw(user_ptr);
            return Err("Failed to create AVIO context");
        }

        Ok(Self { avio_ctx, user_ctx: user_ptr })
    }

    fn as_ptr(&self) -> *mut AVIOContext {
        self.avio_ctx
    }

    fn user_ctx(&self) -> &T {
        unsafe { &*self.user_ctx }
    }
}

impl<T> Drop for CustomIOGuard<T> {
    fn drop(&mut self) {
        unsafe {
            if !self.avio_ctx.is_null() {
                avio_context_free(&mut self.avio_ctx);
            }
            if !self.user_ctx.is_null() {
                let _ = Box::from_raw(self.user_ctx);
            }
        }
    }
}
```

## Crossbeam Channel Pattern

For high-performance streaming with crossbeam channels:

```rust
use crossbeam_channel::{Receiver, TryRecvError};

struct ChannelIOContext {
    receiver: Receiver<Vec<u8>>,
    buffer: Vec<u8>,
    position: usize,
    eof: bool,
}

impl ChannelIOContext {
    fn new(receiver: Receiver<Vec<u8>>) -> Self {
        Self {
            receiver,
            buffer: Vec::new(),
            position: 0,
            eof: false,
        }
    }
}

/// Read callback for crossbeam channel source
unsafe extern "C" fn channel_read_callback(
    opaque: *mut std::ffi::c_void,
    buf: *mut u8,
    buf_size: i32,
) -> i32 {
    if opaque.is_null() || buf.is_null() {
        return ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EIO);
    }

    let ctx = &mut *(opaque as *mut ChannelIOContext);

    // Already reached EOF
    if ctx.eof && ctx.position >= ctx.buffer.len() {
        return ffmpeg_sys_next::AVERROR_EOF;
    }

    // Refill buffer if needed
    while ctx.position >= ctx.buffer.len() && !ctx.eof {
        match ctx.receiver.try_recv() {
            Ok(data) if data.is_empty() => {
                // Empty vec signals EOF from sender
                ctx.eof = true;
                return ffmpeg_sys_next::AVERROR_EOF;
            }
            Ok(data) => {
                ctx.buffer = data;
                ctx.position = 0;
                break;
            }
            Err(TryRecvError::Empty) => {
                // No data available, tell FFmpeg to retry
                return ffmpeg_sys_next::AVERROR(ffmpeg_sys_next::EAGAIN);
            }
            Err(TryRecvError::Disconnected) => {
                ctx.eof = true;
                return ffmpeg_sys_next::AVERROR_EOF;
            }
        }
    }

    // Copy available data
    let available = ctx.buffer.len() - ctx.position;
    let to_copy = available.min(buf_size as usize);

    std::ptr::copy_nonoverlapping(
        ctx.buffer[ctx.position..].as_ptr(),
        buf,
        to_copy,
    );
    ctx.position += to_copy;

    to_copy as i32
}
```

## Common Pitfalls

| Issue | Cause | Solution |
|-------|-------|----------|
| Crash on cleanup | Wrong cleanup order | Close format context first, then free AVIO, then free user context |
| Memory leak | Not freeing user context | Use RAII wrapper or explicit cleanup |
| Hang on read | Blocking in callback | Return EAGAIN for async sources |
| Invalid seeks | Not handling AVSEEK_SIZE | Always check for size query |
| Corruption | Shared mutable state | Use thread-safe data structures |
| Performance issues | Small buffer size | Use 8192+ bytes for streaming |

