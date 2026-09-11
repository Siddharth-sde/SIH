"""
Stage 1: Text Normalization, Acronym Expansion, and UOM Harmonization.
National Unified Material Master Platform - ML Engine.
"""

import re
from typing import Dict, Any, Tuple, Optional, List
import pandas as pd


# ==============================================================================
# 1. UOM (Unit of Measure) Harmonizer & Conversion Matrix
# ==============================================================================

class UOMHarmonizer:
    """Harmonizes messy CPSE unit of measures and detects non-convertible conflicts."""

    # Canonical base representations per category
    CANONICAL_MAP = {
        # Discrete Count
        "EA": "NOS",
        "EACH": "NOS",
        "NO": "NOS",
        "NOS": "NOS",
        "NUM": "NOS",
        "NUMBER": "NOS",
        "PC": "NOS",
        "PCS": "NOS",
        "PIECE": "NOS",
        "PIECES": "NOS",
        "UNIT": "NOS",
        "UNITS": "NOS",
        # Length
        "M": "MTR",
        "MTR": "MTR",
        "MTRS": "MTR",
        "METER": "MTR",
        "METRE": "MTR",
        "METERS": "MTR",
        "METRES": "MTR",
        "KM": "KM",
        "KILOMETER": "KM",
        "KILOMETRE": "KM",
        "FT": "FT",
        "FEET": "FT",
        "FOOT": "FT",
        # Mass / Weight
        "KG": "KG",
        "KGS": "KG",
        "KILOGRAM": "KG",
        "KILOGRAMS": "KG",
        "GM": "GM",
        "GRAM": "GM",
        "GRAMS": "GM",
        "MT": "MT",
        "TON": "MT",
        "TONS": "MT",
        "TONNE": "MT",
        "TONNES": "MT",
        # Volume
        "L": "LTR",
        "LTR": "LTR",
        "LTRS": "LTR",
        "LITER": "LTR",
        "LITRE": "LTR",
        "KL": "KL",
        "ML": "ML",
        # Assembly / Packages
        "SET": "SET",
        "SETS": "SET",
        "KIT": "SET",
        "PAIR": "PAIR",
        "PAIRS": "PAIR",
        "ROLL": "ROLL",
        "ROLLS": "ROLL",
        "BOX": "BOX",
        # Area
        "SQM": "SQM",
        "SQMTR": "SQM",
        "M2": "SQM",
    }

    # High-level physics category
    CATEGORY_MAP = {
        "NOS": "COUNT",
        "MTR": "LENGTH",
        "KM": "LENGTH",
        "FT": "LENGTH",
        "KG": "MASS",
        "GM": "MASS",
        "MT": "MASS",
        "LTR": "VOLUME",
        "KL": "VOLUME",
        "ML": "VOLUME",
        "SET": "ASSEMBLY",
        "PAIR": "ASSEMBLY",
        "ROLL": "ASSEMBLY",
        "BOX": "ASSEMBLY",
        "SQM": "AREA",
    }

    # Conversion factor to standard base within same category
    # Base: Length -> MTR, Mass -> KG, Volume -> LTR
    CONVERSIONS = {
        ("KM", "MTR"): 1000.0,
        ("MTR", "KM"): 0.001,
        ("FT", "MTR"): 0.3048,
        ("MTR", "FT"): 3.28084,
        ("MT", "KG"): 1000.0,
        ("KG", "MT"): 0.001,
        ("GM", "KG"): 0.001,
        ("KG", "GM"): 1000.0,
        ("KL", "LTR"): 1000.0,
        ("LTR", "KL"): 0.001,
    }

    @classmethod
    def canonicalize(cls, uom_str: Optional[str]) -> Tuple[str, str]:
        """Returns (canonical_uom, category)."""
        if not uom_str or not isinstance(uom_str, str):
            return "NOS", "COUNT"

        cleaned = re.sub(r"[^A-Za-z0-9]", "", uom_str).strip().upper()
        canonical = cls.CANONICAL_MAP.get(cleaned, cleaned if cleaned else "NOS")
        category = cls.CATEGORY_MAP.get(canonical, "OTHER")
        return canonical, category

    @classmethod
    def check_compatibility(cls, uom_a: str, uom_b: str) -> Tuple[bool, bool, str]:
        """
        Evaluates compatibility between two UOMs.
        Returns:
            (is_compatible, is_identical, explanation)
        """
        can_a, cat_a = cls.canonicalize(uom_a)
        can_b, cat_b = cls.canonicalize(uom_b)

        if can_a == can_b:
            return True, True, f"Identical canonical UOM: {can_a}"

        if cat_a == cat_b:
            # Same category, convertible
            factor = cls.CONVERSIONS.get((can_a, can_b))
            if factor:
                return True, False, f"Convertible within {cat_a} (1 {can_a} = {factor} {can_b})"
            return True, False, f"Same physical category ({cat_a}), conversion required"

        # Non-convertible physical conflict (e.g. COUNT vs MASS)
        return False, False, f"UOM Conflict: {can_a} ({cat_a}) is incompatible with {can_b} ({cat_b})"


# ==============================================================================
# 2. Pipe & Fitting Dimension Standardizer (Imperial / Metric -> Nominal Bore)
# ==============================================================================

class PipeDimensionNormalizer:
    """Normalizes imperial and metric piping dimensions to standard Nominal Bore (NB)."""

    # Equivalence mapping to canonical NB
    DIMENSION_MAP = {
        # Inches / Fractions
        '1/2"': "15NB",
        '1/2IN': "15NB",
        '1/2INCH': "15NB",
        '0.5IN': "15NB",
        '15MM': "15NB",
        '3/4"': "20NB",
        '3/4IN': "20NB",
        '3/4INCH': "20NB",
        '0.75IN': "20NB",
        '20MM': "20NB",
        '1"': "25NB",
        '1IN': "25NB",
        '1INCH': "25NB",
        '25MM': "25NB",
        '1.25"': "32NB",
        '1-1/4"': "32NB",
        '1.25IN': "32NB",
        '32MM': "32NB",
        '1.5"': "40NB",
        '1-1/2"': "40NB",
        '1.5IN': "40NB",
        '1.5INCH': "40NB",
        '40MM': "40NB",
        '2"': "50NB",
        '2IN': "50NB",
        '2INCH': "50NB",
        '50MM': "50NB",
        '2.5"': "65NB",
        '2-1/2"': "65NB",
        '2.5IN': "65NB",
        '65MM': "65NB",
        '3"': "80NB",
        '3IN': "80NB",
        '3INCH': "80NB",
        '80MM': "80NB",
        '4"': "100NB",
        '4IN': "100NB",
        '4INCH': "100NB",
        '100MM': "100NB",
        '6"': "150NB",
        '6IN': "150NB",
        '6INCH': "150NB",
        '150MM': "150NB",
        '8"': "200NB",
        '8IN': "200NB",
        '8INCH': "200NB",
        '200MM': "200NB",
        '10"': "250NB",
        '10IN': "250NB",
        '10INCH': "250NB",
        '250MM': "250NB",
        '12"': "300NB",
        '12IN': "300NB",
        '12INCH': "300NB",
        '300MM': "300NB",
        '14"': "350NB",
        '14IN': "350NB",
        '350MM': "350NB",
        '16"': "400NB",
        '16IN': "400NB",
        '400MM': "400NB",
        '18"': "450NB",
        '18IN': "450NB",
        '450MM': "450NB",
        '20"': "500NB",
        '20IN': "500NB",
        '500MM': "500NB",
        '24"': "600NB",
        '24IN': "600NB",
        '600MM': "600NB",
    }

    # Regex patterns for dimensions
    REGEX_PIPE_DIM = re.compile(
        r'\b((?:1/2|3/4|1-1/2|1-1/4|2-1/2|\d+(?:\.\d+)?)\s*(?:\"|inch|in|mm|nb))\b',
        re.IGNORECASE
    )

    @classmethod
    def normalize_dimensions(cls, text: str) -> str:
        """Finds dimension references in text and appends/normalizes to canonical NB."""
        def replace_match(m):
            raw = m.group(1).upper().replace(" ", "").replace('"', '"')
            canonical = cls.DIMENSION_MAP.get(raw)
            if canonical:
                return f"{canonical} ({raw.lower()})"
            return m.group(1)

        return cls.REGEX_PIPE_DIM.sub(replace_match, text)


# ==============================================================================
# 3. Domain-Specific Acronym & Abbreviation Expander
# ==============================================================================

class AcronymExpander:
    """Expands industrial engineering abbreviations and CPSE SAP short codes."""

    # Ordered list of tuples (compiled regex, replacement)
    # Using word boundaries \b to prevent partial substring corruption
    EXPANSION_RULES: List[Tuple[re.Pattern, str]] = [
        # --- Bearings ---
        (re.compile(r"\bSPH\s+ROLLER\s+BRG\b", re.I), "spherical roller bearing"),
        (re.compile(r"\bROLL\s+NECK\s+BEARING\b", re.I), "spherical roller bearing"),
        (re.compile(r"\bROLL\s+NECK\s+BRG\b", re.I), "spherical roller bearing"),
        (re.compile(r"\bSRB\b", re.I), "spherical roller bearing"),
        (re.compile(r"\bDGBB\b", re.I), "deep groove ball bearing"),
        (re.compile(r"\bTRB\b", re.I), "tapered roller bearing"),
        (re.compile(r"\bCRB\b", re.I), "cylindrical roller bearing"),
        (re.compile(r"\bBRGS?\b", re.I), "bearing"),
        (re.compile(r"\bSPH\b", re.I), "spherical"),
        # --- Valves & Piping ---
        (re.compile(r"\bGATE\s+VLV\b", re.I), "gate valve"),
        (re.compile(r"\bGLOBE\s+VLV\b", re.I), "globe valve"),
        (re.compile(r"\bBALL\s+VLV\b", re.I), "ball valve"),
        (re.compile(r"\bCHK\s+VLV\b|\bCHECK\s+VLV\b", re.I), "check valve"),
        (re.compile(r"\bNRV\b", re.I), "non return valve"),
        (re.compile(r"\bPRV\b", re.I), "pressure relief valve"),
        (re.compile(r"\bVLV\b", re.I), "valve"),
        (re.compile(r"\bFLGD\b|\bFLG\b", re.I), "flanged"),
        (re.compile(r"\bWNRF\b", re.I), "weld neck raised face"),
        (re.compile(r"\bSORF\b", re.I), "slip on raised face"),
        (re.compile(r"\bBLRF\b", re.I), "blind raised face"),
        (re.compile(r"\bRF\b", re.I), "raised face"),
        (re.compile(r"\bFF\b", re.I), "flat face"),
        (re.compile(r"\bRTJ\b", re.I), "ring type joint"),
        (re.compile(r"\bSW\b", re.I), "socket weld"),
        (re.compile(r"\bBW\b", re.I), "butt weld"),
        (re.compile(r"\bTHRD\b|\bTHD\b", re.I), "threaded"),
        (re.compile(r"\bNPT\b", re.I), "national pipe thread"),
        (re.compile(r"\bBSP\b", re.I), "british standard pipe"),
        (re.compile(r"\bSPWD\b", re.I), "spiral wound"),
        (re.compile(r"\bGSK\b|\bGSKT\b", re.I), "gasket"),
        # --- Materials & Metallurgy ---
        (re.compile(r"\bCS\b", re.I), "carbon steel"),
        (re.compile(r"\bMS\b", re.I), "mild steel"),
        (re.compile(r"\bSS316L?\b", re.I), "stainless steel 316"),
        (re.compile(r"\bSS304L?\b", re.I), "stainless steel 304"),
        (re.compile(r"\bSS\b", re.I), "stainless steel"),
        (re.compile(r"\bCI\b", re.I), "cast iron"),
        (re.compile(r"\bDI\b", re.I), "ductile iron"),
        (re.compile(r"\bGI\b", re.I), "galvanised iron"),
        (re.compile(r"\bALU\b|\bALUMINUM\b", re.I), "aluminium"),
        (re.compile(r"\bAL\b(?=\s*(?:COND|CABLE|ARM|CONDUCTOR|\b))", re.I), "aluminium"),
        (re.compile(r"\bCU\b(?=\s*(?:COND|CABLE|ARM|CONDUCTOR|\b))", re.I), "copper"),
        (re.compile(r"\bGRAPH\b", re.I), "graphite"),
        (re.compile(r"\bPOLY\b", re.I), "polyurethane"),
        (re.compile(r"\bPTFE\b", re.I), "teflon ptfe"),
        (re.compile(r"\bNBR\b", re.I), "nitrile rubber"),
        # --- Electrical & Power ---
        (re.compile(r"\bXLPE\b", re.I), "cross-linked polyethylene"),
        (re.compile(r"\bPVC\b", re.I), "polyvinyl chloride"),
        (re.compile(r"\bARM\b(?=\s*(?:CABLE|ALU|AL|CU|\b))", re.I), "armoured"),
        (re.compile(r"\bUNARM\b", re.I), "unarmoured"),
        (re.compile(r"\bTRF\b|\bXFRMR\b", re.I), "transformer"),
        (re.compile(r"\bMCCB\b", re.I), "moulded case circuit breaker"),
        (re.compile(r"\bMCB\b", re.I), "miniature circuit breaker"),
        (re.compile(r"\bVCB\b", re.I), "vacuum circuit breaker"),
        (re.compile(r"\bACB\b", re.I), "air circuit breaker"),
        (re.compile(r"\bTEFC\b", re.I), "totally enclosed fan cooled"),
        (re.compile(r"\b3PH\b|\b3-PH\b|\b3\s*PHASE\b", re.I), "3 phase"),
        (re.compile(r"\b1PH\b|\b1-PH\b|\b1\s*PHASE\b", re.I), "single phase"),
        (re.compile(r"\bSQMM\b|\bSQ\s*MM\b|\bSQ\.MM\b", re.I), "sqmm"),
        (re.compile(r"\bKV\b", re.I), "kv"),
        (re.compile(r"\bMVA\b", re.I), "mva"),
        (re.compile(r"\bKVA\b", re.I), "kva"),
        (re.compile(r"\bHP\b", re.I), "hp"),
        (re.compile(r"\bKW\b", re.I), "kw"),
        # --- Mechanical, Fasteners & Heavy Engineering ---
        (re.compile(r"\bHEX\b", re.I), "hexagonal"),
        (re.compile(r"\bHT\b(?=\s*(?:BOLT|FASTENER|NUT|\b))", re.I), "high tensile"),
        (re.compile(r"\bZN\b|\bZINC\b", re.I), "zinc plated"),
        (re.compile(r"\bGALV\b", re.I), "galvanized"),
        (re.compile(r"\bGR\b|\bGR\.\b", re.I), "grade"),
        (re.compile(r"\bCL\.?(?=\s*\d+)", re.I), "class "),
        (re.compile(r"(\d+)\s*#", re.I), r"class \1"),
        (re.compile(r"\bTHK\b", re.I), "thickness"),
        (re.compile(r"\bDIA\b", re.I), "diameter"),
        (re.compile(r"\bLG\b|\bLEN\b", re.I), "length"),
        (re.compile(r"\bOD\b", re.I), "outer diameter"),
        (re.compile(r"\bID\b", re.I), "inner diameter"),
        (re.compile(r"\bHVY\b", re.I), "heavy"),
        (re.compile(r"\bDUTY\b", re.I), "duty"),
        (re.compile(r"\bIWRC\b", re.I), "independent wire rope core"),
        (re.compile(r"\bTCI\b", re.I), "tungsten carbide insert"),
        (re.compile(r"\bIADC\b", re.I), "iadc code"),
        (re.compile(r"\bEP\b(?=\s*(?:GRADE|BELT|BELTING|\b))", re.I), "polyester nylon ep"),
    ]

    @classmethod
    def expand(cls, text: str) -> str:
        """Applies all regex replacement expansions on input string."""
        if not text:
            return ""
        result = text
        for pattern, replacement in cls.EXPANSION_RULES:
            result = pattern.sub(replacement, result)
        return result


# ==============================================================================
# 4. Master Text Normalizer & Pipeline Stage 1
# ==============================================================================

class Stage1Preprocessor:
    """Master preprocessor for Stage 1 of the Material Master pipeline."""

    def __init__(self):
        self.uom_harmonizer = UOMHarmonizer()
        self.dim_normalizer = PipeDimensionNormalizer()
        self.expander = AcronymExpander()

    def clean_raw_text(self, text: str) -> str:
        """Cleans formatting noise while protecting standards and specs."""
        if not text or not isinstance(text, str):
            return ""

        # Normalize unicode quotes and dashes
        t = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
        t = t.replace("–", "-").replace("—", "-")

        # Normalize delimiters into clean spaces
        t = re.sub(r"[|/\\,;]", " ", t)

        # Standardize dimensional quote marks: e.g. 6" -> 6 inch
        t = re.sub(r'(\d+)\s*"', r"\1 inch", t)

        # Remove multiple consecutive spaces
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def normalize_text(self, text: str) -> str:
        """Full pipeline: clean -> normalize dimensions -> expand acronyms -> lowercase."""
        if not text:
            return ""

        # 1. Basic formatting clean
        cleaned = self.clean_raw_text(text)

        # 2. Piping dimension standardizer (6 inch / 150mm -> 150NB)
        dim_normalized = self.dim_normalizer.normalize_dimensions(cleaned)

        # 3. Acronym expansion
        expanded = self.expander.expand(dim_normalized)

        # 4. Case folding & final whitespace trim
        final_text = re.sub(r"\s+", " ", expanded).strip().lower()
        return final_text

    @staticmethod
    def _safe_float(val: Any, default: float = 0.0) -> float:
        try:
            if val is None or pd.isna(val):
                return default
            return float(val)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_int(val: Any, default: int = 0) -> int:
        try:
            if val is None or pd.isna(val):
                return default
            return int(float(val))
        except (ValueError, TypeError):
            return default

    def process_record(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Processes a single dictionary / pandas row."""
        raw_desc = str(row.get("material_description", "") or "")
        raw_spec = str(row.get("technical_spec_text", "") or "")
        raw_uom = str(row.get("uom", "") or "")

        # Harmonize UOM
        canonical_uom, uom_category = self.uom_harmonizer.canonicalize(raw_uom)

        # Clean individual fields
        clean_desc = self.normalize_text(raw_desc)
        clean_spec = self.normalize_text(raw_spec)

        # Combined text for embedding generation
        combined_text = f"{clean_desc} {clean_spec}".strip()

        return {
            "source_material_code": row.get("source_material_code", ""),
            "cpse_id": row.get("cpse_id", ""),
            "sector": row.get("sector", ""),
            "raw_description": raw_desc,
            "raw_spec_text": raw_spec,
            "cleaned_description": clean_desc,
            "cleaned_spec_text": clean_spec,
            "combined_text": combined_text,
            "source_uom": raw_uom,
            "canonical_uom": canonical_uom,
            "uom_category": uom_category,
            "unit_price_inr": self._safe_float(row.get("unit_price_inr"), 0.0),
            "current_stock_qty": self._safe_int(row.get("current_stock_qty"), 0),
            "annual_procurement_qty": self._safe_int(row.get("annual_procurement_qty"), 0),
            "bucket": row.get("bucket", "A"),
            "human_review_flag": bool(row.get("human_review_flag", False)),
        }

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies Stage 1 preprocessing over an entire DataFrame."""
        records = [self.process_record(row) for _, row in df.iterrows()]
        return pd.DataFrame(records)


# Global singleton instance for easy import
preprocessor = Stage1Preprocessor()
