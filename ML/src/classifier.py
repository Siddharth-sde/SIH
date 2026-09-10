"""
Stage 3: Dual-Layer Taxonomy Classifier & Vector Embeddings.
National Unified Material Master Platform - ML Engine.
"""

import json
import logging
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import requests

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. Taxonomy Definition (18 Cross-Sector Categories)
# ==============================================================================

TAXONOMY: Dict[str, Dict[str, Any]] = {
    "VALVES_FLOW": {
        "name": "Valves & Flow Control",
        "sector": "Cross-Sector",
        "anchors": [
            "gate valve cast steel flanged class 150 nominal bore api 600",
            "globe valve class 150 300 cast steel rf flanged ends",
            "ball valve full bore stainless steel 316 flanged ends",
            "dual plate check valve non return valve flanged wafer type",
            "butterfly valve wafer lugged type flow control valve",
        ],
        "keywords": ["valve", "gate valve", "globe valve", "ball valve", "check valve", "butterfly valve", "nrv", "prv"],
    },
    "PIPE_FITTINGS": {
        "name": "Flanges & Pipe Fittings",
        "sector": "Cross-Sector",
        "anchors": [
            "weld neck raised face flange wnrf class 150 300 astm a105",
            "blind flange raised face forged carbon steel asme b16.5",
            "pipe elbow 90 degree butt weld seamless carbon steel",
            "equal tee pipe reducer seamless forged pipe fitting",
        ],
        "keywords": ["flange", "wnrf", "sorf", "blrf", "pipe fitting", "pipe elbow", "equal tee"],
    },
    "GASKETS_SEALS": {
        "name": "Gaskets & Seals",
        "sector": "Cross-Sector",
        "anchors": [
            "spiral wound gasket class 150 300 stainless steel 316 graphite asme b16.20",
            "viton o-ring rubber seal chemical resistant mechanical seal",
            "mechanical seal cartridge type sic viton din 24960 pump seal",
        ],
        "keywords": ["gasket", "spiral wound", "spwd", "o-ring", "mechanical seal", "seal", "gsk"],
    },
    "BEARINGS": {
        "name": "Bearings & Spares",
        "sector": "Cross-Sector",
        "anchors": [
            "spherical roller bearing 22220 22316 bore diameter heavy duty iso 15",
            "deep groove ball bearing 6205 6312 rubber sealed metal shielded zz",
            "roll neck bearing spherical roller type mill roll support",
            "tapered roller bearing cylindrical roller bearing pillow block",
        ],
        "keywords": ["bearing", "roller bearing", "ball bearing", "srb", "dgbb", "roll neck bearing", "brg"],
    },
    "MOTORS_DRIVES": {
        "name": "Electric Motors & Drives",
        "sector": "Power & Industrial",
        "anchors": [
            "squirrel cage induction motor 3 phase 415v 50hp tefc is 325",
            "3 phase electric motor foot mounted 415v tefc totally enclosed",
            "flameproof electric motor 415v pump drive variable frequency",
        ],
        "keywords": ["motor", "induction motor", "tefc", "electric motor", "drive motor"],
    },
    "GEARBOXES": {
        "name": "Gearboxes & Speed Reducers",
        "sector": "Mechanical",
        "anchors": [
            "helical gearbox reduction ratio 20:1 input 50hp foot mounted is 7347",
            "bevel helical speed reducer heavy industrial gearbox",
            "worm gear reducer shaft mounted speed gearbox",
        ],
        "keywords": ["gearbox", "helical gearbox", "speed reducer", "worm gear"],
    },
    "CABLES_CONDUCTORS": {
        "name": "Cables & Conductors",
        "sector": "Power & Electrical",
        "anchors": [
            "11kv grade xlpe cable aluminium conductor 3 core 400 sqmm armoured is 7098",
            "power cable copper conductor 3c x 400 sqmm cross linked polyethylene armoured",
            "ht power transmission cable armoured multicore conductor",
        ],
        "keywords": ["cable", "xlpe", "conductor", "armoured cable", "sqmm", "power cable"],
    },
    "TRANSFORMERS": {
        "name": "Transformers",
        "sector": "Power",
        "anchors": [
            "power transformer oil filled onan 25mva 33kv 11kv dyn11 is 2026",
            "distribution transformer oil immersed step down transformer",
            "dry type power transformer 11kv class substation",
        ],
        "keywords": ["transformer", "mva", "dyn11", "onan", "oil filled transformer", "xformer"],
    },
    "SWITCHGEAR": {
        "name": "Insulators & Switchgear",
        "sector": "Power & Electrical",
        "anchors": [
            "moulded case circuit breaker mccb 400a 4 pole 36ka is 60947",
            "vacuum circuit breaker vcb 11kv high voltage indoor switchgear",
            "porcelain disc insulator 11kv ball socket type is 731",
            "air circuit breaker acb electrical protection panel switchgear",
        ],
        "keywords": ["mccb", "vcb", "acb", "circuit breaker", "insulator", "switchgear", "switch gear"],
    },
    "ROPES_CHAINS": {
        "name": "Wire Ropes & Chains",
        "sector": "Mining & Handling",
        "anchors": [
            "steel wire rope 6x36 iwrc high tensile independent wire rope core is 2266",
            "transmission roller chain 16b-1 carbon steel iso 606",
            "hoisting wire rope crane steel cable 32mm diameter",
        ],
        "keywords": ["wire rope", "rope", "iwrc", "roller chain", "chain", "16b-1"],
    },
    "CONVEYOR_BELTING": {
        "name": "Conveyor & Belting",
        "sector": "Bulk Handling",
        "anchors": [
            "rubber conveyor belt 1200mm width 4 ply nylon fabric ep grade cover",
            "v-belt spb 2240 wrapped construction din 7753 transmission belt",
            "endless flat belt conveyor belting material handling",
        ],
        "keywords": ["conveyor belt", "v-belt", "belt", "belting", "spb"],
    },
    "DRILLING_MINING": {
        "name": "Drilling & Mining Tools",
        "sector": "Mining",
        "anchors": [
            "tricone rock drill bit 8.5 inch diameter iadc 517 tungsten carbide insert tci",
            "hydraulic rock breaker hammer excavator attachment operating weight",
            "drill rod drill collar mining excavation drilling consumable",
        ],
        "keywords": ["drill bit", "tricone", "iadc", "rock breaker", "mining tool", "drill rod"],
    },
    "WEAR_PARTS": {
        "name": "Wear Parts & Liners",
        "sector": "Mining & Steel",
        "anchors": [
            "manganese steel crusher liner hadfield steel high mn jaw plate",
            "crusher wear liner impact plate grinding mill liner",
            "chute liner ceramic wear resistant abrasion liner",
        ],
        "keywords": ["crusher liner", "wear liner", "manganese steel", "hadfield", "jaw liner", "wear parts"],
    },
    "STRUCTURAL_STEEL": {
        "name": "Structural Steel & Billets",
        "sector": "Steel & Fabrication",
        "anchors": [
            "hot rolled mild steel plate 12mm thickness 2000x6000mm is 2062 grade b",
            "continuous cast mild steel billet 100x100mm square 6 metre length",
            "ms angle channel beam structural steel fabrication section",
        ],
        "keywords": ["mild steel plate", "ms plate", "billet", "steel billet", "structural steel", "is 2062"],
    },
    "REFRACTORIES": {
        "name": "Refractories & Furnace Linings",
        "sector": "Steel & Thermal",
        "anchors": [
            "fireclay refractory bricks 230x115x65mm high alumina furnace lining",
            "magnesite refractory brick thermal insulation blast furnace",
            "refractory castable mortar high temperature monolithic lining",
        ],
        "keywords": ["refractory", "fireclay", "refractory brick", "furnace lining", "alumina brick"],
    },
    "FASTENERS": {
        "name": "Fasteners & Hardware",
        "sector": "Cross-Sector",
        "anchors": [
            "hex head bolt m16x80 m24x100 property class grade 8.8 zinc plated iso 898-1",
            "high tensile stud bolt hex nut plain washer grade b7",
            "threaded fastener stainless steel socket head cap screw",
        ],
        "keywords": ["bolt", "hex bolt", "fastener", "stud", "nut", "screw", "washer"],
    },
    "COUPLINGS": {
        "name": "Couplings & Power Transmission",
        "sector": "Mechanical",
        "anchors": [
            "flexible jaw coupling l-110 polyurethane spider cast iron hubs",
            "grid coupling g20 carbon steel grid flanged shaft coupling",
            "gear coupling flexible mechanical power transmission coupling",
        ],
        "keywords": ["coupling", "jaw coupling", "grid coupling", "flexible coupling"],
    },
    "PUMPS_ROTATING": {
        "name": "Pumps & Rotating Machinery",
        "sector": "Cross-Sector",
        "anchors": [
            "centrifugal pump cast steel casing stainless steel 316 impeller 50hp 415v",
            "water slurry pump rotating pump casing mechanical seal",
        ],
        "keywords": ["pump", "centrifugal pump", "slurry pump", "impeller"],
    },
    "MISC_UNCLASSIFIED": {
        "name": "Miscellaneous / Unclassified Spares",
        "sector": "Unassigned",
        "anchors": [
            "miscellaneous spare part unidentified machine component drawing",
            "item description unclear drawing reference unspecified spare",
        ],
        "keywords": ["misc", "unclear", "unidentified", "spare part", "unspecified"],
    },
}


# ==============================================================================
# 2. Dual-Layer Taxonomy Classifier
# ==============================================================================

class DualLayerClassifier:
    """
    Classifies material descriptions using:
    - Layer 1: Nearest-Exemplar Cosine Similarity via Sentence-Transformers (all-MiniLM-L6-v2)
    - Layer 2: LLM Verification via Qwen2.5-3B (Ollama) for borderline / ambiguous cases
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        ollama_url: str = "http://127.0.0.1:11434",
        llm_model: str = "qwen2.5:3b",
    ):
        import os
        if os.path.exists("models/all-MiniLM-L6-v2"):
            model_path = "models/all-MiniLM-L6-v2"
            os.environ["HF_HUB_OFFLINE"] = "1"
        else:
            model_path = model_name

        self.model_name = model_path
        self.ollama_url = ollama_url
        self.llm_model = llm_model

        # Load Sentence Transformer on CPU
        logger.info(f"Loading SentenceTransformer: {model_path}")
        self.embedder = SentenceTransformer(model_path, device="cpu", local_files_only=os.path.exists(model_path))

        # Build Category Anchor Embeddings
        self.category_ids: List[str] = list(TAXONOMY.keys())
        self._build_anchor_index()

    def _build_anchor_index(self):
        """Encodes all anchor descriptions into a normalized embedding matrix."""
        all_anchor_texts = []
        self.anchor_to_category: List[str] = []

        for cat_id, cat_info in TAXONOMY.items():
            for anchor in cat_info["anchors"]:
                all_anchor_texts.append(anchor)
                self.anchor_to_category.append(cat_id)

        # Encode and normalize
        embs = self.embedder.encode(all_anchor_texts, convert_to_numpy=True, normalize_embeddings=True)
        self.anchor_matrix = embs  # Shape: (N_anchors, 384)

    def encode_text(self, text: str) -> np.ndarray:
        """Returns 384-d normalized embedding vector."""
        return self.embedder.encode([text], convert_to_numpy=True, normalize_embeddings=True)[0]

    def encode_batch(self, texts: List[str], batch_size: int = 64) -> np.ndarray:
        """Encodes a list of texts into normalized embedding vectors."""
        return self.embedder.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

    def get_embedding_category_scores(self, query_emb: np.ndarray) -> List[Tuple[str, float]]:
        """
        Computes cosine similarity between query embedding and all category anchors.
        Returns list of (category_id, max_similarity) sorted in descending order.
        """
        # Dot product with normalized vectors equals cosine similarity
        sims = np.dot(self.anchor_matrix, query_emb)

        cat_max_sim: Dict[str, float] = {}
        for cat_id in self.category_ids:
            cat_max_sim[cat_id] = 0.0

        for sim, cat_id in zip(sims, self.anchor_to_category):
            if sim > cat_max_sim[cat_id]:
                cat_max_sim[cat_id] = float(sim)

        sorted_cats = sorted(cat_max_sim.items(), key=lambda x: x[1], reverse=True)
        return sorted_cats

    def check_keyword_rules(self, text: str) -> Optional[Tuple[str, float, str]]:
        """High-precision keyword rules as a safety net."""
        t_low = text.lower()

        # Check in order of specificity
        priority_checks = [
            ("gate valve", "VALVES_FLOW", 0.98),
            ("globe valve", "VALVES_FLOW", 0.98),
            ("ball valve", "VALVES_FLOW", 0.98),
            ("check valve", "VALVES_FLOW", 0.98),
            ("butterfly valve", "VALVES_FLOW", 0.98),
            ("valve", "VALVES_FLOW", 0.95),
            ("spherical roller bearing", "BEARINGS", 0.98),
            ("deep groove ball bearing", "BEARINGS", 0.98),
            ("roll neck bearing", "BEARINGS", 0.98),
            ("bearing", "BEARINGS", 0.95),
            ("spiral wound gasket", "GASKETS_SEALS", 0.98),
            ("mechanical seal", "GASKETS_SEALS", 0.96),
            ("gasket", "GASKETS_SEALS", 0.95),
            ("flange", "PIPE_FITTINGS", 0.95),
            ("induction motor", "MOTORS_DRIVES", 0.96),
            ("electric motor", "MOTORS_DRIVES", 0.95),
            ("helical gearbox", "GEARBOXES", 0.98),
            ("gearbox", "GEARBOXES", 0.95),
            ("xlpe cable", "CABLES_CONDUCTORS", 0.98),
            ("power cable", "CABLES_CONDUCTORS", 0.95),
            ("power transformer", "TRANSFORMERS", 0.98),
            ("transformer", "TRANSFORMERS", 0.95),
            ("mccb", "SWITCHGEAR", 0.98),
            ("circuit breaker", "SWITCHGEAR", 0.96),
            ("insulator", "SWITCHGEAR", 0.95),
            ("wire rope", "ROPES_CHAINS", 0.98),
            ("roller chain", "ROPES_CHAINS", 0.96),
            ("conveyor belt", "CONVEYOR_BELTING", 0.98),
            ("v-belt", "CONVEYOR_BELTING", 0.96),
            ("drill bit", "DRILLING_MINING", 0.98),
            ("rock breaker", "DRILLING_MINING", 0.96),
            ("crusher liner", "WEAR_PARTS", 0.98),
            ("mild steel plate", "STRUCTURAL_STEEL", 0.98),
            ("steel billet", "STRUCTURAL_STEEL", 0.98),
            ("billet", "STRUCTURAL_STEEL", 0.95),
            ("refractory brick", "REFRACTORIES", 0.98),
            ("hex bolt", "FASTENERS", 0.98),
            ("fastener", "FASTENERS", 0.95),
            ("jaw coupling", "COUPLINGS", 0.98),
            ("grid coupling", "COUPLINGS", 0.98),
            ("centrifugal pump", "PUMPS_ROTATING", 0.98),
        ]

        for keyword, cat_id, conf in priority_checks:
            # Word boundary check
            if f" {keyword} " in f" {t_low} ":
                cat_name = TAXONOMY[cat_id]["name"]
                return cat_id, conf, f"Rule match: Contains explicit term '{keyword}' mapped to {cat_name}"

        return None

    def query_llm_adjudication(
        self,
        text: str,
        specs: Dict[str, Any],
        top_candidates: List[Tuple[str, float]]
    ) -> Optional[Dict[str, Any]]:
        """
        Invokes Qwen2.5-3B via Ollama to adjudicate borderline categories among top-3 candidates.
        """
        top3 = top_candidates[:3]
        candidate_options = [f"{i+1}. {c[0]} ({TAXONOMY[c[0]]['name']})" for i, c in enumerate(top3)]
        options_text = "\n".join(candidate_options)

        prompt = (
            f"You are an industrial material master expert. Classify this material into EXACTLY ONE of the 3 candidate categories below:\n"
            f"Material Description: {text}\n"
            f"Extracted Specifications: {json.dumps(specs)}\n\n"
            f"Candidate Categories:\n{options_text}\n\n"
            f"Return a strict JSON object with fields:\n"
            f'{{"category_id": "<one of the candidate category_ids>", "confidence": <float between 0.5 and 1.0>, "reasoning": "<one clear explanation sentence>"}}'
        )

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.0}
                },
                timeout=5.0
            )
            if resp.status_code == 200:
                body = resp.json()
                content = body.get("message", {}).get("content", "")
                parsed = json.loads(content)
                cat_id = parsed.get("category_id")
                if cat_id in TAXONOMY:
                    return {
                        "category_id": cat_id,
                        "category_name": TAXONOMY[cat_id]["name"],
                        "confidence": float(parsed.get("confidence", 0.85)),
                        "method": "llm_adjudicated",
                        "reasoning": f"LLM verified: {parsed.get('reasoning', '')}",
                    }
        except Exception as e:
            logger.debug(f"Ollama adjudication skipped: {e}")

        return None

    def classify(
        self,
        cleaned_description: str,
        cleaned_spec_text: str = "",
        extracted_specs: Optional[Dict[str, Any]] = None,
        use_llm: bool = False
    ) -> Dict[str, Any]:
        """
        Master classification entry point.
        """
        specs = extracted_specs or {}
        combined_text = f"{cleaned_description} {cleaned_spec_text}".strip()

        # Check Ambiguous Triage Flag first
        if specs.get("is_ambiguous"):
            return {
                "category_id": "MISC_UNCLASSIFIED",
                "category_name": TAXONOMY["MISC_UNCLASSIFIED"]["name"],
                "confidence": 0.35,
                "method": "triage_rule",
                "reasoning": specs.get("ambiguity_reason", "Item lacks sufficient technical information"),
                "top_candidates": [("MISC_UNCLASSIFIED", 0.35)],
                "embedding": self.encode_text(combined_text).tolist(),
            }

        # Check High-Precision Keyword Rules (Safety Net)
        rule_match = self.check_keyword_rules(combined_text)
        if rule_match:
            cat_id, conf, reason = rule_match
            emb = self.encode_text(combined_text)
            return {
                "category_id": cat_id,
                "category_name": TAXONOMY[cat_id]["name"],
                "confidence": conf,
                "method": "exact_rule",
                "reasoning": reason,
                "top_candidates": [(cat_id, conf)],
                "embedding": emb.tolist(),
            }

        # Layer 1: Nearest-Exemplar Cosine Similarity
        query_emb = self.encode_text(combined_text)
        ranked_cats = self.get_embedding_category_scores(query_emb)
        top_cat_id, top_score = ranked_cats[0]
        second_cat_id, second_score = ranked_cats[1]

        # Check if high-confidence embedding match
        if top_score >= 0.70 and (top_score - second_score >= 0.08):
            return {
                "category_id": top_cat_id,
                "category_name": TAXONOMY[top_cat_id]["name"],
                "confidence": round(float(top_score), 3),
                "method": "embedding_nearest_anchor",
                "reasoning": f"Closest exemplar anchor match with cosine similarity {top_score:.3f} (margin: +{top_score-second_score:.3f})",
                "top_candidates": [(c, round(s, 3)) for c, s in ranked_cats[:3]],
                "embedding": query_emb.tolist(),
            }

        # Layer 2: LLM Adjudication for borderline cases (if enabled)
        if use_llm:
            llm_result = self.query_llm_adjudication(combined_text, specs, ranked_cats)
            if llm_result:
                llm_result["top_candidates"] = [(c, round(s, 3)) for c, s in ranked_cats[:3]]
                llm_result["embedding"] = query_emb.tolist()
                return llm_result

        # Fallback to top embedding candidate
        return {
            "category_id": top_cat_id,
            "category_name": TAXONOMY[top_cat_id]["name"],
            "confidence": round(float(top_score), 3),
            "method": "embedding_nearest_anchor",
            "reasoning": f"Nearest embedding exemplar ({top_score:.3f} similarity to {TAXONOMY[top_cat_id]['name']})",
            "top_candidates": [(c, round(s, 3)) for c, s in ranked_cats[:3]],
            "embedding": query_emb.tolist(),
        }

    def classify_batch(
        self,
        cleaned_descriptions: List[str],
        cleaned_spec_texts: List[str],
        specs_list: List[Dict[str, Any]],
        batch_size: int = 256,
    ) -> List[Dict[str, Any]]:
        """
        High-throughput vectorized batch classification across thousands of items.
        Returns list of classification result dicts with embeddings.
        """
        n = len(cleaned_descriptions)
        combined_texts = [
            f"{d} {s}".strip() for d, s in zip(cleaned_descriptions, cleaned_spec_texts)
        ]

        logger.info(f"Batch encoding {n} items with batch_size={batch_size}...")
        embeddings = self.encode_batch(combined_texts, batch_size=batch_size)

        logger.info(f"Computing anchor similarity matrix for {n} items...")
        anchor_sims = np.dot(embeddings, self.anchor_matrix.T)

        results = []
        for i in range(n):
            specs = specs_list[i] if i < len(specs_list) else {}
            text = combined_texts[i]
            emb = embeddings[i]

            # Ambiguous triage rule
            if specs.get("is_ambiguous"):
                results.append({
                    "category_id": "MISC_UNCLASSIFIED",
                    "category_name": TAXONOMY["MISC_UNCLASSIFIED"]["name"],
                    "confidence": 0.35,
                    "method": "triage_rule",
                    "reasoning": specs.get("ambiguity_reason", "Item lacks sufficient technical information"),
                    "top_candidates": [("MISC_UNCLASSIFIED", 0.35)],
                    "embedding": emb,
                })
                continue

            # Exact keyword rule
            rule_match = self.check_keyword_rules(text)
            if rule_match:
                cat_id, conf, reason = rule_match
                results.append({
                    "category_id": cat_id,
                    "category_name": TAXONOMY[cat_id]["name"],
                    "confidence": conf,
                    "method": "exact_rule",
                    "reasoning": reason,
                    "top_candidates": [(cat_id, conf)],
                    "embedding": emb,
                })
                continue

            # Anchor categorization from precomputed anchor_sims[i]
            row_sims = anchor_sims[i]
            cat_max_sim = {cat_id: 0.0 for cat_id in self.category_ids}
            for sim, cat_id in zip(row_sims, self.anchor_to_category):
                if sim > cat_max_sim[cat_id]:
                    cat_max_sim[cat_id] = float(sim)

            ranked_cats = sorted(cat_max_sim.items(), key=lambda x: x[1], reverse=True)
            top_cat_id, top_score = ranked_cats[0]
            second_cat_id, second_score = ranked_cats[1]

            if top_score >= 0.70 and (top_score - second_score >= 0.08):
                reasoning = f"Closest exemplar anchor match with cosine similarity {top_score:.3f} (margin: +{top_score-second_score:.3f})"
            else:
                reasoning = f"Nearest embedding exemplar ({top_score:.3f} similarity to {TAXONOMY[top_cat_id]['name']})"

            results.append({
                "category_id": top_cat_id,
                "category_name": TAXONOMY[top_cat_id]["name"],
                "confidence": round(float(top_score), 3),
                "method": "embedding_nearest_anchor",
                "reasoning": reasoning,
                "top_candidates": [(c, round(s, 3)) for c, s in ranked_cats[:3]],
                "embedding": emb,
            })

        return results


# Global singleton instance
classifier = DualLayerClassifier()

