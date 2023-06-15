#!/usr/bin/env python3
"""
Updated version of AudioNetwork downloader
"""

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, List, Optional, cast

import bs4
import requests

headers = {
    "User-Agent": "Mozilla/5.0",
}


def download_song(
    session: requests.Session, track_info: Dict[str, Any], output: pathlib.Path
) -> None:
    # Compute the file name
    file_url = track_info["previewUrl"]
    file_ext = file_url.rsplit(".", 1)
    out_name = (
        f"{track_info['albumTrackNumber']:02d}. {track_info['title']}.{file_ext[-1]}"
    )

    try:
        album = track_info["album"]["name"]
        release_year = track_info["releaseDate"].split("-", 1)[0]
        out_folder = output / f"{release_year} - {album}"
    except (KeyError, IndexError):
        out_folder = output

    out_folder.mkdir(parents=True, exist_ok=True)

    # Download the song
    print(out_name, end="...", flush=True)
    response = session.get(file_url, headers=headers)
    response.raise_for_status()
    with open(out_folder / out_name, "wb") as fd:
        fd.write(response.content)
    print("OK.")

    # Add the cover if necessary
    cover_file = out_folder / "folder.jpg"
    if not (cover_file).exists():
        try:
            cover_url = track_info["album"]["artwork"]["url"]
            if cover_url:
                response = session.get(cover_url, headers=headers)
                if response.ok:
                    with open(cover_file, "wb") as fd:
                        fd.write(response.content)
        except KeyError:
            pass


def download_album(
    session: requests.Session,
    album_info: Dict[str, Any],
    tracks_info: List[Dict[str, Any]],
    output: pathlib.Path,
) -> None:
    try:
        album = album_info["title"]
        release_year = album_info["releaseDate"].split("-", 1)[0]
        out_folder = output / f"{release_year} - {album}"
    except (KeyError, IndexError):
        album = "Unknown album"
        out_folder = output

    out_folder.mkdir(parents=True, exist_ok=True)

    # Add the cover if necessary
    cover_file = out_folder / "folder.jpg"
    if not (cover_file).exists():
        try:
            cover_url = album_info["artwork"]["url"]
            if cover_url:
                response = session.get(cover_url, headers=headers)
                if response.ok:
                    with open(cover_file, "wb") as fd:
                        fd.write(response.content)
        except KeyError:
            print("Couldn't find a cover for album", album, file=sys.stderr)

    print("Downloading", len(tracks_info), "tracks for album", album)
    for track_info in tracks_info:
        # Compute the file name
        file_url = track_info["previewUrl"]
        file_ext = file_url.rsplit(".", 1)
        out_name = f"{track_info['albumTrackNumber']:02d}. {track_info['title']}.{file_ext[-1]}"

        # Download the song
        print(out_name, end="...", flush=True)
        response = session.get(file_url, headers=headers)
        response.raise_for_status()
        with open(out_folder / out_name, "wb") as fd:
            fd.write(response.content)
        print("OK.")


def download(url: str, output: pathlib.Path) -> None:
    with requests.Session() as session:
        # Get the song page
        print("Reading", url)
        response = session.get(url, headers=headers)
        response.raise_for_status()

        # Parse the data part
        soup = bs4.BeautifulSoup(response.text, "html.parser")
        results = soup.find_all(id="__NEXT_DATA__")
        if not results:
            raise Exception("Data segment not found")

        try:
            data = json.loads(results[0].text)
            page_info: Dict[str, Any] = data["props"]["pageProps"]
        except KeyError:
            raise Exception("No page info found.")

        if "track" in page_info:
            print("Downloading a single song")
            download_song(session, page_info["track"], output)
        elif "tracks" in page_info:
            print("Downloading an album")
            download_album(session, page_info["album"], page_info["tracks"], output)
        else:
            raise Exception("No track info found")


def main(args: Optional[List[str]] = None) -> int:
    """
    Entry point
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", type=pathlib.Path, help="Output file/folder")
    parser.add_argument("url", help="AudioNetwork URL")
    options = parser.parse_args(args)

    output = cast(Optional[pathlib.Path], options.output)
    if output is None:
        output = pathlib.Path(".").absolute()
    else:
        output = output.absolute()

    try:
        download(options.url, output)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 127
    except Exception as ex:
        print("An error occurred:", ex, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
