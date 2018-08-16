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


if __name__ == '__main__':
    unittest.main()
