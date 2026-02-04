# Batch Processing

**Detection Keywords**: batch processing, multiple files, how to process multiple videos, bulk video conversion, bulk convert, parallel encode, directory process, mass transcode, concurrent processing
**Aliases**: bulk operations, batch encode, multi-file, folder convert, parallel processing

Process multiple media files concurrently using async/parallel execution.

## Table of Contents

- [Quick Example](#quick-example-30-seconds)
- [Concurrent Processing Patterns](#concurrent-processing-patterns)
- [Progress Tracking](#progress-tracking)
- [Error Handling](#error-handling)
- [Resource Management](#resource-management)
- [Sequential Processing](#sequential-processing)

> **Dependencies**:
> ```toml
> # For ez-ffmpeg (async)
> ez-ffmpeg = { version = "0.10.0", features = ["async"] }
> tokio = { version = "1", features = ["full"] }
> futures = "0.3"
>
> # For ffmpeg-sidecar (thread-based)
> ffmpeg-sidecar = "2.4.0"
> rayon = "1.10"  # Optional: for parallel iterator processing
> ```

## Quick Example (30 seconds)

**Concurrent processing with tokio**:
```rust
use ez_ffmpeg::{FfmpegContext, Output};
use futures::future::join_all;
use std::fs;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let files: Vec<_> = fs::read_dir("input_dir")?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().map_or(false, |ext| ext == "mp4"))
        .collect();

    // Process all files concurrently
    let tasks: Vec<_> = files.iter().map(|path| {
        let input = path.to_str().unwrap().to_string();
        let output = format!("output/{}.mp4", path.file_stem().unwrap().to_str().unwrap());
        async move {
            FfmpegContext::builder()
                .input(&input)
                .output(Output::from(&output).set_video_codec("libx264"))
                .build()?.start()?.await
        }
    }).collect();

    join_all(tasks).await;
    Ok(())
}
```

## Library Comparison

| Aspect | ez-ffmpeg | ffmpeg-sidecar |
|--------|-----------|----------------|
| **Concurrent processing** | ✅ Native async | Thread-based (rayon/std::thread) |
| **Resource efficiency** | High (async I/O) | Medium (process per file) |
| **Progress tracking** | FrameFilter callback | Iterator events |
| **Use when** | Large batches, async apps | Small batches, simple CLI |

## Quick Examples

### ez-ffmpeg (async)

```rust
use ez_ffmpeg::{FfmpegContext, Output};
use futures::future::join_all;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let files = vec!["video1.mp4", "video2.mp4", "video3.mp4"];
    let tasks: Vec<_> = files.iter().map(|input| {
        let output = format!("output/{}", input);
        async move {
            FfmpegContext::builder()
                .input(input)
                .output(Output::from(&output).set_video_codec("libx264"))
                .build()?.start()?.await
        }
    }).collect();
    join_all(tasks).await;
    Ok(())
}
```

### ffmpeg-sidecar (thread-based)

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use std::thread;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let files = vec!["video1.mp4", "video2.mp4", "video3.mp4"];
    let handles: Vec<_> = files.iter().map(|input| {
        let input = input.to_string();
        let output = format!("output/{}", input);
        thread::spawn(move || {
            FfmpegCommand::new()
                .input(&input)
                .codec_video("libx264")
                .output(&output)
                .spawn()
                .unwrap()
                .iter()
                .unwrap()
                .for_each(|_| {});
        })
    }).collect();
    for h in handles { h.join().unwrap(); }
    Ok(())
}
```

### ffmpeg-sidecar with rayon (parallel iterator)

```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use rayon::prelude::*;
use std::fs;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let files: Vec<_> = fs::read_dir("input_dir")?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().map_or(false, |ext| ext == "mp4"))
        .collect();

    files.par_iter().for_each(|path| {
        let input = path.to_str().unwrap();
        let output = format!("output/{}", path.file_name().unwrap().to_str().unwrap());
        FfmpegCommand::new()
            .input(input)
            .codec_video("libx264")
            .output(&output)
            .spawn()
            .unwrap()
            .iter()
            .unwrap()
            .for_each(|_| {});
    });
    Ok(())
}
```

## Concurrent Processing Patterns

### Bounded concurrency (recommended)

Limit concurrent tasks to avoid resource exhaustion:

```rust
use ez_ffmpeg::{FfmpegContext, Output};
use tokio::sync::Semaphore;
use std::sync::Arc;
use std::fs;
use std::path::PathBuf;

fn collect_video_files(dir: &str) -> std::io::Result<Vec<PathBuf>> {
    Ok(fs::read_dir(dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().and_then(|s| s.to_str()).map_or(false, |ext| matches!(ext, "mp4" | "mov" | "mkv")))
        .collect())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let files = collect_video_files("input_dir")?;
    let semaphore = Arc::new(Semaphore::new(4)); // Max 4 concurrent

    let tasks: Vec<_> = files.iter().map(|path| {
        let sem = semaphore.clone();
        let input = path.to_str().unwrap().to_string();
        let output = format!("output/{}.mp4", path.file_stem().unwrap().to_str().unwrap());

        async move {
            let _permit = sem.acquire().await.unwrap();
            FfmpegContext::builder()
                .input(&input)
                .output(Output::from(&output).set_video_codec("libx264"))
                .build()?.start()?.await
        }
    }).collect();

    futures::future::join_all(tasks).await;
    Ok(())
}
```

### With progress tracking

**ez-ffmpeg (async)**:
```rust
use ez_ffmpeg::{FfmpegContext, Output};
use tokio::sync::Semaphore;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::fs;
use std::path::PathBuf;

fn collect_video_files(dir: &str) -> std::io::Result<Vec<PathBuf>> {
    Ok(fs::read_dir(dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().and_then(|s| s.to_str()).map_or(false, |ext| matches!(ext, "mp4" | "mov" | "mkv")))
        .collect())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let files = collect_video_files("input_dir")?;
    let total = files.len();
    let completed = Arc::new(AtomicUsize::new(0));
    let semaphore = Arc::new(Semaphore::new(4));

    let tasks: Vec<_> = files.iter().map(|path| {
        let sem = semaphore.clone();
        let counter = completed.clone();
        let input = path.to_str().unwrap().to_string();
        let output = format!("output/{}.mp4", path.file_stem().unwrap().to_str().unwrap());

        async move {
            let _permit = sem.acquire().await.unwrap();
            let result = FfmpegContext::builder()
                .input(&input)
                .output(Output::from(&output).set_video_codec("libx264"))
                .build()?.start()?.await;

            let done = counter.fetch_add(1, Ordering::SeqCst) + 1;
            println!("Progress: {}/{} ({:.1}%)", done, total, done as f64 / total as f64 * 100.0);
            result
        }
    }).collect();

    futures::future::join_all(tasks).await;
    Ok(())
}
```

**ffmpeg-sidecar (with per-file progress)**:
```rust
use ffmpeg_sidecar::command::FfmpegCommand;
use ffmpeg_sidecar::event::FfmpegEvent;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::thread;
use std::fs;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let files: Vec<_> = fs::read_dir("input_dir")?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().map_or(false, |ext| ext == "mp4"))
        .collect();

    let total = files.len();
    let completed = Arc::new(AtomicUsize::new(0));

    let handles: Vec<_> = files.iter().map(|path| {
        let counter = completed.clone();
        let input = path.to_str().unwrap().to_string();
        let output = format!("output/{}", path.file_name().unwrap().to_str().unwrap());
        let file_name = path.file_name().unwrap().to_str().unwrap().to_string();

        thread::spawn(move || {
            FfmpegCommand::new()
                .input(&input)
                .codec_video("libx264")
                .output(&output)
                .spawn()
                .unwrap()
                .iter()
                .unwrap()
                .filter_progress()
                .for_each(|p| {
                    println!("[{}] Frame: {}, Time: {}", file_name, p.frame, p.time);
                });

            let done = counter.fetch_add(1, Ordering::SeqCst) + 1;
            println!("Completed: {}/{} files", done, total);
        })
    }).collect();

    for h in handles { h.join().unwrap(); }
    Ok(())
}
```

### Batch thumbnails (concurrent)

```rust
use ez_ffmpeg::{FfmpegContext, Output};
use tokio::sync::Semaphore;
use std::sync::Arc;
use std::fs;
use std::path::PathBuf;

fn collect_video_files(dir: &str) -> std::io::Result<Vec<PathBuf>> {
    Ok(fs::read_dir(dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().and_then(|s| s.to_str()).map_or(false, |ext| matches!(ext, "mp4" | "mov" | "mkv")))
        .collect())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let files = collect_video_files("videos")?;
    let semaphore = Arc::new(Semaphore::new(8)); // Thumbnails are fast, allow more concurrency

    let tasks: Vec<_> = files.iter().map(|path| {
        let sem = semaphore.clone();
        let input = path.to_str().unwrap().to_string();
        let output = format!("thumbs/{}.jpg", path.file_stem().unwrap().to_str().unwrap());

        async move {
            let _permit = sem.acquire().await.unwrap();
            FfmpegContext::builder()
                .input(&input)
                .output(Output::from(&output).set_max_video_frames(1))
                .build()?.start()?.await
        }
    }).collect();

    futures::future::join_all(tasks).await;
    Ok(())
}
```

## Concurrency Guidelines

| Task Type | Recommended Concurrency | Reason |
|-----------|------------------------|--------|
| Thumbnails | 8-16 | I/O bound, fast |
| Transcoding (CPU) | CPU cores / 2 | CPU intensive |
| Transcoding (GPU) | 2-4 | GPU memory limited |
| Large files | 2-4 | Memory intensive |

## Related Scenarios

| Scenario | Guide |
|----------|-------|
| Video transcoding | [video_transcoding.md](video_transcoding.md) |
| Hardware acceleration | [hardware_acceleration.md](hardware_acceleration.md) |
| Integration patterns | [integration.md](integration.md) |
