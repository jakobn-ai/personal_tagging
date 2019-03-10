#!/usr/bin/env python3

"""An automatic audio metadata tagger with my own ideas of a well organised
library using Mutagen & MusicBrainz.
"""

import re
import os
import sys
import urllib.request
import urllib.error
import base64

import musicbrainzngs
# import mutagen
# from mutagen.oggvorbis import OggVorbis
# from mutagen.flac import FLAC, Picture
import mutagen.oggvorbis
import mutagen.flac
from PIL import Image

# Developing only, but I do not want to look it up every time I need it
# import pprint
# pp = pprint.PrettyPrinter()
# pp.pprint(something)


def setup():
    """Set up a user agent (mandatory)"""
    musicbrainzngs.set_useragent("personal_tagging",
                                 0.1,
                                 "https://github.com/jakobn-ai/"
                                 "personal_tagging")


def get_artist_id(name):
    """Find the ID of an artist by their name."""
    artists = musicbrainzngs.search_artists(name)["artist-list"]
    for artist in artists:
        if name == artist["name"]:
            return artist["id"]
    raise ValueError("Artist %s not literally found" % name)


def get_album_id(name, artist_id, artist_name):
    """Find the ID of an album by its name and its artist ID.
    Artist name is for error output.
    """
    albums_list = (musicbrainzngs.
                   search_releases(query=name, arid=artist_id)["release-list"])
    albums_list = [album for album in albums_list
                   if name == album["title"] and "date" in album]
    if albums_list == []:
        raise ValueError("Album %s not literally found from artist %s" %
                         (name, artist_name))
    sorted(albums_list, key=lambda album: album["date"])
    return(albums_list[0]["id"], albums_list[len(albums_list) - 1]["id"])


def custom_replace_title(title):
    """Make custom spelling replacements to the title"""
    title = re.sub(r"-", "-", title)  # Hyphen to ASCII
    title = re.sub(r"’", "'", title)  # Typesetting apostrophe to ASCII
    # Rock'n'Roll, Guns'n'Roses etc.
    title = re.sub(r"(\S+)( |'| ')(n|N)( |'|' )(\S+)", r"\1'n'\5", title)
    # Capitalise each word
    title.join(word.capitalize() for word in title.split())
    for keyword in ("In", "Of", "The", "To", "And", "At", "A", "An"):
        title = re.sub(r" " + keyword, " " + keyword.lower(), title)
    title = re.sub(r"(.*)Part(s|)(\W*)", r"\1Pt\2.\3", title)  # Pt./Pts.
    return title


def custom_replace_album(artist, album):
    """Make custom spelling replacements to the album"""
    # contains artist name already?
    if re.match(r".*" + artist + r".*", album):
        return album
    keywords = ("best", "classic", "collection", "definitive", "essential",
                "greatest", "live", "hits", "singles", "ultimate")
    for keyword in keywords:
        if re.match(r".*" + keyword + r".*", album, re.IGNORECASE):
            return album + " (" + artist + ")"
    return album


def get_taggable_information(album_ids):
    """Find the songs, release year, and coverartarchive.org URL of an album
    by its ID.
    """
    album_dict = musicbrainzngs.get_release_by_id(id=album_ids[0],
                                                  includes="recordings")
    image_dict = musicbrainzngs.get_image_list(album_ids[1])
    taggable_information = {}

    taggable_information["year"] = re.sub(r"([0-9]{4})(-[0-9]{2}){2}",
                                          r"\1",
                                          album_dict["release"]["date"])

    discs = album_dict["release"]["medium-list"]
    sorted(discs, key=lambda disc: disc["position"])
    taggable_information["tracks"] = []
    for disc in discs:
        sorted(disc["track-list"], key=lambda song: song["position"])
        for song in disc["track-list"]:
            taggable_information["tracks"].append(custom_replace_title(song[
                "recording"]["title"]))

    for image in image_dict["images"]:
        if "Front" in image["types"]:
            taggable_information["image_url"] = image["image"]

    return taggable_information


def get_cover_image(image_url):
    """Get and scale an image from the URL."""
    filename = re.sub(r"(.*/)*(.*)", r"\2", image_url)
    try:
        urllib.request.urlretrieve(image_url, filename)
    except PermissionError:
        raise PermissionError("Could not write image. Please execute from a "
                              "directory where you have write permissions.")
    cover_img = Image.open(filename)
    width, height = cover_img.size
    scalefactor = 600/max(width, height)
    cover_img = cover_img.resize((int(width * scalefactor),
                                  int(height * scalefactor)))
    os.remove(filename)
    filename = re.sub(r"(.*)\.jpg", r"\1.png", filename)
    cover_img.save(filename)
    return filename


def tag(filename,
        artist_name,
        album_name,
        release_year,
        track_list,
        cover_file):
    """Tag a file with given information, latter three arguments are from
    get_taggable_information.
    """
    # Remove filename except number (if it exists)
    format_extension = re.sub(r".*(\.[^\.]*)", r"\1", filename)
    new_filename = re.sub(r"(.*)([0-9]{2})[^/]*", r"\1\2", filename)
    try:
        os.rename(filename, new_filename)
    except PermissionError:
        raise PermissionError("Could not write to directory. Please run on "
                              "directories you have write permissions to.")
    filename = new_filename
    track_number = re.match(r".*([0-9]{2})", filename).group(1)
    # List index starts at 0
    title = track_list[int(track_number) - 1]

    if format_extension == ".ogg":
        try:
            audio = mutagen.oggvorbis.OggVorbis(filename)
        except mutagen.oggvorbis.OggVorbisHeaderError:
            raise ValueError("%s is not an OGG Vorbis file" % (filename))
    else:
        try:
            audio = mutagen.flac.FLAC(filename)
        except mutagen.flac.error:
            raise ValueError("%s is not a FLAC file" % (filename))
    audio["tracknumber"] = track_number
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
    except mutagen.MutagenError:
        raise PermissionError("Could not write to song. Please run on songs "
                              "you have write permissions to.")
    os.rename(filename, filename + " " + title + format_extension)


def get_files(directory):
    """Get all relevant files and output an artist-album-filename dict"""
    if not os.path.isdir(directory):
        raise ValueError("Directory ./" + directory + " does not exist")
    output_dict = {}
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".ogg") or filename.endswith(".flac"):
                filename = os.path.join(root, filename)
                match = re.match(r".*/([^/]*)/([^/]*)/[^/]*", filename)
                artist, album = match.group(1), match.group(2)
                if artist not in output_dict:
                    output_dict[artist] = {}
                    output_dict[artist]["albums"] = {}
                if album not in output_dict[artist]["albums"]:
                    output_dict[artist]["albums"][album] = {}
                    output_dict[artist]["albums"][album]["tracks"] = []
                output_dict[artist]["albums"][album]["tracks"] += [filename]
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
                files[artist]["albums"][album]["album_ids"] = get_album_id(
                    album, files[artist]["artist_id"], artist)
                files[artist]["albums"][album]["taggable_information"] = (
                    get_taggable_information(files[artist]["albums"][album]
                                                  ["album_ids"]))
                files[artist]["albums"][album]["cover_file"] = (
                    get_cover_image(files[artist]["albums"][album]
                                         ["taggable_information"]
                                         ["image_url"]))
                for track in files[artist]["albums"][album]["tracks"]:
                    tag(track,
                        artist,
                        album_name,
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


if __name__ == "__main__":
    main()
