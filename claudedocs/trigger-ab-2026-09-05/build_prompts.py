#!/usr/bin/env python3
"""Build A/B routing prompts: three listing arms x one shared query set."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
old = Path(__file__).with_name("desc_old_239w.txt").read_text().strip()
new = Path(__file__).with_name("desc_new_112w.txt").read_text().strip()
arms = {"old_full": old, "old_trunc": old[:1536], "new": new}

DECOYS = [
    ("codex-implement", "Generates new code (functions, files, classes, components, services) through the Codex CLI. Use when the user asks to write, create, add, implement or generate new code."),
    ("module-docs", "Authors module-level README.md and DESIGN.md following the module standard. Use after creating a new module or crate, or when module docs are missing."),
    ("python-video-tools", "Video and audio editing in Python with moviepy, OpenCV and ffmpeg-python: cut, concatenate, convert, add text. Use when the user works in Python on media files."),
    ("gstreamer-rust", "GStreamer pipelines in Rust with gstreamer-rs: element graphs, appsrc/appsink, RTSP, playbin. Use when the user asks about GStreamer or gst-launch."),
    ("image-processing-rust", "Still-image manipulation in Rust with the image, imageproc and resvg crates: resize, crop, convert PNG/JPEG/WebP, draw text, EXIF. Use for image (not video) tasks in Rust."),
    ("webrtc-signaling", "Designs WebRTC signaling servers, SDP negotiation and STUN/TURN configuration in Node or Go. Use for peer-connection setup and NAT traversal."),
    ("should-build", "Structured product decision analysis before building a feature. Use when the user proposes a new feature, business capability or third-party integration."),
    ("audio-dsp-rust", "Real-time audio DSP in Rust with cpal, dasp and fundsp: synthesizers, effects, low-latency callbacks. Use for audio synthesis or effects code, not file transcoding."),
]

POS = [
    "avformat_find_stream_info",
    "AVSEEK_SIZE custom seek callback",
    "视频转码",
    "Wie transkodiere ich ein Video in Rust?",
    "make this video smaller in Rust",
    "ez-ffmpeg vs ffmpeg-next",
    "EBU R128 integrated loudness",
    "v4l2 camera capture",
    "FrameExtractor RGB output changed",
    "PacketSink avcC AudioSpecificConfig",
    "from_cli_args emits Rust code",
    "StreamMap -c:v:0",
    "WHIP capability probe",
    "h264_mp4toannexb",
    "set_video_filter",
    "WGSL chroma key",
    "burn subtitles without libass in Rust",
    "video plus longer music track -shortest",
    "blackdetect silencedetect QC pass",
    "HDR to SDR washed out colors",
    "progress bar for a Rust transcode",
    "generate a test video with testsrc",
    "embedded RTMP server in Rust",
    "whisper PCM 16 kHz mono ingest",
    "thumbnail sprite sheet recipe",
]
HARD = [
    "make an animated GIF from an mp4 in Rust",
    "capture from avfoundation on macOS in Rust",
    "build an ABR ladder for HLS in Rust",
    "write chapters and metadata into an mp4 with Rust",
    "10-bit VP9 encode in Rust",
    "AVPacket lifetime and av_packet_unref in ffmpeg-sys-next",
    "scene change detection in a Rust transcode pipeline",
    "get decoded video frames as tensors for a PyTorch model from Rust",
    "aac_adtstoasc when remuxing to mp4 in Rust",
    "forced keyframes every 2 seconds for HLS segments in Rust",
]
NEG = [
    "resize a PNG to 256x256 with the image crate",
    "trim a video with moviepy in Python",
    "build a GStreamer pipeline with appsrc in Rust",
    "set up STUN/TURN for my WebRTC signaling server in Go",
    "write a low-latency sine synthesizer with cpal",
    "should we add video upload to our SaaS product?",
    "write a README for my new Rust crate",
    "implement a REST endpoint in axum",
    "what's the difference between Vec and VecDeque",
    "convert this PDF to markdown",
]

queries = [("P%02d" % (i + 1), q) for i, q in enumerate(POS)]
queries += [("H%02d" % (i + 1), q) for i, q in enumerate(HARD)]
queries += [("N%02d" % (i + 1), q) for i, q in enumerate(NEG)]
(OUT / "queries.json").write_text(json.dumps(queries, ensure_ascii=False, indent=0))

for arm, desc in arms.items():
    entries = DECOYS[:3] + [("rust-ffmpeg", desc)] + DECOYS[3:]
    listing = "\n".join(f"- {name}: {d}" for name, d in entries)
    qtext = "\n".join(f"{qid}\t{q}" for qid, q in queries)
    prompt = f"""You are simulating Claude Code's automatic skill routing. Do NOT use any tools, do NOT read files, do NOT consult skills available in your own environment. Use ONLY the skill listing below.

The listing below is exactly what appears in the system prompt as available skills:

{listing}

For EACH user query below, decide which single skill (if any) Claude Code should invoke before doing anything else. Answer "none" if no skill fits. Judge each query independently on the listing text alone.

Queries (id<TAB>query):
{qtext}

Return ONLY a JSON object mapping every query id to the chosen skill name or "none", e.g. {{"P01": "rust-ffmpeg", "N01": "none"}}. No commentary."""
    (OUT / f"prompt_{arm}.txt").write_text(prompt)
    print(arm, len(desc), "chars desc;", len(prompt), "chars prompt")
