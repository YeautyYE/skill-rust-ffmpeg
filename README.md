# rust-ffmpeg

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-Compatible-blue)](https://agentskills.io)

[Agent Skill](https://agentskills.io) for Rust FFmpeg development: library selection, code generation, and problem solving.

## Installation

```bash
/plugin install https://github.com/YeautyYE/skill-rust-ffmpeg
```

Or manually:
```bash
git clone https://github.com/YeautyYE/skill-rust-ffmpeg.git
cp -r skill-rust-ffmpeg/skills/rust-ffmpeg ~/.claude/skills/
```

## Supported Libraries

ez-ffmpeg, ffmpeg-next, ffmpeg-sys-next, ffmpeg-sidecar

## Example Prompts

```
Write a Rust function to extract audio from MP4 to MP3
Implement video transcoding with progress callback
How to use hardware acceleration for video encoding in Rust?
```

## Project Structure

```
skill-rust-ffmpeg/
├── .claude-plugin/plugin.json
├── skills/rust-ffmpeg/
│   ├── SKILL.md
│   └── references/
└── README.md
```

> **Why `skills/` subdirectory?** Claude Code plugin system expects `skills/<name>/`, manual install expects root. This uses plugin structure; manual install needs `cp -r`.

## License

MIT - see [LICENSE](LICENSE)

## Acknowledgments

- [ez-ffmpeg](https://github.com/YeautyYE/ez-ffmpeg)
- [ffmpeg-next](https://github.com/zmwangx/rust-ffmpeg)
- [ffmpeg-sidecar](https://github.com/nathanbabcock/ffmpeg-sidecar)
