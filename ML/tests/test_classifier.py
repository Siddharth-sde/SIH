"""
Unit tests for Stage 3 Classifier and Vector Embeddings.
"""

import pytest
import numpy as np
import pandas as pd
from src.preprocessor import preprocessor
from src.attribute_extractor import attribute_extractor
from src.classifier import classifier, TAXONOMY


def test_embedding_shape_and_normalization():
    emb = classifier.encode_text("Gate Valve Cast Steel 150NB Class 150")
    assert isinstance(emb, np.ndarray)
    assert emb.shape == (384,)
    # Should be normalized unit vector (L2 norm ~ 1.0)
    norm = np.linalg.norm(emb)
    assert abs(norm - 1.0) < 1e-4


def test_category_classification_core_spares():
    test_cases = [
        ("gate valve cast steel 150nb class 150", "VALVES_FLOW"),
        ("spherical roller bearing 22220 iso 15 100x180x46 mm", "BEARINGS"),
        ("spiral wound gasket 150nb class 150 ss316 graphite", "GASKETS_SEALS"),
        ("cable cross-linked polyethylene 11kv 3c x 400 sqmm aluminium armoured", "CABLES_CONDUCTORS"),
        ("power transformer oil filled onan 25mva 33kv 11kv", "TRANSFORMERS"),
        ("moulded case circuit breaker 400a 4 pole 36ka", "SWITCHGEAR"),
        ("steel wire rope 6x36 independent wire rope core 24mm", "ROPES_CHAINS"),
        ("rubber conveyor belt 1200mm 4 ply nylon ep grade", "CONVEYOR_BELTING"),
        ("tricone rock drill bit 8.5 inch iadc 517", "DRILLING_MINING"),
        ("manganese steel crusher liner hadfield steel jaw plate", "WEAR_PARTS"),
        ("hot rolled mild steel plate 12mm thickness 2000x6000mm is 2062", "STRUCTURAL_STEEL"),
        ("fireclay refractory bricks 230x115x65mm", "REFRACTORIES"),
        ("hex head bolt m16 x 80 grade 8.8 zinc plated", "FASTENERS"),
        ("flexible jaw coupling l-110 polyurethane spider", "COUPLINGS"),
        ("grid coupling g20 carbon steel grid flanged", "COUPLINGS"),
        ("centrifugal pump cast steel 50hp 415v", "PUMPS_ROTATING"),
    ]

    for text, expected_cat in test_cases:
        res = classifier.classify(text)
        assert res["category_id"] == expected_cat, f"Expected {expected_cat} for '{text}', got {res['category_id']}"
        assert res["confidence"] >= 0.70
        assert len(res["embedding"]) == 384


def test_adversarial_ambiguous_classification():
    # Ambiguous items should be routed to MISC_UNCLASSIFIED
    specs_ambig = {"is_ambiguous": True, "ambiguity_reason": "Low Information"}
    res = classifier.classify("pt no 4471b misc spare", extracted_specs=specs_ambig)

    assert res["category_id"] == "MISC_UNCLASSIFIED"
    assert res["confidence"] < 0.50
    assert res["method"] == "triage_rule"


def test_classifier_on_400_dataset():
    df = pd.read_csv("material_master_input.csv")
    p_df = preprocessor.process_dataframe(df)

    category_counts = {}
    for _, row in p_df.iterrows():
        specs = attribute_extractor.extract(row["cleaned_description"], row["cleaned_spec_text"])
        res = classifier.classify(row["cleaned_description"], row["cleaned_spec_text"], specs)
        cat = res["category_id"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Should classify across multiple categories
    assert len(category_counts) >= 12
    # Ensure bearings and valves represent substantial portions
    assert category_counts.get("BEARINGS", 0) >= 20
    assert category_counts.get("VALVES_FLOW", 0) >= 20
