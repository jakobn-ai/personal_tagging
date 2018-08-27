#!/usr/bin/env python3

"""Tests for the personal_tagging project"""

import unittest
import os
import musicbrainzngs
from PIL import Image
import personal_tagging


class TestGetArtistID(unittest.TestCase):
    """Test get_artist_id"""

    def test_normal_input(self):
        """Test with normal input"""
        personal_tagging.setup()
        self.test_id = personal_tagging.get_artist_id("MusicBrainz Test "
                                                      "Artist")
        self.assertEqual(self.test_id, "7e84f845-ac16-41fe-9ff8-df12eb32af55")

    def test_sanity(self):
        """Sanity check: Does it yield different IDs for different queries?"""
        personal_tagging.setup()
        self.test_id = personal_tagging.get_artist_id("The Beatles")
        self.assertNotEqual(self.test_id, "7e84f845-ac16-41fe-9ff8-"
                            "df12eb32af55")

    def test_value_error(self):
        """Test value error: Find an artist that does not exist"""
        personal_tagging.setup()
        with self.assertRaises(ValueError):
            personal_tagging.get_artist_id("I cannot think of a query where "
                                           "I can be certain such a band will "
                                           "never exist but I think this does "
                                           "the job")


class TestGetAlbumID(unittest.TestCase):
    """Test get_album_id"""

    def test_normal_input(self):
        """Test with normal input"""
        personal_tagging.setup()
        self.test_id = personal_tagging.get_album_id("Pregap and Data Tracks",
                                                     "7e84f845-ac16-41fe-9ff8-"
                                                     "df12eb32af55",
                                                     "MusicBrainz Test Artist")
        self.assertEqual(self.test_id, "06c015bb-b3bb-4904-a339-e2b55ea3d6bf")

    def test_sanity(self):
        """Sanity check: Does it yield different IDs for different queries?"""
        personal_tagging.setup()
        self.test_id = personal_tagging.get_album_id("The Beatles",
                                                     "b10bbbfc-cf9e-42e0-be17-"
                                                     "e2c3e1d2600d",
                                                     "The Beatles")
        self.assertNotEqual(self.test_id, "06c015bb-b3bb-4904-a339-"
                            "e2b55ea3d6bf")

    def test_value_error(self):
        """Test value error: Find an album that does not exist"""
        personal_tagging.setup()
        with self.assertRaises(ValueError):
            personal_tagging.get_album_id("I cannot think of a query where "
                                          "I can be certain such an album "
                                          "will never exist but I think this "
                                          "does the job",
                                          "7e84f845-ac16-41fe-9ff8-"
                                          "df12eb32af55",
                                          "MusicBrainz Test Artist")


class TestGetTaggableInformationAux(unittest.TestCase):
    """Save this across multiple tests"""
    tracklist = ["Back in the U.S.S.R.",
                 "Dear Prudence",
                 "Glass Onion",
                 "Ob‐La‐Di, Ob‐La‐Da",
                 "Wild Honey Pie",
                 "The Continuing Story of Bungalow Bill",
                 "While My Guitar Gently Weeps",
                 "Happiness Is a Warm Gun",
                 "Martha My Dear",
                 "I’m So Tired",
                 "Blackbird",
                 "Piggies",
                 "Rocky Raccoon",
                 "Don’t Pass Me By",
                 "Why Don’t We Do It in the Road?",
                 "I Will",
                 "Julia",
                 "Birthday",
                 "Yer Blues",
                 "Mother Nature’s Son",
                 "Everybody’s Got Something to Hide Except Me and "
                 "My Monkey",
                 "Sexy Sadie",
                 "Helter Skelter",
                 "Long, Long, Long",
                 "Revolution 1",
                 "Honey Pie",
                 "Savoy Truffle",
                 "Cry Baby Cry, Part 1",
                 "Cry Baby Cry, Part 2",
                 "Revolution 9",
                 "Good Night"]
    url = ("http://coverartarchive.org/release/3fca59cc-a22f-4a57-"
           "8d69-05bf33595ca6/12447401370.jpg")
    expected_information = {}
    expected_information["year"] = "2000"
    expected_information["tracks"] = tracklist
    expected_information["image_url"] = url


class TestGetTaggableInformation(TestGetTaggableInformationAux):
    """Tests get_taggable_information"""

    def test_normal_input(self):
        """Tests with normal input"""
        personal_tagging.setup()
        self.taggable_information = (personal_tagging.
                                     get_taggable_information("3fca59cc-a22f-"
                                                              "4a57-8d69-"
                                                              "05bf33595ca6"))
        self.assertEqual(self.expected_information, self.taggable_information)

    def test_sanity(self):
        """Sanity check: Does it yield different information for different
        queries?
        """
        personal_tagging.setup()
        # Please Please Me because MusicBrainz Test Artist has no cover
        self.taggable_information = (personal_tagging.
                                     get_taggable_information("ade577f6-6087-"
                                                              "4a4f-8e87-"
                                                              "38b0f8169814"))
        self.assertNotEqual(self.expected_information,
                            self.taggable_information)


class TestGetCoverImage(unittest.TestCase):
    """Tests get_cover_image"""

    def test_normal_input(self):
        """Tests with normal input"""
        personal_tagging.setup()
        self.imagefile = (personal_tagging.
                          get_cover_image(personal_tagging.
                                          get_taggable_information("3fca59cc-"
                                                                   "a22f-4a57-"
                                                                   "8d69-05bf3"
                                                                   "3595ca6")
                                          ["image_url"]))
        self.img = Image.open(self.imagefile)
        self.assertEqual(max(self.img.size), 600)
        self.assertRegex(self.imagefile, r".*\.png")
        os.remove(self.imagefile)


if __name__ == '__main__':
    unittest.main()
