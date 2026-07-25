<div align="center">

# qbz

<p>
  <a href="https://github.com/worstgirlinamerica/qbz-cli/releases/tag/v1.1.0">
    <img src="https://img.shields.io/badge/RELEASE-v1.1.0-3776ab?style=for-the-badge&labelColor=555555"></a>

  <a href="https://github.com/worstgirlinamerica/qbz-cli">
    <img src="https://img.shields.io/badge/GitHub-qbz--cli-181717?style=for-the-badge&logo=github&logoColor=white"></a>
</p>

</div>

`qbz` (qbz-cli) is a feature-rich, fast Python-based CLI tool designed for music hoarders. It lets you interactively search the Qobuz catalog, explore artist discographies, and download tracks with pristine metadata, embedded artwork, and official credits.

<table align="center">
<tr>

<td width="65%" valign="top">

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

<p>&nbsp;</p>

</td>

<td width="35%" valign="top" align="center">

<h2>Demonstration</h2>

<img src="assets/QBZ_Demo.gif" width="100%" alt="qbz demonstration">

<div style="height:25px;"></div>

<div align="center">

<a href="https://github.com/worstgirlinamerica/qbz-cli/actions/workflows/test.yml"><img src="https://github.com/worstgirlinamerica/qbz-cli/actions/workflows/test.yml/badge.svg"></a>
<img src="https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black">
<img src="https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=white">
<img src="https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=white">
</div>

</td>

</tr>
</table>

## 📋 Prerequisites

> ### Required

- **Python 3.10 or newer**
- **An active Qobuz subscription**
- **FFmpeg** (Needed for when qbz falls back to a segmented web-player stream)

## 📦 Installation

#### 1. Install QBZ
This installs `qbz` and its Python dependencies, and makes the `qbz` command available in the active environment.

If you already have a suitable [Python environment](#required), the short form is:

```bash
python -m pip install git+https://github.com/worstgirlinamerica/qbz-cli.git
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install git+https://github.com/worstgirlinamerica/qbz-cli.git
```   

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install git+https://github.com/worstgirlinamerica/qbz-cli.git
```

#### 2. 🔑 **Configure Your Qobuz Auth Token**

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

**Search for an artist with the interactive menu**

```bash
qbz artist Slayyyter
```

**Search by ISRC:**

```bash
qbz isrc USRC12502004
```

**Download by URL:**

```bash
qbz "https://open.qobuz.com/album/voi6vtydrimou"
```

**Export credits without downloading audio:**

```bash
qbz "https://open.qobuz.com/album/voi6vtydrimou" --credits-only
```

| Command or flag | What it does |
| --- | --- |
| `qbz` | Opens the interactive prompt using `cli.default_mode` |
| `qbz song <query>` | Search tracks |
| `qbz album <query>` | Search albums |
| `qbz artist <query>` | Browse an artist |
| `qbz isrc <code>` | Search by ISRC |
| `qbz <qobuz-url>` | Download a track or album from a Qobuz URL |
| `qbz whoami` | Show the authenticated Qobuz session |
| `qbz token` | Save or replace the local Qobuz token |
| `qbz config` | Print the config file path |
| `--credits` | Download normally and also write a credits sheet |
| `--credits-only` | Write credits without downloading audio |
| `--help`, `-h` | Show built-in command help |

### Supported URL Types

- Songs (Catalog/Library)
- Albums (Catalog/Library)
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
-  `C` - Credits Only · Written as a readable text sheet

`qbz` reads Qobuz release metadata for each requested track or album to determine the actual maximum available bit depth and sample rate.
`27` is a dynamic quality selector, not a fixed format. It requests the highest available quality from Qobuz and resolves to the actual release specifications. `qbz` displays the detected bit depth and sample rate (for example, 24-bit / 48 kHz) next to `27` rather than assuming a fixed format.

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
| `[display] show_paths` | Print completed audio and credits file paths | `true` |
| `[cli] default_mode` | Optional mode used when pressing Enter at the bare `qbz` prompt | empty; asks you |
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
show_paths = true

[cli]
default_mode = song

[links]
track_template = https://play.qobuz.com/track/{track_id}?quality={quality}
```

## Developer

The token is stored in the platform-appropriate user configuration directory
(`QBZ_TOKEN_FILE` can override it). For development or CI, install the test
extras and run:

```bash
pip install -e '.[test]'
python -m unittest discover -s tests -v
```

Environment overrides are also supported: `QBZ_CONFIG_FILE`, `QBZ_TOKEN_FILE`,
`QBZ_OUTPUT_DIR`, `QBZ_COUNTRY`, `QBZ_TRACK_LINK_TEMPLATE`, and
`QBZ_DEBUG_SELECTED`.

## ❓ Help
To see all available commands and flags anytime:

```bash
qbz --help
```

## 🏆 Credits and disclaimer

[qbz-cli](https://github.com/worstgirlinamerica/qbz-cli) is the official repository at:
https://github.com/worstgirlinamerica/qbz-cli

`qbz` is an independent Qobuz CLI tool and is not affiliated with other projects using the QBZ name, or Qobuz itself. Only the runtime
authentication and segmented-stream implementation were informed by public web-player behavior and community research around qobuz-dl/qopy, including work associated with Sorrow446, DashLt, and catap. 

`qbz` has its own CLI, metadata pipeline, configuration system, and implementation.

Use `qbz` only with an account and content you are authorized to access, and
follow Qobuz’s terms and applicable law.

This tool was made for Educational Purposes!

