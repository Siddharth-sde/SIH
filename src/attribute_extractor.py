"""
Stage 2: Deterministic Regex & Rule-Based Technical Attribute Extractor.
National Unified Material Master Platform - ML Engine.
"""

import re
from typing import Dict, Any, Optional, List, Tuple


class AttributeExtractor:
    """
    Extracts structured technical specifications (dimensions, standards, materials,
    pressure ratings, electrical ratings, part numbers) from engineering text.
    """

    # --- Standards Regexes ---
    RE_STANDARDS = [
        re.compile(r"\b(API\s*\d+[A-Z]?)\b", re.I),
        re.compile(r"\b(ASTM\s*[A-Z]\d+(?:\s+[A-Z0-9]+)?)\b", re.I),
        re.compile(r"\b(ASME\s*B\d+(?:\.\d+)?)\b", re.I),
        re.compile(r"\b(IS(?:/IEC)?\s*\d+(?:\s+Part\s*\d+)?)\b", re.I),
        re.compile(r"\b(ISO\s*\d+(?:-\d+)?)\b", re.I),
        re.compile(r"\b(DIN\s*\d+)\b", re.I),
        re.compile(r"\b(IADC\s*\d+)\b", re.I),
        re.compile(r"\b(IEC\s*\d+(?:-\d+)?)\b", re.I),
    ]

    # --- Pressure / Class Ratings ---
    RE_PRESSURE_CLASS = [
        re.compile(r"\b(?:class|cl\.?)\s*(\d{2,4})\b", re.I),
        re.compile(r"\b(\d{2,4})\s*#\b", re.I),
        re.compile(r"\b(\d{2,4})\s*psi\b", re.I),
        re.compile(r"\b(\d+(?:\.\d+)?)\s*bar\b", re.I),
        re.compile(r"\b(\d+(?:\.\d+)?)\s*mpa\b", re.I),
        re.compile(r"\b(\d+)\s*kA\b", re.I),
    ]

    # --- Dimensions ---
    RE_NOMINAL_BORE = re.compile(r"\b(\d+)\s*NB\b", re.I)
    RE_BOUNDARY_3D = re.compile(r"\b(\d+)\s*x\s*(\d+)\s*x\s*(\d+)\s*(?:mm)?\b", re.I)
    RE_BOUNDARY_2D = re.compile(r"\b(\d+)\s*x\s*(\d+)\s*(?:mm)?\b", re.I)
    RE_BORE_DIA = re.compile(r"\bbore\s*(?:diameter)?\s*(\d+)\s*(?:mm)?\b", re.I)
    RE_BOLT_METRIC = re.compile(r"\b(M\d+)\s*x\s*(\d+)\b", re.I)
    RE_SINGLE_DIA = re.compile(r"\b(\d+(?:\.\d+)?)\s*mm\s*(?:dia(?:meter)?|width|thickness|thk)?\b", re.I)

    # --- Electrical / Ratings ---
    RE_VOLTAGE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(kV|V)\b", re.I)
    RE_POWER_HP = re.compile(r"\b(\d+(?:\.\d+)?)\s*HP\b", re.I)
    RE_POWER_KW = re.compile(r"\b(\d+(?:\.\d+)?)\s*kW\b", re.I)
    RE_POWER_MVA = re.compile(r"\b(\d+(?:\.\d+)?)\s*(MVA|kVA)\b", re.I)
    RE_CURRENT_A = re.compile(r"\b(\d+)\s*A\b", re.I)
    RE_CABLE_CORE_SIZE = re.compile(r"\b(\d+)\s*C\s*x\s*(\d+(?:\.\d+)?)\s*(?:sqmm|sq\s*mm)\b", re.I)

    # --- Part / Model Numbers ---
    RE_BEARING_MODEL = re.compile(
        r"\b((?:22\d{3}|23\d{3}|6\d{3}|6\d{3}-[A-Z0-9]+|6\d{3}\s+ZZ|\d{4,5}))\b",
        re.I
    )
    RE_COUPLING_MODEL = re.compile(r"\b(L-\d+|G\d+)\b", re.I)
    RE_CHAIN_MODEL = re.compile(r"\b(\d{1,2}[A-B]-\d)\b", re.I)
    RE_BELT_MODEL = re.compile(r"\b(SP[A-Z]\s*\d{3,4})\b", re.I)
    RE_MISC_PART_NO = re.compile(r"\b(?:pt|part|drawing|drg)\s*(?:no\.?)?\s*([A-Z0-9\-]+)\b", re.I)

    # --- Materials & Grades ---
    MATERIALS_LIST = [
        ("Stainless Steel 316", [r"\b(?:stainless\s+steel\s+316|ss\s*316l?)\b"]),
        ("Stainless Steel 304", [r"\b(?:stainless\s+steel\s+304|ss\s*304l?)\b"]),
        ("Stainless Steel", [r"\b(?:stainless\s+steel|ss)\b"]),
        ("Carbon Steel", [r"\b(?:carbon\s+steel|cast\s+steel|cs|a216\s*wcb|wcb)\b"]),
        ("Mild Steel", [r"\b(?:mild\s+steel|ms)\b"]),
        ("Cast Iron", [r"\b(?:cast\s+iron|ci)\b"]),
        ("Ductile Iron", [r"\b(?:ductile\s+iron|di)\b"]),
        ("Manganese Steel", [r"\b(?:manganese\s+steel|high-mn|hadfield)\b"]),
        ("Aluminium", [r"\b(?:aluminium|aluminum|alu)\b"]),
        ("Copper", [r"\b(?:copper|cu)\b"]),
        ("Porcelain", [r"\bporcelain\b"]),
        ("Graphite", [r"\bgraphite\b"]),
        ("Polyurethane", [r"\bpolyurethane\b"]),
        ("Teflon PTFE", [r"\b(?:teflon|ptfe)\b"]),
        ("Rubber", [r"\brubber\b"]),
    ]

    GRADES_LIST = [
        ("Grade 8.8", r"\b(?:grade|class|property\s+class)\s*8\.8\b"),
        ("Grade 10.9", r"\b(?:grade|class|property\s+class)\s*10\.9\b"),
        ("Grade 12.9", r"\b(?:grade|class|property\s+class)\s*12\.9\b"),
        ("Grade B", r"\b(?:grade|gr\.?)\s*B\b"),
        ("Grade A", r"\b(?:grade|gr\.?)\s*A\b"),
        ("Class 150", r"\bclass\s*150\b"),
        ("Class 300", r"\bclass\s*300\b"),
        ("Class 600", r"\bclass\s*600\b"),
        ("Class 900", r"\bclass\s*900\b"),
        ("Class 1500", r"\bclass\s*1500\b"),
    ]

    def extract_standards(self, text: str) -> List[str]:
        """Finds all standard codes mentioned in the text."""
        standards = []
        for pat in self.RE_STANDARDS:
            matches = pat.findall(text)
            for m in matches:
                clean_std = re.sub(r"\s+", " ", m.strip()).upper()
                if clean_std not in standards:
                    standards.append(clean_std)
        return standards

    def extract_pressure_class(self, text: str) -> Optional[int]:
        """Extracts numeric pressure class rating (e.g. 150, 300, 600, 1500)."""
        # Look specifically for class / # rating first
        m = re.search(r"\bclass\s*(\d{2,4})\b", text, re.I)
        if m:
            return int(m.group(1))

        m = re.search(r"\b(\d{2,4})\s*#\b", text, re.I)
        if m:
            return int(m.group(1))

        m = re.search(r"\b(\d{2,4})\s*psi\b", text, re.I)
        if m:
            return int(m.group(1))

        return None

    def extract_dimensions(self, text: str) -> Dict[str, Any]:
        """Extracts all dimension references."""
        dims: Dict[str, Any] = {}

        # Piping Nominal Bore (e.g. 150NB)
        m_nb = self.RE_NOMINAL_BORE.search(text)
        if m_nb:
            dims["nominal_bore"] = f"{m_nb.group(1)}NB"

        # 3D boundary dimensions (e.g. 100x180x46 mm or 230x115x65)
        m_3d = self.RE_BOUNDARY_3D.search(text)
        if m_3d:
            dims["boundary_3d"] = f"{m_3d.group(1)}x{m_3d.group(2)}x{m_3d.group(3)} mm"
            dims["length_mm"] = int(m_3d.group(1))
            dims["width_mm"] = int(m_3d.group(2))
            dims["thickness_mm"] = int(m_3d.group(3))

        # 2D boundary dimensions (e.g. 2000x6000mm or 100x100mm)
        elif not m_3d:
            m_2d = self.RE_BOUNDARY_2D.search(text)
            if m_2d:
                dims["boundary_2d"] = f"{m_2d.group(1)}x{m_2d.group(2)} mm"

        # Bore diameter (bearings)
        m_bore = self.RE_BORE_DIA.search(text)
        if m_bore:
            dims["bore_diameter_mm"] = int(m_bore.group(1))

        # Metric Bolt (e.g. M16 x 80)
        m_bolt = self.RE_BOLT_METRIC.search(text)
        if m_bolt:
            dims["bolt_thread"] = m_bolt.group(1).upper()
            dims["bolt_length_mm"] = int(m_bolt.group(2))

        # Diameter in mm (e.g. 24mm wire rope, 32mm)
        m_dia = re.search(r"\b(\d+(?:\.\d+)?)\s*mm\b(?!\s*x)", text, re.I)
        if m_dia and "nominal_bore" not in dims and "boundary_3d" not in dims:
            dims["diameter_mm"] = float(m_dia.group(1))

        return dims

    def extract_material_and_grade(self, text: str) -> Dict[str, Any]:
        """Extracts material family and metallurgical grade."""
        res: Dict[str, Any] = {}

        # Material detection
        for mat_name, patterns in self.MATERIALS_LIST:
            for pat in patterns:
                if re.search(pat, text, re.I):
                    res["material"] = mat_name
                    break
            if "material" in res:
                break

        # Grade detection
        for grade_name, pat in self.GRADES_LIST:
            if re.search(pat, text, re.I):
                res["grade"] = grade_name
                break

        return res

    def extract_electrical(self, text: str) -> Dict[str, Any]:
        """Extracts voltage, power, cable cores, and conductor specs."""
        elec: Dict[str, Any] = {}

        # Voltage
        m_volt = self.RE_VOLTAGE.search(text)
        if m_volt:
            val = m_volt.group(1)
            unit = m_volt.group(2).upper()
            elec["voltage"] = f"{val}{unit}"

        # Power
        m_hp = self.RE_POWER_HP.search(text)
        if m_hp:
            elec["power_hp"] = float(m_hp.group(1))

        m_kw = self.RE_POWER_KW.search(text)
        if m_kw:
            elec["power_kw"] = float(m_kw.group(1))

        m_mva = self.RE_POWER_MVA.search(text)
        if m_mva:
            elec["power_rating"] = f"{m_mva.group(1)} {m_mva.group(2).upper()}"

        # Current
        m_amp = self.RE_CURRENT_A.search(text)
        if m_amp and not m_mva:
            elec["current_rating_a"] = int(m_amp.group(1))

        # Cable Core x Size (e.g. 3C x 400 sqmm)
        m_cable = self.RE_CABLE_CORE_SIZE.search(text)
        if m_cable:
            elec["cable_cores"] = int(m_cable.group(1))
            elec["cable_sqmm"] = float(m_cable.group(2))

        # Conductor Material
        if re.search(r"\b(?:aluminium|aluminum|alu|al)\b", text, re.I):
            elec["conductor"] = "Aluminium"
        elif re.search(r"\b(?:copper|cu)\b", text, re.I):
            elec["conductor"] = "Copper"

        # Insulation & Enclosure
        if re.search(r"\b(?:xlpe|cross-linked\s+polyethylene)\b", text, re.I):
            elec["insulation"] = "XLPE"
        elif re.search(r"\b(?:pvc|polyvinyl\s+chloride)\b", text, re.I):
            elec["insulation"] = "PVC"

        if re.search(r"\barmoured\b", text, re.I):
            elec["armoured"] = True
        elif re.search(r"\bunarmoured\b", text, re.I):
            elec["armoured"] = False

        if re.search(r"\btefc\b", text, re.I):
            elec["enclosure"] = "TEFC"

        return elec

    def extract_part_or_model(self, text: str) -> Dict[str, Any]:
        """Extracts standard component series, bearing numbers, and model identifiers."""
        models: Dict[str, Any] = {}

        # Bearing model (e.g. 22220, 6205-2RSH, 6312, 22316)
        m_brg = re.search(r"\b(222\d{2}|223\d{2}|62\d{2}(?:-[A-Z0-9]+)?|63\d{2})\b", text, re.I)
        if m_brg:
            models["part_number"] = m_brg.group(1).upper()

        # Coupling
        m_cpl = self.RE_COUPLING_MODEL.search(text)
        if m_cpl:
            models["coupling_model"] = m_cpl.group(1).upper()

        # Roller Chain
        m_chn = self.RE_CHAIN_MODEL.search(text)
        if m_chn:
            models["chain_model"] = m_chn.group(1).upper()

        # V-Belt
        m_blt = self.RE_BELT_MODEL.search(text)
        if m_blt:
            models["belt_model"] = m_blt.group(1).upper()

        # Bearing clearance (e.g. C3 clearance)
        if re.search(r"\bC3\s*(?:internal)?\s*clearance\b|\bC3\b", text, re.I):
            models["clearance"] = "C3"

        # Bearing seal type
        if re.search(r"\brubber\s*sealed?\b|\b2rsh?\b|\b2rs\b", text, re.I):
            models["seal_type"] = "Rubber Sealed (2RS)"
        elif re.search(r"\bmetal\s*shield(?:ed)?\b|\bzz\b", text, re.I):
            models["seal_type"] = "Metal Shielded (ZZ)"

        # Misc Part No
        m_misc = self.RE_MISC_PART_NO.search(text)
        if m_misc and "part_number" not in models:
            models["part_number"] = m_misc.group(1).upper()

        return models

    def is_ambiguous_entry(self, text: str, extracted_attrs: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Detects unclassifiable / low-information records (e.g. Bucket C traps like 'Pt No 4471B misc spare').
        Returns (is_ambiguous, reason).
        """
        t_low = text.lower()
        if "insufficient technical information" in t_low or "unidentified spare" in t_low:
            return True, "Low Information: Lacks technical specifications or recognizable equipment type"

        if "no rating" in t_low and "frame" in t_low:
            return True, "Missing Critical Attributes: Motor spare without rating, frame or part number"

        # If completely empty specs
        if not extracted_attrs.get("dimensions") and not extracted_attrs.get("standards") and \
           not extracted_attrs.get("pressure_class") and not extracted_attrs.get("electrical") and \
           not extracted_attrs.get("models"):
            # Check if very short generic string
            words = text.split()
            if len(words) <= 4:
                return True, "Insufficient detail to classify or match"

        return False, ""

    def extract(self, cleaned_description: str, cleaned_spec_text: str = "") -> Dict[str, Any]:
        """
        Master extraction method producing the structured specifications dictionary.
        """
        combined = f"{cleaned_description} {cleaned_spec_text}".strip()

        specs: Dict[str, Any] = {}

        # 1. Standards
        standards = self.extract_standards(combined)
        if standards:
            specs["standards"] = standards

        # 2. Pressure Class
        p_class = self.extract_pressure_class(combined)
        if p_class is not None:
            specs["pressure_class"] = p_class

        # 3. Dimensions
        dims = self.extract_dimensions(combined)
        if dims:
            specs["dimensions"] = dims

        # 4. Material & Grade
        mat_grade = self.extract_material_and_grade(combined)
        specs.update(mat_grade)

        # 5. Electrical / Drive Ratings
        elec = self.extract_electrical(combined)
        if elec:
            specs["electrical"] = elec

        # 6. Part / Model Numbers
        models = self.extract_part_or_model(combined)
        if models:
            specs["models"] = models

        # 7. End Connection / Flange Face
        if re.search(r"\braised\s+face\b|\brf\b", combined, re.I):
            specs["flange_face"] = "Raised Face (RF)"
        elif re.search(r"\bflat\s+face\b|\bff\b", combined, re.I):
            specs["flange_face"] = "Flat Face (FF)"
        elif re.search(r"\bring\s+type\s+joint\b|\brtj\b", combined, re.I):
            specs["flange_face"] = "Ring Type Joint (RTJ)"

        if re.search(r"\bflanged\b", combined, re.I):
            specs["end_connection"] = "Flanged"
        elif re.search(r"\bsocket\s+weld\b", combined, re.I):
            specs["end_connection"] = "Socket Weld"
        elif re.search(r"\bbutt\s+weld\b", combined, re.I):
            specs["end_connection"] = "Butt Weld"
        elif re.search(r"\bthreaded\b", combined, re.I):
            specs["end_connection"] = "Threaded"

        # 8. Ambiguity & Triage Flag
        is_ambig, reason = self.is_ambiguous_entry(combined, specs)
        specs["is_ambiguous"] = is_ambig
        if is_ambig:
            specs["ambiguity_reason"] = reason

        return specs

    def calculate_attribute_match_score(
        self,
        attrs_a: Dict[str, Any],
        attrs_b: Dict[str, Any]
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculates compatibility score (0.0 to 1.0) and detects hard conflicts.
        Returns:
            (match_score, match_reasons, conflict_reasons)
        """
        matches = []
        conflicts = []

        # 1. Hard Conflict Check: Pressure Class
        pca = attrs_a.get("pressure_class")
        pcb = attrs_b.get("pressure_class")
        if pca is not None and pcb is not None:
            if pca == pcb:
                matches.append(f"Pressure class match: Class {pca}")
            else:
                conflicts.append(f"Pressure Class Conflict: Class {pca} vs Class {pcb}")
                return 0.0, matches, conflicts

        # 2. Hard Conflict Check: Conductor Material (Aluminium vs Copper)
        ca = attrs_a.get("electrical", {}).get("conductor")
        cb = attrs_b.get("electrical", {}).get("conductor")
        if ca and cb:
            if ca == cb:
                matches.append(f"Conductor match: {ca}")
            else:
                conflicts.append(f"Conductor Conflict: {ca} vs {cb}")
                return 0.0, matches, conflicts

        # 3. Hard Conflict Check: Bearing Clearance (e.g. C3 vs None)
        cl_a = attrs_a.get("models", {}).get("clearance")
        cl_b = attrs_b.get("models", {}).get("clearance")
        if cl_a != cl_b:
            if cl_a or cl_b:
                conflicts.append(f"Clearance difference: {cl_a or 'Normal'} vs {cl_b or 'Normal'}")

        # 4. Dimension Matching
        dims_a = attrs_a.get("dimensions", {})
        dims_b = attrs_b.get("dimensions", {})

        # Nominal Bore
        nb_a = dims_a.get("nominal_bore")
        nb_b = dims_b.get("nominal_bore")
        if nb_a and nb_b:
            if nb_a == nb_b:
                matches.append(f"Nominal bore match: {nb_a}")
            else:
                conflicts.append(f"Nominal bore mismatch: {nb_a} vs {nb_b}")
                return 0.0, matches, conflicts

        # Boundary dimensions (e.g. 25x52x15 mm)
        b3_a = dims_a.get("boundary_3d")
        b3_b = dims_b.get("boundary_3d")
        if b3_a and b3_b:
            if b3_a == b3_b:
                matches.append(f"Boundary dimensions match: {b3_a}")
            else:
                conflicts.append(f"Dimension mismatch: {b3_a} vs {b3_b}")
                return 0.0, matches, conflicts

        # Bolt specs
        bt_a = dims_a.get("bolt_thread")
        bt_b = dims_b.get("bolt_thread")
        bl_a = dims_a.get("bolt_length_mm")
        bl_b = dims_b.get("bolt_length_mm")
        if bt_a and bt_b:
            if bt_a == bt_b and bl_a == bl_b:
                matches.append(f"Bolt thread & length match: {bt_a}x{bl_a}")
            else:
                conflicts.append(f"Bolt dimension mismatch: {bt_a}x{bl_a} vs {bt_b}x{bl_b}")
                return 0.0, matches, conflicts

        # 5. Part Number Match
        pn_a = attrs_a.get("models", {}).get("part_number")
        pn_b = attrs_b.get("models", {}).get("part_number")
        if pn_a and pn_b:
            if pn_a == pn_b:
                matches.append(f"Part/Model number match: {pn_a}")
            else:
                conflicts.append(f"Part/Model number mismatch: {pn_a} vs {pn_b}")

        # 6. Standards Match
        st_a = set(attrs_a.get("standards", []))
        st_b = set(attrs_b.get("standards", []))
        common_std = st_a.intersection(st_b)
        if common_std:
            matches.append(f"Standards match: {', '.join(common_std)}")

        # 7. Material Match
        mat_a = attrs_a.get("material")
        mat_b = attrs_b.get("material")
        if mat_a and mat_b:
            if mat_a == mat_b:
                matches.append(f"Material match: {mat_a}")
            elif ("Carbon Steel" in (mat_a, mat_b) and "Mild Steel" in (mat_a, mat_b)):
                # Mild steel and carbon steel are close but slightly different
                matches.append(f"Compatible ferrous steel: {mat_a} / {mat_b}")
            else:
                conflicts.append(f"Material mismatch: {mat_a} vs {mat_b}")

        # Score calculation
        total_signals = len(matches) + len(conflicts)
        if total_signals == 0:
            return 0.5, ["Generic match with no conflicting technical attributes"], []

        score = max(0.0, len(matches) / (len(matches) + len(conflicts) * 2.0))
        return round(score, 3), matches, conflicts


# Global singleton instance
attribute_extractor = AttributeExtractor()
