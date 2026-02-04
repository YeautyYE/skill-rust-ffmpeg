# FFmpeg Installation Guide

**Detection Keywords**: install ffmpeg, setup, compilation, linking error, library not found, build from source, vcpkg, homebrew
**Aliases**: installation, setup guide, dependency, linking

Comprehensive platform-specific installation for FFmpeg library development in Rust.

## Table of Contents

- [Related Guides](#related-guides)
- [Quick Reference](#quick-reference)
- [macOS](#macos)
- [Linux](#linux)
- [Windows](#windows)
- [Build Configuration](#build-configuration)
- [Docker/CI Configuration](#dockerci-configuration)
- [Verification](#verification)
- [Version Compatibility](#version-compatibility)
- [Fallback: Build from Source](#fallback-build-from-source)
- [Last Resort: ffmpeg-sidecar](#last-resort-ffmpeg-sidecar)

## Related Guides

| Guide | Content |
|-------|---------|
| [ez_ffmpeg.md](ez_ffmpeg.md) | High-level API (sync and async) |
| [ffmpeg_sidecar.md](ffmpeg_sidecar.md) | Alternative: no-install binary approach |

## Quick Reference

| Platform | Recommended Command | Linking |
|----------|---------------------|---------|
| **macOS** | `brew install ffmpeg` | Dynamic |
| **Ubuntu/Debian** | `sudo apt install libavcodec-dev libavformat-dev libavutil-dev libavfilter-dev libavdevice-dev libswscale-dev libswresample-dev pkg-config clang` | Dynamic |
| **Windows** | `vcpkg install ffmpeg:x64-windows-static-md` + set `VCPKG_ROOT` env | Static |
| **Any (fallback)** | `features = ["build"]` in Cargo.toml | Static (from source) |

## Installation Priority

**Recommended order**: System package manager → `static` feature → `build` feature → ffmpeg-sidecar

---

## macOS

### Homebrew (Recommended)

```bash
brew install ffmpeg

# Verify
pkg-config --modversion libavcodec  # Should show 61.x for FFmpeg 7.x
```

### MacPorts (Alternative)

```bash
sudo port install ffmpeg
```

### Apple Silicon (M1/M2/M3/M4)

Homebrew installs to `/opt/homebrew` on Apple Silicon. Ensure environment is configured:

```bash
# Install (same command works for Intel and ARM)
brew install ffmpeg

# Verify architecture
file $(brew --prefix)/lib/libavcodec.dylib
# Should show: Mach-O 64-bit dynamically linked shared library arm64

# Set PKG_CONFIG_PATH (critical for Apple Silicon)
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"
export LIBRARY_PATH="/opt/homebrew/lib:$LIBRARY_PATH"

# Add to ~/.zshrc for persistence
echo 'export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"' >> ~/.zshrc
echo 'export LIBRARY_PATH="/opt/homebrew/lib:$LIBRARY_PATH"' >> ~/.zshrc
```

**Cross-compilation (Intel target on Apple Silicon)**:
```bash
# Install x86_64 FFmpeg via Rosetta
arch -x86_64 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
arch -x86_64 /usr/local/bin/brew install ffmpeg

# Build for Intel
CARGO_BUILD_TARGET=x86_64-apple-darwin cargo build --release
```

**Hardware acceleration on Apple Silicon**:
- VideoToolbox is fully supported
- Use `h264_videotoolbox` / `hevc_videotoolbox` encoders
- No additional configuration needed

### Troubleshooting macOS

**`ld: library not found for -lavcodec`**:
```bash
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"
# Add to ~/.zshrc for persistence
```

**LTO errors**: Add `lto = false` to `[profile.release]` in Cargo.toml

---

## Linux

### Ubuntu/Debian

```bash
sudo apt update && sudo apt install -y \
    libavcodec-dev libavformat-dev libavutil-dev \
    libavfilter-dev libavdevice-dev libswscale-dev \
    libswresample-dev pkg-config clang
```

### Fedora/RHEL

```bash
# Enable RPM Fusion first
sudo dnf install -y https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
sudo dnf install -y ffmpeg-devel pkg-config clang
```

### Arch Linux

```bash
sudo pacman -S ffmpeg pkg-config clang
```

### Alpine (Docker)

```bash
apk add --no-cache ffmpeg-dev pkgconfig clang build-base
```

### Troubleshooting Linux

**`could not find native static library 'avcodec'`**: Install `-dev` packages (see above)

**Version mismatch**: Check `pkg-config --modversion libavcodec` matches crate requirements

---

## Windows

### vcpkg (Recommended for Distribution)

```powershell
# One-time setup
git clone https://github.com/microsoft/vcpkg.git
cd vcpkg
.\bootstrap-vcpkg.bat
.\vcpkg integrate install

# Install FFmpeg with common features
.\vcpkg install ffmpeg[core,avcodec,avformat,avfilter,avdevice,swresample,swscale,x264,x265,zlib]:x64-windows-static-md --recurse
```

**Environment variables**:
```powershell
$env:VCPKG_ROOT = "C:\path\to\vcpkg"
$env:VCPKGRS_DYNAMIC = "0"  # Force static linking
```

**Cargo.toml**:
```toml
[dependencies]
ez-ffmpeg = { version = "0.10.0", features = ["static"] }
# OR
ffmpeg-next = { version = "7.1.0", features = ["static"] }
```

### MSYS2 (Alternative - Dynamic)

```bash
# In MSYS2 MINGW64 terminal
pacman -S mingw-w64-x86_64-ffmpeg mingw-w64-x86_64-pkg-config
```

Add `C:\msys64\mingw64\bin` to PATH.

### Troubleshooting Windows

**DLL not found at runtime**: Copy DLLs to executable directory or use static linking

**Binary size too large**: Use `strip = true` and `opt-level = "z"` in `[profile.release]`

---

## Build Configuration

### Recommended `.cargo/config.toml`

```toml
[target.x86_64-pc-windows-msvc]
rustflags = ["-C", "target-feature=+crt-static"]

[target.x86_64-apple-darwin]
rustflags = ["-C", "link-args=-Wl,-rpath,/opt/homebrew/lib"]

[target.aarch64-apple-darwin]
rustflags = ["-C", "link-args=-Wl,-rpath,/opt/homebrew/lib"]
```

### Recommended `Cargo.toml` Profile

```toml
[profile.release]
strip = true
opt-level = "z"       # Size optimization (use "3" for speed)
lto = false           # Required for vcpkg FFmpeg
codegen-units = 1
panic = "abort"
```

---

## Docker/CI Configuration

### Debian Dockerfile

```dockerfile
FROM rust:1.75-slim
RUN apt-get update && apt-get install -y \
    libavcodec-dev libavformat-dev libavutil-dev \
    libavfilter-dev libswscale-dev pkg-config clang \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN cargo build --release
```

### Alpine Dockerfile (Smaller)

```dockerfile
FROM rust:1.75-alpine
RUN apk add --no-cache ffmpeg-dev pkgconfig clang musl-dev
WORKDIR /app
COPY . .
RUN cargo build --release
```

### GitHub Actions

```yaml
jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
    - uses: actions/checkout@v4
    - name: Install FFmpeg (Ubuntu)
      if: matrix.os == 'ubuntu-latest'
      run: sudo apt-get update && sudo apt-get install -y libavcodec-dev libavformat-dev libavutil-dev libavfilter-dev libswscale-dev libswresample-dev pkg-config clang
    - name: Install FFmpeg (macOS)
      if: matrix.os == 'macos-latest'
      run: brew install ffmpeg
    - name: Install FFmpeg (Windows) - Use build feature
      if: matrix.os == 'windows-latest'
      run: echo "Using build feature - no system FFmpeg needed"
    - run: cargo build --release
      env:
        # Windows: use build feature to compile FFmpeg from source
        # Alternatively, set up vcpkg for faster builds (see installation.md)
        CARGO_FEATURE_BUILD: ${{ matrix.os == 'windows-latest' && '1' || '' }}
    - run: cargo test --release
```

**Note**: For Windows CI, we recommend the `build` feature (compiles FFmpeg from source) or vcpkg setup. Chocolatey's `ffmpeg` package provides CLI binaries only, not development libraries needed for linking.

---

## Verification

### macOS / Linux

```bash
# Check FFmpeg version
ffmpeg -version  # Should show 7.x

# Check library versions
pkg-config --modversion libavcodec   # 61.x for FFmpeg 7.x
pkg-config --modversion libavformat  # 61.x
pkg-config --modversion libavutil    # 59.x

# Test build
cargo new --bin ffmpeg_test && cd ffmpeg_test
echo 'ez-ffmpeg = "0.10.0"' >> Cargo.toml
cargo build --release
```

### Windows (vcpkg)

```powershell
# Verify vcpkg installation
vcpkg list | Select-String ffmpeg

# Verify integration
vcpkg integrate install

# Test build (pkg-config/ffmpeg CLI may not be available)
cargo new --bin ffmpeg_test
cd ffmpeg_test
Add-Content Cargo.toml 'ez-ffmpeg = { version = "0.10.0", features = ["static"] }'
cargo build --release
```

**Note**: On Windows with vcpkg, `ffmpeg -version` and `pkg-config` are typically unavailable. Verify installation via `vcpkg list` and test with a Cargo build.

---

## Version Compatibility

| Library | Version | FFmpeg Required | libavcodec Version |
|---------|---------|-----------------|-------------------|
| ez-ffmpeg | 0.10.0 | 7.x | 61.x |
| ffmpeg-next | 7.x | 7.x | 61.x |
| ffmpeg-next | 6.x | 6.x | 60.x |
| ffmpeg-next | 5.x | 5.x | 59.x |

---

## Fallback: Build from Source

When system FFmpeg installation is impossible (restricted environments, no admin access), use the `build` feature to compile FFmpeg from source during Rust build.

### Configuration

```toml
[dependencies]
# ffmpeg-next
ffmpeg-next = { version = "7.1.0", features = ["build"] }

# ez-ffmpeg (inherits build capability)
ez-ffmpeg = { version = "0.10.0", features = ["build"] }

# With GPL codecs (x264, x265)
ffmpeg-next = { version = "7.1.0", features = ["build", "build-license-gpl"] }
```

### Requirements

- C compiler (gcc/clang/MSVC)
- Build tools (make, cmake, pkg-config)
- Internet connection
- ~500MB disk space
- 5-15 minute build time

### Platform Setup for Build Feature

**macOS**: `xcode-select --install`

**Ubuntu/Debian**: `sudo apt-get install build-essential cmake pkg-config`

**Windows**: Install Visual Studio Build Tools with C++ workload

### Trade-offs

| Pros | Cons |
|------|------|
| No system FFmpeg needed | Long build time (5-15 min) |
| Full functionality | Large artifacts (~500MB) |
| Consistent version | Requires C compiler |

### When to Use

- CI/CD without pre-installed FFmpeg
- Docker builds you control
- Dev machines without admin access
- Ensuring version consistency

### When NOT to Use

- Production (prefer system packages for security updates)
- Strict build time constraints
- No compiler available

---

## Last Resort: ffmpeg-sidecar

If `build` feature is not viable (no compiler, extremely restricted), see [ffmpeg_sidecar.md](ffmpeg_sidecar.md).

**Trade-offs**: No custom filters, no frame access, IPC overhead. Only use when library integration is impossible.
