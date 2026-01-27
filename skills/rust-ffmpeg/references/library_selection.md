# Library Selection Guide

**Detection Keywords**: which library, choose library, compare libraries, library comparison, best library, recommendation
**Aliases**: library choice, library decision, which crate, compare crates

Quick reference for choosing the right Rust FFmpeg library.

## Decision Matrix

| Your Need | Choose | Why | Trade-off |
|-----------|--------|-----|-----------|
| Async/await support | ez-ffmpeg | Only library with native async | Requires FFmpeg libs installed |
| Simplest API | ez-ffmpeg | Builder pattern, high-level | Less fine-grained control |
| CLI migration | ez-ffmpeg | Direct FFmpeg CLI mapping | Abstraction overhead |
| Frame-level control | ffmpeg-next | Access to codec internals | More boilerplate code |
| Mix with ez-ffmpeg | ffmpeg-next | Compatible, complementary | Two dependencies |
| Maximum performance | ffmpeg-sys-next | Zero-copy, unsafe FFI | Requires unsafe code |
| Custom memory | ffmpeg-sys-next | Direct C API access | Manual memory management |
| No FFmpeg install | ffmpeg-sidecar | Binary wrapper approach | Process overhead, no frame access |
| CLI-style interface | ffmpeg-sidecar | Process-based | Limited real-time control |

## Detailed Criteria

### Choose ez-ffmpeg when:
- You need async/await support (only option)
- You want the simplest API with builder pattern
- You're migrating from FFmpeg CLI commands
- You need embedded high-concurrency RTMP server
- You're building production applications with standard workflows

**Trade-offs**: Requires FFmpeg development libraries installed; less fine-grained control than ffmpeg-next.

### Choose ffmpeg-next when:
- You need frame-level control and codec internals
- You want to combine with ez-ffmpeg for hybrid workflows
- You need specific codec operations not exposed by ez-ffmpeg
- You need stream-level access and manipulation

**Trade-offs**: More boilerplate code; no async support; steeper learning curve.

### Choose ffmpeg-sys-next when:
- You need maximum performance with zero-copy operations
- You're comfortable with unsafe Rust code
- You need custom memory management or buffer handling
- You need direct access to FFmpeg C APIs not wrapped by higher-level crates

**Trade-offs**: Requires unsafe code; manual memory management; no safety guarantees.

### Choose ffmpeg-sidecar when:
- You cannot install FFmpeg development libraries (restricted environments)
- You prefer CLI-style interface with process isolation
- You need to bundle FFmpeg binary with your application
- You're doing batch processing without real-time requirements

**Trade-offs**: Process overhead; no direct frame access; limited real-time control.
