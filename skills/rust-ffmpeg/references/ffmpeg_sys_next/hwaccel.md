# ffmpeg-sys-next: Hardware Acceleration

**Detection Keywords**: gpu decode, gpu encode, cuvid, nvenc, videotoolbox hwaccel, vaapi, qsv, cuda frame, hw context
**Aliases**: hwaccel sys, gpu acceleration, hardware decode

Hardware-accelerated encoding and decoding using GPU capabilities.

## Table of Contents

- [Related Guides](#related-guides)
- [Hardware Types](#hardware-types)
- [GPU Detection](#gpu-detection)
- [Hardware Device Context](#hardware-device-context)
- [Hardware Frame Transfer](#hardware-frame-transfer)
- [Platform-Specific Examples](#platform-specific-examples)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

## Related Guides

| Guide | Content |
|-------|---------|
| [types.md](types.md) | Pixel formats, sample formats |
| [frame_codec.md](frame_codec.md) | Frame allocation, scaling |
| [../ez_ffmpeg/advanced.md](../ez_ffmpeg/advanced.md) | ez-ffmpeg hardware acceleration |

> **Dependencies**: Core constants from [ffmpeg_sys_next.md](../ffmpeg_sys_next.md)

> **When to use ffmpeg-sys-next hardware acceleration**:
> - Direct control over hardware device initialization
> - Custom frame transfer between GPU and CPU memory
> - Platform-specific optimizations not exposed by higher-level APIs

## Hardware Types

| Platform | Decoder | Encoder | Pixel Format |
|----------|---------|---------|--------------|
| NVIDIA (CUDA) | `h264_cuvid`, `hevc_cuvid` | `h264_nvenc`, `hevc_nvenc` | `AV_PIX_FMT_CUDA` |
| macOS (VideoToolbox) | `h264_videotoolbox` | `h264_videotoolbox`, `hevc_videotoolbox` | `AV_PIX_FMT_VIDEOTOOLBOX` |
| Linux (VA-API) | `h264_vaapi`, `hevc_vaapi` | `h264_vaapi`, `hevc_vaapi` | `AV_PIX_FMT_VAAPI` |
| Intel (QSV) | `h264_qsv`, `hevc_qsv` | `h264_qsv`, `hevc_qsv` | `AV_PIX_FMT_QSV` |
| AMD (AMF) | N/A | `h264_amf`, `hevc_amf` | N/A |

## GPU Detection

```rust
use ffmpeg_sys_next::{
    av_hwdevice_iterate_types, av_hwdevice_get_type_name,
    AVHWDeviceType,
};
use std::ffi::CStr;

/// Enumerate available hardware device types
unsafe fn list_hw_device_types() -> Vec<(AVHWDeviceType, String)> {
    let mut types = Vec::new();
    let mut hw_type = AVHWDeviceType::AV_HWDEVICE_TYPE_NONE;

    loop {
        hw_type = av_hwdevice_iterate_types(hw_type);
        if hw_type == AVHWDeviceType::AV_HWDEVICE_TYPE_NONE {
            break;
        }

        let name_ptr = av_hwdevice_get_type_name(hw_type);
        if !name_ptr.is_null() {
            let name = CStr::from_ptr(name_ptr).to_string_lossy().into_owned();
            types.push((hw_type, name));
        }
    }

    types
}

/// Check if a specific hardware type is available
unsafe fn is_hw_type_available(hw_type: AVHWDeviceType) -> bool {
    let types = list_hw_device_types();
    types.iter().any(|(t, _)| *t == hw_type)
}
```

## Platform-Specific Detection

```rust
use ffmpeg_sys_next::AVHWDeviceType;

/// Detect best available hardware acceleration for current platform
unsafe fn detect_best_hw_accel() -> Option<HWAccelInfo> {
    #[cfg(target_os = "macos")]
    {
        if is_hw_type_available(AVHWDeviceType::AV_HWDEVICE_TYPE_VIDEOTOOLBOX) {
            return Some(HWAccelInfo {
                device_type: AVHWDeviceType::AV_HWDEVICE_TYPE_VIDEOTOOLBOX,
                decoder_name: "h264_videotoolbox",
                encoder_name: "h264_videotoolbox",
            });
        }
    }

    #[cfg(target_os = "linux")]
    {
        // Try NVIDIA first, then VA-API
        if is_hw_type_available(AVHWDeviceType::AV_HWDEVICE_TYPE_CUDA) {
            return Some(HWAccelInfo {
                device_type: AVHWDeviceType::AV_HWDEVICE_TYPE_CUDA,
                decoder_name: "h264_cuvid",
                encoder_name: "h264_nvenc",
            });
        }
        if is_hw_type_available(AVHWDeviceType::AV_HWDEVICE_TYPE_VAAPI) {
            return Some(HWAccelInfo {
                device_type: AVHWDeviceType::AV_HWDEVICE_TYPE_VAAPI,
                decoder_name: "h264_vaapi",
                encoder_name: "h264_vaapi",
            });
        }
    }

    #[cfg(target_os = "windows")]
    {
        // Try NVIDIA, then Intel QSV
        if is_hw_type_available(AVHWDeviceType::AV_HWDEVICE_TYPE_CUDA) {
            return Some(HWAccelInfo {
                device_type: AVHWDeviceType::AV_HWDEVICE_TYPE_CUDA,
                decoder_name: "h264_cuvid",
                encoder_name: "h264_nvenc",
            });
        }
        if is_hw_type_available(AVHWDeviceType::AV_HWDEVICE_TYPE_QSV) {
            return Some(HWAccelInfo {
                device_type: AVHWDeviceType::AV_HWDEVICE_TYPE_QSV,
                decoder_name: "h264_qsv",
                encoder_name: "h264_qsv",
            });
        }
    }

    None
}

struct HWAccelInfo {
    device_type: AVHWDeviceType,
    decoder_name: &'static str,
    encoder_name: &'static str,
}
```

## Hardware Device Context

```rust
use ffmpeg_sys_next::{
    av_hwdevice_ctx_create, av_buffer_ref, av_buffer_unref,
    AVHWDeviceType, AVBufferRef,
};

/// Create hardware device context
unsafe fn create_hw_device_ctx(
    device_type: AVHWDeviceType,
    device: Option<&str>,  // e.g., "/dev/dri/renderD128" for VAAPI
) -> Result<*mut AVBufferRef, &'static str> {
    let mut hw_device_ctx: *mut AVBufferRef = std::ptr::null_mut();

    // Keep CString alive for the duration of the FFI call
    let device_cstring = device
        .map(|d| std::ffi::CString::new(d))
        .transpose()
        .map_err(|_| "Device path contains null byte")?;
    let device_ptr = device_cstring
        .as_ref()
        .map(|c| c.as_ptr())
        .unwrap_or(std::ptr::null());

    let ret = av_hwdevice_ctx_create(
        &mut hw_device_ctx,
        device_type,
        device_ptr,
        std::ptr::null_mut(),  // options
        0,                      // flags
    );

    if ret < 0 {
        return Err("Failed to create hardware device context");
    }

    Ok(hw_device_ctx)
}

/// Free hardware device context
unsafe fn free_hw_device_ctx(mut ctx: *mut AVBufferRef) {
    if !ctx.is_null() {
        av_buffer_unref(&mut ctx);
    }
}
```

## Hardware Decoder Setup

```rust
use ffmpeg_sys_next::{
    avcodec_find_decoder_by_name, avcodec_alloc_context3,
    avcodec_open2, avcodec_free_context,
    av_hwdevice_ctx_create, av_buffer_ref,
    AVCodecContext, AVHWDeviceType, AVBufferRef,
};
use std::ffi::CString;

/// Setup hardware-accelerated decoder
unsafe fn setup_hw_decoder(
    codec_name: &str,
    device_type: AVHWDeviceType,
) -> Result<(*mut AVCodecContext, *mut AVBufferRef), &'static str> {
    // Find hardware decoder
    let c_name = CString::new(codec_name).map_err(|_| "Invalid codec name")?;
    let codec = avcodec_find_decoder_by_name(c_name.as_ptr());
    if codec.is_null() {
        return Err("Hardware decoder not found");
    }

    // Allocate codec context
    let codec_ctx = avcodec_alloc_context3(codec);
    if codec_ctx.is_null() {
        return Err("Failed to allocate codec context");
    }

    // Create hardware device context
    let mut hw_device_ctx: *mut AVBufferRef = std::ptr::null_mut();
    let ret = av_hwdevice_ctx_create(
        &mut hw_device_ctx,
        device_type,
        std::ptr::null(),
        std::ptr::null_mut(),
        0,
    );
    if ret < 0 {
        let mut codec_ctx_mut = codec_ctx;
        avcodec_free_context(&mut codec_ctx_mut);
        return Err("Failed to create HW device context");
    }

    // Attach hardware context to codec (av_buffer_ref can return null on OOM)
    let hw_ctx_ref = av_buffer_ref(hw_device_ctx);
    if hw_ctx_ref.is_null() {
        av_buffer_unref(&mut hw_device_ctx);
        let mut codec_ctx_mut = codec_ctx;
        avcodec_free_context(&mut codec_ctx_mut);
        return Err("Failed to reference hardware context");
    }
    (*codec_ctx).hw_device_ctx = hw_ctx_ref;

    // Open codec
    let ret = avcodec_open2(codec_ctx, codec, std::ptr::null_mut());
    if ret < 0 {
        av_buffer_unref(&mut hw_device_ctx);
        let mut codec_ctx_mut = codec_ctx;
        avcodec_free_context(&mut codec_ctx_mut);
        return Err("Failed to open hardware decoder");
    }

    Ok((codec_ctx, hw_device_ctx))
}
```

## Hardware Encoder Setup

```rust
use ffmpeg_sys_next::{
    avcodec_find_encoder_by_name, avcodec_alloc_context3,
    avcodec_open2, avcodec_free_context,
    av_hwdevice_ctx_create, av_hwframe_ctx_alloc, av_hwframe_ctx_init,
    av_buffer_ref, av_buffer_unref,
    AVCodecContext, AVHWDeviceType, AVBufferRef, AVHWFramesContext,
    AVPixelFormat,
};
use std::ffi::CString;

/// Setup hardware-accelerated encoder
unsafe fn setup_hw_encoder(
    codec_name: &str,
    device_type: AVHWDeviceType,
    width: i32,
    height: i32,
    hw_pix_fmt: AVPixelFormat,
    sw_pix_fmt: AVPixelFormat,  // Software format for frame upload
) -> Result<HWEncoderContext, &'static str> {
    // Find hardware encoder
    let c_name = CString::new(codec_name).map_err(|_| "Invalid codec name")?;
    let codec = avcodec_find_encoder_by_name(c_name.as_ptr());
    if codec.is_null() {
        return Err("Hardware encoder not found");
    }

    // Allocate codec context
    let codec_ctx = avcodec_alloc_context3(codec);
    if codec_ctx.is_null() {
        return Err("Failed to allocate codec context");
    }

    // Create hardware device context
    let mut hw_device_ctx: *mut AVBufferRef = std::ptr::null_mut();
    let ret = av_hwdevice_ctx_create(
        &mut hw_device_ctx,
        device_type,
        std::ptr::null(),
        std::ptr::null_mut(),
        0,
    );
    if ret < 0 {
        let mut codec_ctx_mut = codec_ctx;
        avcodec_free_context(&mut codec_ctx_mut);
        return Err("Failed to create HW device context");
    }

    // Create hardware frames context
    let mut hw_frames_ref = av_hwframe_ctx_alloc(hw_device_ctx);
    if hw_frames_ref.is_null() {
        av_buffer_unref(&mut hw_device_ctx);
        let mut codec_ctx_mut = codec_ctx;
        avcodec_free_context(&mut codec_ctx_mut);
        return Err("Failed to allocate HW frames context");
    }

    // Configure frames context
    let frames_ctx = (*hw_frames_ref).data as *mut AVHWFramesContext;
    (*frames_ctx).format = hw_pix_fmt;
    (*frames_ctx).sw_format = sw_pix_fmt;
    (*frames_ctx).width = width;
    (*frames_ctx).height = height;
    (*frames_ctx).initial_pool_size = 20;

    let ret = av_hwframe_ctx_init(hw_frames_ref);
    if ret < 0 {
        av_buffer_unref(&mut hw_frames_ref);
        av_buffer_unref(&mut hw_device_ctx);
        let mut codec_ctx_mut = codec_ctx;
        avcodec_free_context(&mut codec_ctx_mut);
        return Err("Failed to initialize HW frames context");
    }

    // Configure encoder (av_buffer_ref can return null on OOM)
    (*codec_ctx).width = width;
    (*codec_ctx).height = height;
    (*codec_ctx).pix_fmt = hw_pix_fmt;
    let frames_ctx_ref = av_buffer_ref(hw_frames_ref);
    if frames_ctx_ref.is_null() {
        av_buffer_unref(&mut hw_frames_ref);
        av_buffer_unref(&mut hw_device_ctx);
        let mut codec_ctx_mut = codec_ctx;
        avcodec_free_context(&mut codec_ctx_mut);
        return Err("Failed to reference frames context");
    }
    (*codec_ctx).hw_frames_ctx = frames_ctx_ref;

    // Open encoder
    let ret = avcodec_open2(codec_ctx, codec, std::ptr::null_mut());
    if ret < 0 {
        av_buffer_unref(&mut hw_frames_ref);
        av_buffer_unref(&mut hw_device_ctx);
        let mut codec_ctx_mut = codec_ctx;
        avcodec_free_context(&mut codec_ctx_mut);
        return Err("Failed to open hardware encoder");
    }

    Ok(HWEncoderContext {
        codec_ctx,
        hw_device_ctx,
        hw_frames_ref,
    })
}

struct HWEncoderContext {
    codec_ctx: *mut AVCodecContext,
    hw_device_ctx: *mut AVBufferRef,
    hw_frames_ref: *mut AVBufferRef,
}

impl Drop for HWEncoderContext {
    fn drop(&mut self) {
        unsafe {
            if !self.codec_ctx.is_null() {
                avcodec_free_context(&mut self.codec_ctx);
            }
            if !self.hw_frames_ref.is_null() {
                av_buffer_unref(&mut self.hw_frames_ref);
            }
            if !self.hw_device_ctx.is_null() {
                av_buffer_unref(&mut self.hw_device_ctx);
            }
        }
    }
}
```

## Frame Transfer (GPU ↔ CPU)

```rust
use ffmpeg_sys_next::{
    av_hwframe_transfer_data, av_hwframe_get_buffer,
    av_frame_alloc, av_frame_free,
    AVFrame,
};

/// Transfer frame from GPU to CPU memory
unsafe fn download_hw_frame(
    hw_frame: *const AVFrame,
) -> Result<*mut AVFrame, &'static str> {
    let mut sw_frame = av_frame_alloc();
    if sw_frame.is_null() {
        return Err("Failed to allocate software frame");
    }

    let ret = av_hwframe_transfer_data(sw_frame, hw_frame, 0);
    if ret < 0 {
        av_frame_free(&mut sw_frame);
        return Err("Failed to transfer frame from GPU");
    }

    Ok(sw_frame)
}

/// Transfer frame from CPU to GPU memory
unsafe fn upload_hw_frame(
    sw_frame: *const AVFrame,
    hw_frames_ctx: *mut ffmpeg_sys_next::AVBufferRef,
) -> Result<*mut AVFrame, &'static str> {
    let mut hw_frame = av_frame_alloc();
    if hw_frame.is_null() {
        return Err("Failed to allocate hardware frame");
    }

    // Get buffer from hardware frames pool
    let ret = av_hwframe_get_buffer(hw_frames_ctx, hw_frame, 0);
    if ret < 0 {
        av_frame_free(&mut hw_frame);
        return Err("Failed to get hardware frame buffer");
    }

    // Copy data to GPU
    let ret = av_hwframe_transfer_data(hw_frame, sw_frame, 0);
    if ret < 0 {
        av_frame_free(&mut hw_frame);
        return Err("Failed to transfer frame to GPU");
    }

    Ok(hw_frame)
}
```

## NVIDIA-Specific Configuration

```rust
use ffmpeg_sys_next::{av_opt_set, av_opt_set_int, AVCodecContext};
use std::ffi::CString;

/// Configure NVENC encoder options
/// Note: av_opt_set returns negative on error, but encoder options
/// may not exist on all FFmpeg builds. Check returns in production code.
unsafe fn configure_nvenc(codec_ctx: *mut AVCodecContext) -> Result<(), &'static str> {
    // Set preset (fast encoding)
    let preset = CString::new("p4").map_err(|_| "Invalid preset")?;  // p1-p7, p4 is balanced
    let preset_key = CString::new("preset").map_err(|_| "Invalid key")?;
    let ret = av_opt_set(
        (*codec_ctx).priv_data,
        preset_key.as_ptr(),
        preset.as_ptr(),
        0,
    );
    if ret < 0 {
        // Option may not exist, log warning in production
    }

    // Set rate control mode
    let rc = CString::new("vbr").map_err(|_| "Invalid rc")?;  // cbr, vbr, cqp
    let rc_key = CString::new("rc").map_err(|_| "Invalid key")?;
    let ret = av_opt_set(
        (*codec_ctx).priv_data,
        rc_key.as_ptr(),
        rc.as_ptr(),
        0,
    );
    if ret < 0 {
        // Option may not exist, log warning in production
    }

    // Enable B-frames for better compression
    (*codec_ctx).max_b_frames = 2;

    // Set GOP size
    (*codec_ctx).gop_size = 250;

    Ok(())
}
```

## VideoToolbox-Specific Configuration (macOS)

```rust
use ffmpeg_sys_next::{av_opt_set, av_opt_set_int, AVCodecContext};
use std::ffi::CString;

/// Configure VideoToolbox encoder options
/// Note: av_opt_set returns negative on error, but encoder options
/// may not exist on all FFmpeg builds. Check returns in production code.
#[cfg(target_os = "macos")]
unsafe fn configure_videotoolbox(codec_ctx: *mut AVCodecContext) -> Result<(), &'static str> {
    // Enable hardware encoding
    let realtime = CString::new("realtime").map_err(|_| "Invalid value")?;
    let realtime_key = CString::new("realtime").map_err(|_| "Invalid key")?;
    let ret = av_opt_set(
        (*codec_ctx).priv_data,
        realtime_key.as_ptr(),
        realtime.as_ptr(),
        0,
    );
    if ret < 0 {
        // Option may not exist, log warning in production
    }

    // Set profile (main, high, baseline)
    let profile = CString::new("main").map_err(|_| "Invalid profile")?;
    let profile_key = CString::new("profile").map_err(|_| "Invalid key")?;
    let ret = av_opt_set(
        (*codec_ctx).priv_data,
        profile_key.as_ptr(),
        profile.as_ptr(),
        0,
    );
    if ret < 0 {
        // Option may not exist, log warning in production
    }

    // Configure bitrate
    (*codec_ctx).bit_rate = 5_000_000;  // 5 Mbps

    Ok(())
}
```

## Fallback Pattern

```rust
use ffmpeg_sys_next::{
    avcodec_find_decoder, avcodec_find_decoder_by_name,
    AVCodecID, AVCodec,
};
use std::ffi::CString;

/// Try hardware decoder, fall back to software
unsafe fn get_decoder_with_fallback(
    codec_id: AVCodecID,
    hw_decoder_name: Option<&str>,
) -> Result<*const AVCodec, &'static str> {
    // Try hardware decoder first
    if let Some(name) = hw_decoder_name {
        let c_name = CString::new(name).map_err(|_| "Invalid name")?;
        let hw_codec = avcodec_find_decoder_by_name(c_name.as_ptr());
        if !hw_codec.is_null() {
            return Ok(hw_codec);
        }
        // Hardware decoder not available, log and continue
        eprintln!("Hardware decoder '{}' not available, using software", name);
    }

    // Fall back to software decoder
    let sw_codec = avcodec_find_decoder(codec_id);
    if sw_codec.is_null() {
        return Err("No decoder found");
    }

    Ok(sw_codec)
}
```

## Best Practices

1. **Always check availability**: Use `list_hw_device_types()` before attempting hardware acceleration
2. **Implement fallback**: Always provide software fallback for unsupported hardware
3. **Match pixel formats**: Ensure input format matches hardware expectations
4. **Handle transfer overhead**: GPU↔CPU transfers have latency; minimize round-trips
5. **Clean up properly**: Free hardware contexts in reverse creation order
6. **Platform testing**: Test on all target platforms; hardware support varies significantly
7. **Error messages**: Use `av_strerror` for detailed error information during debugging
