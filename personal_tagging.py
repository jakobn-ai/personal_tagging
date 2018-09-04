#!/usr/bin/env python3

"""An automatic audio metadata tagger with my own ideas of a well organised
library using Mutagen & MusicBrainz.
"""

import re
import os
import sys
import urllib.request
import base64

import musicbrainzngs
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import Picture
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
    artists_dict = musicbrainzngs.search_artists(name)
    for artist in artists_dict["artist-list"]:
        if name == artist["name"]:
            return artist["id"]
    raise ValueError("Artist %s not literally found" % name)


def get_album_id(name, artist_id, artist_name):
    """Find the ID of an album by its name and its artist ID.
    Artist name is for error output.
    """
    albums_dict = musicbrainzngs.search_releases(query=name, arid=artist_id)
    for album in albums_dict["release-list"]:
        if name == album["title"]:
            return album["id"]
    raise ValueError("Album %s not literally found from artist %s" %
                     (name, artist_name))


def get_taggable_information(album_id):
    """Find the songs, release year, and coverartarchive.org URL of an album
    by its ID.
    """
    album_dict = musicbrainzngs.get_release_by_id(id=album_id,
                                                  includes="recordings")
    image_dict = musicbrainzngs.get_image_list(album_id)
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
            taggable_information["tracks"].append(song["recording"]["title"])

    for image in image_dict["images"]:
        if "Front" in image["types"]:
            taggable_information["image_url"] = image["image"]

    return taggable_information


def get_cover_image(image_url):
    """Get and scale an image from the URL."""
    filename = re.sub(r"(.*/)*(.*)", r"\2", image_url)
    urllib.request.urlretrieve(image_url, filename)
    cover_img = Image.open(filename)
    width, height = cover_img.size
    scalefactor = 600/max(width, height)
    cover_img = cover_img.resize((int(width*scalefactor),
                                  int(height*scalefactor)))
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
    new_filename = re.sub(r"(.*)([0-9]{2})[^/]*",
                          r"\1\2.ogg",
                          filename)
    os.rename(filename, new_filename)
    filename = new_filename
    track_number = re.match(r".*([0-9]{2})\.ogg", filename).group(1)
    # List index starts at 0
    title = track_list[int(track_number) - 1]

    audio = OggVorbis(filename)
    audio["tracknumber"] = track_number
    audio["title"] = title
    audio["album"] = album_name
    audio["artist"] = artist_name
    audio["date"] = release_year

    # Encode cover image
    with open(cover_file, "rb") as cover:
        data = cover.read()
    picture = Picture()
    picture.data = data
    picture_data = picture.write()
    encoded_data = base64.b64encode(picture_data)
    vcomment_value = encoded_data.decode("ascii")
    audio["metadata_block_picture"] = [vcomment_value]

    audio.save()

    # Insert title into filename
    new_filename = re.sub(r"(.*)\.ogg", r"\1", filename)
    new_filename = new_filename + " " + title + ".ogg"
    os.rename(filename, new_filename)


def main():
    """Operate on files in an album directory in an artist directory"""
    match = re.match(r"([^/]*)/([^/]*)", sys.argv[1])
    artist, album = match.group(1), match.group(2)
    artist_id = get_artist_id(artist)  # TODO - character, catch network
    album_id = get_album_id(album, artist_id, artist)
    taggable_information = get_taggable_information(album_id)
    release_year = taggable_information["year"]
    track_list = taggable_information["tracks"]
    cover_file = get_cover_image(taggable_information["image_url"])
    for subdir, dirs, files in os.walk(artist + "/" + album):
        for filename in files:
            tag(artist + "/" + album + "/" + filename,
                artist,
                album,
                release_year,
                track_list,
                cover_file)
    os.remove(cover_file)


if __name__ == "__main__":
    main()
