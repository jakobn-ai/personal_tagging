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
        raise ValueError(f"Album {name} not literally found by artist "
                         f"{artist_name}")
    albums_list = sorted(albums_list, key=lambda a: a["date"])
    use_for_cover = None
    for album in reversed(albums_list):
        try:
            musicbrainzngs.get_image_list(album["id"])
            use_for_cover = album
            break
        except musicbrainzngs.musicbrainz.ResponseError:
            continue
    if use_for_cover is None:
        raise ValueError(f"No cover art available for {name} by "
                         f"{artist_name}, this is unsupported behaviour")
    else:
        return albums_list[0]["id"], use_for_cover["id"]


def get_number(string):
    number = string.lower()
    number_strings = ("zero", "one", "two", "three", "four", "five", "six",
                      "seven", "eight", "nine", "ten", "eleven", "twelve")
    roman_strings = ("i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix",
                     "x", "xi", "xii")
    english_numbers = {word: str(number)
                       for number, word in enumerate(number_strings)}
    roman_numbers = {roman: str(number)
                     for number, roman in enumerate(roman_strings, start=1)}
    if number in english_numbers:
        number = english_numbers[number]
    elif number in roman_numbers:
        number = roman_numbers[number]
    else:
        number = string
    return number


def custom_replace_title(title):
    """Make custom spelling replacements to the title"""
    for utf8s, latin1 in ((("–", "—", "―", "‒", "‐", "‑", "⁃"), "-"),
                          (("‘", "’", "‚", "›", "‹", "′", "‵", "ʹ", "’"), "'"),
                          (("“", "”", "„", "»", "«", "″", "‶", "ʺ"), '"'),
                          (("…", "..."))):
        regex = r"("
        for utf8 in utf8s[:-1]:
            regex += rf"{utf8}|"
        regex += rf"{utf8s[-1]})"
        title = re.sub(regex, latin1, title)
    # Medley Song 1/Medley Song 2
    title = title.replace(" / ", "/")
    # Rock'n'Roll etc.
    title = re.sub(r"(\S+)( |'| ')(n|N)( |'|' )(\S+)", r"\1'n'\5", title)

    # Capitalise each word
    for char in (" ", "-", "(", '"', "/"):
        matches = re.finditer(rf"\{char}([A-Za-z]*)", title)
        for match in matches:
            title = title.replace(match.group(0),
                                  f"{char}{match.group(1).capitalize()}")
    # but write these lowercase
    for keyword in ("In", "Of", "The", "To", "And", "At", "A", "An"):
        title = re.sub(rf"([^.:-] ){keyword}( |$)", rf"\1{keyword.lower()}\2",
                       title)

    # Pt./Pts.
    matches = re.finditer(r"P(ar)?t(s?)\.? ([A-Za-z0-9]*)"
                          r"( ?(-|&|and) ?([A-Za-z0-9]*))?", title)
    for match in matches:
        replacement = f"Pt{match.group(2)}. {get_number(match.group(3))}"
        if match.group(4) is not None:
            if match.group(5) == "-":
                replacement += "-"
            else:
                replacement += " & "
            replacement += get_number(match.group(6))
        title = title.replace(match.group(0), replacement)

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
    taggable_information["tracks"] = []
    for disc in sorted(discs, key=lambda disc: int(disc["position"])):
        for song in sorted(disc["track-list"],
                           key=lambda song: int(song["position"])):
            if "title" in song:
                title = song["title"]
            else:
                title = song["recording"]["title"]
            taggable_information["tracks"].append(custom_replace_title(title))

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


def remove_forbidden_characters(title):
    return re.sub(r"[<>:/\"\\|?*]", "-", title)


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
    picture.type = mutagen.id3.PictureType.COVER_FRONT
    picture.mime = "image/png"
    picture_data = picture.write()
    encoded_data = base64.b64encode(picture_data)
    vcomment_value = encoded_data.decode("ascii")
    audio["metadata_block_picture"] = [vcomment_value]

    title = remove_forbidden_characters(title)
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
    if not output_dict:
        raise ValueError("Please run on artist-album tree including OGG "
                         "Vorbis or FLAC files")
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
# [including]
# Only ask for image once, function without available image
# improve image  & release heuristic
# (esp. don't use pre-album single of the same name)
# AAC
# "Expanded" albums (personal bonus tracks)
# OST, Podcast/audiobook, classical music
# Track & album information like live recording, feature
# Suites like Atom Heart Mother [Father's Shout/etc.]
# Custom album name like The Beatles -> The Beatles (White Album)
# Auto-tag singles from the song without folder structure


if __name__ == "__main__":
    main()
