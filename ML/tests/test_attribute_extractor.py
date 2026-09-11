"""
Unit tests for Stage 2 Attribute Extractor and Conflict Detector.
"""

try:
    import pytest
except ImportError:
    pytest = None
import unittest
import pandas as pd
from src.preprocessor import preprocessor
from src.attribute_extractor import attribute_extractor


def test_standard_and_pressure_extraction():
    text = "gate valve cast steel 150nb class 150 flanged api 600 astm a216 wcb rf"
    specs = attribute_extractor.extract(text)

    assert "API 600" in specs["standards"]
    assert "ASTM A216 WCB" in specs["standards"]
    assert specs["pressure_class"] == 150
    assert specs["dimensions"]["nominal_bore"] == "150NB"
    assert specs["material"] == "Carbon Steel"
    assert specs["flange_face"] == "Raised Face (RF)"
    assert specs["end_connection"] == "Flanged"


def test_bearing_dimension_and_part_number():
    text = "spherical roller bearing bearing 22220 iso 15 100x180x46 mm"
    specs = attribute_extractor.extract(text)

    assert specs["models"]["part_number"] == "22220"
    assert specs["dimensions"]["boundary_3d"] == "100x180x46 mm"
    assert specs["dimensions"]["length_mm"] == 100
    assert specs["dimensions"]["width_mm"] == 180
    assert specs["dimensions"]["thickness_mm"] == 46
    assert "ISO 15" in specs["standards"]


def test_electrical_cable_specs():
    text = "cable cross-linked polyethylene 11kv 3c x 400 sqmm aluminium armoured is 7098"
    specs = attribute_extractor.extract(text)

    assert specs["electrical"]["voltage"] == "11KV"
    assert specs["electrical"]["cable_cores"] == 3
    assert specs["electrical"]["cable_sqmm"] == 400.0
    assert specs["electrical"]["conductor"] == "Aluminium"
    assert specs["electrical"]["insulation"] == "XLPE"
    assert specs["electrical"]["armoured"] is True
    assert "IS 7098" in specs["standards"]


def test_adversarial_conflict_pressure_class():
    # Class 150 vs Class 300 should trigger a hard conflict and 0.0 match score
    v1 = attribute_extractor.extract("gate valve 150nb class 150 carbon steel flanged api 600")
    v2 = attribute_extractor.extract("gate valve 150nb class 300 carbon steel flanged api 600")

    score, matches, conflicts = attribute_extractor.calculate_attribute_match_score(v1, v2)
    assert score == 0.0
    assert any("Pressure Class Conflict" in c for c in conflicts)


def test_adversarial_conflict_conductor_material():
    # Cable 11kV 3C x 400 sqmm Al vs Cu should trigger a hard conflict
    c_al = attribute_extractor.extract("cable 11kv 3c x 400 sqmm aluminium armoured")
    c_cu = attribute_extractor.extract("cable 11kv 3c x 400 sqmm copper armoured")

    score, matches, conflicts = attribute_extractor.calculate_attribute_match_score(c_al, c_cu)
    assert score == 0.0
    assert any("Conductor Conflict" in c for c in conflicts)


def test_adversarial_ambiguous_trap():
    # Bucket C trap items
    ambig1 = attribute_extractor.extract("pt no 4471b misc spare", "insufficient technical information; unidentified spare")
    assert ambig1["is_ambiguous"] is True

    ambig2 = attribute_extractor.extract("motor spare", "no rating, frame, oem or part number supplied")
    assert ambig2["is_ambiguous"] is True


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


def test_attribute_extractor_on_400_dataset():
    df = pd.read_csv(_find_data_file("material_master_input.csv"))
    processed_df = preprocessor.process_dataframe(df)

    extracted_specs = [
        attribute_extractor.extract(row["cleaned_description"], row["cleaned_spec_text"])
        for _, row in processed_df.iterrows()
    ]

    assert len(extracted_specs) >= 400

    # Ensure all bearings have dimensions or part numbers
    bearings = [s for s in extracted_specs if "models" in s and "part_number" in s["models"]]
    assert len(bearings) > 30

    # Ensure ambiguous items in Bucket C are flagged
    ambiguous_count = sum(1 for s in extracted_specs if s.get("is_ambiguous"))
    assert ambiguous_count >= 5


def test_dirty_and_missing_spec_edge_cases():
    ext = attribute_extractor
    # Empty text
    empty_specs = ext.extract("", "")
    assert empty_specs.get("is_ambiguous") is True

    # Missing text vs complete specs score
    complete_specs = ext.extract("Gate Valve 150NB Class 150", "API 600")
    score, matches, conflicts = ext.calculate_attribute_match_score({}, complete_specs)
    assert score <= 0.5
    assert len(conflicts) == 0

    # Conflicting pressure class
    c1 = ext.extract("Gate Valve Class 150")
    c2 = ext.extract("Gate Valve Class 300")
    score, matches, conflicts = ext.calculate_attribute_match_score(c1, c2)
    assert score == 0.0
    assert any("Pressure Class Conflict" in c for c in conflicts)


if __name__ == "__main__":
    suite = unittest.TestSuite()
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            suite.addTest(unittest.FunctionTestCase(obj))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        exit(1)
