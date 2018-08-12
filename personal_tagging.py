#!/usr/bin/env python3

"""An automatic audio metadata tagger with my own ideas of a well organised
library using Mutagen & MusicBrainz.
""" 
import musicbrainzngs
import re
import urllib.request
import os
from PIL import Image

# Developing only, but I do not want to look it up every time I need it
# import pprint
# pp = pprint.PrettyPrinter()
# pp.pprint(something)


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
    output_dict = {}

    output_dict["year"] = re.sub(r"([0-9]{4})(-[0-9]{2}){2}",
                                 r"\1",
                                 album_dict["release"]["date"])

    result_track_list = album_dict["release"]["medium-list"][0]["track-list"]
    sorted(result_track_list, key=lambda song: song["position"])
    output_dict["tracks"] = []
    for song in result_track_list:
        output_dict["tracks"].append(song["recording"]["title"])

    for image in image_dict["images"]:
        if "Front" in image["types"]:
            output_dict["image_url"] = image["image"]

    return output_dict


def get_cover_image(image_url):
    """Get and scale an image from the URL."""
    filename = re.sub(r"(.*/)*(.*)", r"\2", image_url)
    urllib.request.urlretrieve(image_url, filename)
    cover_img = Image.open(filename)
    width, height = cover_img.size
    scalefactor = 600/max(width, height)
    cover_img = cover_img.resize((int(width*scalefactor), int(height*scalefactor)))
    os.remove(filename)
    filename = re.sub(r"(.*)\.jpg", r"\1.png", filename)
    cover_img.save(filename)
    return filename


def main():
    """Set a user agent (mandatory)"""
    musicbrainzngs.set_useragent("personal_tagging",
                                 0.1,
                                 "https://github.com/jakobn-ai/"
                                 "personal_tagging")


if __name__ == "__main__":
    main()
