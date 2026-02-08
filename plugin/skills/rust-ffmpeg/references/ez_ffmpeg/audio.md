# ez-ffmpeg: Audio Processing

**Detection Keywords**: audio extraction, convert audio, mp3, aac, audio codec, resample, audio filter
**Aliases**: audio processing, extract audio, audio encoding

## Related Guides

| Guide | Content |
|-------|---------|
| [video.md](video.md) | Video transcoding, format conversion |
| [filters.md](filters.md) | FFmpeg filters (scale, crop, etc.) |
| [query.md](query.md) | Media info, duration, codec info |

## Audio Extraction

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Extract audio from video (keep original codec)
FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("audio.aac")
        .add_stream_map("0:a")  // Map only audio stream
        .set_audio_codec("copy"))
    .build()?.start()?.wait()?;

// Extract and convert to MP3
FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("audio.mp3")
        .add_stream_map("0:a")
        .set_audio_codec("libmp3lame")
        .set_audio_codec_opt("b", "192k"))
    .build()?.start()?.wait()?;

// Extract with precise time range
let start_us: i64 = 60_000_000;  // 60 seconds in microseconds

FfmpegContext::builder()
    .input(Input::from("video.mp4")
        .set_start_time_us(start_us))
    .output(Output::from("clip_audio.aac")
        .add_stream_map("0:a")
        .set_recording_time_us(30_000_000)  // 30 seconds
        .set_audio_codec("aac")
        .set_audio_codec_opt("b", "128k"))
    .build()?.start()?.wait()?;
```

## Video Extraction (Remove Audio)

```rust
use ez_ffmpeg::{FfmpegContext, Output};

// Extract video only (remove audio track)
FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("video_only.mp4")
        .add_stream_map("0:v")  // Map only video stream
        .set_video_codec("copy"))
    .build()?.start()?.wait()?;
```

## Split Video to WAV

```rust
use ez_ffmpeg::{FfmpegContext, Output};

// Extract audio as WAV (uncompressed)
FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("audio.wav")
        .add_stream_map("0:a")  // Map only audio stream
        .set_audio_codec("pcm_s16le"))
    .build()?.start()?.wait()?;

// Split audio into multiple WAV segments (10 seconds each)
// Creates output_000.wav, output_001.wav, etc.
FfmpegContext::builder()
    .input("video.mp4")
    .output(Output::from("output_%03d.wav")
        .set_format("segment")
        .set_format_opt("segment_time", "10"))
    .build()?.start()?.wait()?;
```

## Audio Sample Rate Modification

```rust
use ez_ffmpeg::FfmpegContext;

// Resample to 44100 Hz
FfmpegContext::builder()
    .input("audio.mp3")
    .filter_desc("aresample=44100")
    .output("output.mp3")
    .build()?.start()?.wait()?;

// Resample with high quality (SoX resampler)
FfmpegContext::builder()
    .input("audio.mp3")
    .filter_desc("aresample=44100:resampler=soxr")
    .output("output.mp3")
    .build()?.start()?.wait()?;

// Handle PTS gaps with async resampling
// Useful for live streams or recordings with timestamp discontinuities
FfmpegContext::builder()
    .input("stream_recording.ts")
    .filter_desc("aresample=async=1")  // Stretch/squeeze audio to match timestamps
    .output("fixed_audio.aac")
    .build()?.start()?.wait()?;
```

## Audio Channel Modification

```rust
use ez_ffmpeg::FfmpegContext;

// Convert stereo to mono
FfmpegContext::builder()
    .input("stereo.mp3")
    .filter_desc("pan=mono|c0=0.5*c0+0.5*c1")
    .output("mono.mp3")
    .build()?.start()?.wait()?;

// Convert mono to stereo
FfmpegContext::builder()
    .input("mono.mp3")
    .filter_desc("pan=stereo|c0=c0|c1=c0")
    .output("stereo.mp3")
    .build()?.start()?.wait()?;
```

## Audio Volume Adjustment

```rust
use ez_ffmpeg::FfmpegContext;

// Increase volume by 50%
FfmpegContext::builder()
    .input("audio.mp3")
    .filter_desc("volume=1.5")
    .output("louder.mp3")
    .build()?.start()?.wait()?;

// Decrease volume to 50%
FfmpegContext::builder()
    .input("audio.mp3")
    .filter_desc("volume=0.5")
    .output("quieter.mp3")
    .build()?.start()?.wait()?;

// Normalize audio
FfmpegContext::builder()
    .input("audio.mp3")
    .filter_desc("loudnorm")
    .output("normalized.mp3")
    .build()?.start()?.wait()?;
```

## Merge Audio with Video

```rust
use ez_ffmpeg::{FfmpegContext, Output};

// Replace video's audio with new audio track
FfmpegContext::builder()
    .input("video.mp4")
    .input("new_audio.mp3")
    .output(Output::from("output.mp4")
        .add_stream_map("0:v")
        .add_stream_map("1:a")
        .set_video_codec("copy")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;

// Mix original audio with new audio
FfmpegContext::builder()
    .input("video.mp4")
    .input("background_music.mp3")
    .filter_desc("[0:a][1:a]amix=inputs=2:duration=first[aout]")
    .output(Output::from("output.mp4")
        .add_stream_map("0:v")
        .add_stream_map("aout")
        .set_video_codec("copy")
        .set_audio_codec("aac"))
    .build()?.start()?.wait()?;
```

## Audio Format Conversion

```rust
use ez_ffmpeg::{FfmpegContext, Output};

// MP3 to AAC
FfmpegContext::builder()
    .input("audio.mp3")
    .output(Output::from("audio.aac")
        .set_audio_codec("aac")
        .set_audio_codec_opt("b", "192k"))
    .build()?.start()?.wait()?;

// FLAC to MP3 (lossless to lossy)
FfmpegContext::builder()
    .input("audio.flac")
    .output(Output::from("audio.mp3")
        .set_audio_codec("libmp3lame")
        .set_audio_codec_opt("q", "2"))  // VBR quality 0-9, lower is better
    .build()?.start()?.wait()?;

// WAV to Opus (high quality, small size)
FfmpegContext::builder()
    .input("audio.wav")
    .output(Output::from("audio.opus")
        .set_audio_codec("libopus")
        .set_audio_codec_opt("b", "128k"))
    .build()?.start()?.wait()?;
```

## Audio Fade Effects

```rust
use ez_ffmpeg::FfmpegContext;

// Fade in (first 3 seconds)
FfmpegContext::builder()
    .input("audio.mp3")
    .filter_desc("afade=t=in:st=0:d=3")
    .output("fade_in.mp3")
    .build()?.start()?.wait()?;

// Fade out (last 3 seconds, assuming 60s audio)
FfmpegContext::builder()
    .input("audio.mp3")
    .filter_desc("afade=t=out:st=57:d=3")
    .output("fade_out.mp3")
    .build()?.start()?.wait()?;

// Both fade in and fade out
FfmpegContext::builder()
    .input("audio.mp3")
    .filter_desc("afade=t=in:st=0:d=2,afade=t=out:st=58:d=2")
    .output("faded.mp3")
    .build()?.start()?.wait()?;
```

## Audio Concatenation

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};
use std::fs::File;
use std::io::Write;

// Method 1: Concat demuxer (same format, fast)
let mut file = File::create("audio_list.txt")?;
writeln!(file, "file 'audio1.mp3'")?;
writeln!(file, "file 'audio2.mp3'")?;

FfmpegContext::builder()
    .input(Input::from("audio_list.txt")
        .set_format("concat")
        .set_input_opt("safe", "0"))
    .output(Output::from("merged.mp3")
        .set_audio_codec("copy"))
    .build()?.start()?.wait()?;

// Method 2: Filter concat (different formats, re-encode)
FfmpegContext::builder()
    .input("audio1.mp3")
    .input("audio2.wav")
    .filter_desc("[0:a][1:a]concat=n=2:v=0:a=1[aout]")
    .output(Output::from("merged.mp3")
        .add_stream_map("aout")
        .set_audio_codec("libmp3lame"))
    .build()?.start()?.wait()?;
```

## Audio Trimming

```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

// Trim from 10s to 30s (stream copy, fast)
FfmpegContext::builder()
    .input(Input::from("audio.mp3")
        .set_start_time_us(10_000_000))  // 10 seconds in microseconds
    .output(Output::from("trimmed.mp3")
        .set_recording_time_us(20_000_000)  // 20 seconds
        .set_audio_codec("copy"))
    .build()?.start()?.wait()?;

// Precise trim with re-encoding
FfmpegContext::builder()
    .input(Input::from("audio.mp3")
        .set_start_time_us(10_500_000))  // 10.5 seconds
    .output(Output::from("trimmed.mp3")
        .set_recording_time_us(19_500_000)  // 19.5 seconds
        .set_audio_codec("libmp3lame"))
    .build()?.start()?.wait()?;
```
