# qbz
<p align="left">
 <a href="https://github.com/worstgirlinamerica/qbz"><img src="https://img.shields.io/badge/Qobuz-Downloader-21a0c0?style=plastic&labelColor=474747"></a>
 <a href="https://github.com/worstgirlinamerica/qbz/actions/workflows/test.yml"><img src="https://github.com/worstgirlinamerica/qbz/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
 <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
 <img src="https://img.shields.io/badge/CLI-Terminal-black?logo=gnubash&logoColor=white">

</p>

`qbz` is a feature-rich, fast Python-based CLI tool designed for music hoarders. It lets you interactively search the Qobuz catalog, explore artist discographies, and download tracks with pristine metadata, embedded artwork, and official credits.

<table>
<tr>

<td width="40%" valign="top">

<h2>✨ Features</h2>

<ul>
  <li><b>🎵 Interactive Menus</b><br>
  Navigate search results, browse artist albums or tracks, and choose downloads through an intuitive terminal UI.</li>

  <br>

  <li><b>📝 Deep Credits</b><br>
  Export official studio, writing, and performance credits with <code>--credits</code>.</li>

  <br>

  <li><b>🏷️ Detailed Metadata</b><br>
  Automatically embeds high-resolution artwork and complete FLAC metadata.</li>

  <br>

  <li><b>⚙️ Privacy First</b><br>
  Authentication tokens stay on your machine. No telemetry, no tracking.</li>

</ul>

</td>

<td width="60%" valign="top" align="center">

<p align="center">
  <img src="assets/QBZ_Demo.gif" width="100%" alt="qbz demonstration"><br>
  <b>Demonstration</b>
</p>
</td>

</tr>
</table>

## 📋 Prerequisites

> ### Required

- **Python 3.10 or newer**
- **An active Qobuz subscription**
- **FFmpeg** (only needed when qbz falls back to a segmented web-player stream)

## 📦 Installation

#### 1. Install qbz (Recommended)
This installs qbz and its Python dependencies, and makes the `qbz` command available in the active environment.

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install git+https://github.com/worstgirlinamerica/qbz.git
```   

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install git+https://github.com/worstgirlinamerica/qbz.git
```

If you already have a suitable Python environment, the short form is:

```bash
python -m pip install git+https://github.com/worstgirlinamerica/qbz.git
```

For segmented-stream fallback, install FFmpeg separately:

- macOS: `brew install ffmpeg`
- Debian/Ubuntu: `sudo apt install ffmpeg`
- Windows: `winget install Gyan.FFmpeg.Shared`

The canonical source repository is [github.com/worstgirlinamerica/qbz](https://github.com/worstgirlinamerica/qbz).

qbz is self-contained: it does not install or import `qobuz-dl-ultimate`.
At runtime it reads the current public web-player configuration, obtains the
rotating app ID/request secrets, and signs its own API and web-player session
requests. The same package entry point works on macOS, Linux, and Windows.

🔑 **Configure Your Qobuz Auth Token**

Before using qbz, you need to provide your Qobuz browser authentication token. qbz stores it locally and sends it only to Qobuz; it does not send tokens to qbz telemetry or third-party services.
1. Open the [Qobuz Web Player](https://play.qobuz.com) in your browser and log in.
2. Press `F12` to open the Developer Tools.
3. Go to the **Application** tab (Chrome/Edge) or **Storage** tab (Firefox).
4. In the left sidebar, expand **Local Storage** and click on `https://play.qobuz.com`.
5. In the list of keys, find **`localuser`**.
6. At the bottom of the panel (or by expanding the JSON value), look for the **`token`** string.
7. Copy the token string.
8. Open your terminal and Run: **`qbz token`**
9. When the prompt appears, paste the alphanumeric string and press enter to create your token file!
> Your token is now saved locally and qbz is ready to use. Never commit this token or paste it into an issue.

The token is stored in the platform-appropriate user configuration directory
(`QBZ_TOKEN_FILE` can override it). For development or CI, install the test
extras and run:

```bash
pip install -e '.[test]'
python -m unittest discover -s tests -v
```

## ⚙️ Configuration

qbz creates a config file on first run. You can print its location with
`qbz config`. Command-line flags and environment variables override config
values where applicable.

| Section / option | Description | Default |
| --- | --- | --- |
| `[download] quality` | Default quality: `5`, `6`, `7`, or `27` | `27` |
| `[download] output_dir` | Download destination | `~/Qobuz` |
| `[download] country` | Store country/zone override | empty; use token zone |
| `[download] write_credits` | Write a credits text file for downloads | `false` |
| `[display] show_email` | Show the account email in `whoami`/session output | `false` |
| `[auth] token_file` | Override the local token-file path | platform config directory |
| `[auth] app_id` | Override the Qobuz app ID if needed | automatic |
| `[links] track_template` | Link format using `{track_id}` and `{quality}` | `https://play.qobuz.com/track/{track_id}` |

Example:

```ini
[download]
quality = 27
output_dir = D:\\Music\\Qobuz
country = US
write_credits = true

[display]
show_email = false

[links]
track_template = https://play.qobuz.com/track/{track_id}?quality={quality}
```

The config path is platform-native by default. Set `QBZ_CONFIG_FILE` when you
want a specific file, for example in a portable or CI setup.
## 🚀 Usage
```bash
qbz [OPTIONS] URLS...
```
OR 
```bash
python3 -m qbz
```
if you're running the code manually

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
- `7` - Hi-Res FLAC · up to 24b / 96kHz, when available
- `27` - Highest available release resolution, including rates above 96kHz

The format IDs are targets, not guesses about the file. qbz reads Qobuz’s
release metadata and verifies the returned bit depth and sample rate. If a
selected `27`, `7`, or `6` request comes back lower than its target, qbz stops
with a resolution-mismatch error instead of silently accepting or downgrading
the file.


## ❓ Help
To see all available commands and flags anytime:

```bash
qbz --help
```

## 🏆 Credits and disclaimer

qbz is an independent project and is not affiliated with Qobuz. Its runtime
authentication and segmented-stream implementation was informed by public
web-player behavior and community research around qobuz-dl/qopy, including
work associated with Sorrow446, DashLt, and catap. qbz has its own CLI,
metadata pipeline, configuration system, and implementation.

Use qbz only with an account and content you are authorized to access, and
follow Qobuz’s terms and applicable law.
