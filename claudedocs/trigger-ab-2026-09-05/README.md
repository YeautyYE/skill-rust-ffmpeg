# Description Trigger A/B — 2026-09-05 (239 words → 112 words)

**Question**: does cutting the `rust-ffmpeg` description from 1959 to 1020
characters lower auto-trigger recall?

**Why 1024**: the Agent Skills spec caps `description` at 1024 characters
(agentskills.io/specification). Claude Code additionally truncates each
listing entry at 1536 characters (`skillListingMaxDescChars`), so the old
description's last 423 characters — `FrameExtractor`, `SampleExtractor`,
`whisper PCM`, `VideoWriter`, `PacketSink`, `WebCodecs`, `avcC`,
`from_cli_args`, `emit_rust_code`, and the whole Libraries sentence — were
never reaching the model in a live session.

## Method

Simulated routing: a system-prompt-style skill listing with 8 decoy skills
(Python video tools, GStreamer Rust, image crate, WebRTC signaling, audio DSP,
codex-implement, module-docs, should-build) plus one `rust-ffmpeg` entry.
Three arms differ only in that entry:

| Arm | Description | Chars |
|-----|-------------|-------|
| `old_full` | shipped text, untruncated (theoretical ceiling) | 1959 |
| `old_trunc` | shipped text as Claude Code actually shows it (first 1536) | 1536 |
| `new` | rewrite | 1020 |

45 queries, judged independently per arm by a fresh subagent with tools
forbidden: 25 corpus positives (P, from `skill-trigger-regression-corpus.md`),
10 held-out positives not in the corpus (H), 10 negatives that should route to
a decoy or `none` (N). Models: Haiku 4.5, Sonnet, Fable 5.

Files: `build_prompts.py` (regenerates the three prompts), `queries.json`,
`result_<arm>_<model>.json` (raw verdicts), `score.py` (table below).

## Result

| arm | model | corpus P | held-out H | false + N |
|-----|-------|----------|------------|-----------|
| old_full | haiku | 25/25 | 10/10 | 0/10 |
| old_trunc | haiku | **23/25** | 10/10 | 0/10 |
| new | haiku | 25/25 | 10/10 | 0/10 |
| old_full | sonnet | 25/25 | 10/10 | 0/10 |
| old_trunc | sonnet | 25/25 | 10/10 | 0/10 |
| new | sonnet | 25/25 | 10/10 | 0/10 |
| old_full | fable | 25/25 | 10/10 | 0/10 |
| old_trunc | fable | **24/25** | 10/10 | 0/10 |
| new | fable | 25/25 | 10/10 | 0/10 |

`old_trunc` misses: P11 `from_cli_args emits Rust code` (haiku, fable), P24
`whisper PCM 16 kHz mono ingest` (haiku) — exactly the anchors that live in the
truncated tail. The rewrite recovers both.

## Limits

- Simulated listing, not Claude Code's real router; one run per cell, no
  repeats, so a single-query flip is inside noise. The direction is
  consistent across three models, which is the claim being made.
- Negatives all routed to the intended decoy or `none`; N08 (`axum
  endpoint`) went to `codex-implement` on the stronger models and `none` on
  Haiku — unrelated to `rust-ffmpeg`, recorded for completeness.
