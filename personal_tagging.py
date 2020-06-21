#!/usr/bin/env python3

"""An automatic audio metadata tagger with my own ideas of a well organised
library using Mutagen & MusicBrainz.
"""

import base64
import os
import os.path
import re
import sys
import urllib.error
import urllib.request
import urllib.parse

import musicbrainzngs
import mutagen.flac
import mutagen.oggvorbis
import PIL.Image

# Developing only, but I do not want to look it up every time I need it
# import pprint
# pp = pprint.PrettyPrinter()
# pp.pprint(something)


def setup():
    """Set up a user agent (mandatory)"""
    musicbrainzngs.set_useragent("personal_tagging", 0.1,
                                 "https://github.com/jakobn-ai/"
                                 "personal_tagging")


def get_artist_id(name):
    """Find the ID of an artist by their name."""
    try:
        return next(filter(lambda a: a["name"].lower() == name.lower(),
                           musicbrainzngs.search_artists(name)
                           ["artist-list"]))["id"]
    except StopIteration:
        raise ValueError(f"Artist {name} not literally found")


def get_album_ids(name, artist_id, artist_name):
    """Find the first and latest IDs of an album by its name and its artist ID.
    Artist name is for error output.
    """
    albums_list = [album for album in musicbrainzngs.
                   search_releases(query=name, arid=artist_id)["release-list"]
                   if remove_forbidden_characters(custom_replace_title(
                           album["title"])).lower() == name.lower()
                   and "date" in album and album["date"]]
    if not albums_list:
        raise ValueError(f"Album {name} not literally found from artist"
                         f"{artist_name}")
    sorted(albums_list, key=lambda a: a["date"])
    return albums_list[0]["id"], albums_list[-1]["id"]


def custom_replace_title(title):
    """Make custom spelling replacements to the title"""
    title = title.replace("-", "-")  # Hyphen to ASCII
    title = title.replace("’", "'")  # Typesetting apostrophe to ASCII
    # Rock'n'Roll etc.
    title = re.sub(r"(\S+)( |'| ')(n|N)( |'|' )(\S+)", r"\1'n'\5", title)
    # Capitalise each word
    title.join(word.capitalize() for word in title.split())
    for keyword in ("In", "Of", "The", "To", "And", "At", "A", "An"):
        title = title.replace(f" {keyword}", f" {keyword.lower()}")
    title = re.sub(r"(.*)Part(s|)(\W*)", r"\1Pt\2.\3", title)  # Pt./Pts.
    return title


def custom_replace_album(artist, album):
    """Make custom spelling replacements to the album"""
    # contains artist name already?
    if artist in album:
        return album
    keywords = ("best", "classic", "collection", "definitive", "essential",
                "greatest", "live", "hits", "singles", "ultimate")
    for keyword in keywords:
        if keyword in album.lower():
            return f"{album} ({artist})"
    return album


def get_taggable_information(album_ids):
    """Find the songs, release year, and coverartarchive.org URL of an album
    by its ID.
    """
    album_dict = musicbrainzngs.get_release_by_id(id=album_ids[0],
                                                  includes="recordings")
    image_dict = musicbrainzngs.get_image_list(album_ids[1])
    taggable_information = {}

    taggable_information["year"] = re.sub(r"([0-9]{4})(-[0-9]{2}){2}", r"\1",
                                          album_dict["release"]["date"])

    discs = album_dict["release"]["medium-list"]
    sorted(discs, key=lambda disc: disc["position"])
    taggable_information["tracks"] = []
    for disc in discs:
        sorted(disc["track-list"], key=lambda song: song["position"])
        taggable_information["tracks"] += \
            [custom_replace_title(song["recording"]["title"])
             for song in disc["track-list"]]

    for image in image_dict["images"]:
        if "Front" in image["types"]:
            taggable_information["image_url"] = image["image"]

    return taggable_information


def get_cover_image(image_url):
    """Get and scale an image from the URL."""
    filename = os.path.basename(urllib.parse.urlparse(image_url).path)
    try:
        urllib.request.urlretrieve(image_url, filename)
    except PermissionError:
        raise PermissionError("Could not write image. Please execute from a "
                              "directory where you have write permissions.")
    with PIL.Image.open(filename) as cover_img:
        width, height = cover_img.size
        scalefactor = 600 / max(width, height)
        cover_img = cover_img.resize((int(width * scalefactor),
                                      int(height * scalefactor)))
        os.remove(filename)
        filename = f"{os.path.splitext(filename)[0]}.png"
        cover_img.save(filename)
        return filename


def tag(filename, artist_name, album_name,
        release_year, track_list, cover_file):
    """Tag a file with given information, latter three arguments are from
    get_taggable_information.
    """
    no_ext_filename, format_extension = os.path.splitext(filename)
    path, no_path_filename = os.path.split(no_ext_filename)
    try:
        number_string = no_path_filename[0:2]
        track_number = int(number_string)
    except (IndexError, ValueError):
        raise ValueError(f"{filename} does not adhere to the standard of "
                         "starting with two numbers")
    title = track_list[track_number - 1]

    if format_extension == ".ogg":
        try:
            audio = mutagen.oggvorbis.OggVorbis(filename)
        except mutagen.oggvorbis.OggVorbisHeaderError:
            raise ValueError(f"{filename} is not an OGG Vorbis file")
    else:
        try:
            audio = mutagen.flac.FLAC(filename)
        except mutagen.flac.error:
            raise ValueError(f"{filename} is not a FLAC file")
    audio["tracknumber"] = number_string
    audio["title"] = title
    audio["album"] = album_name
    audio["artist"] = artist_name
    audio["date"] = release_year

    # Encode cover image
    with open(cover_file, "rb") as cover:
        data = cover.read()
    picture = mutagen.flac.Picture()
    picture.data = data
    picture_data = picture.write()
    encoded_data = base64.b64encode(picture_data)
    vcomment_value = encoded_data.decode("ascii")
    audio["metadata_block_picture"] = [vcomment_value]

    try:
        audio.save()
        os.rename(filename,
                  os.path.join(path,
                               f"{number_string} {title}{format_extension}"))
    except (mutagen.MutagenError, PermissionError):
        raise PermissionError("Could not write to song. Please run on songs "
                              "you have write permissions to.")


def get_files(directory):
    """Get all relevant files and output an artist-album-filename dict"""
    if not os.path.isdir(directory):
        raise ValueError(f"Directory {directory} does not exist")
    output_dict = {}
    for root, _, files in os.walk(directory):
        for filename in files:
            if not (filename.endswith(".ogg") or filename.endswith(".flac")):
                continue
            filename = os.path.join(root, filename)
            album, _ = os.path.split(filename)
            prefix, album = os.path.split(album)
            _, artist = os.path.split(prefix)
            if artist not in output_dict:
                output_dict[artist] = {}
                output_dict[artist]["albums"] = {}
            if album not in output_dict[artist]["albums"]:
                output_dict[artist]["albums"][album] = {}
                output_dict[artist]["albums"][album]["tracks"] = []
            output_dict[artist]["albums"][album]["tracks"].append(filename)
    return output_dict


def main():
    """Operate on files in an album directory in an artist directory"""
    files = get_files(sys.argv[1])
    setup()
    try:
        for artist in files:
            files[artist]["artist_id"] = get_artist_id(artist)
            for album in files[artist]["albums"]:
                album_name = custom_replace_album(artist, album)
                files[artist]["albums"][album]["album_ids"] = get_album_ids(
                    album, files[artist]["artist_id"], artist)
                files[artist]["albums"][album]["taggable_information"] = (
                    get_taggable_information(files[artist]["albums"][album]
                                                  ["album_ids"]))
                files[artist]["albums"][album]["cover_file"] = (
                    get_cover_image(files[artist]["albums"][album]
                                         ["taggable_information"]
                                         ["image_url"]))
                for track in files[artist]["albums"][album]["tracks"]:
                    tag(track, artist, album_name,
                        files[artist]["albums"][album]["taggable_information"]
                        ["year"],
                        files[artist]["albums"][album]["taggable_information"]
                        ["tracks"],
                        files[artist]["albums"][album]["cover_file"])
                os.remove(files[artist]["albums"][album]["cover_file"])
    except musicbrainzngs.musicbrainz.NetworkError:
        raise urllib.error.URLError("Could not connect to MusicBrainz")


# TODO Target features
# Test case that better represents features (like a Greatest Hits album)
# Catch unexpected title
# "Expanded" albums (personal bonus tracks)
# OST, Podcast/audiobook, classical music
# Track & album information like live recording, feature
# Suites like Atom Heart Mother [Father's Shout/etc.]
# Custom album name like The Beatles -> The Beatles (White Album)
# Auto-tag singles from the song without folder structure
# AAC


if __name__ == "__main__":
    main()
