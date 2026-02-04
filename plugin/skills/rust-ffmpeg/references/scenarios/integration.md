# Integration Patterns

**Detection Keywords**: web server, REST API, upload process, S3 storage, async job, queue worker, backpressure, tokio integration, actix web, axum, log callback, tracing, logging, ffmpeg log, av_log, log redirect, log level
**Aliases**: web integration, API endpoint, cloud storage, job queue, async processing, microservice, log integration

Quick patterns for integrating FFmpeg with web servers, storage systems, and async workflows.

> **Integration Dependencies** (used in examples below):
> ```toml
> # For ez-ffmpeg (async)
> ez-ffmpeg = { version = "0.10.0", features = ["async"] }
> tokio = { version = "1", features = ["full"] }
> axum = "0.7"            # Web framework example
> aws-sdk-s3 = "1"        # S3 integration example
>
> # For ffmpeg-sidecar (sync/blocking)
> ffmpeg-sidecar = "2.4.0"
> actix-web = "4"         # Sync web framework example
> ```

## Related Scenarios

| Scenario | Content |
|----------|---------|
| [streaming_rtmp_hls.md](streaming_rtmp_hls.md) | Real-time streaming, RTMP |
| [batch_processing.md](batch_processing.md) | Batch processing, parallel jobs |
| [hardware_acceleration.md](hardware_acceleration.md) | Progress monitoring, async patterns |

---

## Quick Start

### Web Upload → Process → Download

**Using ez-ffmpeg with Axum (async)**:
```rust
use axum::{extract::Multipart, response::Json};
use ez_ffmpeg::FfmpegContext;

async fn process_video(mut multipart: Multipart) -> Result<Json<String>, String> {
    let input_path = save_upload(&mut multipart).await
        .map_err(|e| e.to_string())?;

    FfmpegContext::builder()
        .input(&input_path)
        .output("output.mp4")
        .build().map_err(|e| e.to_string())?
        .start().map_err(|e| e.to_string())?
        .wait().map_err(|e| e.to_string())?;

    Ok(Json("output.mp4".to_string()))
}
```

**Using ffmpeg-sidecar with Actix-web (sync in spawn_blocking)**:
```rust
use actix_web::{post, web, HttpResponse, Responder};
use ffmpeg_sidecar::command::FfmpegCommand;

#[post("/process")]
async fn process_video(body: web::Bytes) -> impl Responder {
    // Save upload to temp file
    let input_path = "/tmp/input.mp4";
    std::fs::write(input_path, &body).unwrap();

    // Run FFmpeg in blocking task
    let result = web::block(move || {
        FfmpegCommand::new()
            .input(input_path)
            .codec_video("libx264")
            .output("/tmp/output.mp4")
            .spawn()
            .map_err(|e| e.to_string())?
            .wait()
            .map_err(|e| e.to_string())
    }).await;

    match result {
        Ok(Ok(_)) => HttpResponse::Ok().body("output.mp4"),
        _ => HttpResponse::InternalServerError().body("Processing failed"),
    }
}
```
**See also**: [ez_ffmpeg/advanced.md](../ez_ffmpeg/advanced.md)

---

### S3 Upload/Download Integration

**Using ez-ffmpeg with aws-sdk**:
```rust
use aws_sdk_s3::Client;

async fn process_from_s3(s3: &Client, key: &str) -> Result<(), Box<dyn std::error::Error>> {
    let obj = s3.get_object().bucket("my-bucket").key(key).send().await?;
    save_stream_to_file(obj.body, "/tmp/input.mp4").await?;

    FfmpegContext::builder()
        .input("/tmp/input.mp4")
        .output("/tmp/output.mp4")
        .build()?.start()?.wait()?;
    upload_to_s3(s3, "/tmp/output.mp4", "out.mp4").await
}
```
**See also**: [ez_ffmpeg/advanced.md](../ez_ffmpeg/advanced.md)

---

### Async Job Queue (Tokio)

**Using ez-ffmpeg with tokio**:
```rust
use tokio::sync::mpsc;

struct VideoJob { input: String, output: String }

async fn worker(mut rx: mpsc::Receiver<VideoJob>) {
    while let Some(job) = rx.recv().await {
        FfmpegContext::builder()
            .input(&job.input).output(&job.output)
            .build()?.start()?.wait()?;
    }
}
```
**See also**: [ez_ffmpeg/advanced.md](../ez_ffmpeg/advanced.md)

---

### Progress Monitoring API

**Using ffmpeg-sidecar with event iterator**:
```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::FfmpegEvent;

fn transcode_with_progress(input: &str, output: &str) {
    let mut child = FfmpegCommand::new()
        .input(input)
        .codec_video("libx264")
        .output(output)
        .spawn()
        .unwrap();

    child.iter().unwrap().for_each(|event| {
        match event {
            FfmpegEvent::Progress(p) => {
                println!("Frame: {}, Time: {}, Speed: {}x", p.frame, p.time, p.speed);
            }
            FfmpegEvent::Log(level, msg) => {
                println!("[{:?}] {}", level, msg);
            }
            _ => {}
        }
    });
}
```

**Using ez-ffmpeg with FrameFilter**:
```rust
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ez_ffmpeg::{FfmpegContext, Output};
use ffmpeg_next::Frame;
use ffmpeg_sys_next::AVMediaType;
use ez_ffmpeg::container_info::get_duration_us;
use std::sync::{Arc, Mutex};

struct ProgressFilter {
    progress: Arc<Mutex<f64>>,
    total_duration: i64,
}

impl FrameFilter for ProgressFilter {
    fn media_type(&self) -> AVMediaType { AVMediaType::AVMEDIA_TYPE_VIDEO }
    fn filter_frame(&mut self, frame: Frame, _: &FrameFilterContext) -> Result<Option<Frame>, String> {
        if let Some(pts) = frame.pts() {
            let current = pts as f64 / 1_000_000.0;
            let total = self.total_duration as f64 / 1_000_000.0;
            *self.progress.lock().unwrap() = (current / total * 100.0).min(100.0);
        }
        Ok(Some(frame))
    }
}

async fn process_with_progress(input: &str) -> Result<(), Box<dyn std::error::Error>> {
    let progress = Arc::new(Mutex::new(0.0));
    let total_duration = get_duration_us(input)?;

    let pipeline = FramePipelineBuilder::from(AVMediaType::AVMEDIA_TYPE_VIDEO)
        .filter("progress", Box::new(ProgressFilter {
            progress: progress.clone(),
            total_duration,
        }));

    FfmpegContext::builder()
        .input(input)
        .output(Output::from("out.mp4").add_frame_pipeline(pipeline))
        .build()?.start()?.await?;

    println!("Final progress: {:.1}%", *progress.lock().unwrap());
    Ok(())
}
```
**See also**: [ez_ffmpeg/advanced.md](../ez_ffmpeg/advanced.md)

---

### Backpressure Handling

**Using bounded channels**:
```rust
use tokio::sync::mpsc;

async fn process_with_backpressure() {
    let (tx, mut rx) = mpsc::channel(10);  // Bounded

    tokio::spawn(async move {
        for i in 0..100 {
            tx.send(format!("video{}.mp4", i)).await.unwrap();
        }
    });
    while let Some(video) = rx.recv().await { process_video(&video).await; }
}
```
**See also**: [ez_ffmpeg/advanced.md](../ez_ffmpeg/advanced.md)

---

### REST API Example (Actix-web)

**Using ez-ffmpeg with Actix**:
```rust
use actix_web::{post, web, HttpResponse};

#[post("/convert")]
async fn convert_video(body: web::Json<ConvertRequest>) -> HttpResponse {
    match FfmpegContext::builder()
        .input(&body.input_url).output(&body.output_path)
        .build()
        .and_then(|ctx| ctx.start())
        .and_then(|h| h.wait()) {
        Ok(_) => HttpResponse::Ok().json(ConvertResponse { status: "success" }),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() }),
    }
}
```
**See also**: [ez_ffmpeg/advanced.md](../ez_ffmpeg/advanced.md)

---

### FFmpeg Log Callback to Tracing

**Redirect FFmpeg's internal logs to Rust's tracing ecosystem**:

```rust
// ffmpeg-next: Redirect FFmpeg logs to tracing
use ffmpeg_next as ffmpeg;
use tracing::{trace, debug, info, warn, error};

fn setup_ffmpeg_logging() {
    unsafe {
        ffmpeg::ffi::av_log_set_callback(Some(log_callback));
    }
}

unsafe extern "C" fn log_callback(
    _ptr: *mut std::ffi::c_void,
    level: i32,
    fmt: *const i8,
    vl: *mut ffmpeg::ffi::__va_list_tag,
) {
    let mut buf = [0u8; 1024];
    ffmpeg::ffi::av_log_format_line(
        _ptr,
        level,
        fmt,
        vl,
        buf.as_mut_ptr() as *mut i8,
        buf.len() as i32,
        std::ptr::null_mut(),
    );

    let msg = std::ffi::CStr::from_ptr(buf.as_ptr() as *const i8)
        .to_string_lossy()
        .trim()
        .to_string();

    if msg.is_empty() {
        return;
    }

    // Map FFmpeg log levels to tracing levels
    // AV_LOG_QUIET=-8, PANIC=0, FATAL=8, ERROR=16, WARNING=24, INFO=32, VERBOSE=40, DEBUG=48, TRACE=56
    match level {
        l if l <= 8 => error!(target: "ffmpeg", "{}", msg),   // PANIC/FATAL
        l if l <= 16 => error!(target: "ffmpeg", "{}", msg),  // ERROR
        l if l <= 24 => warn!(target: "ffmpeg", "{}", msg),   // WARNING
        l if l <= 32 => info!(target: "ffmpeg", "{}", msg),   // INFO
        l if l <= 40 => debug!(target: "ffmpeg", "{}", msg),  // VERBOSE
        _ => trace!(target: "ffmpeg", "{}", msg),             // DEBUG/TRACE
    }
}

// Set log level (optional)
fn set_ffmpeg_log_level(level: i32) {
    unsafe {
        ffmpeg::ffi::av_log_set_level(level);
    }
}
```

```rust
// ffmpeg-sys-next: Low-level log callback
use ffmpeg_sys_next::*;
use std::sync::Once;

static INIT: Once = Once::new();

pub fn init_logging() {
    INIT.call_once(|| {
        unsafe {
            av_log_set_level(AV_LOG_WARNING);  // Set minimum level
            av_log_set_callback(Some(custom_log_callback));
        }
    });
}

unsafe extern "C" fn custom_log_callback(
    avcl: *mut std::ffi::c_void,
    level: i32,
    fmt: *const i8,
    vl: *mut __va_list_tag,
) {
    if level > av_log_get_level() {
        return;
    }

    let mut line = [0i8; 1024];
    let mut print_prefix = 1i32;

    av_log_format_line(
        avcl,
        level,
        fmt,
        vl,
        line.as_mut_ptr(),
        line.len() as i32,
        &mut print_prefix,
    );

    let msg = std::ffi::CStr::from_ptr(line.as_ptr())
        .to_string_lossy();

    // Forward to your logging framework
    eprintln!("[FFmpeg] {}", msg.trim());
}
```

```rust
// ez-ffmpeg: Uses ffmpeg-next internally, same approach
use ffmpeg_next as ffmpeg;

fn setup_logging() {
    // Same as ffmpeg-next example above
    unsafe {
        ffmpeg::ffi::av_log_set_callback(Some(log_callback));
    }
}
```

**Common Log Levels**:
| Level | Value | When to Use |
|-------|-------|-------------|
| `AV_LOG_QUIET` | -8 | Disable all logging |
| `AV_LOG_ERROR` | 16 | Production (errors only) |
| `AV_LOG_WARNING` | 24 | Production (recommended) |
| `AV_LOG_INFO` | 32 | Development |
| `AV_LOG_DEBUG` | 48 | Debugging |
| `AV_LOG_TRACE` | 56 | Deep debugging |

**See also**: [debugging.md](debugging.md)

---

### Streaming Upload with SSE Progress

Real-time progress updates via Server-Sent Events during video processing.

**Using ez-ffmpeg with Axum SSE**:
```rust
use axum::{
    extract::Multipart,
    response::sse::{Event, Sse},
};
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ez_ffmpeg::{FfmpegContext, Output};
use ez_ffmpeg::container_info::get_duration_us;
use ffmpeg_next::Frame;
use ffmpeg_sys_next::AVMediaType;
use std::sync::{Arc, Mutex};
use tokio::sync::broadcast;
use tokio_stream::wrappers::BroadcastStream;
use futures::stream::Stream;

#[derive(Clone)]
struct ProgressUpdate {
    percent: f64,
    frame: i64,
    status: String,
}

struct SseProgressFilter {
    tx: broadcast::Sender<ProgressUpdate>,
    total_duration: i64,
    frame_count: i64,
}

impl FrameFilter for SseProgressFilter {
    fn media_type(&self) -> AVMediaType { AVMediaType::AVMEDIA_TYPE_VIDEO }

    fn filter_frame(&mut self, frame: Frame, _: &FrameFilterContext) -> Result<Option<Frame>, String> {
        self.frame_count += 1;
        if let Some(pts) = frame.pts() {
            let percent = (pts as f64 / self.total_duration as f64 * 100.0).min(100.0);
            let _ = self.tx.send(ProgressUpdate {
                percent,
                frame: self.frame_count,
                status: "processing".to_string(),
            });
        }
        Ok(Some(frame))
    }
}

async fn process_with_sse(
    multipart: Multipart,
) -> Sse<impl Stream<Item = Result<Event, std::convert::Infallible>>> {
    let (tx, _) = broadcast::channel::<ProgressUpdate>(100);
    let rx = tx.subscribe();

    let tx_clone = tx.clone();
    tokio::spawn(async move {
        let input_path = "/tmp/input.mp4"; // Save from multipart
        let total_duration = get_duration_us(input_path).unwrap_or(1);

        let pipeline = FramePipelineBuilder::from(AVMediaType::AVMEDIA_TYPE_VIDEO)
            .filter("sse_progress", Box::new(SseProgressFilter {
                tx: tx_clone.clone(),
                total_duration,
                frame_count: 0,
            }));

        let _ = FfmpegContext::builder()
            .input(input_path)
            .output(Output::from("/tmp/output.mp4").add_frame_pipeline(pipeline))
            .build()
            .and_then(|ctx| ctx.start())
            .and_then(|h| h.wait());

        let _ = tx_clone.send(ProgressUpdate {
            percent: 100.0,
            frame: 0,
            status: "complete".to_string(),
        });
    });

    let stream = BroadcastStream::new(rx).map(|result| {
        match result {
            Ok(update) => Ok(Event::default()
                .data(format!(r#"{{"percent":{:.1},"frame":{},"status":"{}"}}"#,
                    update.percent, update.frame, update.status))),
            Err(_) => Ok(Event::default().data(r#"{"status":"error"}"#)),
        }
    });

    Sse::new(stream)
}
```

**Using ffmpeg-sidecar with Actix SSE**:
```rust
use actix_web::{web, HttpResponse, Responder};
use actix_web_lab::sse;
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::FfmpegEvent;
use tokio::sync::mpsc;

async fn process_with_sse_sidecar(body: web::Bytes) -> impl Responder {
    let (tx, rx) = mpsc::channel::<sse::Event>(100);

    // Save upload
    let input_path = "/tmp/input.mp4";
    std::fs::write(input_path, &body).unwrap();

    tokio::spawn(async move {
        let mut child = FfmpegCommand::new()
            .input(input_path)
            .codec_video("libx264")
            .output("/tmp/output.mp4")
            .spawn()
            .unwrap();

        if let Ok(iter) = child.iter() {
            for event in iter {
                match event {
                    FfmpegEvent::Progress(p) => {
                        let data = format!(
                            r#"{{"frame":{},"time":"{}","speed":"{}"}}"#,
                            p.frame, p.time, p.speed
                        );
                        let _ = tx.send(sse::Event::Data(sse::Data::new(data))).await;
                    }
                    FfmpegEvent::Done => {
                        let _ = tx.send(sse::Event::Data(
                            sse::Data::new(r#"{"status":"complete"}"#)
                        )).await;
                        break;
                    }
                    _ => {}
                }
            }
        }
    });

    let stream = tokio_stream::wrappers::ReceiverStream::new(rx);
    sse::Sse::from_stream(stream)
}
```

**Client-side JavaScript**:
```javascript
const eventSource = new EventSource('/api/process');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.status === 'complete') {
        eventSource.close();
        console.log('Processing complete!');
    } else {
        console.log(`Progress: ${data.percent?.toFixed(1)}%`);
    }
};

eventSource.onerror = () => {
    eventSource.close();
    console.error('Connection lost');
};
```

---

### WebSocket Progress Updates

For bidirectional communication and more control:

**Using ez-ffmpeg with Axum WebSocket**:
```rust
use axum::{
    extract::ws::{Message, WebSocket, WebSocketUpgrade},
    response::Response,
};
use ez_ffmpeg::filter::frame_filter::FrameFilter;
use ez_ffmpeg::filter::frame_filter_context::FrameFilterContext;
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ez_ffmpeg::{FfmpegContext, Output};
use ffmpeg_next::Frame;
use ffmpeg_sys_next::AVMediaType;
use std::sync::{Arc, atomic::{AtomicBool, Ordering}};
use tokio::sync::mpsc;

struct WsProgressFilter {
    tx: mpsc::Sender<String>,
    cancelled: Arc<AtomicBool>,
    frame_count: i64,
}

impl FrameFilter for WsProgressFilter {
    fn media_type(&self) -> AVMediaType { AVMediaType::AVMEDIA_TYPE_VIDEO }

    fn filter_frame(&mut self, frame: Frame, _: &FrameFilterContext) -> Result<Option<Frame>, String> {
        // Check for cancellation
        if self.cancelled.load(Ordering::Relaxed) {
            return Err("Cancelled by user".to_string());
        }

        self.frame_count += 1;
        let msg = format!(r#"{{"frame":{}}}"#, self.frame_count);
        let _ = self.tx.blocking_send(msg);
        Ok(Some(frame))
    }
}

async fn ws_handler(ws: WebSocketUpgrade) -> Response {
    ws.on_upgrade(handle_socket)
}

async fn handle_socket(mut socket: WebSocket) {
    let (tx, mut rx) = mpsc::channel::<String>(100);
    let cancelled = Arc::new(AtomicBool::new(false));
    let cancelled_clone = cancelled.clone();

    // Spawn processing task
    let process_handle = tokio::spawn(async move {
        let pipeline = FramePipelineBuilder::from(AVMediaType::AVMEDIA_TYPE_VIDEO)
            .filter("ws_progress", Box::new(WsProgressFilter {
                tx,
                cancelled: cancelled_clone,
                frame_count: 0,
            }));

        FfmpegContext::builder()
            .input("input.mp4")
            .output(Output::from("output.mp4").add_frame_pipeline(pipeline))
            .build()?.start()?.wait()
    });

    // Handle bidirectional communication
    loop {
        tokio::select! {
            // Send progress to client
            Some(msg) = rx.recv() => {
                if socket.send(Message::Text(msg)).await.is_err() {
                    break;
                }
            }
            // Receive commands from client
            Some(Ok(msg)) = socket.recv() => {
                if let Message::Text(text) = msg {
                    if text.contains("cancel") {
                        cancelled.store(true, Ordering::Relaxed);
                        let _ = socket.send(Message::Text(
                            r#"{"status":"cancelled"}"#.to_string()
                        )).await;
                        break;
                    }
                }
            }
            // Processing complete
            _ = &mut process_handle => {
                let _ = socket.send(Message::Text(
                    r#"{"status":"complete"}"#.to_string()
                )).await;
                break;
            }
        }
    }
}
```

---

### Chunked Upload with Resume

Handle large file uploads with resumable chunks:

**Using ez-ffmpeg with chunked processing**:
```rust
use axum::{
    extract::{Path, Query},
    response::Json,
    body::Bytes,
};
use std::collections::HashMap;
use std::fs::{File, OpenOptions};
use std::io::{Seek, SeekFrom, Write};
use ez_ffmpeg::FfmpegContext;

#[derive(serde::Deserialize)]
struct ChunkParams {
    chunk_index: u64,
    total_chunks: u64,
    file_id: String,
}

async fn upload_chunk(
    Query(params): Query<ChunkParams>,
    body: Bytes,
) -> Json<serde_json::Value> {
    let chunk_dir = format!("/tmp/chunks/{}", params.file_id);
    std::fs::create_dir_all(&chunk_dir).unwrap();

    let chunk_path = format!("{}/chunk_{:06}", chunk_dir, params.chunk_index);
    std::fs::write(&chunk_path, &body).unwrap();

    // Check if all chunks received
    let received = std::fs::read_dir(&chunk_dir).unwrap().count() as u64;

    if received == params.total_chunks {
        // Merge chunks
        let output_path = format!("/tmp/uploads/{}.mp4", params.file_id);
        merge_chunks(&chunk_dir, &output_path, params.total_chunks).unwrap();

        // Start processing
        tokio::spawn(async move {
            let _ = FfmpegContext::builder()
                .input(&output_path)
                .output(format!("/tmp/processed/{}.mp4", params.file_id))
                .build()
                .and_then(|ctx| ctx.start())
                .and_then(|h| h.wait());

            // Cleanup chunks
            let _ = std::fs::remove_dir_all(&chunk_dir);
        });

        Json(serde_json::json!({"status": "processing_started"}))
    } else {
        Json(serde_json::json!({
            "status": "chunk_received",
            "received": received,
            "total": params.total_chunks
        }))
    }
}

fn merge_chunks(chunk_dir: &str, output: &str, total: u64) -> std::io::Result<()> {
    let mut output_file = File::create(output)?;
    for i in 0..total {
        let chunk_path = format!("{}/chunk_{:06}", chunk_dir, i);
        let chunk_data = std::fs::read(&chunk_path)?;
        output_file.write_all(&chunk_data)?;
    }
    Ok(())
}
```

---

## Decision Guide

**Choose ez-ffmpeg if**:
- Building web services
- Need async/await integration
- Tokio-based applications
- Production microservices

**Choose ffmpeg-sidecar if**:
- Simple CLI-style integration
- Synchronous workflows
- Event-driven processing
- Cannot install FFmpeg libraries

## Common Integration Patterns

| Pattern | Use Case | Complexity |
|---------|----------|------------|
| Web upload → process | User file uploads | Medium |
| S3 integration | Cloud storage workflows | Medium |
| Job queue | Async batch processing | High |
| Progress API | Real-time status updates | Medium |
| Backpressure | Rate limiting | High |
| REST API | Microservice integration | Medium |

## Advanced Topics

For advanced integration scenarios, see:
- [Async patterns](../ez_ffmpeg/advanced.md)
- [Progress monitoring](hardware_acceleration.md)
- [Batch processing](batch_processing.md)
- [Error handling](debugging.md)
- [Cloud deployment](../ez_ffmpeg/advanced.md)
