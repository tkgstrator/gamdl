# Gamdl (Glomatico's Apple Music Downloader)

A command-line app for downloading Apple Music songs, music videos and post videos.

## Features

- High-Quality Songs - Download songs in AAC 256kbps and other codecs
- High-Quality Music Videos - Download music videos in resolutions up to 4K
- Synced Lyrics - Download synced lyrics in LRC, SRT, or TTML formats
-️ Rich Metadata - Automatic tagging with comprehensive metadata
- Artist Support - Download all albums or music videos from an artist
- Highly Customizable - Extensive configuration options for advanced users

## Prerequisites

- Docker
- VSCode

The following tools are also included:

- **[MP4Box](https://github.com/gpac/gpac)**
    - Required for mp4box remux mode, music videos, and experimental codecs
- **[mp4decrypt](https://www.bento4.com/downloads/)**
    - Required for mp4box remux mode
- **[N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE.git)**
    - Required for nm3u8dlre download mode, which is faster than the default downloader
- **[wrapper](https://github.com/WorldObservationLog/wrapper) & [amdecrypt](https://github.com/glomatico/amdecrypt)**
    - For downloading songs in ALAC and other experimental codecs without API limitations

## Installation

### Setup cookies

1. Place your cookies file in the working directory as cookies.txt, or
2. Specify the path using --cookies-path or in the config file

> To get cookies, use the following tool and export in Netscape format.

- [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)

## Usage

```zsh
gamdl [OPTIONS] URLS...
```

### Supported URL Types

- Songs
- Albums (Public/Library)
- Playlists (Public/Library)
- Music Videos
- Artists
- Post Videos

#### Interactive Prompt Controls

| Key            | Action            |
| -------------- | ----------------- |
| **Arrow keys** | Move selection    |
| **Space**      | Toggle selection  |
| **Ctrl + A**   | Select all        |
| **Enter**      | Confirm selection |

## Configuration

The file is created automatically on first run. Command-line arguments override config values.

### Configuration options

| Option                          | Description                     | Default                                        |
| ------------------------------- | ------------------------------- | ---------------------------------------------- |
| **General Options**             |                                 |                                                |
| `--read-urls-as-txt`, `-r`      | Read URLs from text files       | `false`                                        |
| `--config-path`                 | Config file path                | `<home>/.gamdl/config.ini`                     |
| `--log-level`                   | Logging level                   | `INFO`                                         |
| `--log-file`                    | Log file path                   | -                                              |
| `--no-exceptions`               | Don't print exceptions          | `false`                                        |
| `--no-config-file`, `-n`        | Don't use a config file         | `false`                                        |
| **Apple Music Options**         |                                 |                                                |
| `--cookies-path`, `-c`          | Cookies file path               | `./cookies.txt`                                |
| `--wrapper-account-url`         | Wrapper account URL             | `http://127.0.0.1:30020`                       |
| `--language`, `-l`              | Metadata language               | `en-US`                                        |
| **Output Options**              |                                 |                                                |
| `--output-path`, `-o`           | Output directory path           | `./Apple Music`                                |
| `--temp-path`                   | Temporary directory path        | `.`                                            |
| `--wvd-path`                    | .wvd file path                  | -                                              |
| `--overwrite`                   | Overwrite existing files        | `false`                                        |
| `--save-cover`, `-s`            | Save cover as separate file     | `false`                                        |
| `--save-playlist`               | Save M3U8 playlist file         | `false`                                        |
| **Download Options**            |                                 |                                                |
| `--nm3u8dlre-path`              | N_m3u8DL-RE executable path     | `N_m3u8DL-RE`                                  |
| `--mp4decrypt-path`             | mp4decrypt executable path      | `mp4decrypt`                                   |
| `--ffmpeg-path`                 | FFmpeg executable path          | `ffmpeg`                                       |
| `--mp4box-path`                 | MP4Box executable path          | `MP4Box`                                       |
| `--amdecrypt-path`              | amdecrypt executable path       | `amdecrypt`                                    |
| `--use-wrapper`                 | Use wrapper and amdecrypt       | `false`                                        |
| `--wrapper-decrypt-ip`          | Wrapper decryption server IP    | `127.0.0.1:10020`                              |
| `--download-mode`               | Download mode                   | `ytdlp`                                        |
| `--remux-mode`                  | Remux mode                      | `ffmpeg`                                       |
| `--cover-format`                | Cover format                    | `jpg`                                          |
| **Template Options**            |                                 |                                                |
| `--album-folder-template`       | Album folder template           | `{album_artist}/{album}`                       |
| `--compilation-folder-template` | Compilation folder template     | `Compilations/{album}`                         |
| `--no-album-folder-template`    | No album folder template        | `{artist}/Unknown Album`                       |
| `--single-disc-file-template`   | Single disc file template       | `{track:02d} {title}`                          |
| `--multi-disc-file-template`    | Multi disc file template        | `{disc}-{track:02d} {title}`                   |
| `--no-album-file-template`      | No album file template          | `{title}`                                      |
| `--playlist-file-template`      | Playlist file template          | `Playlists/{playlist_artist}/{playlist_title}` |
| `--date-tag-template`           | Date tag template               | `%Y-%m-%dT%H:%M:%SZ`                           |
| `--exclude-tags`                | Comma-separated tags to exclude | -                                              |
| `--cover-size`                  | Cover size in pixels            | `1200`                                         |
| `--truncate`                    | Max filename length             | -                                              |
| **Song Options**                |                                 |                                                |
| `--song-codec`                  | Song codec                      | `aac-legacy`                                   |
| `--synced-lyrics-format`        | Synced lyrics format            | `lrc`                                          |
| `--no-synced-lyrics`            | Don't download synced lyrics    | `false`                                        |
| `--synced-lyrics-only`          | Download only synced lyrics     | `false`                                        |
| **Music Video Options**         |                                 |                                                |
| `--music-video-codec-priority`  | Comma-separated codec priority  | `h264,h265`                                    |
| `--music-video-remux-format`    | Music video remux format        | `m4v`                                          |
| `--music-video-resolution`      | Max music video resolution      | `1080p`                                        |
| **Post Video Options**          |                                 |                                                |
| `--uploaded-video-quality`      | Post video quality              | `best`                                         |

### Logging Level

- `DEBUG`, `INFO`, `WARNING`, `ERROR`

### Download Mode

- `ytdlp`, `nm3u8dlre`

### Remux Mode

- `ffmpeg`
- `mp4box` - Preserve the original closed caption track in music videos and some other minor metadata

### Cover Format

- `jpg`
- `png`
- `raw` - Raw format as provided by the artist (requires `save_cover` to be enabled as it doesn't embed covers into files)

### Metadata Language

Use ISO 639-1 language codes (e.g., `en-US`, `es-ES`, `ja-JP`, `pt-BR`). May not work for all music videos.

### Song Codecs

**Stable:**

- `aac-legacy` - AAC 256kbps 44.1kHz
- `aac-he-legacy` - AAC-HE 64kbps 44.1kHz

**Experimental** (may not work due to API limitations):

- `aac` - AAC 256kbps up to 48kHz
- `aac-he` - AAC-HE 64kbps up to 48kHz
- `aac-binaural` - AAC 256kbps binaural
- `aac-downmix` - AAC 256kbps downmix
- `aac-he-binaural` - AAC-HE 64kbps binaural
- `aac-he-downmix` - AAC-HE 64kbps downmix
- `atmos` - Dolby Atmos 768kbps
- `ac3` - AC3 640kbps
- `alac` - ALAC up to 24-bit/192kHz (unsupported)
- `ask` - Interactive experimental codec selection

### Synced Lyrics Format

- `lrc`
- `srt` - SubRip subtitle format (more accurate timing)
- `ttml` - Native Apple Music format (not compatible with most media players)

### Music Video Codecs

- `h264`
- `h265`
- `ask` - Interactive codec selection

### Music Video Resolutions

- H.264: `240p`, `360p`, `480p`, `540p`, `720p`, `1080p`
- H.265 only: `1440p`, `2160p`

### Music Video Remux Formats

- `m4v`, `mp4`

### Post Video Quality

- `best` - Up to 1080p with AAC 256kbps
- `ask` - Interactive quality selection

## Use Wrapper

To download high bitrate audio files without API limitations, set `use_wrapper` to `true` and configure the `wrapper` server with `amdecrypt`.

Add wrapper container settings in `.devcontainer/compose.yaml`.

```diff
services:
  app:
    build:
      context: ./
      dockerfile: Dockerfile
    volumes:
      - ../:/home/vscode/app:cached
      - venv:/home/vscode/.venv
      - ../config.ini:/home/vscode/.gamdl/config.ini
    tty: true
    stdin_open: true

+  wrapper:
+    image: tkgling/wrapper:23
+    volumes:
+      - ../rootfs/data:/app/rootfs/data
+    environment:
+      USERNAME: $USERNAME
+      PASSWORD: $PASSWORD
+    restart: unless-stopped

volumes:
  venv:
```

Then copy `.env.example` to `.env` and enter your Apple ID credentials.

```zsh
USERNAME=<#YOUR APPLE ID EMAIL>
PASSWORD=<#YOUR PASSWORD>
```

> Requires an active Apple Music subscription.