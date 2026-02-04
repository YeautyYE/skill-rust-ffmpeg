# ffmpeg-sidecar: Setup

**Detection Keywords**: sidecar install, download ffmpeg, auto download, ffmpeg binary, path setup, feature flag
**Aliases**: installation, setup, binary download

Installation guide, auto-download features, and platform-specific configuration for ffmpeg-sidecar.

> **Dependencies**: Examples use `anyhow` for error handling:
> ```toml
> [dependencies]
> ffmpeg-sidecar = "2.4.0"
> anyhow = "1"
> ```

## Related Guides

| Guide | Content |
|-------|---------|
| [core.md](core.md) | Core API (FfmpegCommand, FfmpegChild, FfmpegIterator) |
| [recipes.md](recipes.md) | Quick-start examples and common use cases |
| [troubleshooting.md](troubleshooting.md) | Error handling, best practices |

## Basic Installation

```toml
[dependencies]
ffmpeg-sidecar = "2.4.0"
```

**Prerequisites**: FFmpeg binary must be in PATH, or use the `download_ffmpeg` feature for automatic installation.

## Feature Flags

```toml
[dependencies.ffmpeg-sidecar]
version = "2.4.0"
features = ["download_ffmpeg", "named_pipes"]
```

### Available Features

| Feature | Description | Platforms |
|---------|-------------|-----------|
| `download_ffmpeg` | Auto-download FFmpeg binaries | Windows, macOS, Linux x86_64/arm64 |
| `named_pipes` | Cross-platform named pipe support | All platforms |

## Auto-Download FFmpeg

The `download_ffmpeg` feature automatically downloads and installs FFmpeg binaries for your platform.

### Quick Start

```rust
use ffmpeg_sidecar::download::auto_download;

fn main() -> anyhow::Result<()> {
    // Check if FFmpeg is installed, download if missing
    auto_download()?;

    // Now you can use FFmpeg commands
    Ok(())
}
```

### With Progress Callback

```rust
use ffmpeg_sidecar::download::{auto_download_with_progress, FfmpegDownloadProgressEvent};
use std::io::Write;

fn main() -> anyhow::Result<()> {
    auto_download_with_progress(|event| {
        match event {
            FfmpegDownloadProgressEvent::Starting => {
                println!("Starting download...");
            }
            FfmpegDownloadProgressEvent::Downloading { downloaded_bytes, total_bytes } => {
                print!(
                    "\rDownloaded {:.1}/{:.1} MB    ",
                    downloaded_bytes as f64 / 1024.0 / 1024.0,
                    total_bytes as f64 / 1024.0 / 1024.0
                );
                std::io::stdout().flush().unwrap();
            }
            FfmpegDownloadProgressEvent::UnpackingArchive => {
                println!("\nUnpacking archive...");
            }
            FfmpegDownloadProgressEvent::Done => {
                println!("FFmpeg downloaded successfully!");
            }
        }
    })?;

    Ok(())
}
```

### Manual Download Control

For advanced use cases, you can manually control the download process:

```rust
use ffmpeg_sidecar::{
    command::ffmpeg_is_installed,
    download::{
        check_latest_version,
        download_ffmpeg_package,
        ffmpeg_download_url,
        unpack_ffmpeg
    },
    paths::sidecar_dir,
    version::ffmpeg_version_with_path,
};

fn manual_download() -> anyhow::Result<()> {
    // Check if already installed
    if ffmpeg_is_installed() {
        println!("FFmpeg is already installed!");
        return Ok(());
    }

    // Check latest version (optional)
    match check_latest_version() {
        Ok(version) => println!("Latest version: {}", version),
        Err(_) => println!("Version check not available on this platform"),
    }

    // Get platform-specific download URL
    let download_url = ffmpeg_download_url()?;
    let destination = sidecar_dir()?;

    // Download package
    println!("Downloading from: {}", download_url);
    let archive_path = download_ffmpeg_package(download_url, &destination)?;

    // Extract archive
    println!("Extracting...");
    unpack_ffmpeg(&archive_path, &destination)?;

    // Verify installation
    let version = ffmpeg_version_with_path(destination.join("ffmpeg"))?;
    println!("FFmpeg version: {}", version);

    Ok(())
}
```

## Platform Support

### Supported Platforms

| Platform | Architecture | Download Source |
|----------|--------------|-----------------|
| Windows | x86_64 | gyan.dev |
| macOS Intel | x86_64 | evermeet.cx |
| macOS Apple Silicon | arm64 | osxexperts.net |
| Linux | x86_64 | johnvansickle.com |
| Linux | arm64 | johnvansickle.com |

### Download URLs

The library automatically selects the correct download URL based on your platform:

- **Windows**: `https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip`
- **macOS Intel**: `https://evermeet.cx/ffmpeg/getrelease/zip`
- **macOS M1/M2**: `https://www.osxexperts.net/ffmpeg80arm.zip`
- **Linux x86_64**: `https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz`
- **Linux arm64**: `https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz`

## Version Checking

```rust
use ffmpeg_sidecar::version::{ffmpeg_version, ffmpeg_version_with_path};
use ffmpeg_sidecar::command::ffmpeg_is_installed;

fn check_installation() -> anyhow::Result<()> {
    // Check if FFmpeg is in PATH
    if ffmpeg_is_installed() {
        // Get version from PATH
        let version = ffmpeg_version()?;
        println!("FFmpeg version: {}", version);
    } else {
        println!("FFmpeg not found in PATH");
    }

    // Check specific binary path
    let custom_path = "/usr/local/bin/ffmpeg";
    match ffmpeg_version_with_path(custom_path) {
        Ok(version) => println!("Custom FFmpeg version: {}", version),
        Err(e) => println!("Custom path not found: {}", e),
    }

    Ok(())
}
```

## Custom Installation Paths

By default, FFmpeg is installed to the "sidecar" directory next to your executable. You can customize this:

```rust
use ffmpeg_sidecar::download::{download_ffmpeg_package, ffmpeg_download_url, unpack_ffmpeg};
use std::path::PathBuf;

fn custom_install_path() -> anyhow::Result<()> {
    let download_url = ffmpeg_download_url()?;
    let custom_destination = PathBuf::from("/opt/my-app/ffmpeg");

    // Download to custom location
    let archive_path = download_ffmpeg_package(download_url, &custom_destination)?;
    unpack_ffmpeg(&archive_path, &custom_destination)?;

    println!("FFmpeg installed to: {:?}", custom_destination);
    Ok(())
}
```

## Troubleshooting

### FFmpeg Not Found

If `ffmpeg_is_installed()` returns false:

1. **Check PATH**: Ensure FFmpeg binary is in your system PATH
2. **Use auto_download()**: Enable the `download_ffmpeg` feature
3. **Manual installation**: Download FFmpeg from official sources
4. **Custom path**: Use `FfmpegCommand::new_with_path()` to specify binary location

```rust
use ffmpeg_sidecar::command::FfmpegCommand;

let mut cmd = FfmpegCommand::new_with_path("/custom/path/to/ffmpeg");
```

### Download Failures

If auto-download fails:

- **Network issues**: Check internet connection and firewall settings
- **Platform unsupported**: Verify your platform is in the supported list
- **Disk space**: Ensure sufficient disk space (typically 50-100 MB)
- **Permissions**: Check write permissions for the destination directory

### Version Mismatches

If you encounter version-related issues:

```rust
use ffmpeg_sidecar::download::check_latest_version;

// Check available version before downloading
match check_latest_version() {
    Ok(version) => println!("Latest available: {}", version),
    Err(e) => println!("Version check failed: {}", e),
}
```

## Best Practices

1. **Call auto_download() early**: Run it at application startup before any FFmpeg operations
2. **Handle errors gracefully**: Provide fallback options if download fails
3. **Cache installations**: The library automatically caches downloaded binaries
4. **Version pinning**: Consider pinning FFmpeg versions for reproducible builds
5. **Offline support**: Pre-download FFmpeg for offline/air-gapped environments

## Next Steps

- [Core API Reference](core.md) - Learn the FfmpegCommand, FfmpegChild, and FfmpegIterator APIs
- [Common Recipes](recipes.md) - Quick start with common use cases
- [Video Processing](video.md) - Video encoding, decoding, and frame manipulation
