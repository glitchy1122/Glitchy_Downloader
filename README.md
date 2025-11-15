# Glitchy Downloader

A modern, feature-rich YouTube downloader with a Free Download Manager-style GUI. Download videos, playlists, and convert to MP3 with ease.

## Features

- 🎥 **Video Downloads** - Download videos in multiple quality options (360p, 480p, 720p, 1080p, Best)
- 🎵 **MP3 Downloads** - Quick MP3 conversion for single videos and batch downloads
- 🔻 **Torrent Support** - Download torrents via magnet links or .torrent files (requires python-libtorrent)
- 📋 **Playlist Support** - Select and download specific videos from playlists
- ⚡ **Speed Control** - Customizable speed limits and speed modes (Normal, Slow, Moderate, Snail)
- 📊 **Download Queue** - Manage multiple downloads with pause/resume/cancel/retry
- 🔄 **Batch Operations** - Pause All, Resume All, Clear Completed
- 📁 **Custom Locations** - Set default download path and organize playlists in folders
- 🎨 **Modern GUI** - Light theme with sky blue accents, resizable interface
- ⚙️ **Settings** - Persistent settings for speed modes, concurrent downloads, auto-start
- 📝 **Subtitles** - Download subtitles (if available)
- 🏷️ **File Naming** - Customizable file naming patterns

## Requirements

- Python 3.7 or higher
- FFmpeg (required for MP3 conversion)

### Installing FFmpeg

**Windows:**
1. Download from https://ffmpeg.org/download.html
2. Extract and add to system PATH

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg  # Ubuntu/Debian
```

## Installation

1. Clone this repository:
```bash
git clone https://github.com/glitchy1122/Glitchy_Downloader.git
cd Glitchy_Downloader
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### GUI Mode
```bash
python Glitchoder.py
```

### CLI Mode
```bash
python Glitchoder.py <URL> [download_path]
```

## Features Overview

### Single Video Download
1. Paste YouTube URL
2. Click "Preview" to see available qualities
3. Select quality and click "Download"
4. Or use "🎵 MP3" button for quick audio download

### Torrent Download
1. Paste magnet link or .torrent file URL (or local file path)
2. Click "🔻 Torrent" button
3. Torrent will be added to download queue
4. Supports pause/resume/cancel like regular downloads

### Playlist Download
1. Paste playlist URL
2. Click "📋 Playlist Download"
3. Select videos to download
4. Choose download as video or MP3
5. Downloads are organized in playlist-named folders

### Settings
- **Speed Modes**: Normal (unlimited), Slow (1 MB/s), Moderate (5 MB/s), Snail (0.5 MB/s)
- **Max Concurrent Downloads**: Control how many downloads run simultaneously (1-10)
- **Auto-start**: Automatically start downloads when added to queue
- **Default Location**: Set your preferred download folder

## Supported URLs

- Standard: `https://www.youtube.com/watch?v=VIDEO_ID`
- Short: `https://youtu.be/VIDEO_ID`
- Playlists: `https://www.youtube.com/playlist?list=PLAYLIST_ID`

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).

See [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for personal use only. Respect copyright laws and YouTube's Terms of Service. Only download content you have permission to download.

## Credits

Built with:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - GPL-3.0 License
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - MIT License
- [Pillow](https://python-pillow.org/) - PIL License
