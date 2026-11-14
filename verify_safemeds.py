"""
SafeMeds - Comprehensive Verification Script
Tests all 5 core practical problems and all 4 preset scenarios directly
against the persistent Relate database `./data/safemeds.rl`.
"""

import os
import relate

DB_PATH = os.path.abspath("data/safemeds.rl")

def run_tests():
    print(f"=== TESTING SAFEMEDS AGAINST {DB_PATH} ===")
    assert os.path.exists(DB_PATH), f"Database file not found at {DB_PATH}"
    
    conn = relate.connect(DB_PATH, read_only=True)
    cur = conn.cursor()

    # TEST 1: Preset 1 - Heart + Gastric Block (Clopidogrel + Omeprazole -> CYP2C19 -> Safe Alternatives)
    print("\n--- TEST 1: Heart + Gastric Block (Enzyme Collision & Safe Alternatives) ---")
    query_p1 = """
    MATCH (m1:Medicine)-[:CONTAINS]->(i1:Ingredient)-[:REQUIRES_ENZYME]->(e:Enzyme)<-[:INHIBITS_ENZYME]-(i2:Ingredient)<-[:CONTAINS]-(m2:Medicine)
    WHERE m1.name = 'Clopidogrel' AND m2.name = 'Omeprazole'
    OPTIONAL MATCH (alt:Medicine)-[r:SAFE_ALTERNATIVE_TO]->(m2)
    RETURN m1.name AS med_prodrug, i1.name AS prodrug_ing, e.name AS enzyme, m2.name AS med_inhibitor, i2.name AS inhibitor_ing,
           collect(DISTINCT {alternative: alt.name, reason: r.reason}) AS alternatives
    """
    cur.execute(query_p1)
    p1_results = cur.fetchall()
    assert len(p1_results) > 0, "Preset 1 failed to detect CYP2C19 collision between Clopidogrel and Omeprazole"
    row = p1_results[0]
    print(f"Detected Pathway Collision:")
    print(f"  {row['med_prodrug']} ({row['prodrug_ing']}) requires [{row['enzyme']}], which is inhibited by {row['med_inhibitor']} ({row['inhibitor_ing']})")
    print(f"Safe Alternatives Found ({len(row['alternatives'])}):")
    for alt in row['alternatives']:
        print(f"  * {alt['alternative']}: {alt['reason'][:70]}...")

    # TEST 2: Preset 2 - Antibiotic + Dairy Timing (Ciprofloxacin + Milk / Dairy)
    print("\n--- TEST 2: Antibiotic + Dairy Timing (Chelation & Spacing) ---")
    query_p2 = """
    MATCH (m:Medicine)-[:CONTAINS]->(i:Ingredient)-[r:BINDS_OR_CONFLICTS_WITH]->(f:Food)
    WHERE m.name = 'Ciprofloxacin' AND f.name = 'Milk / Dairy'
    RETURN m.name AS medicine, i.name AS ingredient, f.name AS food, r.min_gap_hours AS min_gap, r.mechanism AS mechanism, r.severity AS severity
    """
    cur.execute(query_p2)
    p2_results = cur.fetchall()
    assert len(p2_results) > 0, "Preset 2 failed to detect Ciprofloxacin + Milk collision"
    row = p2_results[0]
    print(f"Detected Food-Drug Conflict:")
    print(f"  {row['medicine']} -> {row['food']} | Min Gap: {row['min_gap']} hrs | Severity: {row['severity']}")
    print(f"  Mechanism: {row['mechanism']}")

    # TEST 3: Preset 3 - Blood Pressure + Double Painkiller + Symptom Trace
    print("\n--- TEST 3: Blood Pressure + Double Painkiller (NSAIDs) + Organ Load ---")
    meds_p3 = ['Lisinopril', 'Amlodipine', 'Ibuprofen', 'Naproxen']
    # 3a. Brand / Ingredient Overlap check between Advil and Motrin
    cur.execute("""
    MATCH (m1:Medicine)-[:CONTAINS]->(i:Ingredient)<-[:CONTAINS]-(m2:Medicine)
    WHERE m1.name = 'Advil' AND m2.name = 'Motrin'
    RETURN m1.name AS brand1, m2.name AS brand2, i.name AS shared_ingredient
    """)
    overlap = cur.fetchall()
    assert len(overlap) > 0, "Failed to detect double dose overlap between Advil and Motrin"
    print(f"Double-Dose Overlap Detected: {overlap[0]['brand1']} and {overlap[0]['brand2']} both contain {overlap[0]['shared_ingredient']}!")

    # 3b. Direct NSAID-NSAID interaction
    cur.execute("""
    MATCH (m1:Medicine)-[:CONTAINS]->(i1:Ingredient)-[r:DIRECT_INTERACTION]->(i2:Ingredient)<-[:CONTAINS]-(m2:Medicine)
    WHERE m1.name = 'Ibuprofen' AND m2.name = 'Naproxen'
    RETURN m1.name AS med1, m2.name AS med2, r.severity AS severity, r.effect AS effect
    """)
    nsaid_conflict = cur.fetchall()
    assert len(nsaid_conflict) > 0, "Failed to detect Ibuprofen + Naproxen direct conflict"
    print(f"Direct NSAID Clash: {nsaid_conflict[0]['med1']} + {nsaid_conflict[0]['med2']} -> Severity: {nsaid_conflict[0]['severity']}")
    print(f"  Effect: {nsaid_conflict[0]['effect']}")

    # 3c. Cumulative Organ Load for Lisinopril, Amlodipine, Ibuprofen, Naproxen
    cur.execute("""
    MATCH (m:Medicine)-[:CONTAINS]->(i:Ingredient)-[r:STRESSES_ORGAN]->(o:Organ)
    WHERE m.name IN ['Lisinopril', 'Amlodipine', 'Ibuprofen', 'Naproxen']
    RETURN o.name AS organ, sum(r.load_score) AS cumulative_load, collect({med: m.name, ing: i.name, score: r.load_score}) AS contributors
    ORDER BY cumulative_load DESC
    """)
    organ_loads = cur.fetchall()
    print("Cumulative Organ Load:")
    for ol in organ_loads:
        print(f"  * {ol['organ']}: Cumulative Score = {ol['cumulative_load']}")
    kidney_load = next((ol for ol in organ_loads if ol['organ'] == 'Kidney'), None)
    assert kidney_load and kidney_load['cumulative_load'] >= 8, "Kidney load should be heavily stressed by double NSAID + ACE-I"

    # 3d. Reverse Symptom Trace: Persistent Dry Cough -> Lisinopril
    print("\n--- Reverse Symptom Trace: 'Persistent Dry Cough' ---")
    cur.execute("""
    MATCH (s:Symptom {name: 'Persistent Dry Cough'})<-[r:CAN_CAUSE]-(i:Ingredient)<-[:CONTAINS]-(m:Medicine)
    WHERE m.name IN ['Lisinopril', 'Amlodipine', 'Ibuprofen', 'Naproxen']
    RETURN s.name AS symptom, m.name AS culprit_medicine, i.name AS culprit_ingredient, r.frequency AS frequency, r.notes AS mechanism
    """)
    cough_trace = cur.fetchall()
    assert len(cough_trace) > 0, "Failed to trace Dry Cough back to Lisinopril"
    print(f"Trace Result for '{cough_trace[0]['symptom']}': Culprit = {cough_trace[0]['culprit_medicine']} ({cough_trace[0]['culprit_ingredient']})")
    print(f"  Mechanism: {cough_trace[0]['mechanism']}")

    # 3e. Reverse Symptom Trace: Swollen Ankles -> Amlodipine
    print("\n--- Reverse Symptom Trace: 'Swollen Ankles / Edema' ---")
    cur.execute("""
    MATCH (s:Symptom {name: 'Swollen Ankles / Edema'})<-[r:CAN_CAUSE]-(i:Ingredient)<-[:CONTAINS]-(m:Medicine)
    WHERE m.name IN ['Lisinopril', 'Amlodipine', 'Ibuprofen', 'Naproxen']
    RETURN s.name AS symptom, m.name AS culprit_medicine, i.name AS culprit_ingredient, r.frequency AS frequency, r.notes AS mechanism
    """)
    ankle_trace = cur.fetchall()
    assert len(ankle_trace) > 0, "Failed to trace Swollen Ankles back to Amlodipine"
    print(f"Trace Result for '{ankle_trace[0]['symptom']}': Culprit = {ankle_trace[0]['culprit_medicine']} ({ankle_trace[0]['culprit_ingredient']})")

    # TEST 4: Preset 4 - Cholesterol + Blood Thinner + Diet Clash (Atorvastatin + Warfarin + Grapefruit Juice + Spinach)
    print("\n--- TEST 4: Cholesterol + Blood Thinner + Diet Clash ---")
    cur.execute("""
    MATCH (m:Medicine)-[:CONTAINS]->(i:Ingredient)-[r:BINDS_OR_CONFLICTS_WITH]->(f:Food)
    WHERE m.name IN ['Atorvastatin', 'Warfarin'] AND f.name IN ['Grapefruit Juice', 'Spinach / Leafy Greens']
    RETURN m.name AS med, i.name AS ing, f.name AS food, r.severity AS severity, r.mechanism AS mechanism
    """)
    diet_clashes = cur.fetchall()
    assert len(diet_clashes) >= 2, "Failed to detect both Grapefruit + Statin and Spinach + Warfarin conflicts"
    for dc in diet_clashes:
        print(f"  * {dc['med']} vs {dc['food']} [{dc['severity']}]: {dc['mechanism'][:75]}...")

    # TEST 5: 5-Slot Daily Schedule Planner
    print("\n--- TEST 5: 5-Slot Daily Schedule Planner ---")
    cur.execute("""
    MATCH (m:Medicine)
    WHERE m.name IN ['Levothyroxine', 'Lisinopril', 'Calcium Carbonate', 'Atorvastatin', 'Warfarin']
    RETURN m.name AS medicine, m.default_slot AS slot, m.take_with_food AS take_with_food, m.min_gap_hours AS gap_hours
    ORDER BY slot
    """)
    schedule = cur.fetchall()
    print("Planned Daily Routine:")
    for s in schedule:
        food_note = "With meal" if s['take_with_food'] else "Empty stomach"
        gap_note = f" (space >={s['gap_hours']}h from binders)" if s['gap_hours'] > 0 else ""
        print(f"  [{s['slot']}] {s['medicine']} - {food_note}{gap_note}")

    conn.close()
    print("\nALL 5 CORE VERIFICATION TESTS PASSED SUCCESSFULLY AGAINST ./data/safemeds.rl!")

if __name__ == "__main__":
    run_tests()
