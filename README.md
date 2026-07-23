# qbz
`qbz` is a feature-rich, fast Python-based CLI tool designed for music hoarders. It lets you interactively search the Qobuz catalog, explore artist discographies, and download tracks with pristine metadata, embedded artwork, and official credits.

## Features
- 🎵**Interactive Menus:** Navigate search results, choose between Artist Albums or Tracks, and pick your downloads using intuitive terminal UI prompts.
- 📝**Deep Credits:** Fetch official studio, writing, and performance credits with the `--credits` flag (saves directly as a `Credits.txt` file).
- 🏷️**Detailed Metadata:** Automatically tags downloads with full FLAC metadata and embeds high-resolution cover art.
- ⚙️**Privacy First:** Your authentication tokens are stored strictly locally. No telemetry, no logs, no tracking.

## 📋 Prerequisites

> ### Required

- **Python**
- **Active Qobuz subscription**

## 📦 Installation

#### Option 1: Install Globally (Recommended)
This is the easiest method. It installs the required dependencies and automatically makes the `qbz` command available everywhere in your terminal. *(Note: You may need to use `pip3` depending on your system).*

```bash
pip install git+https://github.com/worstgirlinamerica/qbz.git
```
2. **Create / set up the token file:**
   - Get your Browser Auth token string by following the Usage section
   - Run 'qbz token' and wait for the prompt to input the string.
   - Press enter and use freely!
     
#### Option 2: Clone & Run Manually
If you prefer to download the source code and run it locally:

1. **Clone the repository:**

```bash
git clone https://github.com/worstgirlinamerica/qbz.git
cd qbz
```
2.  **Install the required libraries:**

```bash
pip install .
```
(Or install directly via ```bash pip install -r requirements.txt``` if you prefer).
3. **You can now run the tool directly:**

```bash
python3 -m qbz
```

### Usage 🔑
```bash
qbz [OPTIONS] URLS...
```
### Examples

**Search for an artist:**

```bash
qbz artist Slayyyter
```

**Download a song:**

```bash
qbz "https://open.qobuz.com/track/409663689"
```

**Download an album:**

```bash
qbz "https://open.qobuz.com/album/voi6vtydrimou"
```

### Supported URL Types

- Songs (Catalog/Library)
- Albums (Catalog/Library)
- Playlists (Catalog/Library)
- Artists

**Interactive Prompt Controls:**

| Key            | Action            |
| -------------- | ----------------- |
| **Arrow keys** | Move selection    |
| **Enter**      | Confirm selection |

### Song Codecs
- `5` - MP3 320kbps · up to 44.1kHz
- `6` - Lossless / CD Quality FLAC · 16b 44.1kHz
- `7` - Hi-Res FLAC · 24b / 48kHz
- `27` - Highest • 24 bit / 48 kHz / Stereo / default

### How to get your Auth Token
Before usage, you will need to provide your browser's Auth Token during the initial configuration. Here is how to easily find it:
1. Open the [Qobuz Web Player](https://play.qobuz.com) in your browser and log in.
2. Press `F12` to open the Developer Tools.
3. Go to the **Application** tab (Chrome/Edge) or **Storage** tab (Firefox).
4. In the left sidebar, expand **Local Storage** and click on `https://play.qobuz.com`.
5. In the list of keys, find **`localuser`**.
6. At the bottom of the panel (or by expanding the JSON value), look for the **`token`** string.
7. Open your terminal and enter ```qbz token``` When the prompt appears, paste your alphanumeric string and press enter to save to your config!

#### ❓ Help
To see all available commands and flags anytime:

```bash
qbz --help
```
