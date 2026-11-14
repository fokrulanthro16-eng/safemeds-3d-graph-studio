# SafeMeds
An offline-first medication, food, and condition safety graph tool powered by Relate by Neo4j.

## Use case
Patients taking multiple daily medications often experience adverse drug events due to hidden pharmacological pathways that traditional static drug checklists miss. SafeMeds uses in-process openCypher graph traversal over multi-hop relationships to solve five critical problems:

1. **Multi-Hop Hidden Pathway Collisions (3–4 Hops)**:
   - Detects enzyme inhibition collisions such as `(Medicine)-[:CONTAINS]->(Ingredient)-[:REQUIRES_ENZYME]->(Enzyme)<-[:INHIBITS_ENZYME]-(Ingredient)<-[:CONTAINS]-(Medicine)` (e.g. Omeprazole blocking Clopidogrel activation) and suggests safe alternatives (`[:SAFE_ALTERNATIVE_TO]`) like Famotidine or Pantoprazole.
2. **Hidden Brand Overdose / Double-Dose Detection**:
   - Detects when two differently branded products contain identical active generic ingredients: `(BrandA)-[:CONTAINS]->(Ingredient)<-[:CONTAINS]-(BrandB)` (e.g. Advil and Motrin both containing Ibuprofen).
3. **Smart 5-Slot Daily Timetable Routine**:
   - Uses `take_with_food` and `min_gap_hours` relationship properties to automatically schedule medications across 5 slots: `Morning (Empty Stomach)`, `Breakfast`, `Lunch`, `Evening`, and `Bedtime` while spacing out chelation binders (e.g. Ciprofloxacin spaced 3 hours from Milk / Calcium).
4. **Cumulative Organ Load Aggregation**:
   - Computes physiological stress across `(:Ingredient)-[:STRESSES_ORGAN {load_score}]->(:Organ)` for Kidney, Liver, Stomach/GI, and Brain/CNS.
5. **Reverse Symptom Tracer ("Why am I feeling this?")**:
   - Traverses backwards along `(:Symptom)<-[:CAN_CAUSE]-(:Ingredient)<-[:CONTAINS]-(:Medicine)` to isolate which medication in the patient's active regimen is causing symptoms like persistent dry cough or ankle swelling.

## How it uses Relate
- **Mode**: single file
- **Why this mode**: A single persistent file (`./data/safemeds.rl`) runs 100% locally in-process with zero external database servers, zero cloud latency, and complete offline patient data privacy. The file is portable, deterministic, and inspectable immediately upon repository clone.
- **What the graph models**:
  - `(:Medicine)`: 53 brand and generic medicines with dosage and scheduling properties.
  - `(:Ingredient)`: 25 active pharmacological ingredients.
  - `(:Enzyme)`: 5 primary hepatic cytochrome P450 enzymes (`CYP2C19`, `CYP3A4`, `CYP2C9`, `CYP2D6`, `CYP1A2`).
  - `(:Food)`: 12 foods, beverages, and dietary supplements with binding/chelation properties.
  - `(:Condition)`: 10 chronic health conditions.
  - `(:Organ)`: 4 vital organ systems (`Kidney`, `Liver`, `Stomach / GI`, `Brain / CNS`).
  - `(:Symptom)`: 15 common adverse clinical symptoms.
  - **Relationships**: `[:CONTAINS]`, `[:REQUIRES_ENZYME]`, `[:INHIBITS_ENZYME]`, `[:BINDS_OR_CONFLICTS_WITH]`, `[:CONTRAINDICATED_IN]`, `[:STRESSES_ORGAN]`, `[:CAN_CAUSE]`, `[:DIRECT_INTERACTION]`, and `[:SAFE_ALTERNATIVE_TO]`.

## Setup and run
### Prerequisites
- Python 3.9+
- Relate CLI and Python library (`pip install relate-db`)

### Installation & Launch
1. Clone the repository and navigate into the folder:
   ```bash
   git clone <repo-url>
   cd safe-meds
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Re-seed the persistent store:
   ```bash
   python scripts/seed_data.py
   ```
4. Verify the test suite against the persistent database:
   ```bash
   python verify_safemeds.py
   ```
5. Start the local server:
   ```bash
   python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
   ```
6. Open your browser at `http://127.0.0.1:8000`.

## Where the data lives
`./data/safemeds.rl` (Committed directly in this repository).
