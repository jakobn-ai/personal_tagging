#!/usr/bin/env python3

"""Tests for the personal_tagging project"""

import unittest
import os
import stat
import shutil
import musicbrainzngs
import mutagen
from PIL import Image
import personal_tagging
import aux_information


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
        expected_string = "06c015bb-b3bb-4904-a339-e2b55ea3d6bf"
        self.assertEqual(test_id, (expected_string, expected_string))

    def test_sanity(self):
        """Sanity check: Does it yield different IDs for different queries?"""
        personal_tagging.setup()
        test_id = personal_tagging.get_album_id("The Beatles",
                                                "b10bbbfc-cf9e-42e0-be17-"
                                                "e2c3e1d2600d",
                                                "The Beatles")
        expected_string = "06c015bb-b3bb-4904-a339-e2b55ea3d6bf"
        self.assertNotEqual(test_id, (expected_string, expected_string))

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


class TestGetTaggableInformation(unittest.TestCase):
    """Tests get_taggable_information"""

    def test_normal_input(self):
        """Tests with normal input"""
        self.maxDiff = None

        personal_tagging.setup()
        query_id = "3fca59cc-a22f-4a57-8d69-05bf33595ca6"
        taggable_information = (personal_tagging.
                                get_taggable_information((query_id, query_id)))
        self.assertEqual(aux_information.expected_information,
                         taggable_information)

    def test_sanity(self):
        """Sanity check: Does it yield different information for different
        queries?
        """
        personal_tagging.setup()
        # Please Please Me because MusicBrainz Test Artist has no cover
        query_id = "ade577f6-6087-4a4f-8e87-38b0f8169814"
        taggable_information = (personal_tagging.
                                get_taggable_information((query_id, query_id)))
        self.assertNotEqual(aux_information.expected_information,
                            taggable_information)

    def test_404(self):
        """Tests 404 upon searching the image for an album without a cover"""
        personal_tagging.setup()
        query_id = "06c015bb-b3bb-4904-a339-e2b55ea3d6bf"
        with self.assertRaises(musicbrainzngs.musicbrainz.ResponseError):
            personal_tagging.get_taggable_information((query_id, query_id))


class TestGetCoverImage(unittest.TestCase):
    """Tests get_cover_image"""

    def test_normal_input(self):
        """Tests with normal input"""
        personal_tagging.setup()
        query_id = "3fca59cc-a22f-4a57-8d69-05bf33595ca6"
        image_url = (personal_tagging.
                     get_taggable_information((query_id, query_id))
                     ["image_url"])
        imagefile = personal_tagging.get_cover_image(image_url)
        img = Image.open(imagefile)
        self.assertEqual(max(img.size), 600)
        self.assertRegex(imagefile, r".*\.png")
        os.remove(imagefile)

    def test_permission_error(self):
        """Tests with missing write access"""
        personal_tagging.setup()
        original_perms = os.stat(".").st_mode
        # Revoke write permissions
        os.chmod(".", original_perms & ~stat.S_IWUSR)
        query_id = "3fca59cc-a22f-4a57-8d69-05bf33595ca6"
        image_url = (personal_tagging.
                     get_taggable_information((query_id, query_id))
                     ["image_url"])
        with self.assertRaises(PermissionError):
            personal_tagging.get_cover_image(image_url)
        os.chmod(".", original_perms)


class TestTag(unittest.TestCase):
    """Tests tag"""

    def test_normal_input(self):
        """Tests with normal input"""
        personal_tagging.setup()
        query_id = "3fca59cc-a22f-4a57-8d69-05bf33595ca6"
        image_url = (personal_tagging.
                     get_taggable_information((query_id, query_id))
                     ["image_url"])
        imagefile = personal_tagging.get_cover_image(image_url)
        for extension in ("ogg", "flac"):
            filename = "01 Back in the U.S.S.R.." + extension
            shutil.copyfile("testlibrary/testartist/testalbum/testfile." +
                            extension, filename)
            personal_tagging.tag(filename,
                                 "The Beatles",
                                 "The Beatles",
                                 aux_information.expected_information["year"],
                                 aux_information.expected_information["tra"
                                                                      "cks"],
                                 imagefile)
            tags_dict = mutagen.File(filename)
            self.assertEqual(tags_dict["artist"][0], "The Beatles")
            self.assertEqual(tags_dict["album"][0], "The Beatles")
            self.assertEqual(tags_dict["tracknumber"][0], "01")
            self.assertEqual(tags_dict["title"][0], "Back in the U.S.S.R.")
            self.assertEqual(tags_dict["date"][0], "2000")
            self.assertEqual(tags_dict["metadata_block_picture"][0],
                             aux_information.cover_data)
            os.remove(filename)
        os.remove(imagefile)

    def test_permission_errors(self):
        """Tests with missing write access"""
        personal_tagging.setup()
        query_id = "3fca59cc-a22f-4a57-8d69-05bf33595ca6"
        image_url = (personal_tagging.
                     get_taggable_information((query_id, query_id))
                     ["image_url"])
        imagefile = personal_tagging.get_cover_image(image_url)
        filename = "01 Back in the U.S.S.R..ogg"
        shutil.copyfile("testlibrary/testartist/testalbum/testfile.ogg",
                        filename)
        original_perms = os.stat(".").st_mode
        # Revoke write permissions on directory
        os.chmod(".", original_perms & ~stat.S_IWUSR)
        with self.assertRaises(PermissionError):
            personal_tagging.tag(filename,
                                 "The Beatles",
                                 "The Beatles",
                                 aux_information.expected_information["year"],
                                 aux_information.expected_information["tra"
                                                                      "cks"],
                                 imagefile)
        os.chmod(".", original_perms)

        original_perms = os.stat(filename).st_mode
        # Revoke write permissions on song
        os.chmod(filename, os.stat(filename).st_mode & ~stat.S_IWUSR)
        with self.assertRaises(PermissionError):
            personal_tagging.tag(filename,
                                 "The Beatles",
                                 "The Beatles",
                                 aux_information.expected_information["year"],
                                 aux_information.expected_information["tra"
                                                                      "cks"],
                                 imagefile)
        os.chmod("01", original_perms)

        os.remove("01")
        os.remove(imagefile)


class TestGetFiles(unittest.TestCase):
    """Tests get_files"""

    def test_normal_input(self):
        """Tests with normal input"""
        files_dict = personal_tagging.get_files("testlibrary")
        self.assertEqual(list(files_dict), ["testartist"])
        self.assertEqual(list(files_dict["testartist"]["albums"]),
                         ["testalbum"])
        self.assertEqual(sorted(files_dict["testartist"]["albums"]["testalbum"]
                         ["tracks"]),
                         ["testlibrary/testartist/testalbum/testfile.flac",
                          "testlibrary/testartist/testalbum/testfile.ogg"])

    def test_missing_dir(self):
        """Tests with a directory that doesn't exist"""
        with self.assertRaises(ValueError):
            personal_tagging.get_files("library")


if __name__ == '__main__':
    unittest.main()
