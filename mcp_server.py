"""
SafeMeds - MCP (Model Context Protocol) & AI Agent Server
Exposes SafeMeds Relate graph operations as high-level tools for AI agents.
"""

import os
import json
import relate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "safemeds.rl")

def query_graph(cypher: str, params: dict = None):
    """Executes a read-only Cypher query against the persistent Relate database."""
    conn = relate.connect(DB_PATH, read_only=True)
    cur = conn.cursor()
    try:
        if params:
            cur.execute(cypher, params)
        else:
            cur.execute(cypher)
        return [dict(r) for r in cur]
    finally:
        conn.close()

def check_medication_safety(medicines: list, foods: list = None, conditions: list = None):
    """Analyzes a patient's regimen for enzyme blocks, double-doses, food clashes, and organ loads."""
    foods = foods or []
    conditions = conditions or []

    results = {
        "enzyme_blocks": query_graph("""
            MATCH (m1:Medicine)-[:CONTAINS]->(i1:Ingredient)-[:REQUIRES_ENZYME]->(e:Enzyme)<-[:INHIBITS_ENZYME]-(i2:Ingredient)<-[:CONTAINS]-(m2:Medicine)
            WHERE m1.name IN $meds AND m2.name IN $meds AND m1.name <> m2.name
            OPTIONAL MATCH (alt:Medicine)-[r:SAFE_ALTERNATIVE_TO]->(m2)
            RETURN m1.name AS prodrug, e.name AS blocked_enzyme, m2.name AS inhibitor,
                   collect(DISTINCT {alt: alt.name, reason: r.reason}) AS safe_alternatives
        """, {"meds": medicines}),
        
        "double_doses": query_graph("""
            MATCH (m1:Medicine)-[:CONTAINS]->(i:Ingredient)<-[:CONTAINS]-(m2:Medicine)
            WHERE m1.name IN $meds AND m2.name IN $meds AND m1.name < m2.name
            RETURN m1.name AS med1, m2.name AS med2, i.name AS active_ingredient
        """, {"meds": medicines}),

        "food_conflicts": query_graph("""
            MATCH (m:Medicine)-[:CONTAINS]->(i:Ingredient)-[r:BINDS_OR_CONFLICTS_WITH]->(f:Food)
            WHERE m.name IN $meds AND f.name IN $foods
            RETURN m.name AS med, f.name AS food, r.min_gap_hours AS min_gap, r.mechanism AS mechanism
        """, {"meds": medicines, "foods": foods}) if foods else [],

        "condition_contraindications": query_graph("""
            MATCH (m:Medicine)-[:CONTAINS]->(i:Ingredient)-[r:CONTRAINDICATED_IN]->(c:Condition)
            WHERE m.name IN $meds AND c.name IN $conds
            RETURN m.name AS med, c.name AS condition, r.severity AS severity, r.reason AS reason
        """, {"meds": medicines, "conds": conditions}) if conditions else [],

        "organ_stress": query_graph("""
            MATCH (m:Medicine)-[:CONTAINS]->(i:Ingredient)-[r:STRESSES_ORGAN]->(o:Organ)
            WHERE m.name IN $meds
            RETURN o.name AS organ, sum(r.load_score) AS cumulative_load
            ORDER BY cumulative_load DESC
        """, {"meds": medicines})
    }
    return results

def trace_symptom_backwards(symptom: str, active_meds: list = None):
    """Traces a symptom backwards through the graph to pinpoint culprit medicines."""
    active_meds = active_meds or []
    if active_meds:
        q = """
        MATCH (s:Symptom {name: $symptom})<-[r:CAN_CAUSE]-(i:Ingredient)<-[:CONTAINS]-(m:Medicine)
        WHERE m.name IN $meds
        RETURN m.name AS culprit_medicine, i.name AS active_ingredient, r.frequency AS frequency, r.notes AS mechanism
        """
        return query_graph(q, {"symptom": symptom, "meds": active_meds})
    else:
        q = """
        MATCH (s:Symptom {name: $symptom})<-[r:CAN_CAUSE]-(i:Ingredient)<-[:CONTAINS]-(m:Medicine)
        RETURN m.name AS culprit_medicine, i.name AS active_ingredient, r.frequency AS frequency, r.notes AS mechanism
        LIMIT 10
        """
        return query_graph(q, {"symptom": symptom})

if __name__ == "__main__":
    print("Testing SafeMeds MCP Tool definitions...")
    test_res = check_medication_safety(["Clopidogrel", "Omeprazole"], foods=["Milk / Dairy"], conditions=["Gastric Ulcer / GERD"])
    print(json.dumps(test_res, indent=2))
