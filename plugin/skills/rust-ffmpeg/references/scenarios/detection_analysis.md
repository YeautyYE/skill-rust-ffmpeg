# Detection & Measurement (Typed Analysis)

**Detection Keywords**: blackdetect, silencedetect, scene detection, cropdetect, EBU R128, LUFS, true peak, measure loudness, content analysis, QC, typed analysis
**Aliases**: Analysis runner, MetadataEventFilter, detection events

ez-ffmpeg's `analysis` module runs FFmpeg's detector filters and returns the
results as **typed Rust data** (structs), not text you have to scrape from
`av_log`. Black frames, scene cuts, silence, crop windows and EBU R128 loudness
all come back as `Vec`s / `Option`s.

**No feature flag required** — `analysis` is in the default build.

## Table of Contents

- [Related Scenarios](#related-scenarios)
- [One-Shot Analysis (single decode pass)](#one-shot-analysis-single-decode-pass)
- [Streaming Detection (detect while transcoding)](#streaming-detection-detect-while-transcoding)

## Related Scenarios

| Scenario | Content |
|----------|---------|
| [debugging.md](debugging.md) | General debugging, probing, integrity checks |
| [audio_extraction.md](audio_extraction.md) | Loudness normalization (`loudnorm`), pure LUFS measurement |

## One-Shot Analysis (single decode pass)

`Analysis` runs every detector you add in a single decode pass and hands back an
`AnalysisReport`:

```rust
use ez_ffmpeg::analysis::{Analysis, AudioDetector, VideoDetector};

/// Detect black frames, scene cuts, silence and EBU R128 loudness in a single
/// decode pass, returned as typed Rust data (not FFmpeg logs).
fn analyze(path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let report = Analysis::new(path)
        .video_detector(VideoDetector::Black {
            min_duration_s: 0.1,
            pixel_th: 0.10,
            picture_th: 0.98,
        })
        .video_detector(VideoDetector::Scene { threshold_pct: 10.0 })
        .audio_detector(AudioDetector::Silence {
            noise_db: -30.0,
            min_duration_s: 0.5,
            mono: false,
        })
        .audio_detector(AudioDetector::Ebur128 { true_peak: true })
        .run()?;

    println!("black regions  : {:?}", report.black);
    println!("scene changes  : {}", report.scenes.len());
    println!("silence regions: {:?}", report.silence);
    if let Some(loudness) = report.loudness {
        println!("integrated     : {:?} LUFS", loudness.integrated);
        println!("true peak      : {:?} dBTP", loudness.true_peak);
    }
    Ok(())
}
```

Detectors and what they map to:

| Detector | Variant | FFmpeg filter |
|----------|---------|---------------|
| Black frames | `VideoDetector::Black { min_duration_s, pixel_th, picture_th }` | `blackdetect` |
| Scene cuts | `VideoDetector::Scene { threshold_pct }` (0..=100) | `scdet` |
| Crop window | `VideoDetector::Crop { limit, round, reset }` | `cropdetect` |
| Silence | `AudioDetector::Silence { noise_db, min_duration_s, mono }` | `silencedetect` |
| Loudness (EBU R128) | `AudioDetector::Ebur128 { true_peak }` | `ebur128` |

`AnalysisReport` fields: `black: Vec<BlackRange>`, `silence: Vec<SilenceRange>`,
`scenes: Vec<SceneChange>`, `crop: Option<CropSuggestion>`,
`loudness: Option<LoudnessReport>`.

## Streaming Detection (detect while transcoding)

To receive detection events live *while* a transcode runs, put a
`MetadataEventFilter` on the output frame pipeline. A detector filter in the graph
(e.g. `blackdetect`) attaches `lavfi.*` metadata to frames; the filter parses that
into typed `MetadataEvent`s on a channel and forwards each frame unchanged.

```rust
use ez_ffmpeg::analysis::{MetadataEvent, MetadataEventFilter};
use ez_ffmpeg::filter::frame_pipeline_builder::FramePipelineBuilder;
use ez_ffmpeg::{FfmpegContext, Output};
use ffmpeg_sys_next::AVMediaType::AVMEDIA_TYPE_VIDEO;
use std::sync::mpsc::sync_channel;

fn detect_while_transcoding() -> Result<(), Box<dyn std::error::Error>> {
    let (tx, rx) = sync_channel::<MetadataEvent>(256);

    // Drain events on a background thread so the media pipeline is never
    // back-pressured (the filter's default policy aborts if the sink stalls).
    let consumer = std::thread::spawn(move || {
        for ev in rx {
            if let MetadataEvent::BlackStart { at } = ev {
                println!("black frame starts at {} us", at.time_us);
            }
        }
    });

    let detector = MetadataEventFilter::new(AVMEDIA_TYPE_VIDEO, tx);
    let pipeline = FramePipelineBuilder::new(AVMEDIA_TYPE_VIDEO)
        .filter("detect", Box::new(detector))
        .build();

    FfmpegContext::builder()
        .input("test.mp4")
        .filter_desc("blackdetect=d=0.1")
        .output(Output::from("output.mp4").set_frame_pipelines(vec![pipeline]))
        .build()?
        .start()?
        .wait()?;

    consumer.join().ok();
    Ok(())
}
```

`MetadataEvent` variants include `BlackStart`/`BlackEnd`, `SilenceStart`/`SilenceEnd`,
`SceneChange`, `CropDetect`, `R128Frame`/`R128Summary` and `StreamEnd`; each carries
a `Timestamp` (`time_us`, optional `pts`/`time_base`). For pure LUFS/true-peak
measurement see [audio_extraction.md — EBU R128 Loudness Measurement](audio_extraction.md#ebu-r128-loudness-measurement).
