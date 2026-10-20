import json
import unittest

from graph.extract_domain_graph import compact_retry_messages, select_inventory_papers


class InventorySelectionTests(unittest.TestCase):
    def setUp(self):
        self.inventory = [
            {"year": 2024, "arxiv_id": "2401.0002"},
            {"year": 2022, "arxiv_id": "2201.0001"},
            {"year": 2024, "arxiv_id": "2401.0001"},
            {"year": 2022, "arxiv_id": "2201.0002"},
        ]

    def test_all_papers_is_sorted_and_includes_every_inventory_entry(self):
        selected = select_inventory_papers(self.inventory, papers_per_year=1, seed=7, all_papers=True)
        self.assertEqual(
            [(paper["year"], paper["arxiv_id"]) for paper in selected],
            [(2022, "2201.0001"), (2022, "2201.0002"), (2024, "2401.0001"), (2024, "2401.0002")],
        )

    def test_default_selection_remains_a_balanced_pilot(self):
        selected = select_inventory_papers(self.inventory, papers_per_year=1, seed=7)
        self.assertEqual(len(selected), 2)
        self.assertEqual({paper["year"] for paper in selected}, {2022, 2024})


class CompactRetryMessageTests(unittest.TestCase):
    def test_context_limit_keeps_both_ends_of_passage(self):
        passage = "A" * 1200 + "IMPORTANT END" + "B" * 1200
        messages = [
            {"role": "developer", "content": "Original prompt"},
            {"role": "user", "content": json.dumps({"passage_id": "p1", "passage": passage})},
        ]

        compact = compact_retry_messages(messages, passage_char_limit=500)
        payload = json.loads(compact[1]["content"])

        self.assertEqual(len(payload["passage"]), 500)
        self.assertTrue(payload["passage"].startswith("A" * 100))
        self.assertTrue(payload["passage"].endswith("B" * 100))
        self.assertNotIn("IMPORTANT END", payload["passage"])
        self.assertNotEqual(compact[0]["content"], messages[0]["content"])

    def test_no_limit_preserves_full_passage_text(self):
        passage = "A passage with full evidence."
        messages = [
            {"role": "developer", "content": "Original prompt"},
            {"role": "user", "content": json.dumps({"passage_id": "p1", "passage": passage})},
        ]

        payload = json.loads(compact_retry_messages(messages)[1]["content"])
        self.assertEqual(payload["passage"], passage)


if __name__ == "__main__":
    unittest.main()
