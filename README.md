# rust-ffmpeg

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-Compatible-blue)](https://agentskills.io)

Claude Code [Agent Skill](https://agentskills.io) for Rust FFmpeg video/audio development: library selection, code generation, and problem solving.

## Why This Skill

Rust FFmpeg development is hard — 4 competing libraries, each with different APIs, trade-offs, and documentation quality. This skill gives Claude deep domain knowledge so it can:

- **Select the right library** — 3-layer decision framework routes to the optimal library based on your requirements (async? frame-level? no install?)
- **Generate production-ready code** — Not toy examples. Proper error handling, `Result<>` returns, async patterns, hardware acceleration
- **Cover 15+ scenarios** — Transcoding, streaming, capture, GIF creation, batch processing, subtitles, modern codecs, debugging, and more
- **Support all 4 libraries** — Same task shown across ez-ffmpeg, ffmpeg-next, ffmpeg-sys-next, and ffmpeg-sidecar with trade-off comparison

## Supported Libraries

- [ez-ffmpeg](https://github.com/YeautyYE/ez-ffmpeg) — High-level safe API with sync and async support
- [ffmpeg-next](https://github.com/zmwangx/rust-ffmpeg) — Medium-level safe API with frame-level control
- [ffmpeg-sys-next](https://crates.io/crates/ffmpeg-sys-next) — Low-level unsafe FFI bindings for max performance
- [ffmpeg-sidecar](https://github.com/nathanbabcock/ffmpeg-sidecar) — CLI wrapper, no FFmpeg library installation needed

## Installation

```bash
/plugin marketplace add YeautyYE/skill-rust-ffmpeg
/plugin install rust-ffmpeg
```

Or manually:
```bash
git clone https://github.com/YeautyYE/skill-rust-ffmpeg.git
cp -r skill-rust-ffmpeg/plugin/skills/rust-ffmpeg ~/.claude/skills/
```

## Usage

After installation, ask Claude naturally:

```
Write a Rust function to extract audio from MP4 to MP3
Implement async video transcoding with progress callback
How to do RTMP live streaming in Rust?
Convert FFmpeg CLI command to Rust code using ez-ffmpeg
Batch convert all .avi files to MP4 with hardware acceleration
Generate thumbnails from video at 1-second intervals
Create a high-quality GIF from a video clip
How to capture webcam video in Rust cross-platform?
Which Rust FFmpeg library should I use for frame-level processing?
```

Claude will automatically select the optimal library, load relevant references, and generate production-ready code.

## What's Inside

50 reference documents (~54K words) organized as:

- **Scenario guides** — Video transcoding, audio extraction, streaming, hardware acceleration, batch processing, subtitles, modern codecs, GIF creation, device capture, debugging, testing, integration
- **Library-specific guides** — Detailed API docs for each library with video, audio, streaming, filters, and advanced topics
- **Decision framework** — Library selection logic, quick start, installation guide, version compatibility

## Project Structure

```
plugin/skills/rust-ffmpeg/
├── SKILL.md              # Decision framework + routing logic
└── references/
    ├── scenarios/        # 13 cross-library scenario guides
    ├── ez_ffmpeg/        # 8 library-specific guides
    ├── ffmpeg_next/      # 8 library-specific guides
    ├── ffmpeg_sidecar/   # 9 library-specific guides
    ├── ffmpeg_sys_next/  # 4 library-specific guides
    └── *.md              # Quick start, installation, library selection
```

## License

MIT - see [LICENSE](LICENSE)

## Acknowledgments

- [ffmpeg-next](https://github.com/zmwangx/rust-ffmpeg)
- [ffmpeg-sidecar](https://github.com/nathanbabcock/ffmpeg-sidecar)
