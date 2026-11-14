"""
SafeMeds - FastAPI Local Backend Server
Connects in-process to the persistent Relate database `./data/safemeds.rl`.
Exposes Cypher-powered analysis endpoints, reverse symptom tracing, and live query inspection.
"""

import os
import sys
import time
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import relate

# Locate persistent Relate database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "safemeds.rl")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if not os.path.exists(DB_PATH):
    raise RuntimeError(f"Persistent Relate database not found at {DB_PATH}. Run scripts/seed_data.py first.")

app = FastAPI(
    title="SafeMeds API",
    description="Offline-first Medication, Food, and Condition Graph powered by Relate by Neo4j",
    version="1.0.0"
)

# Helpers for Relate queries
def get_db(read_only: bool = True):
    return relate.connect(DB_PATH, read_only=read_only)

def execute_cypher(query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    t0 = time.perf_counter()
    conn = get_db(read_only=True)
    cur = conn.cursor()
    try:
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        rows = [dict(row) for row in cur]
        columns = list(rows[0].keys()) if rows else []
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "query": query.strip(),
            "params": params or {},
            "columns": columns,
            "rows": rows,
            "count": len(rows),
            "elapsed_ms": elapsed_ms
        }
    finally:
        conn.close()

# Request Models
class AnalyzeRequest(BaseModel):
    medicines: List[str] = []
    foods: List[str] = []
    conditions: List[str] = []

class SymptomTraceRequest(BaseModel):
    symptom: str
    active_medicines: List[str] = []

class CypherQueryRequest(BaseModel):
    query: str
    params: Optional[Dict[str, Any]] = None

class AgentRequest(BaseModel):
    message: str
    active_medicines: List[str] = []
    foods: List[str] = []
    conditions: List[str] = []

# 1. HEALTH & METADATA
@app.get("/api/health")
def health():
    size_bytes = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    return {
        "status": "healthy",
        "database": {
            "mode": "single file",
            "path": DB_PATH,
            "rel_path": "./data/safemeds.rl",
            "size_bytes": size_bytes,
            "size_kb": round(size_bytes / 1024, 1),
            "exists": os.path.exists(DB_PATH)
        },
        "engine": "Relate by Neo4j (in-process Rust Cypher engine)",
        "version": "1.0.1"
    }

# 2. PRESETS
@app.get("/api/presets")
def get_presets():
    return [
        {
            "id": "preset_1",
            "title": "Heart + Gastric Block",
            "tag": "CYP2C19 Enzyme Collision",
            "description": "Clopidogrel requires CYP2C19 activation; Omeprazole strongly inhibits CYP2C19, risking stent thrombosis or stroke.",
            "medicines": ["Clopidogrel", "Omeprazole"],
            "foods": [],
            "conditions": ["Gastric Ulcer / GERD"],
            "symptom": "Stomach Pain / Gastritis"
        },
        {
            "id": "preset_2",
            "title": "Antibiotic + Dairy Timing",
            "tag": "Polyvalent Cation Chelation",
            "description": "Ciprofloxacin binds calcium in Milk / Dairy forming insoluble complexes that reduce antibiotic absorption by 85%.",
            "medicines": ["Ciprofloxacin"],
            "foods": ["Milk / Dairy", "Calcium Supplements / Antacids"],
            "conditions": [],
            "symptom": "Nausea / Vomiting"
        },
        {
            "id": "preset_3",
            "title": "BP + Double Painkiller + Trace",
            "tag": "Double NSAID Overlap & Kidney Stress",
            "description": "Advil and Aleve together cause extreme renal and gastric strain, blunting Lisinopril/Amlodipine BP control. Traces Dry Cough to Lisinopril and Swollen Ankles to Amlodipine.",
            "medicines": ["Lisinopril", "Amlodipine", "Advil", "Aleve"],
            "foods": [],
            "conditions": ["Hypertension"],
            "symptom": "Persistent Dry Cough"
        },
        {
            "id": "preset_4",
            "title": "Statin + Warfarin + Diet Clash",
            "tag": "Enzyme Block & Vitamin K Antagonism",
            "description": "Grapefruit inhibits CYP3A4, causing toxic Atorvastatin accumulation (rhabdomyolysis), while Spinach (Vitamin K) neutralizes Warfarin.",
            "medicines": ["Atorvastatin", "Warfarin"],
            "foods": ["Grapefruit Juice", "Spinach / Leafy Greens"],
            "conditions": ["Bleeding Risk / Thrombocytopenia"],
            "symptom": "Muscle Pain / Myopathy"
        }
    ]

# 3. CATALOG
@app.get("/api/catalog")
def get_catalog():
    conn = get_db(read_only=True)
    cur = conn.cursor()
    try:
        cur.execute("""
            MATCH (m:Medicine)-[:CONTAINS]->(i:Ingredient)
            RETURN m.name AS name, m.brand_name AS brand, m.is_brand AS is_brand,
                   m.generic_name AS generic_name, i.name AS ingredient,
                   m.default_slot AS default_slot, m.take_with_food AS take_with_food
            ORDER BY m.name
        """)
        medicines = [dict(r) for r in cur]

        cur.execute("MATCH (f:Food) RETURN f.name AS name, f.category AS category, f.notes AS notes ORDER BY f.name")
        foods = [dict(r) for r in cur]

        cur.execute("MATCH (c:Condition) RETURN c.name AS name, c.category AS category ORDER BY c.name")
        conditions = [dict(r) for r in cur]

        cur.execute("MATCH (s:Symptom) RETURN s.name AS name, s.severity AS severity, s.description AS description ORDER BY s.name")
        symptoms = [dict(r) for r in cur]

        return {
            "medicines": medicines,
            "foods": foods,
            "conditions": conditions,
            "symptoms": symptoms
        }
    finally:
        conn.close()

# 4. COMPREHENSIVE ANALYSIS
@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    meds = req.medicines
    foods = req.foods
    conditions = req.conditions

    queries_executed = []
    nodes = {}
    edges = []
    warnings = []
    brand_overlaps = []
    safe_alternatives = []
    schedule = []
    organ_load = {"Kidney": 0, "Liver": 0, "Stomach / GI": 0, "Brain / CNS": 0}

    def add_node(id_val: str, label_type: str, title: str, category: str = "", extra: Dict = None):
        if id_val not in nodes:
            nodes[id_val] = {
                "id": id_val,
                "label": label_type,
                "title": title,
                "category": category,
                "extra": extra or {}
            }

    def add_edge(source: str, target: str, type_val: str, label: str, severity: str = "normal", notes: str = ""):
        edges.append({
            "source": source,
            "target": target,
            "type": type_val,
            "label": label,
            "severity": severity,
            "notes": notes
        })

    # Add selected medicine nodes
    for m in meds:
        add_node(f"med_{m}", "Medicine", m, "Medicine")
    for f in foods:
        add_node(f"food_{f}", "Food", f, "Food")
    for c in conditions:
        add_node(f"cond_{c}", "Condition", c, "Condition")

    if not meds and not foods and not conditions:
        return {
            "warnings": [],
            "brand_overlaps": [],
            "safe_alternatives": [],
            "schedule": [],
            "organ_load": organ_load,
            "graph": {"nodes": [], "edges": []},
            "queries_executed": []
        }

    conn = get_db(read_only=True)
    cur = conn.cursor()

    try:
        # A. MAP MEDICINES TO INGREDIENTS
        if meds:
            q_ing = """
            MATCH (m:Medicine)-[r:CONTAINS]->(i:Ingredient)
            WHERE m.name IN $meds
            RETURN m.name AS medicine, i.name AS ingredient, r.dosage_mg AS dosage, i.description AS description
            """
            cur.execute(q_ing, {"meds": meds})
            ing_rows = [dict(r) for r in cur]
            queries_executed.append({"name": "Medicine Ingredients", "query": q_ing, "params": {"meds": meds}})
            for r in ing_rows:
                add_node(f"ing_{r['ingredient']}", "Ingredient", r["ingredient"], "Active Ingredient", {"desc": r["description"]})
                add_edge(f"med_{r['medicine']}", f"ing_{r['ingredient']}", "CONTAINS", f"{r['dosage']}mg", "normal")

        # B. DOUBLE-DOSE / BRAND OVERLAP DETECTOR
        if len(meds) >= 2:
            q_dd = """
            MATCH (m1:Medicine)-[:CONTAINS]->(i:Ingredient)<-[:CONTAINS]-(m2:Medicine)
            WHERE m1.name IN $meds AND m2.name IN $meds AND m1.name < m2.name
            RETURN m1.name AS med1, m2.name AS med2, i.name AS ingredient
            """
            cur.execute(q_dd, {"meds": meds})
            dd_rows = [dict(r) for r in cur]
            queries_executed.append({"name": "Double Dose Overlap", "query": q_dd, "params": {"meds": meds}})
            for r in dd_rows:
                brand_overlaps.append({
                    "med1": r["med1"],
                    "med2": r["med2"],
                    "ingredient": r["ingredient"],
                    "warning": f"Accidental Overdose Hazard: '{r['med1']}' and '{r['med2']}' both contain the exact same active generic ingredient '{r['ingredient']}'!"
                })
                add_edge(f"med_{r['med1']}", f"med_{r['med2']}", "BRAND_OVERLAP", "Double Dose!", "conflict", f"Shared: {r['ingredient']}")

        # C. MULTI-HOP ENZYME COLLISIONS (3-4 Hops)
        if len(meds) >= 2:
            q_enz = """
            MATCH (m1:Medicine)-[:CONTAINS]->(i1:Ingredient)-[:REQUIRES_ENZYME]->(e:Enzyme)<-[:INHIBITS_ENZYME]-(i2:Ingredient)<-[:CONTAINS]-(m2:Medicine)
            WHERE m1.name IN $meds AND m2.name IN $meds AND m1.name <> m2.name
            RETURN m1.name AS prodrug_med, i1.name AS prodrug_ing, e.name AS enzyme,
                   m2.name AS inhibitor_med, i2.name AS inhibitor_ing
            """
            cur.execute(q_enz, {"meds": meds})
            enz_rows = [dict(r) for r in cur]
            queries_executed.append({"name": "Enzyme Collisions", "query": q_enz, "params": {"meds": meds}})
            for r in enz_rows:
                warnings.append({
                    "type": "Enzyme Collision (Prodrug Block)",
                    "severity": "Severe",
                    "title": f"{r['prodrug_med']} Efficacy Blocked by {r['inhibitor_med']}",
                    "details": f"{r['prodrug_med']} ({r['prodrug_ing']}) requires the hepatic enzyme [{r['enzyme']}] for activation. {r['inhibitor_med']} ({r['inhibitor_ing']}) is a strong inhibitor of [{r['enzyme']}], preventing therapeutic activation and risking therapeutic failure (e.g. vascular thrombosis / stroke)."
                })
                add_node(f"enz_{r['enzyme']}", "Enzyme", r["enzyme"], "CYP Enzyme")
                add_edge(f"ing_{r['prodrug_ing']}", f"enz_{r['enzyme']}", "REQUIRES_ENZYME", "Requires", "conflict")
                add_edge(f"ing_{r['inhibitor_ing']}", f"enz_{r['enzyme']}", "INHIBITS_ENZYME", "Blocks", "conflict")

        # D. DIRECT DRUG-DRUG INTERACTIONS
        if len(meds) >= 2:
            q_ddi = """
            MATCH (m1:Medicine)-[:CONTAINS]->(i1:Ingredient)-[r:DIRECT_INTERACTION]->(i2:Ingredient)<-[:CONTAINS]-(m2:Medicine)
            WHERE m1.name IN $meds AND m2.name IN $meds AND m1.name < m2.name
            RETURN m1.name AS med1, m2.name AS med2, i1.name AS ing1, i2.name AS ing2,
                   r.severity AS severity, r.mechanism AS mechanism, r.effect AS effect
            """
            cur.execute(q_ddi, {"meds": meds})
            ddi_rows = [dict(r) for r in cur]
            queries_executed.append({"name": "Direct Drug-Drug Interactions", "query": q_ddi, "params": {"meds": meds}})
            for r in ddi_rows:
                warnings.append({
                    "type": "Drug-Drug Conflict",
                    "severity": r["severity"],
                    "title": f"Direct Interaction: {r['med1']} + {r['med2']}",
                    "details": f"{r['mechanism']}. Clinical Effect: {r['effect']}"
                })
                add_edge(f"ing_{r['ing1']}", f"ing_{r['ing2']}", "DIRECT_INTERACTION", r["severity"], "conflict", r["effect"])

        # E. FOOD-DRUG INTERACTIONS & CHELATION
        if meds and foods:
            q_food = """
            MATCH (m:Medicine)-[:CONTAINS]->(i:Ingredient)-[r:BINDS_OR_CONFLICTS_WITH]->(f:Food)
            WHERE m.name IN $meds AND f.name IN $foods
            RETURN m.name AS med, i.name AS ing, f.name AS food,
                   r.min_gap_hours AS min_gap_hours, r.severity AS severity, r.mechanism AS mechanism
            """
            cur.execute(q_food, {"meds": meds, "foods": foods})
            food_rows = [dict(r) for r in cur]
            queries_executed.append({"name": "Food-Drug Interactions", "query": q_food, "params": {"meds": meds, "foods": foods}})
            for r in food_rows:
                severity_type = "conflict" if r["severity"] in ["High", "Severe"] else "spacing"
                warnings.append({
                    "type": "Food-Drug Conflict" if severity_type == "conflict" else "Timing Spacing Required",
                    "severity": r["severity"],
                    "title": f"{r['med']} Conflict with {r['food']}",
                    "details": f"{r['mechanism']}. Mandatory minimum spacing: {r['min_gap_hours']} hours."
                })
                add_edge(f"ing_{r['ing']}", f"food_{r['food']}", "BINDS_OR_CONFLICTS_WITH", f"{r['min_gap_hours']}h Gap", severity_type, r["mechanism"])

        # F. CONDITION CONTRAINDICATIONS
        if meds and conditions:
            q_cond = """
            MATCH (m:Medicine)-[:CONTAINS]->(i:Ingredient)-[r:CONTRAINDICATED_IN]->(c:Condition)
            WHERE m.name IN $meds AND c.name IN $conditions
            RETURN m.name AS med, i.name AS ing, c.name AS condition,
                   r.severity AS severity, r.reason AS reason
            """
            cur.execute(q_cond, {"meds": meds, "conditions": conditions})
            cond_rows = [dict(r) for r in cur]
            queries_executed.append({"name": "Condition Contraindications", "query": q_cond, "params": {"meds": meds, "conditions": conditions}})
            for r in cond_rows:
                warnings.append({
                    "type": "Contraindication",
                    "severity": r["severity"],
                    "title": f"{r['med']} Contraindicated in {r['condition']}",
                    "details": r["reason"]
                })
                add_edge(f"ing_{r['ing']}", f"cond_{r['condition']}", "CONTRAINDICATED_IN", r["severity"], "conflict", r["reason"])

        # G. CUMULATIVE ORGAN LOAD
        if meds:
            q_load = """
            MATCH (m:Medicine)-[:CONTAINS]->(i:Ingredient)-[r:STRESSES_ORGAN]->(o:Organ)
            WHERE m.name IN $meds
            RETURN o.name AS organ, sum(r.load_score) AS total_score,
                   collect(DISTINCT {med: m.name, score: r.load_score, notes: r.notes}) AS contributors
            """
            cur.execute(q_load, {"meds": meds})
            load_rows = [dict(r) for r in cur]
            queries_executed.append({"name": "Cumulative Organ Load", "query": q_load, "params": {"meds": meds}})
            for r in load_rows:
                if r["organ"] in organ_load:
                    organ_load[r["organ"]] = r["total_score"]
                add_node(f"org_{r['organ']}", "Organ", r["organ"], "Target Organ", {"score": r["total_score"]})
                for c in r["contributors"]:
                    add_edge(f"med_{c['med']}", f"org_{r['organ']}", "STRESSES_ORGAN", f"Load +{c['score']}", "normal", c.get("notes", ""))

        # H. SAFE ALTERNATIVES
        if meds:
            q_alt = """
            MATCH (m_alt:Medicine)-[r:SAFE_ALTERNATIVE_TO]->(m_tgt:Medicine)
            WHERE m_tgt.name IN $meds AND NOT m_alt.name IN $meds
            RETURN m_alt.name AS alternative, m_tgt.name AS target_medicine,
                   r.reason AS reason, r.target_condition AS condition
            """
            cur.execute(q_alt, {"meds": meds})
            alt_rows = [dict(r) for r in cur]
            queries_executed.append({"name": "Safe Alternatives", "query": q_alt, "params": {"meds": meds}})
            for r in alt_rows:
                safe_alternatives.append({
                    "alternative": r["alternative"],
                    "replaces": r["target_medicine"],
                    "condition": r["condition"],
                    "reason": r["reason"]
                })
                add_node(f"med_{r['alternative']}", "Medicine", r["alternative"], "Safe Alternative", {"is_alt": True})
                add_edge(f"med_{r['alternative']}", f"med_{r['target_medicine']}", "SAFE_ALTERNATIVE_TO", "Safe Alternative", "alternative", r["reason"])

        # I. SMART 5-SLOT DAILY SCHEDULE PLANNER
        if meds:
            q_sched = """
            MATCH (m:Medicine)
            WHERE m.name IN $meds
            RETURN m.name AS name, m.default_slot AS slot,
                   m.take_with_food AS take_with_food, m.min_gap_hours AS min_gap_hours
            ORDER BY m.default_slot
            """
            cur.execute(q_sched, {"meds": meds})
            sched_rows = [dict(r) for r in cur]
            queries_executed.append({"name": "Daily Schedule", "query": q_sched, "params": {"meds": meds}})
            
            # Map into 5 standard slots
            slots_order = [
                "Morning (Empty Stomach)",
                "Breakfast",
                "Lunch",
                "Evening",
                "Bedtime"
            ]
            slot_map = {s: [] for s in slots_order}
            for row in sched_rows:
                slot_name = row["slot"] if row["slot"] in slot_map else "Morning (Empty Stomach)"
                slot_map[slot_name].append({
                    "medicine": row["name"],
                    "take_with_food": row["take_with_food"],
                    "gap_hours": row["min_gap_hours"],
                    "instructions": "Take with a meal/food" if row["take_with_food"] else "Take on empty stomach with water" + (f" (space >={row['min_gap_hours']}h from binders)" if row["min_gap_hours"] > 0 else "")
                })

            # Include food timing guidance if relevant foods selected
            if "Milk / Dairy" in foods or "Calcium Supplements / Antacids" in foods:
                slot_map["Lunch"].append({
                    "medicine": "Dairy / Calcium Intake",
                    "take_with_food": True,
                    "gap_hours": 3,
                    "instructions": "Scheduled at Lunch to allow >=3h separation from morning fluoroquinolones (Ciprofloxacin) / thyroid medications"
                })

            schedule = [{"slot": s, "items": slot_map[s]} for s in slots_order if slot_map[s]]

        return {
            "warnings": warnings,
            "brand_overlaps": brand_overlaps,
            "safe_alternatives": safe_alternatives,
            "schedule": schedule,
            "organ_load": organ_load,
            "graph": {
                "nodes": list(nodes.values()),
                "edges": edges
            },
            "queries_executed": queries_executed
        }
    finally:
        conn.close()

# 5. REVERSE SYMPTOM TRACER
@app.post("/api/trace-symptom")
def trace_symptom(req: SymptomTraceRequest):
    symptom = req.symptom
    meds = req.active_medicines

    if not symptom:
        raise HTTPException(status_code=400, detail="Symptom name is required")

    conn = get_db(read_only=True)
    cur = conn.cursor()
    try:
        if meds:
            q = """
            MATCH (s:Symptom {name: $symptom})<-[r:CAN_CAUSE]-(i:Ingredient)<-[:CONTAINS]-(m:Medicine)
            WHERE m.name IN $meds
            RETURN s.name AS symptom, s.severity AS severity, m.name AS medicine,
                   i.name AS ingredient, r.frequency AS frequency, r.notes AS mechanism
            """
            cur.execute(q, {"symptom": symptom, "meds": meds})
        else:
            q = """
            MATCH (s:Symptom {name: $symptom})<-[r:CAN_CAUSE]-(i:Ingredient)<-[:CONTAINS]-(m:Medicine)
            RETURN s.name AS symptom, s.severity AS severity, m.name AS medicine,
                   i.name AS ingredient, r.frequency AS frequency, r.notes AS mechanism
            LIMIT 15
            """
            cur.execute(q, {"symptom": symptom})

        rows = [dict(r) for r in cur]
        
        # Build mini focused subgraph for symptom trace
        nodes = [{"id": f"sym_{symptom}", "label": "Symptom", "title": symptom, "category": "Symptom"}]
        edges = []
        for r in rows:
            med_id = f"med_{r['medicine']}"
            ing_id = f"ing_{r['ingredient']}"
            if not any(n["id"] == med_id for n in nodes):
                nodes.append({"id": med_id, "label": "Medicine", "title": r["medicine"], "category": "Culprit Medicine"})
            if not any(n["id"] == ing_id for n in nodes):
                nodes.append({"id": ing_id, "label": "Ingredient", "title": r["ingredient"], "category": "Active Ingredient"})
            edges.append({"source": med_id, "target": ing_id, "type": "CONTAINS", "label": "Contains", "severity": "normal"})
            edges.append({"source": ing_id, "target": f"sym_{symptom}", "type": "CAN_CAUSE", "label": r["frequency"], "severity": "conflict", "notes": r["mechanism"]})

        return {
            "symptom": symptom,
            "culprits": rows,
            "count": len(rows),
            "graph": {"nodes": nodes, "edges": edges},
            "query_executed": {"query": q.strip(), "params": {"symptom": symptom, "meds": meds}}
        }
    finally:
        conn.close()

# 6. LIVE CYPHER QUERY INSPECTOR / REPL
@app.post("/api/cypher")
def run_custom_cypher(req: CypherQueryRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Cypher query cannot be empty")
    
    # Restrict write queries via live inspector for safety
    restricted_keywords = ["DROP", "DELETE", "REMOVE", "CREATE CONSTRAINT", "CREATE INDEX"]
    upper_q = query.upper()
    if any(k in upper_q for k in restricted_keywords):
        raise HTTPException(
            status_code=403,
            detail="Modifying DDL/DML (DROP, DELETE, REMOVE) is restricted in live inspector mode to protect persistent store."
        )

    try:
        result = execute_cypher(query, req.params)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 7. ZERO-API-KEY LOCAL AGENT QUERY HANDLER
@app.post("/api/agent")
def agent_query(req: AgentRequest):
    msg = req.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Query message cannot be empty")

    msg_lower = msg.lower()
    meds = req.active_medicines
    foods = req.foods
    conditions = req.conditions

    t0 = time.perf_counter()
    conn = get_db(read_only=True)
    cur = conn.cursor()

    try:
        # Pre-fetch catalog names for fast entity matching
        cur.execute("MATCH (m:Medicine) RETURN m.name AS name, m.generic_name AS generic, m.is_brand AS is_brand")
        all_meds = [dict(r) for r in cur]
        
        cur.execute("MATCH (s:Symptom) RETURN s.name AS name, s.description AS description")
        all_symptoms = [dict(r) for r in cur]

        cur.execute("MATCH (f:Food) RETURN f.name AS name")
        all_foods = [r["name"] for r in cur]

        # 1. CHECK FOR SAFE SWAP / RESOLUTION REQUEST
        if any(w in msg_lower for w in ["make this safe", "how do i fix", "how to resolve", "substitute", "safe alternative", "what should i switch", "how can i make", "how to make"]):
            q_alt = """
            MATCH (alt:Medicine)-[r:SAFE_ALTERNATIVE_TO]->(tgt:Medicine)
            WHERE tgt.name IN $meds
            RETURN alt.name AS alternative, tgt.name AS target, r.reason AS reason, r.target_condition AS condition
            """
            cur.execute(q_alt, {"meds": meds})
            alts = [dict(r) for r in cur]
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            if alts:
                alt = alts[0]
                answer = (
                    f"SafeMeds recommends switching from **{alt['target']}** to **{alt['alternative']}**. "
                    f"{alt['reason']} Click 'Apply Safe Swap' in the right panel to automatically update your regimen!"
                )
                return {
                    "answer": answer,
                    "cypher": q_alt.strip(),
                    "highlight_nodes": [f"med_{alt['alternative']}", f"med_{alt['target']}"],
                    "swap_action": {"replace": alt["target"], "with": alt["alternative"]},
                    "elapsed_ms": elapsed_ms
                }
            else:
                return {
                    "answer": "Your current regimen does not have an active enzyme or direct conflict requiring an immediate alternative swap. All current pathways are within typical parameters.",
                    "cypher": q_alt.strip(),
                    "highlight_nodes": [],
                    "swap_action": None,
                    "elapsed_ms": elapsed_ms
                }

        # 2. CHECK FOR SYMPTOM ADVERSE EFFECT INQUIRY ("Why do I have ...")
        matched_symptom = None
        for s in all_symptoms:
            s_name = s["name"].lower()
            main_words = [w for w in s_name.replace("/", " ").replace("-", " ").split() if len(w) > 3]
            if any(w in msg_lower for w in main_words) or s_name in msg_lower:
                matched_symptom = s["name"]
                break

        if matched_symptom or any(w in msg_lower for w in ["symptom", "pain", "cough", "swelling", "nausea", "headache", "bleeding"]):
            target_sym = matched_symptom or ("Muscle Pain / Myopathy" if "muscle" in msg_lower else ("Persistent Dry Cough" if "cough" in msg_lower else "Stomach Pain / Gastritis"))
            q_sym = """
            MATCH (s:Symptom {name: $symptom})<-[r:CAN_CAUSE]-(i:Ingredient)<-[:CONTAINS]-(m:Medicine)
            WHERE m.name IN $meds
            RETURN s.name AS symptom, m.name AS medicine, i.name AS ingredient, r.frequency AS frequency, r.notes AS mechanism
            """
            cur.execute(q_sym, {"symptom": target_sym, "meds": meds})
            sym_rows = [dict(r) for r in cur]
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            if sym_rows:
                c = sym_rows[0]
                answer = (
                    f"Adverse Symptom Linked: **{c['symptom']}** is a known {c['frequency']} adverse effect of **{c['medicine']}** (active ingredient: *{c['ingredient']}*). "
                    f"Pharmacological mechanism: {c['mechanism']}."
                )
                if "Atorvastatin" in meds and "Grapefruit Juice" in foods and "Muscle" in target_sym:
                    answer += " ⚠️ CRITICAL: Concomitant Grapefruit Juice inhibits CYP3A4, multiplying systemic Atorvastatin blood concentrations and dramatically spiking rhabdomyolysis muscle damage risk!"
                return {
                    "answer": answer,
                    "cypher": q_sym.strip(),
                    "highlight_nodes": [f"med_{c['medicine']}", f"ing_{c['ingredient']}", f"sym_{c['symptom']}"],
                    "swap_action": None,
                    "elapsed_ms": elapsed_ms
                }
            else:
                return {
                    "answer": f"SafeMeds checked '{target_sym}' against your active medications in the Relate graph. None of your currently active drugs directly cause this symptom in their primary profile.",
                    "cypher": q_sym.strip(),
                    "highlight_nodes": [],
                    "swap_action": None,
                    "elapsed_ms": elapsed_ms
                }

        # 3. CHECK FOR CANDIDATE MEDICINE INQUIRY ("Can I add / take ...?")
        candidate_med = None
        for m in all_meds:
            if m["name"].lower() in msg_lower or (m["generic"] and m["generic"].lower() in msg_lower):
                candidate_med = m["name"]
                break

        if candidate_med:
            # Check interaction with active meds
            q_cand_ddi = """
            MATCH (m1:Medicine)-[:CONTAINS]->(i1:Ingredient)-[r:DIRECT_INTERACTION]-(i2:Ingredient)<-[:CONTAINS]-(m2:Medicine)
            WHERE m1.name = $cand AND m2.name IN $meds
            RETURN m1.name AS med1, m2.name AS med2, r.severity AS severity, r.mechanism AS mechanism, r.effect AS effect
            """
            cur.execute(q_cand_ddi, {"cand": candidate_med, "meds": meds})
            ddi_rows = [dict(r) for r in cur]

            q_cand_dd = """
            MATCH (m1:Medicine)-[:CONTAINS]->(i:Ingredient)<-[:CONTAINS]-(m2:Medicine)
            WHERE m1.name = $cand AND m2.name IN $meds
            RETURN m1.name AS med1, m2.name AS med2, i.name AS ingredient
            """
            cur.execute(q_cand_dd, {"cand": candidate_med, "meds": meds})
            dd_rows = [dict(r) for r in cur]

            q_cand_cond = """
            MATCH (m:Medicine)-[:CONTAINS]->(i:Ingredient)-[r:CONTRAINDICATED_IN]->(c:Condition)
            WHERE m.name = $cand AND c.name IN $conditions
            RETURN m.name AS med, c.name AS condition, r.severity AS severity, r.reason AS reason
            """
            cur.execute(q_cand_cond, {"cand": candidate_med, "conditions": conditions})
            cond_rows = [dict(r) for r in cur]

            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

            if dd_rows:
                dd = dd_rows[0]
                answer = f"🚫 ACCIDENTAL OVERDOSE HAZARD: Do not add **{candidate_med}**! It contains the exact same active generic ingredient (*{dd['ingredient']}*) as **{dd['med2']}**, which is already in your regimen."
                return {
                    "answer": answer,
                    "cypher": q_cand_dd.strip(),
                    "highlight_nodes": [f"med_{candidate_med}", f"med_{dd['med2']}"],
                    "swap_action": None,
                    "elapsed_ms": elapsed_ms
                }
            elif ddi_rows:
                ddi = ddi_rows[0]
                answer = f"⚠️ HIGH RISK INTERACTION: Adding **{candidate_med}** creates a {ddi['severity']} collision with **{ddi['med2']}**. Mechanism: {ddi['mechanism']}. Clinical Effect: {ddi['effect']}."
                return {
                    "answer": answer,
                    "cypher": q_cand_ddi.strip(),
                    "highlight_nodes": [f"med_{candidate_med}", f"med_{ddi['med2']}"],
                    "swap_action": None,
                    "elapsed_ms": elapsed_ms
                }
            elif cond_rows:
                co = cond_rows[0]
                answer = f"⚠️ CONTRAINDICATION: **{candidate_med}** is contraindicated in your diagnosed condition **{co['condition']}** ({co['severity']} severity). Reason: {co['reason']}."
                return {
                    "answer": answer,
                    "cypher": q_cand_cond.strip(),
                    "highlight_nodes": [f"med_{candidate_med}", f"cond_{co['condition']}"],
                    "swap_action": None,
                    "elapsed_ms": elapsed_ms
                }
            else:
                answer = f"✅ SAFE TO EVALUATE: **{candidate_med}** has no detected direct collisions, double doses, or contraindications with your current selection in the SafeMeds knowledge graph."
                return {
                    "answer": answer,
                    "cypher": q_cand_ddi.strip(),
                    "highlight_nodes": [f"med_{candidate_med}"],
                    "swap_action": None,
                    "elapsed_ms": elapsed_ms
                }

        # 4. DEFAULT GENERAL QUERY
        q_gen = "MATCH (m:Medicine) WHERE m.name IN $meds RETURN m.name AS name, m.generic_name AS generic"
        cur.execute(q_gen, {"meds": meds})
        active_list = [f"{r['name']} ({r['generic']})" for r in cur]
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        answer = (
            f"SafeMeds graph agent is monitoring {len(meds)} active medications: {', '.join(active_list) if active_list else 'none selected'}. "
            f"Ask about adding a specific medicine (e.g. 'Can I add Ibuprofen?'), investigating an adverse symptom (e.g. 'Why do I have muscle pain?'), or resolving an enzyme conflict."
        )
        return {
            "answer": answer,
            "cypher": q_gen,
            "highlight_nodes": [f"med_{m}" for m in meds],
            "swap_action": None,
            "elapsed_ms": elapsed_ms
        }

    finally:
        conn.close()

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
