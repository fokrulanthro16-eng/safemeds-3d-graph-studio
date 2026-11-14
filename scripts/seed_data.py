"""
SafeMeds - Relate Database Seeding Script
Populates `./data/safemeds.rl` with accurate pharmacological data:
- Medicines (brand + generic pairs)
- Active ingredients
- CYP Enzymes
- Foods / dietary agents
- Health conditions
- Target organs
- Clinical symptoms
- Safe alternatives
"""

import os
import sys
import relate

def seed_database(db_path: str):
    print(f"Connecting to Relate store at: {db_path}")
    
    # If store exists, remove it to ensure clean deterministic seed
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("Cleaned existing database file for deterministic rebuild.")
        except Exception as e:
            print(f"Note: Could not remove existing db file ({e}), continuing with MERGE...")

    conn = relate.connect(db_path)
    cur = conn.cursor()

    # Create constraints & indexes
    print("Creating constraints and indexes...")
    constraints = [
        "CREATE CONSTRAINT c_med FOR (m:Medicine) REQUIRE m.name IS UNIQUE",
        "CREATE CONSTRAINT c_ing FOR (i:Ingredient) REQUIRE i.name IS UNIQUE",
        "CREATE CONSTRAINT c_enz FOR (e:Enzyme) REQUIRE e.name IS UNIQUE",
        "CREATE CONSTRAINT c_food FOR (f:Food) REQUIRE f.name IS UNIQUE",
        "CREATE CONSTRAINT c_cond FOR (c:Condition) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT c_org FOR (o:Organ) REQUIRE o.name IS UNIQUE",
        "CREATE CONSTRAINT c_sym FOR (s:Symptom) REQUIRE s.name IS UNIQUE"
    ]
    for c in constraints:
        try:
            cur.execute(c)
        except Exception as e:
            print(f"Constraint notice ({c[:30]}...): {e}")

    # 1. ENZYMES
    enzymes = [
        ("CYP2C19", "Liver enzyme responsible for activating prodrugs like clopidogrel and metabolizing PPIs"),
        ("CYP3A4", "Major hepatic and intestinal enzyme metabolizing ~50% of therapeutic drugs including statins"),
        ("CYP2C9", "Principal enzyme metabolizing narrow-therapeutic index drugs like warfarin and NSAIDs"),
        ("CYP2D6", "Enzyme metabolizing beta-blockers, antidepressants, and activating codeine/tramadol"),
        ("CYP1A2", "Hepatic enzyme metabolizing caffeine, theophylline, and clozapine; induced by tobacco")
    ]
    for name, desc in enzymes:
        cur.execute(
            "MERGE (e:Enzyme {name: $name}) SET e.description = $desc",
            {"name": name, "desc": desc}
        )

    # 2. FOODS
    foods = [
        ("Milk / Dairy", "Dairy", "High calcium content forms insoluble chelation complexes with tetracyclines and fluoroquinolones"),
        ("Grapefruit Juice", "Fruit", "Potent intestinal CYP3A4 inhibitor; spikes bio-availability of statins and calcium blockers to toxic levels"),
        ("Spinach / Leafy Greens", "Vegetable", "Rich in Vitamin K; antagonizes warfarin anticoagulation mechanism"),
        ("Coffee / Caffeine", "Beverage", "CNS stimulant and mild diuretic; competitive CYP1A2 substrate"),
        ("Alcohol", "Beverage", "CNS depressant, gastric mucosal irritant, and acute CYP2E1 competitive inhibitor"),
        ("High-Fat Meal", "Food", "Alters gastric emptying rate and lipidic absorption kinetics"),
        ("Aged Cheese (Tyramine)", "Food", "High tyramine content; severe hypertensive crisis with MAO inhibitors"),
        ("Licorice (Glycyrrhizin)", "Confectionery", "Pseudoaldosteronism effect causing potassium loss and hypertension"),
        ("Calcium Supplements / Antacids", "Supplement", "Polyvalent cation binding; elevates gastric pH reducing acidic drug dissolution"),
        ("Iron Supplements", "Supplement", "Chelates antibiotics and thyroid hormones in GI tract"),
        ("St. John's Wort", "Herbal", "Potent CYP3A4 and P-gp inducer; drops drug concentrations drastically"),
        ("Green Tea", "Beverage", "Contains Vitamin K and epigallocatechin gallate; inhibits OATP1A2 uptake")
    ]
    for name, cat, notes in foods:
        cur.execute(
            "MERGE (f:Food {name: $name}) SET f.category = $cat, f.notes = $notes",
            {"name": name, "cat": cat, "notes": notes}
        )

    # 3. CONDITIONS
    conditions = [
        ("Gastric Ulcer / GERD", "Gastrointestinal"),
        ("Chronic Kidney Disease", "Renal"),
        ("Liver Impairment", "Hepatic"),
        ("Hypertension", "Cardiovascular"),
        ("Atrial Fibrillation", "Cardiovascular"),
        ("Heart Failure", "Cardiovascular"),
        ("Asthma / Bronchospasm", "Respiratory"),
        ("Diabetes Type 2", "Endocrine"),
        ("Gout / Hyperuricemia", "Metabolic"),
        ("Bleeding Risk / Thrombocytopenia", "Hematologic")
    ]
    for name, cat in conditions:
        cur.execute(
            "MERGE (c:Condition {name: $name}) SET c.category = $cat",
            {"name": name, "cat": cat}
        )

    # 4. ORGANS
    organs = [
        ("Kidney", "Renal clearance, glomerular filtration, and electrolyte balance"),
        ("Liver", "Hepatic biotransformation, enzymatic metabolism, and biliary excretion"),
        ("Stomach / GI", "Gastric mucosal barrier, digestion, and acid secretion"),
        ("Brain / CNS", "Neurotransmitter modulation, cognitive function, and psychomotor control")
    ]
    for name, desc in organs:
        cur.execute(
            "MERGE (o:Organ {name: $name}) SET o.description = $desc",
            {"name": name, "desc": desc}
        )

    # 5. SYMPTOMS
    symptoms = [
        ("Persistent Dry Cough", "Moderate", "Chronic non-productive tickling cough refractory to antitussives"),
        ("Swollen Ankles / Edema", "Moderate", "Bilateral peripheral fluid retention in lower extremities"),
        ("Muscle Pain / Myopathy", "High", "Symmetric diffuse muscle aching, weakness, or tenderness"),
        ("Dizziness / Lightheadedness", "Moderate", "Orthostatic sensation of unsteadiness or near-syncope"),
        ("Stomach Pain / Gastritis", "High", "Epigastric burning, dyspepsia, or mucosal ulceration"),
        ("Bruising / Bleeding", "Severe", "Spontaneous subcutaneous hematomas or petechiae"),
        ("Headache", "Low", "Frontal or throbbing cephalalgia"),
        ("Nausea / Vomiting", "Moderate", "Upper gastrointestinal malaise or emesis"),
        ("Insomnia", "Moderate", "Difficulty initiating or maintaining restorative sleep"),
        ("Constipation", "Low", "Decreased bowel movement frequency or hard stool consistency"),
        ("Tinnitus / Ringing in Ears", "Moderate", "Perception of ringing or buzzing acoustic noise"),
        ("Fatigue / Lethargy", "Low", "Persistent exhaustion unaffected by rest"),
        ("Heart Palpitations", "High", "Sensation of racing, pounding, or fluttering heartbeat"),
        ("Dry Mouth / Xerostomia", "Low", "Salivary hypofunction and oral mucosal dryness"),
        ("Tremors", "Moderate", "Involuntary rhythmic muscle contraction and relaxation")
    ]
    for name, sev, desc in symptoms:
        cur.execute(
            "MERGE (s:Symptom {name: $name}) SET s.severity = $sev, s.description = $desc",
            {"name": name, "sev": sev, "desc": desc}
        )

    # 6. INGREDIENTS
    # (name, desc, requires_enz, inhibits_enz, stresses_organs, causes_symptoms, contraindications)
    ingredients_data = [
        {
            "name": "Clopidogrel",
            "desc": "Thienopyridine P2Y12 antiplatelet prodrug requiring two-step hepatic CYP activation",
            "requires_enz": ["CYP2C19"],
            "inhibits_enz": [],
            "stresses": [("Stomach / GI", 2, "Mild mucosal irritation, bleeding tendency"), ("Liver", 2, "Metabolic processing")],
            "symptoms": [("Bruising / Bleeding", "Common", "Inhibited platelet aggregation"), ("Stomach Pain / Gastritis", "Occasional", "Gastric discomfort")],
            "contraindicated": [("Bleeding Risk / Thrombocytopenia", "Severe", "Contraindicated during active pathological bleeding")]
        },
        {
            "name": "Omeprazole",
            "desc": "Proton pump inhibitor that blocks H+/K+ ATPase enzyme and strongly inhibits CYP2C19",
            "requires_enz": [],
            "inhibits_enz": ["CYP2C19"],
            "stresses": [("Kidney", 2, "Rare interstitial nephritis risk"), ("Stomach / GI", 1, "Hypochlorhydria with long-term use")],
            "symptoms": [("Headache", "Common", "Vasodilatory cranial response"), ("Nausea / Vomiting", "Occasional", "Transient altered gastric motility"), ("Constipation", "Occasional", "Altered digestion")],
            "contraindicated": []
        },
        {
            "name": "Pantoprazole",
            "desc": "Proton pump inhibitor with low affinity for CYP2C19, making it a safer PPI co-prescription",
            "requires_enz": [],
            "inhibits_enz": [],
            "stresses": [("Stomach / GI", 1, "Hypochlorhydria")],
            "symptoms": [("Headache", "Occasional", "Transient cephalalgia")],
            "contraindicated": []
        },
        {
            "name": "Famotidine",
            "desc": "Histamine H2-receptor antagonist for gastric acid suppression with zero CYP2C19 inhibition",
            "requires_enz": [],
            "inhibits_enz": [],
            "stresses": [("Kidney", 1, "Renally cleared")],
            "symptoms": [("Headache", "Occasional", "Mild headache"), ("Dizziness / Lightheadedness", "Occasional", "Rare CNS effect")],
            "contraindicated": []
        },
        {
            "name": "Ciprofloxacin",
            "desc": "Fluoroquinolone broad-spectrum bactericidal antibiotic that binds polyvalent cations",
            "requires_enz": [],
            "inhibits_enz": ["CYP1A2"],
            "stresses": [("Kidney", 3, "Glomerular filtration stress, crystalluria in alkaline urine"), ("Brain / CNS", 2, "GABA inhibition, neurotoxicity risk")],
            "symptoms": [("Nausea / Vomiting", "Common", "Direct gastric irritation"), ("Dizziness / Lightheadedness", "Occasional", "CNS GABAergic antagonism"), ("Insomnia", "Occasional", "CNS agitation")],
            "contraindicated": [("Asthma / Bronchospasm", "Moderate", "Rare hypersensitivity bronchospasm")]
        },
        {
            "name": "Lisinopril",
            "desc": "Angiotensin-converting enzyme (ACE) inhibitor; impairs bradykinin degradation",
            "requires_enz": [],
            "inhibits_enz": [],
            "stresses": [("Kidney", 2, "Hemodynamic reduction in glomerular filtration pressure")],
            "symptoms": [("Persistent Dry Cough", "Common", "Pulmonary bradykinin and substance P accumulation"), ("Dizziness / Lightheadedness", "Common", "Orthostatic blood pressure drop")],
            "contraindicated": [("Chronic Kidney Disease", "Moderate", "Hyperkalemia and acute GFR reduction in bilateral renal artery stenosis")]
        },
        {
            "name": "Amlodipine",
            "desc": "Dihydropyridine calcium channel blocker inhibiting calcium ion influx in vascular smooth muscle",
            "requires_enz": ["CYP3A4"],
            "inhibits_enz": [],
            "stresses": [("Liver", 2, "Extensively metabolized by hepatic CYP3A4")],
            "symptoms": [("Swollen Ankles / Edema", "Common", "Selective precapillary arteriolar vasodilation"), ("Dizziness / Lightheadedness", "Common", "Peripheral vasodilatory hypotension"), ("Headache", "Occasional", "Cerebral vasodilation")],
            "contraindicated": [("Heart Failure", "Moderate", "May worsen peripheral edema")]
        },
        {
            "name": "Ibuprofen",
            "desc": "Non-steroidal anti-inflammatory drug (NSAID) non-selectively inhibiting COX-1 and COX-2 enzymes",
            "requires_enz": ["CYP2C9"],
            "inhibits_enz": [],
            "stresses": [("Kidney", 4, "Blunts vasodilatory renal prostaglandins; decreases renal perfusion"), ("Stomach / GI", 4, "Suppresses protective gastric prostaglandins, causing ulcers and bleeding")],
            "symptoms": [("Stomach Pain / Gastritis", "Common", "Gastric mucosal barrier disruption"), ("Nausea / Vomiting", "Occasional", "Gastric dyspepsia"), ("Heart Palpitations", "Occasional", "Fluid retention and BP elevation")],
            "contraindicated": [
                ("Gastric Ulcer / GERD", "Severe", "Exacerbates active peptic ulceration and promotes hemorrhage"),
                ("Chronic Kidney Disease", "Severe", "Induces acute kidney injury via renal vasoconstriction"),
                ("Hypertension", "High", "Causes sodium and water retention, neutralizing antihypertensive drugs"),
                ("Bleeding Risk / Thrombocytopenia", "High", "Reversible platelet COX-1 inhibition impairs clotting")
            ]
        },
        {
            "name": "Naproxen",
            "desc": "Long-acting non-steroidal anti-inflammatory drug (NSAID) with potent COX inhibition",
            "requires_enz": ["CYP2C9"],
            "inhibits_enz": [],
            "stresses": [("Kidney", 4, "Renal prostaglandin inhibition leading to acute interstitial nephritis or GFR drop"), ("Stomach / GI", 4, "Direct mucosal toxicity and mucosal barrier erosion")],
            "symptoms": [("Stomach Pain / Gastritis", "Common", "Direct gastric irritation and ulcerogenic potential"), ("Headache", "Occasional", "Mild vascular reaction"), ("Bruising / Bleeding", "Occasional", "Impaired primary hemostasis")],
            "contraindicated": [
                ("Gastric Ulcer / GERD", "Severe", "High ulcer and gastrointestinal hemorrhage hazard"),
                ("Chronic Kidney Disease", "Severe", "Worsens renal failure and causes hyperkalemia"),
                ("Hypertension", "High", "Elevates systemic vascular resistance"),
                ("Bleeding Risk / Thrombocytopenia", "High", "Inhibits platelet aggregation")
            ]
        },
        {
            "name": "Acetaminophen",
            "desc": "Central analgesic and antipyretic without peripheral anti-inflammatory or antiplatelet activity",
            "requires_enz": ["CYP2E1"],
            "inhibits_enz": [],
            "stresses": [("Liver", 3, "Toxic NAPQI metabolite formation upon glutathione depletion")],
            "symptoms": [("Nausea / Vomiting", "Occasional", "Rare mild gastric distress")],
            "contraindicated": [("Liver Impairment", "Severe", "High risk of fatal hepatic necrosis")]
        },
        {
            "name": "Atorvastatin",
            "desc": "HMG-CoA reductase inhibitor (statin) heavily cleared by CYP3A4",
            "requires_enz": ["CYP3A4"],
            "inhibits_enz": [],
            "stresses": [("Liver", 2, "Transaminase elevation"), ("Kidney", 1, "Myoglobinuria stress during rhabdomyolysis")],
            "symptoms": [("Muscle Pain / Myopathy", "Common", "Mitochondrial coenzyme Q10 depletion and myotoxicity"), ("Fatigue / Lethargy", "Occasional", "Cellular energy deficit"), ("Headache", "Occasional", "Mild cranial vascular effect")],
            "contraindicated": [("Liver Impairment", "Severe", "Active liver disease is absolute contraindication")]
        },
        {
            "name": "Warfarin",
            "desc": "Vitamin K epoxide reductase inhibitor anticoagulant with narrow therapeutic window",
            "requires_enz": ["CYP2C9"],
            "inhibits_enz": [],
            "stresses": [("Liver", 2, "Hepatic synthesis modulation"), ("Stomach / GI", 2, "GI bleeding vulnerability")],
            "symptoms": [("Bruising / Bleeding", "Common", "Depression of functional factors II, VII, IX, X"), ("Stomach Pain / Gastritis", "Occasional", "Occult GI bleeding")],
            "contraindicated": [("Bleeding Risk / Thrombocytopenia", "Severe", "Lethal hemorrhage risk")]
        },
        {
            "name": "Metformin",
            "desc": "Biguanide antihyperglycemic agent that reduces hepatic glucose production",
            "requires_enz": [],
            "inhibits_enz": [],
            "stresses": [("Kidney", 3, "Exclusively renally eliminated; lactic acidosis risk in renal failure"), ("Stomach / GI", 3, "Frequent gastrointestinal intolerance")],
            "symptoms": [("Nausea / Vomiting", "Common", "GI dysmotility and mucosal irritation"), ("Stomach Pain / Gastritis", "Common", "Abdominal cramping and diarrhea")],
            "contraindicated": [("Chronic Kidney Disease", "Severe", "High risk of fatal metformin-associated lactic acidosis (MALA)")]
        },
        {
            "name": "Levothyroxine",
            "desc": "Synthetic T4 thyroid hormone with absorption vulnerable to binding agents in gut",
            "requires_enz": [],
            "inhibits_enz": [],
            "stresses": [("Brain / CNS", 1, "Thyroid hormone level sensitivity")],
            "symptoms": [("Heart Palpitations", "Occasional", "Thyrotoxic adrenergic stimulation"), ("Insomnia", "Occasional", "CNS hyperactivation")],
            "contraindicated": []
        },
        {
            "name": "Metoprolol",
            "desc": "Cardioselective beta-1 adrenergic receptor blocker metabolized by CYP2D6",
            "requires_enz": ["CYP2D6"],
            "inhibits_enz": [],
            "stresses": [("Brain / CNS", 2, "Lipophilic crossing of blood-brain barrier")],
            "symptoms": [("Fatigue / Lethargy", "Common", "Decreased cardiac output and peripheral perfusion"), ("Dizziness / Lightheadedness", "Common", "Bradycardia and hypotension"), ("Insomnia", "Occasional", "Suppression of nocturnal melatonin secretion")],
            "contraindicated": [("Asthma / Bronchospasm", "High", "May cause bronchoconstriction at higher doses"), ("Heart Failure", "Moderate", "Requires careful titration during acute decompensation")]
        },
        {
            "name": "Losartan",
            "desc": "Angiotensin II receptor blocker (ARB) activated by CYP2C9; alternative to ACE inhibitors",
            "requires_enz": ["CYP2C9"],
            "inhibits_enz": [],
            "stresses": [("Kidney", 2, "Renal hemodynamics")],
            "symptoms": [("Dizziness / Lightheadedness", "Common", "Antihypertensive vasodilation")],
            "contraindicated": [("Chronic Kidney Disease", "Moderate", "Hyperkalemia monitoring required")]
        },
        {
            "name": "Diphenhydramine",
            "desc": "First-generation anticholinergic antihistamine with potent sedative CNS activity",
            "requires_enz": ["CYP2D6"],
            "inhibits_enz": ["CYP2D6"],
            "stresses": [("Brain / CNS", 4, "Strong central anticholinergic and H1 blockade"), ("Kidney", 2, "Urinary retention risk")],
            "symptoms": [("Fatigue / Lethargy", "Common", "Central sedation and cognitive dulling"), ("Dry Mouth / Xerostomia", "Common", "Muscarinic cholinergic receptor blockade"), ("Constipation", "Common", "Suppressed bowel motility"), ("Dizziness / Lightheadedness", "Occasional", "Vestibular and sedative effect")],
            "contraindicated": []
        },
        {
            "name": "Fluoxetine",
            "desc": "Selective serotonin reuptake inhibitor (SSRI) and potent inhibitor of CYP2D6 and CYP2C19",
            "requires_enz": [],
            "inhibits_enz": ["CYP2D6", "CYP2C19"],
            "stresses": [("Brain / CNS", 3, "Central serotonergic modulation"), ("Liver", 2, "Hepatic elimination")],
            "symptoms": [("Insomnia", "Common", "CNS activation"), ("Nausea / Vomiting", "Common", "Enteric serotonin receptor stimulation"), ("Tremors", "Occasional", "Serotonergic neuromuscular hyperactivity"), ("Headache", "Occasional", "Vascular tone fluctuation")],
            "contraindicated": []
        },
        {
            "name": "Tramadol",
            "desc": "Dual-action weak opioid agonist and SNRI prodrug activated by CYP2D6",
            "requires_enz": ["CYP2D6"],
            "inhibits_enz": [],
            "stresses": [("Brain / CNS", 4, "Opioid and monoaminergic CNS depression"), ("Stomach / GI", 2, "Slows peristalsis")],
            "symptoms": [("Nausea / Vomiting", "Common", "Chemoreceptor trigger zone stimulation"), ("Dizziness / Lightheadedness", "Common", "CNS depression and hypotension"), ("Constipation", "Common", "Mu-opioid enteric hypomotility"), ("Fatigue / Lethargy", "Common", "Central sedation")],
            "contraindicated": [("Asthma / Bronchospasm", "Moderate", "Respiratory depression risk")]
        },
        {
            "name": "Aspirin",
            "desc": "Irreversible COX-1 and COX-2 inhibitor acetylating platelet cyclooxygenase",
            "requires_enz": [],
            "inhibits_enz": [],
            "stresses": [("Stomach / GI", 4, "Direct acidic irritation and complete suppression of protective prostaglandins"), ("Kidney", 2, "Renal blood flow reduction")],
            "symptoms": [("Bruising / Bleeding", "Common", "Irreversible 7-10 day antiplatelet effect"), ("Stomach Pain / Gastritis", "Common", "Gastroduodenal erosions"), ("Tinnitus / Ringing in Ears", "Occasional", "Salicylate cochlear toxicity at high doses")],
            "contraindicated": [
                ("Gastric Ulcer / GERD", "Severe", "Precipitates severe gastrointestinal bleeding"),
                ("Bleeding Risk / Thrombocytopenia", "Severe", "Prolongs bleeding time markedly"),
                ("Gout / Hyperuricemia", "Moderate", "Low doses decrease renal uric acid excretion")
            ]
        },
        {
            "name": "Rosuvastatin",
            "desc": "Hydrophilic HMG-CoA reductase inhibitor primarily eliminated non-CYP3A4 (CYP2C9 minor)",
            "requires_enz": [],
            "inhibits_enz": [],
            "stresses": [("Liver", 2, "Hepatic uptake via OATP1B1"), ("Kidney", 2, "Renal excretion fraction")],
            "symptoms": [("Muscle Pain / Myopathy", "Occasional", "Statin class myotoxicity"), ("Headache", "Occasional", "Mild cephalalgia")],
            "contraindicated": [("Liver Impairment", "Severe", "Active hepatic disease")]
        },
        {
            "name": "Apixaban",
            "desc": "Direct factor Xa inhibitor anticoagulant cleared by CYP3A4 and P-glycoprotein",
            "requires_enz": ["CYP3A4"],
            "inhibits_enz": [],
            "stresses": [("Kidney", 2, "27% renal clearance"), ("Stomach / GI", 2, "GI bleeding")],
            "symptoms": [("Bruising / Bleeding", "Common", "Direct factor Xa suppression"), ("Nausea / Vomiting", "Occasional", "Mild dyspepsia")],
            "contraindicated": [("Bleeding Risk / Thrombocytopenia", "Severe", "Active pathological bleeding")]
        },
        {
            "name": "Gabapentin",
            "desc": "Voltage-gated calcium channel alpha-2-delta ligand cleared purely by renal excretion",
            "requires_enz": [],
            "inhibits_enz": [],
            "stresses": [("Kidney", 3, "100% renal elimination; accumulates severely in renal dysfunction"), ("Brain / CNS", 3, "Central CNS sedative depression")],
            "symptoms": [("Dizziness / Lightheadedness", "Common", "Central nervous system suppression"), ("Fatigue / Lethargy", "Common", "Sedation and somnolence"), ("Swollen Ankles / Edema", "Occasional", "Vasodilation-induced peripheral edema")],
            "contraindicated": [("Chronic Kidney Disease", "Moderate", "Requires mandatory dose reduction")]
        },
        {
            "name": "Prednisone",
            "desc": "Systemic corticosteroid prodrug converted by liver 11-beta-HSD to active prednisolone",
            "requires_enz": [],
            "inhibits_enz": [],
            "stresses": [("Stomach / GI", 3, "Synergistic ulceration risk with NSAIDs"), ("Brain / CNS", 2, "Mood instability"), ("Kidney", 2, "Fluid and sodium retention")],
            "symptoms": [("Insomnia", "Common", "CNS arousal"), ("Stomach Pain / Gastritis", "Common", "Gastric mucosal irritation"), ("Swollen Ankles / Edema", "Common", "Mineralocorticoid fluid retention")],
            "contraindicated": [("Diabetes Type 2", "High", "Markedly induces hepatic gluconeogenesis and insulin resistance"), ("Gastric Ulcer / GERD", "High", "Impairs ulcer healing")]
        },
        {
            "name": "Calcium Carbonate",
            "desc": "Oral calcium salt that binds phosphorus and divalent cations; elevates gastric pH",
            "requires_enz": [],
            "inhibits_enz": [],
            "stresses": [("Stomach / GI", 1, "Constipation, acid rebound"), ("Kidney", 2, "Hypercalciuria and nephrolithiasis risk")],
            "symptoms": [("Constipation", "Common", "Reduced intestinal peristalsis"), ("Stomach Pain / Gastritis", "Occasional", "Acid rebound dyspepsia")],
            "contraindicated": []
        }
    ]

    for ing in ingredients_data:
        cur.execute(
            "MERGE (i:Ingredient {name: $name}) SET i.description = $desc",
            {"name": ing["name"], "desc": ing["desc"]}
        )
        for enz in ing["requires_enz"]:
            cur.execute(
                "MATCH (i:Ingredient {name: $ing}), (e:Enzyme {name: $enz}) MERGE (i)-[:REQUIRES_ENZYME]->(e)",
                {"ing": ing["name"], "enz": enz}
            )
        for enz in ing["inhibits_enz"]:
            cur.execute(
                "MATCH (i:Ingredient {name: $ing}), (e:Enzyme {name: $enz}) MERGE (i)-[:INHIBITS_ENZYME {potency: 'Strong'}]->(e)",
                {"ing": ing["name"], "enz": enz}
            )
        for org, score, notes in ing["stresses"]:
            cur.execute(
                "MATCH (i:Ingredient {name: $ing}), (o:Organ {name: $org}) MERGE (i)-[:STRESSES_ORGAN {load_score: $score, notes: $notes}]->(o)",
                {"ing": ing["name"], "org": org, "score": score, "notes": notes}
            )
        for sym, freq, notes in ing["symptoms"]:
            cur.execute(
                "MATCH (i:Ingredient {name: $ing}), (s:Symptom {name: $sym}) MERGE (i)-[:CAN_CAUSE {frequency: $freq, notes: $notes}]->(s)",
                {"ing": ing["name"], "sym": sym, "freq": freq, "notes": notes}
            )
        for cond, sev, reason in ing["contraindicated"]:
            cur.execute(
                "MATCH (i:Ingredient {name: $ing}), (c:Condition {name: $cond}) MERGE (i)-[:CONTRAINDICATED_IN {severity: $sev, reason: $reason}]->(c)",
                {"ing": ing["name"], "cond": cond, "sev": sev, "reason": reason}
            )

    # 7. FOOD INTERACTIONS
    food_interactions = [
        ("Ciprofloxacin", "Milk / Dairy", 3, "High", "Polyvalent Ca2+ cations chelate fluoroquinolones, cutting GI absorption by up to 85%"),
        ("Ciprofloxacin", "Calcium Supplements / Antacids", 3, "High", "Calcium carbonate severely chelates ciprofloxacin molecules, eliminating antibiotic efficacy"),
        ("Ciprofloxacin", "Coffee / Caffeine", 2, "Moderate", "Ciprofloxacin inhibits CYP1A2, elevating serum caffeine levels up to 300% causing tachycardia"),
        ("Atorvastatin", "Grapefruit Juice", 4, "High", "Intestinal CYP3A4 inhibition increases statin AUC by 250-400%, precipitating rhabdomyolysis and severe myopathy"),
        ("Warfarin", "Spinach / Leafy Greens", 4, "High", "High dietary Vitamin K1 directly circumvents vitamin K epoxide reductase inhibition, crashing INR and increasing stroke/clot risk"),
        ("Warfarin", "Alcohol", 4, "High", "Acute ingestion competitively inhibits warfarin breakdown (raising INR and bleed risk); chronic use induces metabolism (lowering INR)"),
        ("Metformin", "Alcohol", 4, "Severe", "Ethanol inhibits hepatic lactate utilization, drastically precipitating fatal lactic acidosis"),
        ("Lisinopril", "Alcohol", 2, "Moderate", "Synergistic vasodilatory hypotension triggering orthostatic syncope"),
        ("Amlodipine", "Grapefruit Juice", 3, "Moderate", "CYP3A4 inhibition moderately increases amlodipine exposure, causing excessive peripheral edema and hypotension"),
        ("Levothyroxine", "Coffee / Caffeine", 2, "High", "Coffee significantly impairs thyroid hormone intestinal absorption; mandatory 60-minute separation required"),
        ("Levothyroxine", "Calcium Supplements / Antacids", 4, "High", "Calcium forms insoluble, unabsorbable adsorption complexes with levothyroxine in stomach"),
        ("Levothyroxine", "Iron Supplements", 4, "High", "Ferrous iron chelates levothyroxine, causing clinical hypothyroidism"),
        ("Ibuprofen", "Alcohol", 3, "High", "Synergistic mucosal toxicity causing severe gastric erosions and upper gastrointestinal hemorrhage"),
        ("Naproxen", "Alcohol", 3, "High", "Additive gastric mucosal ulceration and increased risk of gastrointestinal bleeding")
    ]
    for ing, food, gap, sev, mech in food_interactions:
        cur.execute(
            """
            MATCH (i:Ingredient {name: $ing}), (f:Food {name: $food})
            MERGE (i)-[:BINDS_OR_CONFLICTS_WITH {min_gap_hours: $gap, severity: $sev, mechanism: $mech}]->(f)
            """,
            {"ing": ing, "food": food, "gap": gap, "sev": sev, "mech": mech}
        )

    # 8. DIRECT DRUG-DRUG INTERACTIONS
    direct_ddi = [
        ("Ibuprofen", "Naproxen", "Severe", "Additive non-selective COX inhibition", "Multiplies gastrointestinal perforation and acute renal ischemia risk with zero added analgesic benefit"),
        ("Ibuprofen", "Aspirin", "High", "Competitive binding at platelet COX-1 active site", "Ibuprofen sterically prevents aspirin from irreversibly acetylating Ser529, destroying aspirin's cardioprotective antiplatelet effect"),
        ("Warfarin", "Ibuprofen", "Severe", "Synergistic platelet inhibition and gastric mucosal injury", "Warfarin anticoagulation combined with NSAID-induced gastric erosions and platelet dysfunction causes catastrophic GI bleeding"),
        ("Warfarin", "Naproxen", "Severe", "Synergistic anticoagulant-antiplatelet toxicity", "Extreme gastrointestinal bleeding and hematoma hazard"),
        ("Warfarin", "Aspirin", "Severe", "Dual pathway coagulation cascade and platelet suppression", "High spontaneous bleeding risk; requires rigorous clinical indication and monitoring"),
        ("Warfarin", "Atorvastatin", "High", "Hepatic clearance competition and protein displacement", "Can increase free warfarin levels, prolonging PT/INR and increasing hemorrhage risk"),
        ("Lisinopril", "Ibuprofen", "High", "Antagonism of renal hemodynamics and prostaglandin-mediated vasodilation", "NSAIDs blunt antihypertensive efficacy of ACE inhibitors and precipitate acute kidney injury via afferent arteriolar constriction"),
        ("Lisinopril", "Naproxen", "High", "Renal prostaglandin suppression", "Reduces antihypertensive control, induces sodium retention, and heightens renal failure risk"),
        ("Fluoxetine", "Tramadol", "Severe", "Potent CYP2D6 inhibition and dual serotonergic elevation", "Blocks tramadol activation to M1 analgesic while causing serotonin syndrome and seizure threshold reduction"),
        ("Prednisone", "Ibuprofen", "Severe", "Synergistic gastrointestinal mucosal ulceration", "Multiplies gastrointestinal ulceration, perforation, and severe GI hemorrhage risk by over 4-fold"),
        ("Prednisone", "Naproxen", "Severe", "Dual mucosal insult", "Severe peptic ulcer and bleeding risk")
    ]
    for ing1, ing2, sev, mech, eff in direct_ddi:
        cur.execute(
            """
            MATCH (i1:Ingredient {name: $ing1}), (i2:Ingredient {name: $ing2})
            MERGE (i1)-[:DIRECT_INTERACTION {severity: $sev, mechanism: $mech, effect: $eff}]->(i2)
            """,
            {"ing1": ing1, "ing2": ing2, "sev": sev, "mech": mech, "eff": eff}
        )

    # 9. MEDICINES (Brands & Generics)
    # (name, brand_name, is_brand, generic_name, ingredient_name, dosage_mg, default_slot, take_with_food, min_gap_hours)
    medicines = [
        # Heart & Gastric Block
        ("Plavix", "Plavix", True, "Clopidogrel", "Clopidogrel", 75.0, "Morning (Empty Stomach)", False, 0),
        ("Clopidogrel", "Plavix", False, "Clopidogrel", "Clopidogrel", 75.0, "Morning (Empty Stomach)", False, 0),
        ("Prilosec", "Prilosec", True, "Omeprazole", "Omeprazole", 20.0, "Morning (Empty Stomach)", False, 0),
        ("Omeprazole", "Prilosec", False, "Omeprazole", "Omeprazole", 20.0, "Morning (Empty Stomach)", False, 0),
        ("Pepcid", "Pepcid", True, "Famotidine", "Famotidine", 20.0, "Bedtime", False, 0),
        ("Famotidine", "Pepcid", False, "Famotidine", "Famotidine", 20.0, "Bedtime", False, 0),
        ("Protonix", "Protonix", True, "Pantoprazole", "Pantoprazole", 40.0, "Morning (Empty Stomach)", False, 0),
        ("Pantoprazole", "Protonix", False, "Pantoprazole", "Pantoprazole", 40.0, "Morning (Empty Stomach)", False, 0),

        # Antibiotic & Timing
        ("Cipro", "Cipro", True, "Ciprofloxacin", "Ciprofloxacin", 500.0, "Morning (Empty Stomach)", False, 3),
        ("Ciprofloxacin", "Cipro", False, "Ciprofloxacin", "Ciprofloxacin", 500.0, "Morning (Empty Stomach)", False, 3),

        # Blood Pressure & Painkillers
        ("Zestril", "Zestril", True, "Lisinopril", "Lisinopril", 10.0, "Breakfast", True, 0),
        ("Prinivil", "Prinivil", True, "Lisinopril", "Lisinopril", 10.0, "Breakfast", True, 0),
        ("Lisinopril", "Zestril", False, "Lisinopril", "Lisinopril", 10.0, "Breakfast", True, 0),
        ("Norvasc", "Norvasc", True, "Amlodipine", "Amlodipine", 5.0, "Breakfast", True, 0),
        ("Amlodipine", "Norvasc", False, "Amlodipine", "Amlodipine", 5.0, "Breakfast", True, 0),
        
        # Double Painkiller Brand Overlap
        ("Advil", "Advil", True, "Ibuprofen", "Ibuprofen", 200.0, "Lunch", True, 0),
        ("Motrin", "Motrin", True, "Ibuprofen", "Ibuprofen", 400.0, "Lunch", True, 0),
        ("Ibuprofen", "Advil", False, "Ibuprofen", "Ibuprofen", 400.0, "Lunch", True, 0),
        ("Aleve", "Aleve", True, "Naproxen", "Naproxen", 220.0, "Lunch", True, 0),
        ("Naprosyn", "Naprosyn", True, "Naproxen", "Naproxen", 500.0, "Lunch", True, 0),
        ("Naproxen", "Aleve", False, "Naproxen", "Naproxen", 500.0, "Lunch", True, 0),
        ("Tylenol", "Tylenol", True, "Acetaminophen", "Acetaminophen", 500.0, "Lunch", True, 0),
        ("Acetaminophen", "Tylenol", False, "Acetaminophen", "Acetaminophen", 500.0, "Lunch", True, 0),

        # Cholesterol & Anticoagulant
        ("Lipitor", "Lipitor", True, "Atorvastatin", "Atorvastatin", 20.0, "Evening", True, 0),
        ("Atorvastatin", "Lipitor", False, "Atorvastatin", "Atorvastatin", 20.0, "Evening", True, 0),
        ("Crestor", "Crestor", True, "Rosuvastatin", "Rosuvastatin", 10.0, "Evening", True, 0),
        ("Rosuvastatin", "Crestor", False, "Rosuvastatin", "Rosuvastatin", 10.0, "Evening", True, 0),
        ("Coumadin", "Coumadin", True, "Warfarin", "Warfarin", 5.0, "Bedtime", False, 0),
        ("Warfarin", "Coumadin", False, "Warfarin", "Warfarin", 5.0, "Bedtime", False, 0),
        ("Eliquis", "Eliquis", True, "Apixaban", "Apixaban", 5.0, "Breakfast", True, 0),
        ("Apixaban", "Eliquis", False, "Apixaban", "Apixaban", 5.0, "Breakfast", True, 0),

        # Metabolic & Chronic Meds
        ("Glucophage", "Glucophage", True, "Metformin", "Metformin", 500.0, "Breakfast", True, 0),
        ("Metformin", "Glucophage", False, "Metformin", "Metformin", 500.0, "Breakfast", True, 0),
        ("Synthroid", "Synthroid", True, "Levothyroxine", "Levothyroxine", 0.05, "Morning (Empty Stomach)", False, 4),
        ("Levothyroxine", "Synthroid", False, "Levothyroxine", "Levothyroxine", 0.05, "Morning (Empty Stomach)", False, 4),
        ("Lopressor", "Lopressor", True, "Metoprolol", "Metoprolol", 50.0, "Breakfast", True, 0),
        ("Metoprolol", "Lopressor", False, "Metoprolol", "Metoprolol", 50.0, "Breakfast", True, 0),
        ("Cozaar", "Cozaar", True, "Losartan", "Losartan", 50.0, "Breakfast", True, 0),
        ("Losartan", "Cozaar", False, "Losartan", "Losartan", 50.0, "Breakfast", True, 0),

        # CNS & Pain
        ("Benadryl", "Benadryl", True, "Diphenhydramine", "Diphenhydramine", 25.0, "Bedtime", False, 0),
        ("Diphenhydramine", "Benadryl", False, "Diphenhydramine", "Diphenhydramine", 25.0, "Bedtime", False, 0),
        ("Prozac", "Prozac", True, "Fluoxetine", "Fluoxetine", 20.0, "Breakfast", True, 0),
        ("Fluoxetine", "Prozac", False, "Fluoxetine", "Fluoxetine", 20.0, "Breakfast", True, 0),
        ("Ultram", "Ultram", True, "Tramadol", "Tramadol", 50.0, "Lunch", True, 0),
        ("Tramadol", "Ultram", False, "Tramadol", "Tramadol", 50.0, "Lunch", True, 0),
        ("Bayer Aspirin", "Bayer", True, "Aspirin", "Aspirin", 81.0, "Breakfast", True, 0),
        ("Aspirin", "Bayer", False, "Aspirin", "Aspirin", 81.0, "Breakfast", True, 0),
        ("Neurontin", "Neurontin", True, "Gabapentin", "Gabapentin", 300.0, "Evening", True, 0),
        ("Gabapentin", "Neurontin", False, "Gabapentin", "Gabapentin", 300.0, "Evening", True, 0),
        ("Deltasone", "Deltasone", True, "Prednisone", "Prednisone", 10.0, "Breakfast", True, 0),
        ("Prednisone", "Deltasone", False, "Prednisone", "Prednisone", 10.0, "Breakfast", True, 0),
        ("Tums", "Tums", True, "Calcium Carbonate", "Calcium Carbonate", 500.0, "Lunch", True, 2),
        ("Caltrate", "Caltrate", True, "Calcium Carbonate", "Calcium Carbonate", 600.0, "Lunch", True, 2)
    ]

    for m in medicines:
        name, brand, is_br, gen, ing, dose, slot, food_req, gap = m
        cur.execute(
            """
            MERGE (m:Medicine {name: $name})
            SET m.brand_name = $brand,
                m.is_brand = $is_br,
                m.generic_name = $gen,
                m.default_slot = $slot,
                m.take_with_food = $food_req,
                m.min_gap_hours = $gap
            """,
            {"name": name, "brand": brand, "is_br": is_br, "gen": gen, "slot": slot, "food_req": food_req, "gap": gap}
        )
        cur.execute(
            """
            MATCH (m:Medicine {name: $med}), (i:Ingredient {name: $ing})
            MERGE (m)-[:CONTAINS {dosage_mg: $dose}]->(i)
            """,
            {"med": name, "ing": ing, "dose": dose}
        )

    # 10. SAFE ALTERNATIVES
    safe_alts = [
        ("Famotidine", "Omeprazole", "Famotidine is an H2-blocker that suppresses gastric acid without inhibiting CYP2C19, preserving Clopidogrel antiplatelet activation", "Gastric Ulcer / GERD"),
        ("Pepcid", "Prilosec", "Pepcid (famotidine) does not inhibit CYP2C19, allowing Plavix (clopidogrel) full therapeutic activation", "Gastric Ulcer / GERD"),
        ("Pantoprazole", "Omeprazole", "Pantoprazole exhibits significantly less CYP2C19 inhibition than omeprazole, providing PPI gastroprotection with lower clopidogrel interaction risk", "Gastric Ulcer / GERD"),
        ("Protonix", "Prilosec", "Protonix (pantoprazole) has minimal CYP2C19 affinity compared to Prilosec, preserving Plavix efficacy", "Gastric Ulcer / GERD"),
        ("Acetaminophen", "Ibuprofen", "Acetaminophen provides pain/fever relief without inhibiting renal prostaglandins or damaging the gastric mucosa, making it safe in hypertension, kidney disease, and peptic ulcers", "Pain / Headache"),
        ("Tylenol", "Advil", "Tylenol (acetaminophen) avoids NSAID-induced gastric ulceration and does not blunt ACE inhibitor blood pressure control", "Pain / Headache"),
        ("Tylenol", "Motrin", "Tylenol avoids nephrotoxic and ulcerogenic NSAID mechanisms", "Pain / Headache"),
        ("Tylenol", "Aleve", "Tylenol avoids long-acting naproxen renal and gastric stress", "Pain / Headache"),
        ("Losartan", "Lisinopril", "Losartan (ARB) blocks angiotensin II receptors directly without causing bradykinin accumulation, preventing persistent ACE-inhibitor dry cough", "Hypertension"),
        ("Cozaar", "Zestril", "Cozaar avoids the bradykinin-mediated cough characteristic of Zestril", "Hypertension"),
        ("Rosuvastatin", "Atorvastatin", "Rosuvastatin is primarily excreted non-CYP3A4, avoiding grapefruit juice and CYP3A4 interaction risks seen with Atorvastatin", "Hyperlipidemia / Cholesterol"),
        ("Crestor", "Lipitor", "Crestor metabolism is largely independent of CYP3A4, eliminating grapefruit juice toxicity hazard", "Hyperlipidemia / Cholesterol")
    ]

    for alt, target, reason, cond in safe_alts:
        cur.execute(
            """
            MATCH (m_alt:Medicine {name: $alt}), (m_tgt:Medicine {name: $target})
            MERGE (m_alt)-[:SAFE_ALTERNATIVE_TO {reason: $reason, target_condition: $cond}]->(m_tgt)
            """,
            {"alt": alt, "target": target, "reason": reason, "cond": cond}
        )

    conn.commit()
    print("Database transaction committed successfully!")

    # Verify counts
    print("\n--- DATABASE VERIFICATION COUNTS ---")
    counts = [
        ("Medicine", "MATCH (n:Medicine) RETURN count(n) AS cnt"),
        ("Ingredient", "MATCH (n:Ingredient) RETURN count(n) AS cnt"),
        ("Enzyme", "MATCH (n:Enzyme) RETURN count(n) AS cnt"),
        ("Food", "MATCH (n:Food) RETURN count(n) AS cnt"),
        ("Condition", "MATCH (n:Condition) RETURN count(n) AS cnt"),
        ("Organ", "MATCH (n:Organ) RETURN count(n) AS cnt"),
        ("Symptom", "MATCH (n:Symptom) RETURN count(n) AS cnt"),
        ("Total Relationships", "MATCH ()-[r]->() RETURN count(r) AS cnt")
    ]
    for label, query in counts:
        cur.execute(query)
        cnt = cur.fetchone()["cnt"]
        print(f"  - {label}: {cnt}")

    conn.close()
    print(f"\nPersistent store successfully created and populated at {db_path} (Size: {os.path.getsize(db_path)} bytes)")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_db = os.path.join(base_dir, "data", "safemeds.rl")
    os.makedirs(os.path.dirname(target_db), exist_ok=True)
    seed_database(target_db)
