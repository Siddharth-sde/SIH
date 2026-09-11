"""
Unit tests for Stage 4 Deduplication Matcher, Clustering, and Evaluation.
"""

try:
    import pytest
except ImportError:
    pytest = None
import unittest
import pandas as pd
import numpy as np
from src.preprocessor import preprocessor
from src.attribute_extractor import attribute_extractor
from src.classifier import classifier
from src.matcher import matcher, DeduplicationMatcher, ISO_BEARING_DIMENSIONS, normalize_bearing_part_no


def test_cnmc_generation():
    m = DeduplicationMatcher()
    code1 = m.generate_cnmc_code("VALVES_FLOW", "Oil & Gas", 1)
    assert code1 == "NMC-OG-VLV-0001"

    code2 = m.generate_cnmc_code("BEARINGS", "Steel", 42)
    assert code2 == "NMC-ST-BRG-0042"

    code3 = m.generate_cnmc_code("CABLES_CONDUCTORS", "Power", 9)
    assert code3 == "NMC-PW-CBL-0009"


def test_pairwise_similarity_bearing_cluster():
    m = DeduplicationMatcher()

    # Item 1: CPCL Spherical Roller Bearing
    item1 = {
        "source_material_code": "CP-10010",
        "cleaned_description": "spherical roller bearing bearing 22220",
        "canonical_uom": "NOS",
        "specs": {
            "models": {"part_number": "22220"},
            "dimensions": {"boundary_3d": "100x180x46 mm"},
            "standards": ["ISO 15"]
        },
        "embedding": classifier.encode_text("spherical roller bearing bearing 22220 iso 15 100x180x46 mm")
    }

    # Item 2: SAIL Roll Neck Bearing (same 22220)
    item2 = {
        "source_material_code": "SA-10012",
        "cleaned_description": "spherical roller bearing bearing 22220",
        "canonical_uom": "NOS",
        "specs": {
            "models": {"part_number": "22220"},
            "dimensions": {"boundary_3d": "100x180x46 mm"},
            "standards": ["ISO 15"]
        },
        "embedding": classifier.encode_text("spherical roller bearing bearing 22220 iso 15 100x180x46 mm")
    }

    score, matches, conflicts = m.calculate_pairwise_similarity(item1, item2)
    assert score >= 0.85
    assert not conflicts
    assert any("22220" in m for m in matches)


def test_pairwise_rejection_valve_pressure_conflict():
    m = DeduplicationMatcher()

    v150 = {
        "source_material_code": "CP-50000",
        "cleaned_description": "gate valve 150nb class 150 carbon steel flanged",
        "canonical_uom": "NOS",
        "specs": {"pressure_class": 150, "dimensions": {"nominal_bore": "150NB"}},
        "embedding": classifier.encode_text("gate valve 150nb class 150 carbon steel flanged")
    }

    v300 = {
        "source_material_code": "CP-50010",
        "cleaned_description": "gate valve 150nb class 300 carbon steel flanged",
        "canonical_uom": "NOS",
        "specs": {"pressure_class": 300, "dimensions": {"nominal_bore": "150NB"}},
        "embedding": classifier.encode_text("gate valve 150nb class 300 carbon steel flanged")
    }

    score, matches, conflicts = m.calculate_pairwise_similarity(v150, v300)
    assert score == 0.0
    assert any("Pressure Class Conflict" in c for c in conflicts)


def test_iso_bearing_crosswalk():
    m = DeduplicationMatcher()

    # Case 1: 6205-2RSH vs generic 25x52x15 mm
    item_oem = {
        "source_material_code": "CP-BRG-1",
        "cleaned_description": "deep groove ball bearing 6205-2rsh",
        "canonical_uom": "NOS",
        "specs": {"models": {"part_number": "6205-2RSH"}},
        "embedding": classifier.encode_text("deep groove ball bearing 6205")
    }
    item_gen = {
        "source_material_code": "NT-BRG-1",
        "cleaned_description": "ball bearing 25x52x15 mm rubber sealed",
        "canonical_uom": "NOS",
        "specs": {"dimensions": {"boundary_3d": "25x52x15 mm"}},
        "embedding": classifier.encode_text("ball bearing 25x52x15 mm")
    }
    score1, matches1, conflicts1 = m.calculate_pairwise_similarity(item_oem, item_gen)
    assert score1 >= 0.85
    assert not conflicts1

    # Case 2: 6206-ZZ vs generic 30x62x16 mm
    item_oem2 = {
        "source_material_code": "SA-BRG-2",
        "cleaned_description": "deep groove ball bearing 6206-zz",
        "canonical_uom": "NOS",
        "specs": {"models": {"part_number": "6206-ZZ"}},
        "embedding": classifier.encode_text("deep groove ball bearing 6206")
    }
    item_gen2 = {
        "source_material_code": "CI-BRG-2",
        "cleaned_description": "ball bearing 30x62x16 mm metal shielded",
        "canonical_uom": "NOS",
        "specs": {"dimensions": {"boundary_3d": "30x62x16 mm"}},
        "embedding": classifier.encode_text("ball bearing 30x62x16 mm")
    }
    score2, matches2, conflicts2 = m.calculate_pairwise_similarity(item_oem2, item_gen2)
    assert score2 >= 0.85
    assert not conflicts2


import os


def _find_data_file(filename: str) -> str:
    for candidate in [
        filename,
        os.path.join("ML", filename),
        os.path.join("Datasets", filename),
        os.path.join(os.path.dirname(__file__), "..", filename),
        os.path.join(os.path.dirname(__file__), "..", "..", "Datasets", filename),
    ]:
        if os.path.exists(candidate):
            return candidate
    return filename


def test_clustering_and_evaluation_on_400_dataset():
    df = pd.read_csv(_find_data_file("material_master_input.csv"))
    gt = pd.read_csv(_find_data_file("ground_truth_clusters.csv"))

    p_df = preprocessor.process_dataframe(df)

    records = []
    for idx, row in p_df.iterrows():
        specs = attribute_extractor.extract(row["cleaned_description"], row["cleaned_spec_text"])
        cls = classifier.classify(row["cleaned_description"], row["cleaned_spec_text"], specs)
        records.append({
            "idx": idx,
            "source_material_code": row["source_material_code"],
            "cpse_id": row["cpse_id"],
            "plant_code": df.iloc[idx].get("plant_code", ""),
            "raw_description": row["raw_description"],
            "cleaned_description": row["cleaned_description"],
            "specs": specs,
            "category_id": cls["category_id"],
            "embedding": np.array(cls["embedding"]),
            "canonical_uom": row["canonical_uom"],
            "source_uom": row["source_uom"],
            "unit_price_inr": row["unit_price_inr"],
            "current_stock_qty": row["current_stock_qty"],
            "annual_procurement_qty": row["annual_procurement_qty"],
        })

    golden_clusters, crosswalk_records = matcher.cluster_and_harmonize(records)

    assert len(crosswalk_records) >= 400
    assert len(golden_clusters) > 100

    # Ensure every crosswalk item has a valid CNMC code
    assert all(r["cnmc_code"].startswith("NMC-") for r in crosswalk_records)

    # Evaluate against ground truth
    metrics = matcher.evaluate_against_ground_truth(records, golden_clusters, gt)

    print("\nBenchmark Evaluation Results:")
    print(f"  Total Items:        {metrics['total_items']}")
    print(f"  Golden Clusters:    {metrics['total_golden_clusters']}")
    print(f"  Duplicate Clusters: {metrics['duplicate_clusters']}")
    print(f"  Precision:          {metrics['precision']:.4f}")
    print(f"  Recall:             {metrics['recall']:.4f}")
    print(f"  F1 Score:           {metrics['f1_score']:.4f}")

    assert metrics["precision"] >= 0.90
    assert metrics["recall"] >= 0.60
    assert metrics["f1_score"] >= 0.70


def test_single_item_and_empty_records_clustering():
    m = matcher
    # Empty records
    clusters, crosswalk = m.cluster_and_harmonize([])
    assert clusters == []
    assert crosswalk == []

    # Single item
    single_record = [{
        "idx": 0,
        "source_material_code": "SOLO-01",
        "cpse_id": "TEST_CPSE",
        "sector": "Power",
        "raw_description": "Single Unique Spare Part",
        "cleaned_description": "Single Unique Spare Part",
        "specs": {},
        "category_id": "MISC_UNCLASSIFIED",
        "embedding": np.zeros(384),
        "canonical_uom": "NOS",
        "source_uom": "NOS",
        "unit_price_inr": 1000.0,
        "current_stock_qty": 5,
        "annual_procurement_qty": 10,
    }]
    clusters, crosswalk = m.cluster_and_harmonize(single_record)
    assert len(clusters) == 1
    assert len(crosswalk) == 1
    assert crosswalk[0]["match_type"] == "UNIQUE_MATERIAL"


if __name__ == "__main__":
    suite = unittest.TestSuite()
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            suite.addTest(unittest.FunctionTestCase(obj))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        exit(1)
