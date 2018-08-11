#!/usr/bin/env python3

"""An automatic audio metadata tagger with my own ideas of a well organised
 library using Mutagen & MusicBrainz.
 """

import musicbrainzngs

# Developing only, but I do not want to look it up every time I need it
# import pprint
# pp = pprint.PrettyPrinter()
# pp.pprint(something)


def get_artist_id(name):
    """Find the ID of an artist by their name"""
    artists_dict = musicbrainzngs.search_artists(name)
    for i in range(len(artists_dict["artist-list"])):
        if name == artists_dict["artist-list"][i]["name"]:
            return artists_dict["artist-list"][i]["id"]
    raise ValueError("Artist %s not literally found" % name)


def get_album_id(name, artist_id):
    """Find the ID of an album by its name and its artist ID"""
    albums_dict = musicbrainzngs.search_releases(name)
    for i in range(len(albums_dict["release-list"])):
        if name == albums_dict["release-list"][i]["title"]:
            for j in range(len(albums_dict["release-list"][i][
                    "artist-credit"])):
                if artist_id == albums_dict["release-list"][i][
                        "artist-credit"][j]["artist"]["id"]:
                    return albums_dict["release-list"][i]["id"]
    raise ValueError("Album %s not literally found with artist %s" % (
        name, musicbrainzngs.get_artist_by_id(artist_id)["artist"]["name"]))


def main():
    """Set a user agent (mandatory)"""
    musicbrainzngs.set_useragent("personal_tagging", 0.1)


if __name__ == "__main__":
    main()
