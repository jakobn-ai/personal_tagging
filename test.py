#!/usr/bin/env python3

"""Tests for the personal_tagging project"""

import unittest
import personal_tagging


class TestGetArtistID(unittest.TestCase):
    """Test get_artist_id"""

    def test_normal_input(self):
        """Test with normal input"""
        personal_tagging.setup()
        test_id = personal_tagging.get_artist_id("MusicBrainz Test Artist")
        self.assertEqual(test_id, "7e84f845-ac16-41fe-9ff8-df12eb32af55")

    def test_sanity(self):
        """Sanity check: Does it yield different IDs for different queries?"""
        personal_tagging.setup()
        test_id = personal_tagging.get_artist_id("The Beatles")
        self.assertNotEqual(test_id, "7e84f845-ac16-41fe-9ff8-df12eb32af55")

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
        test_id = personal_tagging.get_album_id("Pregap and Data Tracks",
                                                "7e84f845-ac16-41fe-9ff8-"
                                                "df12eb32af55",
                                                "MusicBrainz Test Artist")
        self.assertEqual(test_id, "06c015bb-b3bb-4904-a339-e2b55ea3d6bf")

    def test_sanity(self):
        """Sanity check: Does it yield different IDs for different queries?"""
        personal_tagging.setup()
        test_id = personal_tagging.get_album_id("Please Please Me",
                                                "b10bbbfc-cf9e-42e0-be17-"
                                                "e2c3e1d2600d",
                                                "The Beatles")
        self.assertNotEqual(test_id, "7170854d-7ab3-453d-a5e8-60ef21ffa4c6")

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


if __name__ == '__main__':
    unittest.main()
