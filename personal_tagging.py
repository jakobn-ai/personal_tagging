#!/usr/bin/env python3

import musicbrainzngs

def get_artist_id(name):
    artists_dict = musicbrainzngs.search_artists(name)
    for i in range(len(artists_dict["artist-list"])):
        if name == artists_dict["artist-list"][i]["name"]:
            return artists_dict["artist-list"][i]["id"]
    raise ValueError("Artist %s not literally found" % name)
    

def main():
    musicbrainzngs.set_useragent("personal_tagging", 0.1)

if __name__ == "__main__":
    main()
