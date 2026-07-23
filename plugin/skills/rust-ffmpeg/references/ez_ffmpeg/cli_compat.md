# ez-ffmpeg: CLI Compatibility Facade (`cli` feature)

**Detection Keywords**: from_cli_args, emit_rust_code, cli feature, run ffmpeg command in rust, translate ffmpeg command, verified shape, cli-compat, ffmpeg command to builder code
**Aliases**: cli facade, CliError, cli::from_cli, cli-compat manifest

> **New in 0.15**, opt-in Cargo feature (`features = ["cli"]`), no dependent
> features. This is a **different, narrower artifact** from
> [cli_migration.md](cli_migration.md)'s hand-written mapping tables — see
> [Relationship to the manual mapping guide](#relationship-to-the-manual-mapping-guide)
> before reaching for this feature.

Two functions, both under `ez_ffmpeg::cli` (re-exported: `CliError`, `CliScope`):

| Function | Signature | Does |
|----------|-----------|------|
| `from_cli(command: &str)` | `-> Result<FfmpegContext, CliError>` | Parses a single command string, returns a **plain `FfmpegContext`** you still `.build()?.start()?.wait()?` yourself |
| `from_cli_args(args: &[S])` (`S: AsRef<str>`) | `-> Result<FfmpegContext, CliError>` | Same, argv form — accepts `&[&str]`, `&[String]`, `&Vec<String>`. Tolerates/strips a leading `"ffmpeg"` token |
| `emit_rust_code(command: &str)` | `-> Result<String, CliError>` | Translates the command into a **complete, standalone Rust source file** (imports + `fn main`) — pure text generation, never touches FFmpeg |
| `emit_rust_code_from_args(args: &[S])` | `-> Result<String, CliError>` | Same, argv form |

```rust
use ez_ffmpeg::cli::from_cli_args;

from_cli_args(&["-i", "in.mkv", "-c:v", "libx264", "-crf", "23",
                "-preset", "fast", "-c:a", "aac", "-y", "out.mp4"])?
    .start()?
    .wait()?;
```

Three different error types can surface here: `from_cli_args(...)?` unwraps
`CliError`; `.start()?`/`.wait()?` unwrap the crate's ordinary
`error::Error` — a **successful** `from_cli_args()` return has only passed
tokenization, classification, and `build()` (opening the demuxer); it hasn't
decoded/encoded/muxed a single frame yet.

```toml
[dependencies.ez-ffmpeg]
version = "0.15.0"
features = ["cli"]
```

## Table of Contents

- [The verification model](#the-verification-model)
- [Runtime Profile Gate](#runtime-profile-gate-read-this-before-using-from_cli_args)
- [Supported option surface](#supported-option-surface)
- [Explicitly out of scope](#explicitly-out-of-scope)
- [Error diagnostics](#error-diagnostics)
- [Worked examples](#worked-examples)
- [Relationship to the manual mapping guide](#relationship-to-the-manual-mapping-guide)

## The verification model

Classification is three-tier, computed from a command's **fingerprint** (its
sorted set of scope-qualified option keys, e.g. `out:-c:v`, `in:-ss`):

| Classification | Meaning | `emit_rust_code` | `from_cli_args` |
|----------------|---------|:---:|:---:|
| **Verified** (6 shapes, `V1`–`V6`) | Fingerprint **and** key values **and** output extension all match a golden-tested shape | ✅ | ✅ (if the runtime gate also passes — see below) |
| **Unverified** (25 shapes) | Fingerprint matches a known combination, but values/extension aren't pinned — parses cleanly, no semantic golden behind it | ✅ (prints an `UNVERIFIED SCAFFOLDING` banner) | ❌ `CliError::NotVerified` |
| **Unmatched** | Fingerprint matches neither table | ❌ `CliError::UnmatchedShape` | ❌ `CliError::UnmatchedShape` |

**`emit_rust_code` always succeeds on a strictly broader set than
`from_cli_args` can execute** — use it as a scaffolding generator even for
commands you can't run through the facade directly.

The 6 verified (execute-capable) shapes:

| Shape | Recipe | Output ext |
|-------|--------|------------|
| V1 | H.264/AAC transcode (`-crf` + `-preset`) | `.mp4` |
| V2 | Re-encoded clip (input `-ss`, output `-t`) | `.mp4` |
| V3 | Audio extract (`-vn`, AAC) | `.m4a` |
| V4 | Single-frame thumbnail (input `-ss`, `-an`, mjpeg) | `.jpg` |
| V5 | Scaled H.264/AAC transcode (`-vf scale=...`) | `.mp4` |
| V6 | Single-rendition VOD HLS | `.m3u8` |

## Runtime Profile Gate (read this before using `from_cli_args`)

Even a **Verified**-shape command additionally requires the **linked FFmpeg
build** to match a `VERIFIED_PROFILES` entry — checked via
`avcodec_version()`/`avformat_version()` major.minor. As of 0.15.0 there is
**exactly one** verified profile: **FFmpeg 7.1** (avcodec 61.19 / avformat
61.7). **FFmpeg 8.1 is not yet listed** — a profile only earns its row once a
version-matched golden lane has run the semantic suite against that release.

**Practical consequence: on an FFmpeg 8.x system, `from_cli_args`/`from_cli`
refuse to execute *any* command today, even V1–V6 shapes**, failing with
`CliError::UnverifiedRuntimeProfile`. `emit_rust_code`/`emit_rust_code_from_args`
are unaffected — they never check the runtime profile, so they still work on
any linked FFmpeg version. Check `codec::get_encoders()` /
`avcodec_version()` first, or just use `emit_rust_code` and run the emitted
builder code (which has no such gate) if you're on FFmpeg 8.

A second execution-only gate: `-vf` shapes (V5) require the opened input to
have **exactly one** video stream — checked against the demuxer
`from_cli_args` actually opens (no separate probe, no TOCTOU window). A
multi-video-stream input fails as `CliError::AmbiguousFilterSource`. The
emitted Rust code for the same shape has no such check — it inherits the
plain builder's default stream-selection behavior instead.

## Supported option surface

30 option rows total. The common ones:

| CLI option(s) | Scope | Lowers to |
|---|---|---|
| `-y` | global | Mandatory — **required**, not optional (`MissingOverwriteFlag` without it) |
| `-loglevel`/`-v`, `-hide_banner`, `-nostdin`, `-stats`/`-nostats` | global | No-op (carried into comments) |
| `-ss` / `-t` / `-to` | input or output | `set_start_time_us` / `set_recording_time_us` / `set_stop_time_us` |
| `-f` | input or output | `set_format` |
| `-vn` / `-an` | output | `disable_video` / `disable_audio` |
| `-c:v` / `-c:a` | output | `set_video_codec` / `set_audio_codec` (or `"copy"`) |
| `-b:v` / `-b:a` | output | `set_video_bitrate` / `set_audio_bitrate` |
| `-crf` (libx264 only, 0–51), `-preset` (x264 whitelist) | output | `set_video_codec_opt` |
| `-pix_fmt`, `-ar`, `-ac` | output | `set_pix_fmt`, `set_audio_sample_rate`, `set_audio_channels` |
| `-frames:v 1` (exactly `1`) | output | `set_max_video_frames(1)` |
| `-vf` (single `scale=...` chain **only**) | output | `set_video_filter` |
| `-map` (basic index only: `0`, `0:v`, `0:a:1`) | output | `add_stream_map` / `add_stream_map_with_copy` |
| `-movflags +faststart` (exactly that value) | output | `set_format_opt("movflags", "+faststart")` |
| `-hls_time`, `-hls_playlist_type vod`, `-hls_list_size 0`, `-hls_segment_filename` | output | `set_format_opt(...)` |

**Structural rules**: exactly one `-i` and exactly one output path; canonical
order `[global/input opts] -i INPUT [output opts] OUTPUT [global opts]`; `-`
stdin/stdout pseudo-paths are rejected outright.

## Explicitly out of scope

Every rejection carries a **named reason**, not a generic "unknown option":

- **Unsplit/alias spellings** (each hints the correct form): `-c`, `-codec`,
  `-vcodec`/`-acodec`/`-scodec`, `-b`, `-filter:v`, `-vframes`.
- **Multi-input / multi-output commands** — a second `-i`, or two output
  paths, is rejected structurally (`overlay`, `concat`, tee — all need a
  future release).
- **`-map` beyond basic index form** — no `[label]`s, no `?`, no negative
  indices, no subtitle/data selectors.
- **Not yet in the subset, but the builder already supports it**:
  `-filter_complex`/`-lavfi`, `-af`, `-map_metadata`, `-metadata`,
  `-shortest` (→ `Output::set_shortest`), `-re`/`-readrate` (→
  `Input::set_readrate` — **this is why RTMP push via `-f flv rtmp://...`
  isn't runnable through this facade today**, even without `-re` the shape is
  `Unmatched`), `-stream_loop`, `-hwaccel`, `-force_key_frames`, `-attach`.
- **Permanent gaps**: `-pass`/`-passlogfile` (two-pass), per-stream-indexed
  forms (`-b:v:1`, `-crf:v:0`), `-q`/`-qscale`/`-r`/`-s`/`-g`/`-profile`/`-level`/`-threads`,
  `-fps_mode`/`-vsync`, `-n`, `-sn`/`-dn`, encrypted/multi-rendition HLS
  (`-hls_key_info_file`, `-var_stream_map` — use `HlsLadder` instead, see
  [streaming_rtmp_hls.md](../scenarios/streaming_rtmp_hls.md)).

If you need any of these today, use the manual mapping in
[cli_migration.md](cli_migration.md) — nearly all of them already have a
direct builder method.

## Error diagnostics

`CliError` (`#[non_exhaustive]`), every message ends with
*"want this supported? open an issue: .../ez-ffmpeg/issues"*:

| Variant | Carries |
|---------|---------|
| `Tokenize` | Byte offset in the original string + what's wrong |
| `UnsupportedOption` | Offending token, argv index, scope, reason, nearest-spelling hint |
| `UnsupportedValue` | The **value** token's own index + the grammar it violated |
| `UnsupportedLayout` | Structural violation (missing/duplicate files, bad ordering) |
| `ConflictingOptions` | Two options that can't coexist, each anchored to its first occurrence |
| `MissingOverwriteFlag` | No `-y` present |
| `NotVerified` / `UnmatchedShape` | The command's full fingerprint |
| `AmbiguousFilterSource` | Actual video-stream count found on open |
| `UnverifiedRuntimeProfile` | Linked avcodec/avformat versions vs. the verified list |
| `Build` | Wraps the crate's ordinary `error::Error` from context building |

Example — `ffmpeg -i in.mp4 -fps_mode cfr -y out.mp4`:
```
unsupported option `-fps_mode` (token #2, output #0)
  frame sync modes are permanently excluded: the crate models vsync per output, not per stream, so no -fps_mode form can be mapped faithfully
  want this supported? open an issue: https://github.com/YeautyYE/ez-ffmpeg/issues
```

## Worked examples

**Transcode (V1)** — `ffmpeg -i in.mkv -c:v libx264 -crf 23 -preset fast -c:a aac -y out.mp4`:
```rust
use ez_ffmpeg::{FfmpegContext, Output};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    FfmpegContext::builder()
        .input("in.mkv")
        .output(
            Output::from("out.mp4")
                .set_video_codec("libx264")
                .set_audio_codec("aac")
                .set_video_codec_opt("crf", "23")
                .set_video_codec_opt("preset", "fast"),
        )
        .build()?.start()?.wait()?;
    Ok(())
}
```

**Clip (V2)** — `ffmpeg -ss 10 -i in.mp4 -t 4 -c:v libx264 -crf 23 -c:a aac -y clip.mp4`:
```rust
use ez_ffmpeg::{FfmpegContext, Input, Output};

FfmpegContext::builder()
    .input(Input::from("in.mp4").set_start_time_us(10_000_000)) // -ss
    .output(
        Output::from("clip.mp4")
            .set_recording_time_us(4_000_000) // -t
            .set_video_codec("libx264")
            .set_audio_codec("aac")
            .set_video_codec_opt("crf", "23"),
    )
    .build()?.start()?.wait()?;
```

**Scaled transcode (V5)** — `ffmpeg -i in.mp4 -vf scale=1280:-2 -c:v libx264 -crf 23 -preset fast -c:a aac -y scaled.mp4`:
```rust
use ez_ffmpeg::{FfmpegContext, Output};

FfmpegContext::builder()
    .input("in.mp4")
    .output(
        Output::from("scaled.mp4")
            .set_video_codec("libx264")
            .set_audio_codec("aac")
            .set_video_codec_opt("crf", "23")
            .set_video_codec_opt("preset", "fast")
            .set_video_filter("scale=1280:-2"), // -vf scale=1280:-2
    )
    .build()?.start()?.wait()?;
```

**Not supported today** — `ffmpeg -re -i input.mp4 -c:v libx264 -c:a aac -f flv -y rtmp://localhost/live/stream`
fails with `UnsupportedOption` on `-re` ("readrate streaming is planned for a
future release; builder equivalent: `Input::set_readrate`"). RTMP push itself
is a first-class, fully supported builder capability
([streaming.md](streaming.md)) — it just isn't in this facade's current
6/25-shape manifest.

## Relationship to the manual mapping guide

**This is not "the same options, auto-converted" — it's a strictly smaller,
curated slice.** Every builder method the `cli` feature's manifest lowers to
already existed in, and is a proper subset of,
[cli_migration.md](cli_migration.md)'s hand-written table (~50 rows spanning
hardware accel, complex filtergraphs, bitstream filters, metadata, one-shot
recipes, device capture — none of which the `cli` manifest covers yet). The
feature adds no new builder capability; it adds only (a) a CLI-argv front end
over methods that already existed, and (b) a golden-tested verification
apparatus the hand-written docs never had. Broad CLI compatibility is an
explicit non-goal — chasing FFmpeg's ~14k lines of option machinery wholesale
produces "runs, but subtly different" failures.

**Use this feature when**: the command matches (or nearly matches) one of the
6 verified shapes and you want either to run it in-process with a
versioned correctness guarantee, or to bootstrap idiomatic builder code via
`emit_rust_code` (works even for the 25 unverified shapes, clearly labeled as
unverified scaffolding).

**Use [cli_migration.md](cli_migration.md)'s manual tables when**: the
command uses anything outside the 30-option/31-shape surface above — which
today includes hardware acceleration, complex filtergraphs, RTMP/HLS live
push, bitstream filters, `-shortest`, forced keyframes, and multi-input
commands (overlay, concat, tee).
