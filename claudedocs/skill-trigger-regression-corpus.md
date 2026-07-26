# rust-ffmpeg Skill — Description Trigger Regression Corpus

**Purpose**: gate every future edit of the SKILL.md frontmatter `description`.
The description is the ONLY pre-trigger signal (skill-creator: body loads
after triggering; all when-to-use info must live in the description). A
change ships only if this corpus passes the lexical-anchor check below and
any newly accepted misses are recorded in the table.

**Method**: for each query, the listed anchor tokens must appear (case-
insensitive substring) in the description, OR the row is explicitly marked
`SEMANTIC` (broad-intent wording expected to match without a literal token —
a judgment, not a guarantee) or `ACCEPTED-MISS` (deliberate, recorded loss).
Run: `python3 claudedocs/check_trigger_corpus.py` (inline in repo history;
re-create from this table if lost).

**Origin**: agent-ux red-team walkthrough (UX-1, Evidence Protocol run
ep-20260726T183134) + Phase-3 additions. 9 of the original 16 queries were
judged likely-fail under a naive 150-word rewrite; the replacement
description must keep them alive.

| # | Query | Anchor tokens (any of) | Class |
|---|-------|------------------------|-------|
| 1 | avformat_find_stream_info | `avformat_find_stream_info` | C-API bare term |
| 2 | AVSEEK_SIZE custom seek callback | `AVSEEK_SIZE`, `custom I/O` | C-API bare term (pre-existing gap, fixed in Phase 3) |
| 3 | 视频转码 (Chinese: video transcode) | SEMANTIC (`transcode`, `video`, `media`) | multilingual broad intent |
| 4 | Wie transkodiere ich ein Video in Rust? | SEMANTIC (`transcode`, `video`, `Rust`) | multilingual broad intent |
| 5 | make this video smaller in Rust | SEMANTIC (`resize`, `transcode`, `convert`) | indirect intent |
| 6 | ez-ffmpeg vs ffmpeg-next | `ez-ffmpeg`, `ffmpeg-next`, `vs` | library comparison |
| 7 | EBU R128 integrated loudness | `EBU R128`, `LUFS` | loudness/QC bare term |
| 8 | v4l2 camera capture | `v4l2`, `capture` | capture backend |
| 9 | FrameExtractor RGB output changed | `FrameExtractor` | frame-export API |
| 10 | PacketSink avcC AudioSpecificConfig | `PacketSink`, `avcC`, `AudioSpecificConfig` | packet-export API |
| 11 | from_cli_args emits Rust code | `from_cli_args`, `emit_rust_code` | CLI translation API |
| 12 | StreamMap -c:v:0 | `StreamMap`, `-c:v:0` | per-stream encoder |
| 13 | WHIP capability probe | `WHIP` | modern streaming output |
| 14 | h264_mp4toannexb | `h264_mp4toannexb` | bitstream filter |
| 15 | set_video_filter | `set_video_filter` | per-output filter API |
| 16 | WGSL chroma key | `WGSL`, `chroma key` | GPU shader |
| 17 | burn subtitles without libass in Rust | `libass`, `burn` | subtitle burn-in |
| 18 | video plus longer music track -shortest | `-shortest` | mux control |
| 19 | blackdetect silencedetect QC pass | `blackdetect`, `silencedetect` | detection |
| 20 | HDR to SDR washed out colors | `HDR to SDR`, `tone mapping` | modern codecs |
| 21 | progress bar for a Rust transcode | `progress`, `ProgressHandle` | progress reporting |
| 22 | generate a test video with testsrc | `testsrc` | testing |
| 23 | embedded RTMP server in Rust | `RTMP server` | streaming |
| 24 | whisper PCM 16 kHz mono ingest | `whisper PCM`, `SampleExtractor` | ASR ingest |
| 25 | thumbnail sprite sheet recipe | `thumbnail`, `sprite sheet` | recipes |

## Accepted misses (recorded per Phase-3 rewrite, 2026-07-27)

| Dropped token(s) | Class | Rationale |
|------------------|-------|-----------|
| `EncodedVideoChunk`, `EncodedAudioChunk` | WebCodecs type names | `WebCodecs`, `PacketSink`, `avcC` remain as the cluster's anchors |
| `PSNR`, `showwaves` | niche one-off effects | no dedicated reference section; Layer 2 covers post-trigger |
| `VideoProcessor`, `MediaInfo`, `FilterGraph`, `TranscodeTask`, `AudioResampler`, `StreamReader`, `FrameConverter` | invented struct-design cue names | replaced by the generic `struct/trait design for media processing` phrase |
| `ref_counted_frames`, `send_packet` | deep C-API terms | `AVPacket`/`AVFrame`/`EAGAIN`/C-API cluster remains; judged semantically adjacent |
| `watchdog`, `retry logic`, `timeout` | generic async-ops vocabulary | not FFmpeg-specific; `async transcode` remains |
| release/version annotations (`0.14`/`0.15`/`0.16`, `experimental`) | metadata noise | trigger value unverified (TE-5); versions live in SKILL.md body |

## Maintenance rule (ends the append-only convention)

Adding a trigger spelling to the description requires: (a) replacing or
consolidating existing text — net word count must stay ≤ 300; (b) adding a
corpus row here demonstrating the query class it serves; (c) re-running the
anchor check. Never append numbered release groups.
