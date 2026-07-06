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
| ez_ffmpeg/filters.md + scenarios/hardware_acceleration.md | GPU custom filter, WGSL shader, WgpuFrameFilter, headless GPU | wgpu, compute shader |
| scenarios/subtitles.md | native subtitle burn-in, SubtitleFilter, pure-Rust subtitle, no libass | hardsub, force_style |
| scenarios/debugging.md + scenarios/audio_extraction.md | detection, measurement, blackdetect, silencedetect, EBU R128, Analysis runner | QC, loudness measure |
| scenarios/image_sequences.md + gif_creation.md + streaming_rtmp_hls.md | thumbnail, sprite sheet, animated gif, HLS ABR ladder, one-shot recipe | HlsLadder, storyboard |
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
| hardware_acceleration.md | hardware acceleration, GPU encoding, progress monitor, GPU filter backend, custom shader, wgpu, WGSL, libplacebo | nvenc, videotoolbox |
| batch_processing.md | batch processing, multiple files, bulk convert, parallel encode | bulk, multi-file |
| subtitles.md | subtitles, srt, ass, vtt, burn subtitles, embed subtitles, native burn-in, without libass | captions, subs |
| debugging.md | detect black frames, silence detect, scene detect, cropdetect, EBU R128, LUFS, measure loudness, content analysis, QC | blackdetect, silencedetect |
| gif_creation.md | animated gif, gif recipe, palettegen, gif loop, gif dither | gif, video to gif |
| image_sequences.md | thumbnail recipe, sprite sheet, storyboard, contact sheet, frame extraction | thumbnails, tiles |

## Validation Rules

1. Each file MUST have Detection Keywords
2. Keywords should be lowercase
3. No keyword should appear in more than 2 files
4. Aliases provide alternative spellings/abbreviations
5. Update this document when adding new keywords
