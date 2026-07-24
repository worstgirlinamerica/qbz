import tempfile
import unittest
from pathlib import Path

from qbz.cli import extract_lyrics, normalize_credit_role, quality_choices_for_item
import qbz.download as download


class MetadataTests(unittest.TestCase):
    def test_credit_roles_are_readable(self):
        self.assertEqual(normalize_credit_role("PerformingArtist"), "Performing Artist")
        tags = download.build_credit_tags({
            "credits_by_role": {"PerformingArtist": ["Tyla"], "ComposerLyricist": ["Writer"]},
        })
        self.assertIn("Performing Artist", tags)
        self.assertIn("Composer", tags)
        self.assertIn("Lyricist", tags)

    def test_lyrics_are_extracted_from_catalog_payloads(self):
        payload = {"lyrics": {"text": "line one\nline two"}}
        self.assertEqual(extract_lyrics(payload), "line one\nline two")

    def test_quality_menu_has_credits_only(self):
        values = [value for value, _ in quality_choices_for_item({})]
        self.assertIn("C", values)

    def test_folder_uses_delivered_resolution_fields(self):
        previous = download.OUTPUT_ROOT
        try:
            with tempfile.TemporaryDirectory() as root:
                download.OUTPUT_ROOT = Path(root)
                meta = {
                    "artist": "Test Artist",
                    "album": {"title": "Test Album"},
                    "quality_id": "27",
                    "bit_depth": 24,
                    "sampling_rate": 96000,
                }
                folder = download.output_folder_for(meta, meta)
                self.assertTrue(folder.name.endswith("[24b 96k]"))
        finally:
            download.OUTPUT_ROOT = previous
