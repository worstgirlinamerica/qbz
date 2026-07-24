#!/usr/bin/env python3

import os, sys, subprocess, json, re, getpass
from concurrent.futures import ThreadPoolExecutor, as_completed

from datetime import datetime

from pathlib import Path

import requests

from rich.console import Console

from rich.table import Table

from rich.panel import Panel

from rich.prompt import Prompt

from rich.progress import Progress, SpinnerColumn, TextColumn

from rich import box
try:
    import questionary
except Exception:
    questionary = None

try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice as InquirerChoice
except Exception:
    inquirer = None
    InquirerChoice = None



console = Console()

APP_ID = "798273057"

TOKEN_FILE = Path(
    os.getenv("QBZ_TOKEN_FILE", str(Path.home() / ".config" / "qbz" / "token"))
).expanduser()


def load_token():

    if TOKEN_FILE.is_file():

        return TOKEN_FILE.read_text(encoding="utf-8").strip()

    return os.getenv("QOBUZ_TOKEN", "").strip()


TOKEN = load_token()
if TOKEN:
    # Keep the metadata client and the download helper on the same token.
    # The helper is launched as a subprocess and reads QOBUZ_TOKEN.
    os.environ["QOBUZ_TOKEN"] = TOKEN
SESSION_COUNTRY = ""



APP_DIR = Path(__file__).resolve().parent

def runtime_dir():
    configured = os.getenv("QBZ_RUNTIME_DIR", "").strip()
    if configured:
        path = Path(configured).expanduser()
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "qbz"
    else:
        path = Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "qbz"
    path.mkdir(parents=True, exist_ok=True)
    return path


TEMP_SELECTED_JSON = runtime_dir() / "temp_selected_track.json"

DEBUG_SELECTED_JSON = runtime_dir() / "debug_selected_track.json"

HELPER_SCRIPT = APP_DIR / "authorized_stream_fetch.py"
CURRENT_QUALITY_ID = "27"
CURRENT_ID_ONLY = False
WRITE_CREDITS = False



def banner():

    try:

        import pyfiglet

        title = pyfiglet.figlet_format("QBZ", font="slant")

    except Exception:

        title = "QBZ"

    console.print(f"[bold cyan]{title}[/bold cyan]")

    console.print("[dim]Qobuz catalog search client • song / album / artist / isrc[/dim]\n")



def die(msg):

    console.print(Panel(f"[bold red]Error[/bold red]\n{msg}", border_style="red"))

    sys.exit(1)



def api(path, params=None):

    if not TOKEN:

        die("Missing token. Add this to ~/.zshrc:\n\nexport QOBUZ_TOKEN='YOUR_TOKEN'")

    headers = {"x-app-id": APP_ID, "x-user-auth-token": TOKEN}

    r = requests.get(f"https://www.qobuz.com/api.json/0.2/{path}", headers=headers, params=params or {}, timeout=20)

    if r.status_code != 200:

        die(f"Qobuz HTTP {r.status_code}\n{r.text[:500]}")

    data = r.json()

    if data.get("status") == "error":

        die(data.get("message", "Unknown Qobuz API error"))

    return data



def verify():

    global SESSION_COUNTRY

    u = api("user/get")
    SESSION_COUNTRY = (u.get("zone") or "").strip().upper()

    console.print(Panel(

        f"[bold]Account[/bold] {u.get('email')}\n"

        f"[bold]Store[/bold] {u.get('store')}   [bold]Zone[/bold] {u.get('zone')}   [bold]ID[/bold] {u.get('id')}",

        title="Qobuz Session",

        border_style="cyan"

    ))

    configured_country = os.getenv("QBZ_COUNTRY", "").strip().upper()

    if configured_country and SESSION_COUNTRY and configured_country != SESSION_COUNTRY:

        console.print(
            f"[yellow]Warning: QBZ_COUNTRY={configured_country} differs from "
            f"the token zone {SESSION_COUNTRY}.[/yellow]\n"
        )



def active_country():

    return os.getenv("QBZ_COUNTRY", "").strip().upper() or SESSION_COUNTRY or "AU"



def switch_token():

    global TOKEN

    candidate = getpass.getpass("New Qobuz token: ").strip()

    if not candidate:

        die("Token was empty; the current account was not changed.")

    previous_token = TOKEN
    TOKEN = candidate

    try:

        verify()

    except BaseException:

        TOKEN = previous_token
        raise

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(candidate + "\n", encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    os.environ["QOBUZ_TOKEN"] = candidate

    console.print(f"[green]Active token saved to {TOKEN_FILE}[/green]")



def clean_value(v):

    if isinstance(v, dict):

        return v.get("name") or v.get("title") or v.get("id") or v

    if isinstance(v, list):

        cleaned = [clean_value(x) for x in v]

        return ", ".join(str(x) for x in cleaned if x not in (None, ""))

    return v



def nested_get(obj, *paths):

    for path in paths:

        cur = obj

        ok = True

        for key in path.split("."):

            if isinstance(cur, dict) and key in cur:

                cur = cur[key]

            else:

                ok = False

                break

        if ok and cur not in (None, ""):

            return cur

    return None


def merge_dicts(base, extra):
    merged = dict(base or {})
    for key, value in (extra or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dicts(merged[key], value)
        elif value is not None:
            merged[key] = value
    return merged


def unique_values(values):
    seen = set()
    result = []
    for value in values:
        if value in (None, ""):
            continue
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


PERSON_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def clean_credit_name(value):
    text = clean_value(value)
    if not text:
        return text

    def fix_word(word):
        bare = re.sub(r"[^A-Za-z]", "", word)
        if len(bare) <= 3 and bare.upper() == bare:
            return word
        if len(bare) > 1 and bare.upper() == bare and any(ch in "AEIOU" for ch in bare):
            fixed = word[:1].upper() + word[1:].lower()
            if fixed.lower().startswith("mc") and len(fixed) > 2:
                fixed = "Mc" + fixed[2:3].upper() + fixed[3:]
            return fixed
        return word

    return " ".join(fix_word(part) for part in text.split())


def parse_performer_credits(value):
    credits = []
    by_role = {}
    by_person = {}

    if not isinstance(value, str):
        return credits, by_role, by_person

    for group in re.split(r"\s+-\s+", value.strip()):
        parts = [part.strip() for part in group.split(",") if part.strip()]
        if len(parts) < 2:
            continue

        person = parts[0]
        role_start = 1
        if len(parts) >= 3 and parts[1].casefold() in PERSON_SUFFIXES:
            person = f"{person}, {parts[1]}"
            role_start = 2

        person = clean_credit_name(person)
        roles = unique_values(parts[role_start:])
        if not roles:
            continue

        credits.append({"name": person, "roles": roles})
        by_person.setdefault(person, [])
        by_person[person] = unique_values(by_person[person] + roles)
        for role in roles:
            by_role.setdefault(role, [])
            by_role[role] = unique_values(by_role[role] + [person])

    return credits, by_role, by_person


def people_for_role(credits_by_role, role):
    wanted = role.casefold()
    for candidate, people in credits_by_role.items():
        if candidate.casefold() == wanted:
            return people
    return []


def hydrate_selected_item(kind, selected):
    hydrated = dict(selected or {})
    raw = {"selected": selected}

    if kind == "track" and selected.get("id"):
        full_track = api("track/get", {"track_id": selected["id"]})
        if isinstance(full_track, dict):
            hydrated = merge_dicts(hydrated, full_track)
            raw["track"] = full_track

        album_id = nested_get(hydrated, "album.id")
        if album_id:
            full_album = api("album/get", {"album_id": album_id})
            if isinstance(full_album, dict):
                raw["album"] = full_album
                matching_track = next(
                    (
                        track
                        for track in nested_get(full_album, "tracks.items") or []
                        if str(track.get("id")) == str(hydrated.get("id"))
                    ),
                    None,
                )
                if matching_track:
                    hydrated = merge_dicts(hydrated, matching_track)
                hydrated["album"] = full_album

    elif kind == "album" and selected.get("id"):
        full_album = api("album/get", {"album_id": selected["id"]})
        if isinstance(full_album, dict):
            hydrated = merge_dicts(hydrated, full_album)
            raw["album"] = full_album

    return hydrated, raw



def normalize_cover_url(url):

    if not url:

        return None

    if isinstance(url, dict):

        url = url.get("original") or url.get("large") or url.get("small") or url.get("thumbnail")

    if not isinstance(url, str):

        return url

    for size in ("_600.", "_500.", "_400.", "_300.", "_230.", "_150."):

        url = url.replace(size, "_1200.")

    return url



def normalize_date(v):

    if v in (None, ""):

        return None

    if isinstance(v, (int, float)):

        try:

            return datetime.fromtimestamp(v).strftime("%Y-%m-%d")

        except Exception:

            return str(v)

    text = str(v)

    if text.isdigit() and len(text) >= 9:

        try:

            return datetime.fromtimestamp(int(text)).strftime("%Y-%m-%d")

        except Exception:

            return text

    return text.split("T")[0]



def release_date_value(x):

    return (

        x.get("release_date")

        or x.get("released_at")

        or x.get("release_date_original")

        or x.get("maximum_bit_depth_date")

        or nested_get(x, "album.release_date", "album.released_at", "album.release_date_original")

        or ""

    )



def date_key(x):
    raw = release_date_value(x)
    normalized = normalize_date(raw)
    if not normalized:
        return datetime.min
    try:
        return datetime.fromisoformat(str(normalized).replace("Z", "").split("T")[0])
    except Exception:
        return datetime.min

def hydrate_album_dates(albums):

    fixed = []

    for a in albums:

        if release_date_value(a):

            fixed.append(a)

            continue

        album_id = a.get("id")

        if not album_id:

            fixed.append(a)

            continue

        try:

            full = api("album/get", {"album_id": album_id})

            if isinstance(full, dict):

                merged = dict(a)

                merged.update({k: v for k, v in full.items() if v is not None})

                fixed.append(merged)

            else:

                fixed.append(a)

        except Exception:

            fixed.append(a)

    return fixed



def run_after_metadata_helper():

    if not HELPER_SCRIPT.exists():

        return

    try:

        return subprocess.run(

            [sys.executable, str(HELPER_SCRIPT), str(TEMP_SELECTED_JSON)],

            check=True,

        )

    except subprocess.CalledProcessError as e:

        console.print(f"[yellow]Helper script exited with code {e.returncode}.[/yellow]")

    except Exception as e:

        console.print(f"[yellow]Helper script could not run: {e}[/yellow]")

    return None




def build_selected_metadata(kind, selected):
    selected, raw_qobuz = hydrate_selected_item(kind, selected)

    raw_date = (
        selected.get("date")
        or selected.get("release_date")
        or selected.get("released_at")
        or selected.get("release_date_original")
        or nested_get(selected, "album.release_date", "album.released_at", "album.release_date_original")
    )

    album = selected.get("album") if isinstance(selected.get("album"), dict) else {}
    performers_raw = selected.get("performers")
    credits, credits_by_role, credits_by_person = parse_performer_credits(performers_raw)
    composers = people_for_role(credits_by_role, "Composer")
    lyricists = people_for_role(credits_by_role, "Lyricist")
    producers = unique_values(
        people_for_role(credits_by_role, "Producer")
        + people_for_role(credits_by_role, "Additional Production")
        + people_for_role(credits_by_role, "AdditionalStudioProducer")
    )
    album_artists = album.get("artists") if isinstance(album.get("artists"), list) else []
    album_artist_names = unique_values(
        clean_value(artist) for artist in album_artists if isinstance(artist, dict)
    )
    if not album_artist_names:
        album_artist_names = unique_values(
            [clean_value(selected.get("album_artist") or album.get("artist"))]
        )
    audio_info = selected.get("audio_info") if isinstance(selected.get("audio_info"), dict) else {}
    release_dates = {
        key: normalize_date(selected.get(key) or album.get(key))
        for key in (
            "release_date_original",
            "release_date_download",
            "release_date_stream",
            "release_date_purchase",
        )
        if selected.get(key) not in (None, "") or album.get(key) not in (None, "")
    }
    normalized_date = normalize_date(raw_date)

    selected_metadata = {
        "id": selected.get("id"),
        "title": selected.get("title") or selected.get("name"),
        "artist": clean_value(selected.get("artist") or selected.get("performer")),
        "album": clean_value(album or selected.get("album")),
        "album_artist": ", ".join(album_artist_names) or None,
        "track_number": selected.get("track_number") or selected.get("track_number_position") or selected.get("media_number"),
        "track_total": album.get("tracks_count") or nested_get(album, "tracks.total"),
        "disc_number": selected.get("media_number"),
        "disc_total": album.get("media_count"),
        "label": clean_value(selected.get("label") or album.get("label")),
        "label_id": nested_get(album, "label.id"),
        "genre": clean_value(selected.get("genre") or album.get("genre")),
        "genres": album.get("genres_list") or [],
        "date": normalized_date,
        "year": (normalized_date or "")[:4] or None,
        "release_dates": release_dates,
        "isrc": selected.get("isrc"),
        "upc": album.get("upc"),
        "barcode": album.get("upc"),
        "copyright": selected.get("copyright") or album.get("copyright"),
        "composer": ", ".join(composers) or clean_value(selected.get("composer")),
        "composers": composers,
        "lyricists": lyricists,
        "producers": producers,
        "performers_raw": performers_raw,
        "credits": credits,
        "credits_by_role": credits_by_role,
        "credits_by_person": credits_by_person,
        "duration": selected.get("duration"),
        "version": selected.get("version"),
        "work": selected.get("work"),
        "explicit": selected.get("parental_warning"),
        "maximum_bit_depth": selected.get("maximum_bit_depth") or album.get("maximum_bit_depth"),
        "maximum_sampling_rate": selected.get("maximum_sampling_rate") or album.get("maximum_sampling_rate"),
        "maximum_channel_count": selected.get("maximum_channel_count") or album.get("maximum_channel_count"),
        "maximum_technical_specifications": album.get("maximum_technical_specifications"),
        "replaygain_track_gain": audio_info.get("replaygain_track_gain"),
        "replaygain_track_peak": audio_info.get("replaygain_track_peak"),
        "hires": selected.get("hires"),
        "hires_streamable": selected.get("hires_streamable"),
        "streamable": selected.get("streamable"),
        "downloadable": selected.get("downloadable"),
        "artist_id": nested_get(selected, "performer.id", "artist.id"),
        "album_id": album.get("id"),
        "album_qobuz_id": album.get("qobuz_id"),
        "qobuz_url": album.get("url") or album.get("product_url"),
        "cover_url": normalize_cover_url(selected.get("cover_url") or selected.get("image") or album.get("image")),
        "quality_id": CURRENT_QUALITY_ID,
        "country": active_country(),
        "qobuz_raw": raw_qobuz,
        "write_credits": WRITE_CREDITS,
    }
    return selected_metadata, raw_qobuz, credits, credits_by_role


def export_selected_metadata(kind, selected, debug=False):
    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold cyan]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("Loading complete Qobuz metadata", total=None)
        selected_metadata, raw_qobuz, credits, credits_by_role = build_selected_metadata(kind, selected)

    with open(TEMP_SELECTED_JSON, "w", encoding="utf-8") as f:
        json.dump(selected_metadata, f, indent=2, ensure_ascii=False)

    if debug:
        with open(DEBUG_SELECTED_JSON, "w", encoding="utf-8") as f:
            json.dump(raw_qobuz, f, indent=2, ensure_ascii=False)

    console.print(
        f"[cyan]Metadata ready:[/cyan] {len(credits)} credited people, "
        f"{len(credits_by_role)} distinct roles"
    )

    run_after_metadata_helper()

    if debug:
        console.print(f"[dim]Debug object written to {DEBUG_SELECTED_JSON}[/dim]")


def album_track_sort_key(track):
    try:
        disc = int(track.get("media_number") or 1)
    except Exception:
        disc = 1
    try:
        number = int(track.get("track_number") or 0)
    except Exception:
        number = 0
    return (disc, number)


def export_album_metadata(selected, debug=False):
    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold cyan]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("Loading complete album metadata", total=None)
        album_id = selected.get("id")
        full_album = api("album/get", {"album_id": album_id}) if album_id else selected
        tracks = nested_get(full_album, "tracks.items") or []
        tracks = sorted(tracks, key=album_track_sort_key)

        track_metadatas = []
        raw_items = []
        for index, track in enumerate(tracks, 1):
            merged = dict(track or {})
            merged["album"] = full_album
            metadata, raw_qobuz, credits, credits_by_role = build_selected_metadata("track", merged)
            metadata["album_download"] = True
            metadata["album_track_index"] = index
            metadata["album_track_count"] = len(tracks)
            metadata["quality_id"] = CURRENT_QUALITY_ID
            track_metadatas.append(metadata)
            raw_items.append(raw_qobuz)

    if not track_metadatas:
        die("That album did not return any track items to download.")

    batch = {
        "batch_type": "album",
        "quality_id": CURRENT_QUALITY_ID,
        "country": active_country(),
        "album": {
            "id": full_album.get("id"),
            "title": full_album.get("title"),
            "artist": clean_value(full_album.get("artist")),
            "explicit": full_album.get("parental_warning"),
            "maximum_bit_depth": full_album.get("maximum_bit_depth"),
            "maximum_sampling_rate": full_album.get("maximum_sampling_rate"),
            "maximum_channel_count": full_album.get("maximum_channel_count"),
            "maximum_technical_specifications": full_album.get("maximum_technical_specifications"),
        },
        "tracks": track_metadatas,
        "write_credits": WRITE_CREDITS,
    }

    with open(TEMP_SELECTED_JSON, "w", encoding="utf-8") as f:
        json.dump(batch, f, indent=2, ensure_ascii=False)

    if debug:
        with open(DEBUG_SELECTED_JSON, "w", encoding="utf-8") as f:
            json.dump({"album": full_album, "tracks": raw_items}, f, indent=2, ensure_ascii=False)

    console.print(
        f"[cyan]Album metadata ready:[/cyan] {len(track_metadatas)} tracks "
        f"• quality {CURRENT_QUALITY_ID}"
    )

    run_after_metadata_helper()

    if debug:
        console.print(f"[dim]Debug object written to {DEBUG_SELECTED_JSON}[/dim]")

def search(query):

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:

        p.add_task(description=f"Searching Qobuz {active_country()} for: {query}", total=None)

        return api("catalog/search", {"query": query})



def get_artist_releases(artist_id):

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:

        task = p.add_task(description="Loading all artist releases", total=None)

        offset = 0
        limit = 100
        artist_data = {}
        releases = []

        while True:
            page = api(
                "artist/get",
                {"artist_id": artist_id, "extra": "albums", "limit": limit, "offset": offset},
            )
            if not artist_data:
                artist_data = dict(page)

            albums = page.get("albums") or {}
            items = albums.get("items") or []
            releases.extend(items)

            total = albums.get("total") or len(releases)
            p.update(task, description=f"Loading all artist releases ({len(releases)}/{total})")
            if not items or len(releases) >= total:
                break
            offset += len(items)

        artist_data["albums"] = {
            "items": unique_items(releases),
            "total": len(unique_items(releases)),
            "offset": 0,
            "limit": len(unique_items(releases)),
        }
        return artist_data



def pick_best_artist(artists, query):

    if not artists:

        return None

    return rank_artists(artists, query)[0]



def normalized_words(value):

    return re.findall(r"[a-z0-9]+", str(value or "").casefold())



def artist_name(item):

    return clean_value(
        nested_get(item, "performer.name", "artist.name", "album.artist.name")
        or item.get("performer")
        or item.get("artist")
        or nested_get(item, "album.artist")
    ) or ""



def artist_relevance(item, query):

    name = artist_name(item).casefold().strip()
    query_text = str(query or "").casefold().strip()
    if not name or not query_text:
        return 0
    if name == query_text:
        return 4
    if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", query_text):
        return 3

    name_words = set(normalized_words(name))
    query_words = set(normalized_words(query_text))
    if name_words and name_words.issubset(query_words):
        return 2
    if name_words and len(name_words & query_words) == len(name_words):
        return 1
    return 0



def artist_candidate_relevance(item, query):

    name = str(item.get("name") or "").casefold().strip()
    query_text = str(query or "").casefold().strip()
    if name == query_text:
        return 4
    if name.startswith(query_text) or query_text.startswith(name):
        return 3

    name_words = set(normalized_words(name))
    query_words = set(normalized_words(query_text))
    if query_words and query_words.issubset(name_words):
        return 2
    return len(name_words & query_words) / max(len(query_words), 1)



def rank_artists(items, query):

    return sorted(
        items or [],
        key=lambda item: (
            artist_candidate_relevance(item, query),
            int(item.get("albums_count") or 0),
            str(item.get("name") or "").casefold(),
        ),
        reverse=True,
    )



def rank_results(items, query):

    return sorted(
        items or [],
        key=lambda item: (artist_relevance(item, query), date_key(item)),
        reverse=True,
    )



def unique_items(items):

    seen = set()
    result = []
    for item in items or []:
        key = item.get("id")
        if key in (None, ""):
            key = (
                str(item.get("title") or item.get("name") or "").casefold(),
                str(release_date_value(item)),
                artist_name(item).casefold(),
            )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result



def artist_release_items(artist_data):

    raw = artist_data.get("albums")

    if isinstance(raw, dict):

        albums = raw.get("items") or []

    elif isinstance(raw, list):

        albums = raw

    else:

        albums = []

    albums = hydrate_album_dates(albums)

    return sorted(albums, key=date_key, reverse=True)



def copy_link(link):

    try:

        subprocess.run(["pbcopy"], input=link.encode(), check=True)

        return True

    except Exception:

        return False




def item_max_spec(item):
    bit_depth = item.get("maximum_bit_depth") or nested_get(item, "album.maximum_bit_depth")
    sample_rate = item.get("maximum_sampling_rate") or nested_get(item, "album.maximum_sampling_rate")
    channel_count = item.get("maximum_channel_count") or nested_get(item, "album.maximum_channel_count")
    technical = item.get("maximum_technical_specifications") or nested_get(item, "album.maximum_technical_specifications")

    if technical:
        return str(technical).replace(" - ", " • ")

    parts = []
    if bit_depth:
        parts.append(f"{bit_depth} bit")
    if sample_rate:
        try:
            sr = float(sample_rate)
            parts.append(f"{sr:g} kHz")
        except Exception:
            parts.append(f"{sample_rate} kHz")
    if channel_count:
        channels = "Stereo" if str(channel_count) == "2" else f"{channel_count} ch"
        parts.append(channels)

    return " / ".join(parts) if parts else "best available"


def quality_choices_for_item(item):
    max_spec = item_max_spec(item)
    return [
        ("5", "MP3 • lossy / low"),
        ("6", "Lossless • CD quality / FLAC"),
        ("7", f"Hi-Res • {max_spec}"),
        ("27", f"Highest • {max_spec} / default"),
        ("0", "Copy selected item ID only"),
    ]


def choose_quality(kind, item):
    global CURRENT_QUALITY_ID, CURRENT_ID_ONLY
    CURRENT_ID_ONLY = False

    choices = quality_choices_for_item(item)

    console.print()
    if inquirer is not None and InquirerChoice is not None:
        selected = inquirer.select(
            message="Select quality to download:",
            choices=[
                InquirerChoice(name=f"{qid}  {label}", value=qid)
                for qid, label in choices
            ],
            default="27",
        ).execute()
        choice = str(selected or "27").strip()
    elif questionary is not None:
        selected = questionary.select(
            "Select quality to download:",
            choices=[
                questionary.Choice(title=f"{qid}  {label}", value=qid)
                for qid, label in choices
            ],
            default="27",
            use_indicator=True,
            use_shortcuts=False,
        ).ask()
        choice = str(selected or "27").strip()
    else:
        console.print("[bold cyan]Quality[/bold cyan]")
        for qid, label in choices:
            console.print(f"[cyan]{qid}[/cyan]  {label}")
        choice = Prompt.ask("Quality", default="27").strip()

    if choice == "0":
        CURRENT_ID_ONLY = True
        CURRENT_QUALITY_ID = "27"
        return
    if choice not in ("5", "6", "7", "27"):
        console.print("[yellow]Invalid quality, using 27.[/yellow]")
        choice = "27"
    CURRENT_QUALITY_ID = choice

def link_for(kind, item):
    item_id = item.get("id")
    if not item_id:
        return ""
    if CURRENT_ID_ONLY:
        return str(item_id)
    if kind == "track":
        template = os.getenv("QBZ_TRACK_LINK_TEMPLATE", "https://play.qobuz.com/track/{track_id}")
        return template.format(track_id=item_id, quality=CURRENT_QUALITY_ID)
    if kind == "album":
        return f"https://play.qobuz.com/album/{item_id}"
    return f"https://play.qobuz.com/{kind}/{item_id}"

def selected_card(kind, item):

    choose_quality(kind, item)

    link = link_for(kind, item)
    copied = copy_link(link)

    if not CURRENT_ID_ONLY:
        if kind == "album":
            export_album_metadata(item, debug=os.getenv("QBZ_DEBUG_SELECTED", "").strip() == "1")
        else:
            export_selected_metadata(kind, item, debug=os.getenv("QBZ_DEBUG_SELECTED", "").strip() == "1")

    title = item.get("title", item.get("name", "Selected item"))

    artist = clean_value(item.get("artist") or item.get("performer")) or ""

    album = clean_value(item.get("album")) or title

    label = clean_value(item.get("label") or nested_get(item, "album.label", "album.label.name")) or ""

    genre = clean_value(item.get("genre") or nested_get(item, "album.genre", "album.genre.name")) or ""

    date = normalize_date(item.get("date") or item.get("release_date") or item.get("released_at") or nested_get(item, "album.release_date", "album.released_at")) or ""

    isrc = item.get("isrc") or ""

    if CURRENT_ID_ONLY:
        status = "[green]✓ Copied selected item ID[/green]" if copied else "[yellow]Printed, but clipboard copy failed.[/yellow]"
    elif kind == "album":
        status = "[green]✓ Album metadata exported[/green]\n[green]✓ Album download started[/green]"
        status += "\n" + ("[green]✓ Copied album link to clipboard[/green]" if copied else "[yellow]Printed, but clipboard copy failed.[/yellow]")
    else:
        status = "[green]✓ Metadata exported[/green]\n"
        status += "[green]✓ Copied to clipboard[/green]" if copied else "[yellow]Printed, but clipboard copy failed.[/yellow]"

    card = (

        f"[bold cyan]{title}[/bold cyan]\n"

        f"{artist} • {date}\n"

        f"{album}\n"

        f"{label}" + (f" • {genre}" if genre else "") + "\n"

        f"ISRC: {isrc}\n\n"

        + status

    )

    console.print(Panel(card, title="Selected", border_style="green" if copied else "yellow"))



def ellipsize(text, width):
    text = clean_value(text) if not isinstance(text, str) else text
    text = str(text or "").replace("\n", " ").strip()
    if len(text) <= width:
        return text.ljust(width)
    if width <= 1:
        return "…"[:width]
    return (text[: width - 1] + "…").ljust(width)


def item_label(kind, item, idx=None):
    if kind == "track":
        title = item.get("title", item.get("name", ""))
        artist = clean_value((item.get("performer") or {}).get("name") or item.get("artist")) or ""
        explicit = "Yes" if item.get("parental_warning") else "No"
        isrc = item.get("isrc") or ""
        date = normalize_date((item.get("album") or {}).get("release_date") or release_date_value(item)) or ""
        return (
            f"{ellipsize(title, 34)}  "
            f"{ellipsize(artist, 18)}  "
            f"{ellipsize(explicit, 8)}  "
            f"{ellipsize(isrc, 13)}  "
            f"{ellipsize(date, 10)}"
        )

    if kind == "artist":
        name = item.get("name", "")
        artist_id = item.get("id", "")
        albums_count = item.get("albums_count", "")
        return (
            f"{ellipsize(name, 36)}  "
            f"{ellipsize(artist_id, 14)}  "
            f"{ellipsize(albums_count, 8)}"
        )

    title = item.get("title", item.get("name", ""))
    artist = clean_value((item.get("artist") or {}).get("name") or item.get("artist") or item.get("performer")) or ""
    explicit = "Yes" if item.get("parental_warning") else "No"
    upc = item.get("upc") or ""
    date = normalize_date(release_date_value(item)) or ""
    return (
        f"{ellipsize(title, 34)}  "
        f"{ellipsize(artist, 18)}  "
        f"{ellipsize(explicit, 8)}  "
        f"{ellipsize(upc, 14)}  "
        f"{ellipsize(date, 10)}"
    )


def result_header(kind):
    if kind == "track":
        return (
            f"{'Title':34}  {'Artist':18}  {'Explicit':8}  {'ISRC':13}  {'Date':10}\n"
            f"{'─' * 34}  {'─' * 18}  {'─' * 8}  {'─' * 13}  {'─' * 10}"
        )
    if kind == "artist":
        return (
            f"{'Artist':36}  {'ID':14}  {'Albums':8}\n"
            f"{'─' * 36}  {'─' * 14}  {'─' * 8}"
        )
    return (
        f"{'Title':34}  {'Artist':18}  {'Explicit':8}  {'UPC':14}  {'Date':10}\n"
        f"{'─' * 34}  {'─' * 18}  {'─' * 8}  {'─' * 14}  {'─' * 10}"
    )


def choose_from_menu(kind, shown, title="Select result"):
    if not shown:
        return None

    console.print()
    console.print(Panel(
        result_header(kind),
        title=title,
        border_style="cyan",
    ))

    if inquirer is not None and InquirerChoice is not None:
        choices = [
            InquirerChoice(name=item_label(kind, item), value=i)
            for i, item in enumerate(shown)
        ]
        choices.append(InquirerChoice(name="Skip", value=None))
        selected = inquirer.select(
            message="Move with ↑/↓, Enter to select:",
            choices=choices,
            default=0,
            height=min(max(len(choices), 8), 18),
            border=True,
        ).execute()
        return shown[selected] if selected is not None else None

    if questionary is not None:
        choices = [
            questionary.Choice(title=item_label(kind, item), value=i)
            for i, item in enumerate(shown)
        ]
        choices.append(questionary.Choice(title="Skip", value=None))
        selected = questionary.select(
            "Move with ↑/↓, Enter to select:",
            choices=choices,
            use_indicator=True,
            use_shortcuts=False,
        ).ask()
        return shown[selected] if selected is not None else None

    # Plain fallback for terminals without InquirerPy/questionary.
    console.print(Panel(
        "Interactive selector unavailable.\nType the left result number to select it.\nPress Enter to skip.",
        title="Select Result",
        border_style="cyan",
    ))
    for i, item in enumerate(shown, 1):
        console.print(f"[cyan]{i:>2}[/cyan]  {item_label(kind, item)}")
    choice = Prompt.ask("Select #", default="").strip()
    if not choice:
        console.print("[dim]Skipped.[/dim]")
        return None
    if not choice.isdigit() or not (1 <= int(choice) <= len(shown)):
        console.print(f"[yellow]Pick a valid number from 1 to {len(shown)}.[/yellow]")
        return None
    return shown[int(choice) - 1]


def select_copy(kind, items):
    shown = list(items or [])
    selected = choose_from_menu(kind, shown, title="Search Results")
    if selected is None:
        console.print("[dim]Skipped.[/dim]")
        return
    selected_card(kind, selected)


def show_tracks(items, query=""):
    return rank_results(items, query) if query else sorted(items, key=date_key, reverse=True)


def show_albums(items, query=""):
    items = hydrate_album_dates(items)
    return rank_results(items, query) if query else sorted(items, key=date_key, reverse=True)


def show_artists(items, query=""):
    if query:
        return rank_artists(items, query)
    return sorted(items or [], key=lambda item: str(item.get("name", "")).casefold())


def select_artist(items):
    shown = list(items or [])
    return choose_from_menu("artist", shown, title="Matching Artists")


def choose_artist_catalog():
    choices = [("Albums", "albums"), ("Tracks", "tracks")]
    if inquirer is not None and InquirerChoice is not None:
        return inquirer.select(
            message="Browse artist catalog:",
            choices=[InquirerChoice(name=label, value=value) for label, value in choices],
            default="albums",
        ).execute() or "albums"
    if questionary is not None:
        return questionary.select(
            "Browse artist catalog:",
            choices=[questionary.Choice(title=label, value=value) for label, value in choices],
            default="albums",
        ).ask() or "albums"
    return Prompt.ask("Browse artist catalog", choices=["albums", "tracks"], default="albums")


def artist_matches(track, album, artist):
    artist_id = str(artist.get("id") or "")
    artist_text = str(artist.get("name") or "").casefold().strip()
    candidate_ids = {
        str(nested_get(track, "performer.id") or ""),
        str(nested_get(track, "artist.id") or ""),
        str(nested_get(album, "artist.id") or ""),
    }
    if artist_id and artist_id in candidate_ids:
        return True

    candidate_names = {
        str(nested_get(track, "performer.name") or "").casefold().strip(),
        str(nested_get(track, "artist.name") or "").casefold().strip(),
        str(nested_get(album, "artist.name") or "").casefold().strip(),
    }
    return bool(artist_text and artist_text in candidate_names)



def artist_track_items(releases, artist):
    tracks = []
    release_ids = [album.get("id") for album in unique_items(releases) if album.get("id")]

    def fetch_album(album_id):
        try:
            return api("album/get", {"album_id": album_id})
        except Exception:
            return None

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
        task = p.add_task(description=f"Loading artist tracks (0/{len(release_ids)})", total=None)
        completed = 0
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(fetch_album, album_id) for album_id in release_ids]
            for future in as_completed(futures):
                full_album = future.result()
                completed += 1
                p.update(task, description=f"Loading artist tracks ({completed}/{len(release_ids)})")
                if not full_album:
                    continue
                album_tracks = nested_get(full_album, "tracks.items") or []
                for track in album_tracks:
                    if not artist_matches(track, full_album, artist):
                        continue
                    merged = dict(track or {})
                    merged["album"] = full_album
                    tracks.append(merged)

    return sorted(unique_items(tracks), key=date_key, reverse=True)


def parse_direct_url_arg(value):
    text = (value or "").strip()
    if not text:
        return None

    patterns = [
        r'(?:open|play)\.qobuz\.com/(track|album)/([A-Za-z0-9]+)',
        r'qobuz\.com/[a-z]{2}-[a-z]{2}/(?:album|interpreter|artist)?/?[^\s]*/([A-Za-z0-9]+)',
        r'qobuz\.com/[a-z]{2}-[a-z]{2}/track/[^\s]*/([0-9]+)',
    ]

    m = re.search(patterns[0], text)
    if m:
        return m.group(1), m.group(2)

    if "qobuz.com" not in text:
        return None

    # Public album URLs usually end in the album id slug.
    m = re.search(r'qobuz\.com/[a-z]{2}-[a-z]{2}/album/[^\s/]+/([A-Za-z0-9]+)', text)
    if m:
        return "album", m.group(1)

    # Public track URLs usually contain a numeric track id.
    m = re.search(r'qobuz\.com/[a-z]{2}-[a-z]{2}/track/[^\s/]+/([0-9]+)', text)
    if m:
        return "track", m.group(1)

    # Last-resort play/open URL variants.
    m = re.search(r'/track/([0-9]+)', text)
    if m:
        return "track", m.group(1)
    m = re.search(r'/album/([A-Za-z0-9]+)', text)
    if m:
        return "album", m.group(1)

    return None


def handle_direct_url(value):
    direct = parse_direct_url_arg(value)
    if not direct:
        return False

    kind, item_id = direct
    verify()
    if kind == "track":
        selected_card("track", api("track/get", {"track_id": item_id}))
        return True
    if kind == "album":
        selected_card("album", api("album/get", {"album_id": item_id}))
        return True
    return False

def main():

    global WRITE_CREDITS

    flags = {arg for arg in sys.argv[1:] if arg == "--credits"}
    WRITE_CREDITS = "--credits" in flags
    if flags:
        sys.argv[:] = [arg for arg in sys.argv if arg not in flags]

    banner()

    if len(sys.argv) > 1:
        first_arg = sys.argv[1].strip()
        if first_arg.lower() in ("token", "switch-token"):
            switch_token()
            return
        if handle_direct_url(first_arg):
            return
        mode = first_arg.lower()
    else:
        mode_or_link = Prompt.ask("Enter mode or link", default="song").strip()
        if handle_direct_url(mode_or_link):
            return
        mode = mode_or_link.lower()

    if mode == "qobuzurl":
        url = " ".join(sys.argv[2:]).strip() if len(sys.argv) > 2 else Prompt.ask("Qobuz URL").strip()
        if handle_direct_url(url):
            return
        die("Could not understand that Qobuz track/album URL.")

    if mode not in ("song", "album", "artist", "isrc", "whoami"):
        die("Use: qbz song | qbz album | qbz artist | qbz isrc | qbz whoami | qbz token | qbz qobuzurl")

    verify()
    if mode == "whoami":
        return

    if len(sys.argv) > 2:
        query = " ".join(sys.argv[2:]).strip()
    elif mode == "isrc":
        query = Prompt.ask("ISRC").strip()
    elif mode == "artist":
        query = Prompt.ask("Artist").strip()
    elif mode == "song":
        query = Prompt.ask("Song or Song - Artist").strip()
    else:
        query = Prompt.ask("Album or Album - Artist").strip()

    if not query:
        die('Empty search. Example: qbz artist "The Kid Laroi"')

    if handle_direct_url(query):
        return

    data = search(query)

    tracks = (data.get("tracks") or {}).get("items") or []
    albums = (data.get("albums") or {}).get("items") or []
    artists = (data.get("artists") or {}).get("items") or []

    if mode in ("song", "isrc"):

        if tracks:

            tracks = show_tracks(tracks, query)

            select_copy("track", tracks)

            return

        else:

            console.print("[yellow]No matching tracks found.[/yellow]")

        if albums:

            console.print()

            show_albums(albums[:10], query)

            return



    elif mode == "album":

        if albums:

            albums = show_albums(albums, query)

            select_copy("album", albums)

            return

        else:

            console.print("[yellow]No matching albums found.[/yellow]")

        if tracks:

            console.print()

            show_tracks(tracks[:10], query)

            return



    elif mode == "artist":

        if not artists:

            console.print("[yellow]No matching artist found.[/yellow]")

        else:

            artists = show_artists(artists, query)
            artist = select_artist(artists) or pick_best_artist(artists, query)

            if not artist:
                console.print("[dim]Skipped.[/dim]")
                return

            console.print(Panel(

                f"[bold cyan]{artist.get('name','Unknown Artist')}[/bold cyan]\n"

                f"[dim]Artist ID: {artist.get('id','')}[/dim]\n\n"

                "Choose whether to browse releases or individual tracks available in this Qobuz store.",

                title="Artist Catalog",

                border_style="cyan"

            ))

            artist_data = get_artist_releases(artist.get("id"))

            releases = artist_release_items(artist_data)
            if not releases:
                console.print("[yellow]No releases were returned for this artist.[/yellow]")
                return

            if choose_artist_catalog() == "albums":
                console.print(Panel(
                    f"[bold cyan]{artist.get('name','Unknown Artist')}[/bold cyan]\n"
                    f"[dim]Artist ID: {artist.get('id','')}[/dim]\n\n"
                    "Releases from this Qobuz store, including albums, EPs, and singles.",
                    title="Artist Albums",
                    border_style="cyan",
                ))
                select_copy("album", releases)
                return

            artist_tracks = artist_track_items(releases, artist)

            if artist_tracks:

                show_tracks(artist_tracks)

                select_copy("track", artist_tracks)

                return

            if releases:

                console.print("[yellow]No artist tracks were returned directly, showing releases instead.[/yellow]")

                show_albums(releases)

                select_copy("album", releases)

                return

            else:

                console.print("[yellow]No releases were returned for this artist.[/yellow]")

                if albums:

                    console.print()

                    show_albums(albums[:10])



    console.print("\n[dim]Tip: one-word searches work, but “Title - Artist” is more precise. Newest dates sort first.[/dim]")


if __name__ == "__main__":

    main()
