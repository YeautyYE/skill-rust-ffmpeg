# Detection Keywords Standard

> **Note**: This is an internal maintenance document for skill authors. Not linked from SKILL.md.

Internal reference for maintaining consistent Detection Keywords across the skill.

## Format Standard

```markdown
**Detection Keywords**: keyword1, keyword2, keyword3, keyword4, keyword5
**Aliases**: alias1, alias2, alias3
```

- **Location**: After the title (H1), before the first H2 section
- **Count**: 5-8 primary keywords + 3-5 aliases
- **Style**: Lowercase, user-facing terms (not code identifiers)

## Design Principles

1. **User Intent**: What would a user type when looking for this?
2. **Action-Oriented**: Prefer verbs (extract, convert, stream) over nouns
3. **No Overlap**: Minimize keyword duplication across files
4. **Specificity**: More specific keywords route better than generic ones

## Keywords by Library

### ez-ffmpeg Keywords
| File | Primary Keywords | Aliases |
|------|------------------|---------|
| ez_ffmpeg.md | high-level API, simple transcoding, builder pattern, rust ffmpeg easy | ez-ffmpeg, ezffmpeg |
| video_transcoding.md | transcode video, convert format, change container, video to mp4 | convert, basic |
| filters.md | video filter, audio filter, scale, crop, overlay, drawtext | filter chain, vf, af |
| streaming_rtmp_hls.md | RTMP output, HLS output, live streaming output | stream to, broadcast |
| frame_filter.md | custom filter, frame processing, pixel manipulation, rust callback | FrameFilter trait |
| async_processing.md | async ffmpeg, tokio integration, non-blocking, concurrent | async, await |
| device_enumeration.md | list devices, available cameras, input devices | webcam list, mic list |
| metadata.md | read duration, get codec info, video properties | probe, info |

### ffmpeg-next Keywords
| File | Primary Keywords | Aliases |
|------|------------------|---------|
| ffmpeg_next.md | rust bindings, medium-level API, codec control, frame access | ffmpeg-next |
| video.md | seeking, seek position, jump to time, timestamp | seek, position |
| transcoding.md | H.264 transcoding, frame extraction, dump frames, thumbnail | h264, x264, encode |
| output.md | save as PNG, save as JPEG, image output, remux container | png, jpg, mux |
| audio.md | audio resampling, sample rate conversion, audio format | resample, audio convert |
| filters.md | filter graph, complex filter, filtergraph API | filter_complex |
| streaming.md | RTMP input, HLS input, network input, stream source | receive stream |
| metadata.md | read metadata, stream info, chapter info | tags, properties |
| ffi.md | unsafe FFmpeg, raw pointer, AVFrame direct, C API | ffmpeg-sys, ffi |

### ffmpeg-sidecar Keywords
| File | Primary Keywords | Aliases |
|------|------------------|---------|
| ffmpeg_sidecar.md | CLI wrapper, subprocess, binary approach, no compilation | sidecar, subprocess |
| command_builder.md | FfmpegCommand, fluent API, command construction | builder, cmd |
| event_handling.md | progress event, FfmpegEvent, parse output, callback | progress, events |
| iterator_patterns.md | frame iterator, output iterator, streaming frames | iter, frames |
| binary_management.md | download ffmpeg, bundle binary, locate executable | binary, executable |
| error_handling.md | error recovery, retry logic, timeout handling | error, timeout |
| testing.md | mock ffmpeg, test helpers, integration testing | test, mock |
| cross_platform.md | windows ffmpeg, macos ffmpeg, linux ffmpeg | platform, os |
| ci_cd.md | github actions ffmpeg, docker ffmpeg, CI setup | ci, cd, github |

### ffmpeg-sys-next Keywords
| File | Primary Keywords | Aliases |
|------|------------------|---------|
| ffmpeg_sys_next.md | unsafe bindings, raw FFmpeg, direct C API, zero-copy | sys, ffi, unsafe |
| memory.md | AVFrame allocation, buffer management, manual free | alloc, dealloc, memory |
| hwaccel.md | hardware context, CUDA setup, VAAPI setup, device init | hw, gpu, cuda |
| custom_io.md | custom AVIOContext, memory IO, callback IO | avio, custom read |

### Performance Scenarios Keywords
| File | Primary Keywords | Aliases |
|------|------------------|---------|
| audio_extraction.md | first frame, thumbnail, audio extract, metadata read | poster, preview |
| transcoding.md | multi-output, concat videos, watermark, decode-encode | merge, join, overlay |
| streaming_rtmp_hls.md | real-time, RTMP, HLS, TCP socket, screen capture | live, broadcast, capture |
| hardware_acceleration.md | hardware acceleration, GPU encoding, progress monitor | nvenc, videotoolbox |
| batch_processing.md | batch processing, multiple files, bulk convert, parallel encode | bulk, multi-file |
| subtitles.md | subtitles, srt, ass, vtt, burn subtitles, embed subtitles | captions, subs |

## Validation Rules

1. Each file MUST have Detection Keywords
2. Keywords should be lowercase
3. No keyword should appear in more than 2 files
4. Aliases provide alternative spellings/abbreviations
5. Update this document when adding new keywords
