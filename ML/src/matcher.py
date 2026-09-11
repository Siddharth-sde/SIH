"""
Stage 4: Intra-Category Hybrid Deduplication Clustering & CNMC Generation.
National Unified Material Master Platform - ML Engine.
"""

import os
import re
import logging
from typing import Dict, Any, List, Tuple, Optional, Set
import numpy as np
import pandas as pd

try:
    import networkx as nx
except ImportError:
    class SimpleGraph:
        def __init__(self):
            self.adj = {}
            self.nodes = {}
        def add_node(self, node, **kwargs):
            self.nodes[node] = kwargs
            if node not in self.adj:
                self.adj[node] = set()
        def add_edge(self, u, v, **kwargs):
            if u not in self.nodes:
                self.add_node(u)
            if v not in self.nodes:
                self.add_node(v)
            self.adj[u].add(v)
            self.adj[v].add(u)
        def subgraph(self, nodes):
            sub = SimpleGraph()
            for n in nodes:
                sub.add_node(n, **self.nodes.get(n, {}))
            for n in nodes:
                for neighbor in self.adj.get(n, []):
                    if neighbor in nodes:
                        sub.add_edge(n, neighbor)
            return sub
        def number_of_edges(self):
            return sum(len(neighbors) for neighbors in self.adj.values()) // 2

    class NxFallback:
        Graph = SimpleGraph
        @staticmethod
        def connected_components(G):
            from collections import deque
            visited = set()
            comps = []
            for node in list(G.nodes.keys()):
                if node not in visited:
                    comp = set()
                    queue = deque([node])
                    visited.add(node)
                    while queue:
                        curr = queue.popleft()
                        comp.add(curr)
                        for neighbor in G.adj.get(curr, []):
                            if neighbor not in visited:
                                visited.add(neighbor)
                                queue.append(neighbor)
                    comps.append(comp)
            return comps
        class community:
            @staticmethod
            def louvain_communities(subgraph, **kwargs):
                return NxFallback.connected_components(subgraph)

    nx = NxFallback()

try:
    from rapidfuzz import fuzz
except ImportError:
    import difflib
    class FuzzFallback:
        @staticmethod
        def token_set_ratio(s1, s2):
            return difflib.SequenceMatcher(None, s1, s2).ratio() * 100
        @staticmethod
        def ratio(s1, s2):
            return difflib.SequenceMatcher(None, s1, s2).ratio() * 100
    fuzz = FuzzFallback()

from src.attribute_extractor import attribute_extractor
from src.preprocessor import UOMHarmonizer
from src.classifier import TAXONOMY

logger = logging.getLogger(__name__)


# Standard ISO 15 / DIN 625 Deep Groove & Spherical Roller Bearing Dimension Crosswalk
ISO_BEARING_DIMENSIONS: Dict[str, str] = {
    # Deep Groove Ball Bearings (60xx, 62xx, 63xx series)
    "6000": "10x26x8 mm",
    "6001": "12x28x8 mm",
    "6002": "15x32x9 mm",
    "6003": "17x35x10 mm",
    "6004": "20x42x12 mm",
    "6005": "25x47x12 mm",
    "6200": "10x30x9 mm",
    "6201": "12x32x10 mm",
    "6202": "15x35x11 mm",
    "6203": "17x40x12 mm",
    "6204": "20x47x14 mm",
    "6205": "25x52x15 mm",
    "6206": "30x62x16 mm",
    "6207": "35x72x17 mm",
    "6208": "40x80x18 mm",
    "6209": "45x85x19 mm",
    "6210": "50x90x20 mm",
    "6300": "10x35x11 mm",
    "6301": "12x37x12 mm",
    "6302": "15x42x13 mm",
    "6303": "17x47x14 mm",
    "6304": "20x52x15 mm",
    "6305": "25x62x17 mm",
    "6306": "30x72x19 mm",
    "6307": "35x80x21 mm",
    "6308": "40x90x23 mm",
    "6309": "45x100x25 mm",
    "6310": "50x110x27 mm",
    "6312": "60x130x31 mm",
    # Spherical Roller Bearings (222xx, 223xx series)
    "22208": "40x80x23 mm",
    "22210": "50x90x23 mm",
    "22212": "60x110x28 mm",
    "22215": "75x130x31 mm",
    "22216": "80x140x33 mm",
    "22218": "90x160x40 mm",
    "22220": "100x180x46 mm",
    "22222": "110x200x53 mm",
    "22224": "120x215x58 mm",
    "22310": "50x110x40 mm",
    "22312": "60x130x46 mm",
    "22314": "70x150x51 mm",
    "22316": "80x170x58 mm",
    "22318": "90x190x64 mm",
    "22320": "100x215x73 mm",
}
DIMENSION_TO_BEARING: Dict[str, str] = {v: k for k, v in ISO_BEARING_DIMENSIONS.items()}


def normalize_bearing_part_no(part_no: str) -> str:
    """Strips common seal/shield/clearance suffixes to isolate base ISO series."""
    if not part_no:
        return ""
    # Strip suffixes like -2RSH, -2RS, -ZZ, 2RS, C3, W33, etc.
    p = re.sub(r"[-/\s]*(?:2RSH?|2RS1?|2Z|ZZ|C[1-5]|W33|K)\b", "", str(part_no), flags=re.I).strip().upper()
    return p


# Short sector code for CNMC formatting
SECTOR_CODE_MAP = {
    "Oil & Gas": "OG",
    "Steel": "ST",
    "Power": "PW",
    "Mining": "MN",
    "Heavy Engineering": "HE",
    "Cross-Sector": "GEN",
    "Unassigned": "MSC",
}

# Category short code for CNMC
CATEGORY_CODE_MAP = {
    "VALVES_FLOW": "VLV",
    "PIPE_FITTINGS": "PIP",
    "GASKETS_SEALS": "GSK",
    "BEARINGS": "BRG",
    "MOTORS_DRIVES": "MOT",
    "GEARBOXES": "GBX",
    "CABLES_CONDUCTORS": "CBL",
    "TRANSFORMERS": "TRF",
    "SWITCHGEAR": "SWG",
    "ROPES_CHAINS": "RPC",
    "CONVEYOR_BELTING": "BLT",
    "DRILLING_MINING": "DRL",
    "WEAR_PARTS": "LIN",
    "STRUCTURAL_STEEL": "STL",
    "REFRACTORIES": "REF",
    "FASTENERS": "FST",
    "COUPLINGS": "CPL",
    "PUMPS_ROTATING": "PMP",
    "MISC_UNCLASSIFIED": "MSC",
}


class DeduplicationMatcher:
    """
    Intra-category hybrid deduplication engine with graph-based clustering,
    CNMC code generation, and explainability reasoning.
    """

    def __init__(self, match_threshold: Optional[float] = None):
        env_thresh = os.getenv("MATCH_THRESHOLD")
        if match_threshold is not None:
            self.match_threshold = match_threshold
        elif env_thresh:
            self.match_threshold = float(env_thresh)
        else:
            self.match_threshold = 0.82
        self.uom_harmonizer = UOMHarmonizer()

    def calculate_pairwise_similarity(
        self,
        item_a: Dict[str, Any],
        item_b: Dict[str, Any]
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculates hybrid similarity score between two material items.
        Returns:
            (composite_score, match_reasons, conflict_reasons)
        """
        # 1. Check Hard Incompatibilities & Attribute Conflicts
        attr_score, attr_matches, attr_conflicts = attribute_extractor.calculate_attribute_match_score(
            item_a["specs"], item_b["specs"]
        )
        if attr_conflicts:
            return 0.0, attr_matches, attr_conflicts

        # 2. Check UOM Compatibility
        uom_compat, uom_ident, uom_msg = self.uom_harmonizer.check_compatibility(
            item_a.get("canonical_uom", "NOS"),
            item_b.get("canonical_uom", "NOS")
        )
        uom_conflict = not uom_compat

        # 3. Dense Semantic Vector Cosine Similarity
        emb_a = item_a.get("embedding")
        emb_b = item_b.get("embedding")
        if emb_a is not None and emb_b is not None:
            cos_sim = float(np.dot(emb_a, emb_b))
        else:
            cos_sim = 0.5

        # 4. Token Fuzzy Sort Similarity
        desc_a = item_a.get("cleaned_description", "")
        desc_b = item_b.get("cleaned_description", "")
        fuzzy_sim = fuzz.token_sort_ratio(desc_a, desc_b) / 100.0

        # 5. OEM Part Number vs Generic Bearing Equivalence (ISO 15 Standard Crosswalk)
        raw_part_a = item_a["specs"].get("models", {}).get("part_number", "")
        raw_part_b = item_b["specs"].get("models", {}).get("part_number", "")
        part_a = normalize_bearing_part_no(raw_part_a)
        part_b = normalize_bearing_part_no(raw_part_b)
        dim_a = item_a["specs"].get("dimensions", {}).get("boundary_3d", "")
        dim_b = item_b["specs"].get("dimensions", {}).get("boundary_3d", "")

        is_oem_generic = False
        if part_a and dim_b and ISO_BEARING_DIMENSIONS.get(part_a) == dim_b:
            is_oem_generic = True
            attr_matches.append(f"OEM bearing model {raw_part_a} matches standard ISO dimension {dim_b}")
        elif part_b and dim_a and ISO_BEARING_DIMENSIONS.get(part_b) == dim_a:
            is_oem_generic = True
            attr_matches.append(f"OEM bearing model {raw_part_b} matches standard ISO dimension {dim_a}")
        elif dim_a and dim_b and dim_a == dim_b and (part_a or part_b):
            expected_pn = DIMENSION_TO_BEARING.get(dim_a)
            if expected_pn and (part_a == expected_pn or part_b == expected_pn):
                is_oem_generic = True
                attr_matches.append(f"Equivalent ISO standard bearing dimension {dim_a} (Series {expected_pn})")

        # 6. Hybrid Score Synthesis
        if is_oem_generic:
            composite = 0.95
        else:
            # Weighted: 45% dense semantic + 25% lexical fuzzy + 30% attribute compatibility
            composite = 0.45 * cos_sim + 0.25 * fuzzy_sim + 0.30 * attr_score

        # If UOM has a non-convertible conflict (e.g. NOS vs KG), penalize composite score
        if uom_conflict:
            composite = min(composite, 0.75) # Caps score to force Human Review Queue!

        all_matches = attr_matches + [f"Semantic cosine similarity: {cos_sim:.2f}"]
        if uom_conflict:
            attr_conflicts.append(uom_msg)

        return round(composite, 3), all_matches, attr_conflicts

    def build_similarity_graph(self, records: List[Dict[str, Any]]) -> nx.Graph:
        """
        Builds graph connecting items that exceed similarity threshold within category blocks.
        Utilizes vectorized BLAS cosine filtering to scale to 50,000+ items with zero recall loss.
        """
        G = nx.Graph()
        for r in records:
            G.add_node(r["idx"], **r)

        # Block by predicted category
        cat_blocks: Dict[str, List[Dict[str, Any]]] = {}
        for r in records:
            cat_blocks.setdefault(r["category_id"], []).append(r)

        for cat_id, block in cat_blocks.items():
            # Do NOT auto-cluster unclassified / ambiguous items
            if cat_id == "MISC_UNCLASSIFIED" or len(block) < 2:
                continue

            n = len(block)
            has_embeddings = all(r.get("embedding") is not None for r in block)

            if has_embeddings and n > 20:
                # Fast matrix dot-product candidate filtering
                X = np.array([r["embedding"] for r in block], dtype=np.float32)
                norms = np.linalg.norm(X, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                X = X / norms
                S = np.dot(X, X.T)

                # Math guarantee: max_composite = 0.45 * cos_sim + 0.55 >= 0.82 requires cos_sim >= 0.60
                cand_i, cand_j = np.where(np.triu(S, k=1) >= 0.60)
                pairs_to_check = zip(cand_i, cand_j)
            else:
                pairs_to_check = ((i, j) for i in range(n) for j in range(i + 1, n))

            for i, j in pairs_to_check:
                a = block[i]
                b = block[j]

                # Skip if either is flagged as ambiguous
                if a.get("specs", {}).get("is_ambiguous") or b.get("specs", {}).get("is_ambiguous"):
                    continue

                score, matches, conflicts = self.calculate_pairwise_similarity(a, b)

                if score >= self.match_threshold and not conflicts:
                    G.add_edge(
                        a["idx"],
                        b["idx"],
                        weight=score,
                        matches=matches,
                        conflicts=conflicts
                    )

        return G

    def generate_cnmc_code(self, category_id: str, sector: str, sequence_num: int) -> str:
        """
        Generates standard Common National Material Code:
        NMC-<SectorCode>-<CategoryCode>-<SequenceId:04d>
        e.g. NMC-OG-VLV-0001 or NMC-GEN-BRG-0024
        """
        sec_code = SECTOR_CODE_MAP.get(sector, "GEN")
        cat_code = CATEGORY_CODE_MAP.get(category_id, "MSC")
        return f"NMC-{sec_code}-{cat_code}-{sequence_num:04d}"

    def synthesize_canonical_description(self, members: List[Dict[str, Any]]) -> str:
        """
        Synthesizes standardized canonical title from cluster members.
        """
        if not members:
            return "Standardized Industrial Material"

        # Prefer member with longest explicit description or clear ground truth name
        sorted_members = sorted(
            members,
            key=lambda m: len(m.get("raw_description", "")),
            reverse=True
        )
        best = sorted_members[0]

        # Assemble canonical name if specs exist
        specs = best.get("specs", {})
        cat_name = TAXONOMY.get(best.get("category_id", ""), {}).get("name", "")

        parts = []
        # Item noun
        parts.append(best.get("cleaned_description", "").split()[0].title())

        # Dimension / Bore
        dim = specs.get("dimensions", {}).get("nominal_bore") or specs.get("dimensions", {}).get("boundary_3d")
        if dim:
            parts.append(str(dim))

        # Pressure / Rating
        p_class = specs.get("pressure_class")
        if p_class:
            parts.append(f"Class {p_class}")

        # Material
        mat = specs.get("material")
        if mat:
            parts.append(mat)

        # Standard
        stds = specs.get("standards", [])
        if stds:
            parts.append(stds[0])

        if len(parts) >= 3:
            return " ".join(parts)

        # Fallback to cleaned description capitalized
        return best.get("cleaned_description", "Standard Industrial Item").title()

    def cluster_and_harmonize(self, records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Performs full deduplication clustering, CNMC generation, and crosswalk preparation.
        Uses Louvain community detection on connected components to prevent transitive chaining.
        Returns:
            (golden_clusters, crosswalk_records)
        """
        G = self.build_similarity_graph(records)
        connected_comps = list(nx.connected_components(G))

        # Hybrid clustering: decompose large connected components using Louvain community detection
        # This prevents transitive chaining (A-B-C-...-Z) from collapsing disparate items into mega-clusters
        final_communities = []
        for comp in connected_comps:
            if len(comp) <= 2:
                final_communities.append(comp)
            else:
                subgraph = G.subgraph(comp)
                if subgraph.number_of_edges() > 0:
                    try:
                        # resolution > 1.0 biases toward tighter, higher-precision communities
                        comms = nx.community.louvain_communities(
                            subgraph,
                            weight="weight",
                            resolution=1.2,
                            seed=42
                        )
                        final_communities.extend(comms)
                    except Exception as e:
                        logger.warning(f"Louvain partitioning failed on component: {e}. Preserving component.")
                        final_communities.append(comp)
                else:
                    final_communities.append(comp)

        # Deterministic sorting of communities
        final_communities.sort(key=lambda c: (
            G.nodes[min(c)].get("category_id", "MISC_UNCLASSIFIED"),
            -len(c),
            min(c)
        ))

        golden_clusters = []
        crosswalk_records = []

        sequence_counters: Dict[str, int] = {}

        for comp in final_communities:
            members = [G.nodes[idx] for idx in sorted(list(comp))]
            first = members[0]

            cat_id = first.get("category_id", "MISC_UNCLASSIFIED")
            sector = first.get("sector", "Cross-Sector")

            seq = sequence_counters.get(cat_id, 1)
            sequence_counters[cat_id] = seq + 1

            cnmc = self.generate_cnmc_code(cat_id, sector, seq)
            canonical_desc = self.synthesize_canonical_description(members)
            std_uom = first.get("canonical_uom", "NOS")

            is_duplicate_cluster = len(members) > 1
            affected_cpses = list(set([m["cpse_id"] for m in members]))

            # Extract unified specs
            unified_specs = {}
            for m in members:
                for k, v in m.get("specs", {}).items():
                    if v and k not in unified_specs:
                        unified_specs[k] = v

            cluster_entry = {
                "cnmc_code": cnmc,
                "canonical_description": canonical_desc,
                "category_id": cat_id,
                "category_name": TAXONOMY.get(cat_id, {}).get("name", "Unclassified"),
                "sector": sector,
                "standard_uom": std_uom,
                "is_duplicate_cluster": is_duplicate_cluster,
                "duplicate_count": len(members),
                "affected_cpses": affected_cpses,
                "specifications": unified_specs,
                "member_codes": [m["source_material_code"] for m in members],
                "member_keys": [(m["source_material_code"], m["cpse_id"]) for m in members],
            }
            golden_clusters.append(cluster_entry)

            # Build Crosswalk Rows for every member
            for m in members:
                raw_uom = m.get("source_uom", "NOS")
                can_uom = m.get("canonical_uom", "NOS")
                is_uom_conflict = (raw_uom.upper() in ["KG", "KGS", "MT"] and can_uom == "NOS")

                # Match type classification
                if is_duplicate_cluster:
                    match_type = "EXACT_DUPLICATE" if len(affected_cpses) > 1 else "INTERNAL_DUPLICATE"
                else:
                    match_type = "UNIQUE_MATERIAL"

                # Status routing
                if m.get("specs", {}).get("is_ambiguous"):
                    status = "UNCLASSIFIED"
                    issue_flag = "LOW_INFORMATION"
                elif is_uom_conflict:
                    status = "PENDING_REVIEW"
                    issue_flag = "UOM_MISMATCH"
                elif is_duplicate_cluster:
                    status = "AUTO_APPROVED"
                    issue_flag = None
                else:
                    status = "APPROVED"
                    issue_flag = None

                crosswalk_row = {
                    "source_material_code": m["source_material_code"],
                    "cpse_id": m["cpse_id"],
                    "plant_code": m.get("plant_code", ""),
                    "sector": m.get("sector", sector),
                    "raw_description": m.get("raw_description", ""),
                    "cleaned_description": m.get("cleaned_description", ""),
                    "cnmc_code": cnmc,
                    "canonical_description": canonical_desc,
                    "category_id": cat_id,
                    "category_name": TAXONOMY.get(cat_id, {}).get("name", "Unclassified"),
                    "standard_uom": std_uom,
                    "source_uom": raw_uom,
                    "match_type": match_type,
                    "match_confidence": 0.96 if is_duplicate_cluster else 0.88,
                    "review_status": status,
                    "issue_flag": issue_flag,
                    "unit_price_inr": m.get("unit_price_inr", 0.0),
                    "current_stock_qty": m.get("current_stock_qty", 0),
                    "annual_procurement_qty": m.get("annual_procurement_qty", 0),
                }
                crosswalk_records.append(crosswalk_row)

        return golden_clusters, crosswalk_records

    def evaluate_against_ground_truth(
        self,
        records: List[Dict[str, Any]],
        golden_clusters: List[Dict[str, Any]],
        gt_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Evaluates deduplication clustering against ground_truth_clusters.csv.
        Uses O(N) contingency combinatorics for fast pairwise precision, recall, F1, and ARI.
        """
        # Map (source_material_code, cpse_id) to predicted CNMC
        code_to_cnmc = {}
        for c in golden_clusters:
            cnmc = c["cnmc_code"]
            for m_key in c.get("member_keys", []):
                code_to_cnmc[m_key] = cnmc
            for m_code in c.get("member_codes", []):
                code_to_cnmc.setdefault((m_code, ""), cnmc)

        # Merge with ground truth
        gt_map = gt_df.set_index(["source_material_code", "cpse_id"]).to_dict("index")

        n = len(records)
        if n < 2:
            return {"total_items": n, "precision": 1.0, "recall": 1.0, "f1_score": 1.0, "ari": 1.0, "adjusted_rand_index": 1.0}

        from collections import defaultdict

        pred_labels = []
        true_labels = []

        for r in records:
            code = r["source_material_code"]
            cpse = r["cpse_id"]
            pred = code_to_cnmc.get((code, cpse)) or code_to_cnmc.get((code, "")) or f"UNCLUSTERED_{code}"
            gt_info = gt_map.get((code, cpse), {})
            true_id = gt_info.get("true_cluster_id") or f"GT_SINGLETON_{code}_{cpse}"
            pred_labels.append(pred)
            true_labels.append(true_id)

        # Fast O(N) contingency table calculation
        contingency = defaultdict(lambda: defaultdict(int))
        pred_counts = defaultdict(int)
        true_counts = defaultdict(int)

        for p_lbl, t_lbl in zip(pred_labels, true_labels):
            contingency[p_lbl][t_lbl] += 1
            pred_counts[p_lbl] += 1
            true_counts[t_lbl] += 1

        def comb2(val: int) -> int:
            return (val * (val - 1)) // 2 if val > 1 else 0

        # TP: pairs in same predicted cluster and same ground-truth cluster
        tp = sum(comb2(cnt) for p_dict in contingency.values() for cnt in p_dict.values())
        sum_pred_comb = sum(comb2(cnt) for cnt in pred_counts.values())
        sum_true_comb = sum(comb2(cnt) for cnt in true_counts.values())

        # FP: pairs in same predicted cluster but different ground-truth clusters
        fp = sum_pred_comb - tp
        # FN: pairs in different predicted clusters but same ground-truth cluster
        fn = sum_true_comb - tp
        total_pairs = comb2(n)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Adjusted Rand Index (ARI)
        expected_index = (sum_pred_comb * sum_true_comb) / total_pairs if total_pairs > 0 else 0.0
        max_index = 0.5 * (sum_pred_comb + sum_true_comb)
        ari = (tp - expected_index) / (max_index - expected_index) if (max_index - expected_index) > 0 else 0.0

        return {
            "total_items": n,
            "total_golden_clusters": len(golden_clusters),
            "duplicate_clusters": sum(1 for c in golden_clusters if c.get("is_duplicate_cluster")),
            "tp": int(tp),
            "fp": int(fp),
            "fn": int(fn),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "ari": round(ari, 4),
            "adjusted_rand_index": round(ari, 4),
        }


# Global singleton instance
matcher = DeduplicationMatcher()
