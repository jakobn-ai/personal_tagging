#!/usr/bin/env python3

"""Tests for the personal_tagging project"""

import os
import os.path
import shutil
import stat
import unittest

import mutagen
import PIL.Image

import personal_tagging


led_zeppelin = "678d88b2-87b0-403b-b63d-5da7465aecc3"
physical_graffiti_possible = ("e3f0f405-d50f-45a4-ba71-795e7333fb56",
                              "0d06025c-afff-49fd-a1db-8005e686e4d9")
physical_graffiti = physical_graffiti_possible[0]
physical_graffiti_cover = "052dfa98-047d-43c2-bb46-bfadde0765f8"
rolling_stones = "b071f9fa-14b0-4217-8e97-eb41da73f598"
let_it_bleed = "15d6b4ef-8517-348e-a50f-e3e2417f009b"
let_it_bleed_cover = "abd6d55d-7cc5-4794-bedb-0ccb636c26c2"
tracklist = ["Custard Pie", "The Rover", "In My Time of Dying",
             "Houses of the Holy", "Trampled Under Foot", "Kashmir",
             "In the Light", "Bron-Yr-Aur", "Down By the Seaside",
             "Ten Years Gone", "Night Flight", "The Wanton Song",
             "Boogie With Stu", "Black Country Woman", "Sick Again"]
url = ("http://coverartarchive.org/release/"
       "052dfa98-047d-43c2-bb46-bfadde0765f8/8739384867.jpg")
expected_information = {"year": "1975", "tracks": tracklist, "image_url": url}


class TestGetArtistID(unittest.TestCase):
    """Test get_artist_id"""

    def test_normal_input(self):
        """Test with normal input"""
        personal_tagging.setup()
        test_id = personal_tagging.get_artist_id("Led Zeppelin")
        self.assertEqual(test_id, led_zeppelin)

    def test_sanity(self):
        """Sanity check: Does it yield different IDs for different queries?"""
        personal_tagging.setup()
        test_id = personal_tagging.get_artist_id("The Rolling Stones")
        self.assertNotEqual(test_id, led_zeppelin)

    def test_value_error(self):
        """Test value error: Find an artist that does not exist"""
        personal_tagging.setup()
        with self.assertRaises(ValueError):
            personal_tagging.get_artist_id("I cannot think of a query where "
                                           "I can be certain such an artist "
                                           "will never exist but I think this "
                                           "does the job")


class TestGetAlbumIDs(unittest.TestCase):
    """Tests get_album_ids"""

    def test_normal_input(self):
        """Test with normal input"""
        personal_tagging.setup()
        test_ids = personal_tagging.get_album_ids("Physical Graffiti",
                                                  led_zeppelin, "Led Zeppelin")
        # release used for cover may change in the future
        self.assertIn(test_ids[0], physical_graffiti_possible)

    def test_sanity(self):
        """Sanity check: Does it yield different IDs for different queries?"""
        personal_tagging.setup()
        test_ids = personal_tagging.get_album_ids("Let It Bleed",
                                                  rolling_stones,
                                                  "The Rolling Stones")
        for test_id in test_ids:
            self.assertNotIn(test_id, physical_graffiti_possible)

    def test_value_error(self):
        """Test value error: Find an album that does not exist"""
        personal_tagging.setup()
        with self.assertRaises(ValueError):
            personal_tagging.get_album_ids("I cannot think of a query where "
                                           "I can be certain such an album "
                                           "will never exist but I think this "
                                           "does the job", led_zeppelin,
                                           "Led Zeppelin")


class TestGetTaggableInformation(unittest.TestCase):
    """Tests get_taggable_information"""

    def test_normal_input(self):
        """Tests with normal input"""
        self.maxDiff = None
        personal_tagging.setup()
        taggable_information = personal_tagging.get_taggable_information(
            (physical_graffiti, physical_graffiti_cover))
        self.assertEqual(expected_information, taggable_information)

    def test_sanity(self):
        """Sanity check: Does it yield different information for different
        queries?
        """
        personal_tagging.setup()
        taggable_information = personal_tagging.get_taggable_information(
            (let_it_bleed, let_it_bleed_cover))
        self.assertNotEqual(expected_information, taggable_information)


class TestGetCoverImage(unittest.TestCase):
    """Tests get_cover_image"""

    def test_normal_input(self):
        """Tests with normal input"""
        personal_tagging.setup()
        image_url = personal_tagging.get_taggable_information(
            (physical_graffiti, physical_graffiti_cover))["image_url"]
        imagefile = personal_tagging.get_cover_image(image_url)
        with PIL.Image.open(imagefile) as img:
            self.assertEqual(max(img.size), 600)
        self.assertRegex(imagefile, r".*\.png")
        os.remove(imagefile)

    def test_permission_error(self):
        """Tests with missing write access"""
        personal_tagging.setup()
        original_perms = os.stat(".").st_mode
        # Revoke write permissions
        os.chmod(".", original_perms & ~stat.S_IWUSR)
        image_url = personal_tagging.get_taggable_information(
            (physical_graffiti, physical_graffiti_cover))["image_url"]
        with self.assertRaises(PermissionError):
            personal_tagging.get_cover_image(image_url)
        os.chmod(".", original_perms)


class TestRemoveForbiddenCharacters(unittest.TestCase):
    """Tests remove_forbidden_characters"""

    def test_normal_input(self):
        """Tests with normal input"""
        self.assertEqual(personal_tagging.
                         remove_forbidden_characters('<>:"/\\|?*'),
                         "---------")


class TestTag(unittest.TestCase):
    """Tests tag"""

    def test_normal_input(self):
        """Tests with normal input"""
        personal_tagging.setup()
        image_url = personal_tagging.get_taggable_information(
            (physical_graffiti, physical_graffiti_cover))["image_url"]
        imagefile = personal_tagging.get_cover_image(image_url)
        for extension in ("ogg", "flac"):
            filename = "01 Custard Pie." + extension
            shutil.copyfile(os.path.join("testlibrary", "testartist",
                                         "testalbum", f"testfile.{extension}"),
                            filename)
            personal_tagging.tag(filename, "Led Zeppelin", "Physical Graffiti",
                                 "1975", tracklist, imagefile)
            tags_dict = mutagen.File(filename)
            self.assertEqual(tags_dict["artist"][0], "Led Zeppelin")
            self.assertEqual(tags_dict["album"][0], "Physical Graffiti")
            self.assertEqual(tags_dict["tracknumber"][0], "01")
            self.assertEqual(tags_dict["title"][0], "Custard Pie")
            self.assertEqual(tags_dict["date"][0], "1975")
            os.remove(filename)
        os.remove(imagefile)

    def test_permission_errors(self):
        """Tests with missing write access"""
        personal_tagging.setup()
        image_url = personal_tagging.get_taggable_information(
            (physical_graffiti, physical_graffiti_cover))["image_url"]
        imagefile = personal_tagging.get_cover_image(image_url)
        filename = "01.ogg"
        shutil.copyfile(os.path.join("testlibrary", "testartist", "testalbum",
                                     "testfile.ogg"), filename)
        original_perms = os.stat(".").st_mode
        # Revoke write permissions on directory
        os.chmod(".", original_perms & ~stat.S_IWUSR)
        with self.assertRaises(PermissionError):
            personal_tagging.tag(filename, "Led Zeppelin", "Physical Graffiti",
                                 "1975", tracklist, imagefile)
        os.chmod(".", original_perms)

        original_perms = os.stat(filename).st_mode
        # Revoke write permissions on song
        os.chmod(filename, os.stat(filename).st_mode & ~stat.S_IWUSR)
        with self.assertRaises(PermissionError):
            personal_tagging.tag(filename, "Led Zeppelin", "Physical Graffiti",
                                 "1975", tracklist, imagefile)
        os.chmod(filename, original_perms)

        os.remove(filename)
        os.remove(imagefile)

    def test_not_given_format(self):
        """Tests with files that aren't the given format"""
        personal_tagging.setup()
        image_url = personal_tagging.get_taggable_information(
            (physical_graffiti, physical_graffiti_cover))["image_url"]
        imagefile = personal_tagging.get_cover_image(image_url)
        for extension in (".ogg", ".flac"):
            filename = "01" + extension
            open(filename, "w").close()
            with self.assertRaises(ValueError):
                personal_tagging.tag(filename, "Led Zeppelin",
                                     "Physical Graffiti", "1975", tracklist,
                                     imagefile)
            os.remove(filename)
        os.remove(imagefile)


class TestGetFiles(unittest.TestCase):
    """Tests get_files"""

    def test_normal_input(self):
        """Tests with normal input"""
        files_dict = personal_tagging.get_files("testlibrary")
        self.assertEqual(list(files_dict), ["testartist"])
        self.assertEqual(list(files_dict["testartist"]["albums"]),
                         ["testalbum"])
        files = [os.path.join("testlibrary", "testartist", "testalbum",
                              f"testfile.{extension}")
                 for extension in ("flac", "ogg")]
        self.assertEqual(sorted(files_dict["testartist"]["albums"]["testalbum"]
                                ["tracks"]), files)

    def test_missing_dir(self):
        """Tests with a directory that doesn't exist"""
        with self.assertRaises(ValueError):
            personal_tagging.get_files("library")


if __name__ == "__main__":
    unittest.main()
