"""
Unit tests for Stage 1 Preprocessing and UOM Harmonization.
"""

import pytest
import pandas as pd
from src.preprocessor import (
    UOMHarmonizer,
    PipeDimensionNormalizer,
    AcronymExpander,
    Stage1Preprocessor,
)


def test_uom_canonicalization():
    harmonizer = UOMHarmonizer()
    assert harmonizer.canonicalize("EA")[0] == "NOS"
    assert harmonizer.canonicalize("EACH")[0] == "NOS"
    assert harmonizer.canonicalize("nos")[0] == "NOS"
    assert harmonizer.canonicalize("MTR")[0] == "MTR"
    assert harmonizer.canonicalize("METRE")[0] == "MTR"
    assert harmonizer.canonicalize("KM")[0] == "KM"
    assert harmonizer.canonicalize("MT")[0] == "MT"
    assert harmonizer.canonicalize("TONNES")[0] == "MT"
    assert harmonizer.canonicalize("KG")[0] == "KG"
    assert harmonizer.canonicalize("SET")[0] == "SET"


def test_uom_compatibility_and_conflict():
    harmonizer = UOMHarmonizer()

    # Identical
    compat, ident, _ = harmonizer.check_compatibility("EA", "NOS")
    assert compat and ident

    # Convertible length
    compat, ident, _ = harmonizer.check_compatibility("MTR", "KM")
    assert compat and not ident

    # Convertible mass
    compat, ident, _ = harmonizer.check_compatibility("MT", "KG")
    assert compat and not ident

    # Severe non-convertible conflict (Discrete Count vs Mass)
    compat, ident, msg = harmonizer.check_compatibility("NOS", "KG")
    assert not compat and not ident
    assert "UOM Conflict" in msg


def test_acronym_expansion():
    expander = AcronymExpander()

    # Valve expansions
    expanded = expander.expand("GATE VLV 150NB CL150 CS BODY RF")
    assert "gate valve" in expanded.lower()
    assert "carbon steel" in expanded.lower()
    assert "class" in expanded.lower()
    assert "raised face" in expanded.lower()

    # Bearing expansions across CPSE naming styles
    s1 = expander.expand("SPH ROLLER BRG Bearing 22220")
    s2 = expander.expand("ROLL NECK BEARING Bearing 22220")
    s3 = expander.expand("SRB Bearing 22220")

    assert "spherical roller bearing" in s1.lower()
    assert "spherical roller bearing" in s2.lower()
    assert "spherical roller bearing" in s3.lower()

    # Electrical expansions
    elec = expander.expand("CABLE XLPE 11KV 3Cx400 ALU ARM")
    assert "cross-linked polyethylene" in elec.lower()
    assert "aluminium" in elec.lower()
    assert "armoured" in elec.lower()


def test_dimension_normalization():
    norm = PipeDimensionNormalizer()
    t1 = norm.normalize_dimensions("Valve Gate 6 inch CS Flanged")
    assert "150NB" in t1

    t2 = norm.normalize_dimensions("Flange 150mm CL150")
    assert "150NB" in t2


def test_full_preprocessor_on_samples():
    prep = Stage1Preprocessor()

    sample_row = {
        "source_material_code": "OG-10023",
        "cpse_id": "CPCL_OG",
        "sector": "Oil & Gas",
        "material_description": "GATE VLV 150NB CL150 CS BODY",
        "technical_spec_text": "Cast steel gate valve, 150NB, Class 150, flanged ends, API 600 design",
        "uom": "EA",
        "unit_price_inr": 27000.0,
        "current_stock_qty": 50,
        "annual_procurement_qty": 100,
        "bucket": "A",
        "human_review_flag": False,
    }

    result = prep.process_record(sample_row)

    assert result["canonical_uom"] == "NOS"
    assert result["uom_category"] == "COUNT"
    assert "gate valve" in result["cleaned_description"]
    assert "carbon steel" in result["cleaned_description"]
    assert "api 600" in result["cleaned_spec_text"]


def test_preprocessor_on_entire_400_dataset():
    df = pd.read_csv("material_master_input.csv")
    prep = Stage1Preprocessor()
    processed_df = prep.process_dataframe(df)

    assert len(processed_df) == 400
    assert not processed_df["cleaned_description"].isna().any()
    assert not processed_df["canonical_uom"].isna().any()
    assert "gate valve" in processed_df.loc[processed_df["source_material_code"] == "CP-10040", "cleaned_description"].values[0]
