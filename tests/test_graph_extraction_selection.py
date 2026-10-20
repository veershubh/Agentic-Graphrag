import unittest

from graph.extract_domain_graph import select_inventory_papers


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


if __name__ == "__main__":
    unittest.main()
