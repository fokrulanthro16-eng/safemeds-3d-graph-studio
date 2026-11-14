// ==========================================================================
// SafeMeds — Frosted Glassmorphism Frontend Controller
// Real-time Cypher-driven clinical graph traversal
// ==========================================================================

let catalog = { medicines: [], foods: [], conditions: [], symptoms: [] };
let selectedMedicines = new Set();
let selectedFoods = new Set();
let selectedConditions = new Set();
let activeTraceResult = null;
let currentAnalysisData = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
  await loadHealth();
  await loadCatalog();
  setupAutocomplete();
  
  // AUTO-LOAD PRESET 1 ON INITIAL PAGE LOAD (NEVER EMPTY)
  await loadPreset('preset_1');

  // Re-draw SVG connectors on window resize or scroll
  window.addEventListener('resize', () => {
    if (currentAnalysisData) drawPathwayConnectors(currentAnalysisData);
  });
  
  const canvas = document.getElementById('pathwayCanvas');
  if (canvas) {
    canvas.addEventListener('scroll', () => {
      if (currentAnalysisData) drawPathwayConnectors(currentAnalysisData);
    });
  }
});

// 1. HEALTH & METADATA
async function loadHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    if (data.status === 'healthy') {
      const dbPathEl = document.getElementById('dbPathDisplay');
      if (dbPathEl) {
        dbPathEl.textContent = `${data.database.rel_path} (${data.database.size_kb} KB)`;
      }
    }
  } catch (e) {
    console.error('Health check failed', e);
  }
}

// 2. CATALOG & DROPDOWNS
async function loadCatalog() {
  try {
    const res = await fetch('/api/catalog');
    catalog = await res.json();

    populateFoodPicker(catalog.foods);
    populateConditionPicker(catalog.conditions);
    populateSymptomPicker(catalog.symptoms);
  } catch (e) {
    console.error('Failed to load catalog', e);
  }
}

function populateFoodPicker(foods) {
  const select = document.getElementById('foodSelectPicker');
  select.innerHTML = '<option value="">+ Add Dietary Intake / Supplement...</option>';
  foods.forEach(f => {
    const opt = document.createElement('option');
    opt.value = f.name;
    opt.textContent = `${f.name} (${f.category})`;
    select.appendChild(opt);
  });
}

function populateConditionPicker(conds) {
  const select = document.getElementById('condSelectPicker');
  select.innerHTML = '<option value="">+ Add Chronic Health Condition...</option>';
  conds.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.name;
    opt.textContent = `${c.name} (${c.category})`;
    select.appendChild(opt);
  });
}

function populateSymptomPicker(symptoms) {
  const select = document.getElementById('symptomSelect');
  select.innerHTML = '<option value="">-- Choose Adverse Symptom --</option>';
  symptoms.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.name;
    opt.textContent = `${s.name} (${s.severity})`;
    select.appendChild(opt);
  });
}

// 3. AUTOCOMPLETE SEARCH FOR MEDICINES (NO CLUTTERED BUTTONS)
function setupAutocomplete() {
  const input = document.getElementById('medSearchInput');
  const dropdown = document.getElementById('medDropdown');

  input.addEventListener('input', (e) => {
    const query = e.target.value.trim().toLowerCase();
    if (!query) {
      dropdown.style.display = 'none';
      return;
    }

    const matches = catalog.medicines.filter(m => 
      m.name.toLowerCase().includes(query) ||
      (m.generic_name && m.generic_name.toLowerCase().includes(query)) ||
      (m.ingredient && m.ingredient.toLowerCase().includes(query))
    );

    if (matches.length === 0) {
      dropdown.innerHTML = '<div class="dropdown-item" style="color:var(--text-faint);font-style:italic;">No matching medicines found</div>';
      dropdown.style.display = 'block';
      return;
    }

    dropdown.innerHTML = '';
    matches.slice(0, 10).forEach(m => {
      const item = document.createElement('div');
      item.className = 'dropdown-item';
      item.innerHTML = `
        <div>
          <span class="item-name">${m.name}</span>
          ${m.is_brand ? `<span style="font-size:0.6rem;background:rgba(190,242,100,0.18);color:var(--glow-lime);padding:1px 5px;border-radius:3px;margin-left:4px;">Brand</span>` : ''}
        </div>
        <span class="item-meta">${m.ingredient || m.generic_name}</span>
      `;
      item.onclick = () => {
        if (!selectedMedicines.has(m.name)) {
          selectedMedicines.add(m.name);
          updateChipsUI();
          triggerAnalysis();
        }
        input.value = '';
        dropdown.style.display = 'none';
      };
      dropdown.appendChild(item);
    });
    dropdown.style.display = 'block';
  });

  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.style.display = 'none';
    }
  });
}

// ADD HANDLERS
function handleAddFood(foodName) {
  if (!foodName) return;
  selectedFoods.add(foodName);
  document.getElementById('foodSelectPicker').value = '';
  updateChipsUI();
  triggerAnalysis();
}

function handleAddCondition(condName) {
  if (!condName) return;
  selectedConditions.add(condName);
  document.getElementById('condSelectPicker').value = '';
  updateChipsUI();
  triggerAnalysis();
}

// REMOVE HANDLERS
function removeMedicine(name) {
  selectedMedicines.delete(name);
  updateChipsUI();
  triggerAnalysis();
}

function removeFood(name) {
  selectedFoods.delete(name);
  updateChipsUI();
  triggerAnalysis();
}

function removeCondition(name) {
  selectedConditions.delete(name);
  updateChipsUI();
  triggerAnalysis();
}

// 4. UPDATE REMOVABLE CHIPS
function updateChipsUI() {
  const container = document.getElementById('selectedChipsContainer');
  const totalCount = selectedMedicines.size + selectedFoods.size + selectedConditions.size;
  document.getElementById('activeItemsCount').textContent = `${totalCount} item${totalCount === 1 ? '' : 's'}`;

  if (totalCount === 0) {
    container.innerHTML = `
      <div class="empty-chips-hint">
        <span>No items selected. Type to add medications or select a preset above.</span>
      </div>
    `;
    return;
  }

  container.innerHTML = '';

  // Medicines
  selectedMedicines.forEach(med => {
    const chip = document.createElement('div');
    chip.className = 'regimen-chip chip-med';
    chip.innerHTML = `
      <span>💊 ${med}</span>
      <span class="chip-remove" onclick="removeMedicine('${med}')">&times;</span>
    `;
    container.appendChild(chip);
  });

  // Foods
  selectedFoods.forEach(food => {
    const chip = document.createElement('div');
    chip.className = 'regimen-chip chip-food';
    chip.innerHTML = `
      <span>🥛 ${food}</span>
      <span class="chip-remove" onclick="removeFood('${food}')">&times;</span>
    `;
    container.appendChild(chip);
  });

  // Conditions
  selectedConditions.forEach(cond => {
    const chip = document.createElement('div');
    chip.className = 'regimen-chip chip-cond';
    chip.innerHTML = `
      <span>🩺 ${cond}</span>
      <span class="chip-remove" onclick="removeCondition('${cond}')">&times;</span>
    `;
    container.appendChild(chip);
  });
}

// 5. CLEAR ALL SELECTIONS
function clearAllSelections(skipTrigger = false) {
  selectedMedicines.clear();
  selectedFoods.clear();
  selectedConditions.clear();
  activeTraceResult = null;
  currentAnalysisData = null;

  document.getElementById('symptomSelect').value = '';
  document.getElementById('traceResultBox').style.display = 'none';

  updateChipsUI();
  if (!skipTrigger) {
    triggerAnalysis();
  }
}

// 6. ONE-CLICK PRESET BUTTONS (ALWAYS CLEARS PREVIOUS FIRST)
async function loadPreset(presetId) {
  try {
    clearAllSelections(true);

    const res = await fetch('/api/presets');
    const presets = await res.json();
    const p = presets.find(x => x.id === presetId);
    if (!p) return;

    p.medicines.forEach(m => selectedMedicines.add(m));
    p.foods.forEach(f => selectedFoods.add(f));
    p.conditions.forEach(c => selectedConditions.add(c));

    updateChipsUI();

    if (p.symptom) {
      document.getElementById('symptomSelect').value = p.symptom;
    }

    await triggerAnalysis();
  } catch (e) {
    console.error('Failed to load preset', e);
  }
}

// 7. COMPREHENSIVE ANALYSIS
async function triggerAnalysis() {
  const reqBody = {
    medicines: Array.from(selectedMedicines),
    foods: Array.from(selectedFoods),
    conditions: Array.from(selectedConditions)
  };

  const emptyState = document.getElementById('pathwayEmptyState');
  const safeState = document.getElementById('pathwaySafeState');

  if (reqBody.medicines.length === 0 && reqBody.foods.length === 0 && reqBody.conditions.length === 0) {
    clearPathwayDiagram();
    emptyState.style.display = 'block';
    safeState.style.display = 'none';
    renderClinicalWarnings([], [], []);
    renderSchedule([]);
    renderOrganLoad({ Kidney: 0, Liver: 0, 'Stomach / GI': 0, 'Brain / CNS': 0 });
    renderExecutedQueries([]);
    return;
  }

  emptyState.style.display = 'none';

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reqBody)
    });
    const data = await res.json();
    currentAnalysisData = data;

    // Render the structured 4-column pathway diagram
    renderPathwayDiagram(data);

    // Render Right Column panels
    renderClinicalWarnings(data.warnings, data.brand_overlaps, data.safe_alternatives);
    renderSchedule(data.schedule);
    renderOrganLoad(data.organ_load);
    renderExecutedQueries(data.queries_executed);

  } catch (e) {
    console.error('Analysis failed', e);
  }
}

// 8. STRUCTURED 4-COLUMN LEFT-TO-RIGHT PATHWAY DIAGRAM (NO TANGLED CIRCLES)
function clearPathwayDiagram() {
  document.getElementById('stackIntake').innerHTML = '';
  document.getElementById('stackIngredients').innerHTML = '';
  document.getElementById('stackConflicts').innerHTML = '';
  document.getElementById('stackAlternatives').innerHTML = '';
  const svg = document.getElementById('pathwaySvg');
  // keep defs intact
  const defs = svg.querySelector('defs');
  svg.innerHTML = '';
  if (defs) svg.appendChild(defs);
}

function renderPathwayDiagram(data) {
  clearPathwayDiagram();

  const emptyState = document.getElementById('pathwayEmptyState');
  const safeState = document.getElementById('pathwaySafeState');
  emptyState.style.display = 'none';

  const stackIntake = document.getElementById('stackIntake');
  const stackIngredients = document.getElementById('stackIngredients');
  const stackConflicts = document.getElementById('stackConflicts');
  const stackAlternatives = document.getElementById('stackAlternatives');

  // Filter out any Organ nodes and STRESSES_ORGAN edges
  const nonOrganNodes = (data.graph.nodes || []).filter(n => n.label !== 'Organ');
  const nonOrganEdges = (data.graph.edges || []).filter(e => e.type !== 'STRESSES_ORGAN');

  // 1. COLUMN 1: INTAKE (Medicines, Foods, Conditions)
  const intakeNodes = nonOrganNodes.filter(n => ['Medicine', 'Food', 'Condition'].includes(n.label) && !n.extra?.is_alt);
  intakeNodes.forEach(node => {
    const card = document.createElement('div');
    card.className = 'pathway-card card-intake';
    card.id = `card_${sanitizeId(node.id)}`;
    
    let icon = '💊';
    if (node.label === 'Food') icon = '🥛';
    if (node.label === 'Condition') icon = '🩺';

    card.innerHTML = `
      <span class="card-category-pill">${icon} ${node.label}</span>
      <div class="card-main-title">${node.title}</div>
      ${node.category ? `<span class="card-subtext">${node.category}</span>` : ''}
    `;
    stackIntake.appendChild(card);
  });

  // 2. COLUMN 2: INGREDIENTS
  const ingNodes = nonOrganNodes.filter(n => n.label === 'Ingredient');
  ingNodes.forEach(node => {
    const card = document.createElement('div');
    card.className = 'pathway-card card-ingredient';
    card.id = `card_${sanitizeId(node.id)}`;
    card.innerHTML = `
      <span class="card-category-pill">Active Molecule</span>
      <div class="card-main-title">${node.title}</div>
      <span class="card-subtext">Generic Substance</span>
    `;
    stackIngredients.appendChild(card);
  });

  // 3. COLUMN 3: CONFLICT POINTS (Enzymes, Brand Overlaps, Chelation Gaps, Contraindications)
  const conflictItems = [];

  // Enzymes (e.g. CYP2C19, CYP3A4)
  const enzymeNodes = nonOrganNodes.filter(n => n.label === 'Enzyme');
  enzymeNodes.forEach(e => {
    conflictItems.push({
      id: `conf_${sanitizeId(e.id)}`,
      title: `${e.title} Blocked`,
      pill: 'CYP ENZYME COLLISION',
      sub: 'Bioactivation Inhibited',
      isAmber: false,
      relatedSourceId: e.id
    });
  });

  // Brand Overlap (Double Dose)
  (data.brand_overlaps || []).forEach((bo, idx) => {
    conflictItems.push({
      id: `conf_bo_${idx}`,
      title: `Double Dose Overdose`,
      pill: 'BRAND OVERLAP',
      sub: `${bo.ingredient} in both`,
      isAmber: false,
      med1: bo.med1,
      med2: bo.med2
    });
  });

  // Food Interactions / Chelation Gaps
  const foodEdges = nonOrganEdges.filter(e => e.type === 'BINDS_OR_CONFLICTS_WITH');
  foodEdges.forEach((fe, idx) => {
    const isAmber = fe.severity === 'spacing' || (fe.label && fe.label.includes('Gap'));
    conflictItems.push({
      id: `conf_fe_${idx}`,
      title: isAmber ? '3-Hour Spacing Needed' : 'Food Inactivation',
      pill: isAmber ? 'TIMING SEPARATION' : 'FOOD CLASH',
      sub: fe.label || 'Binding Chelation',
      isAmber: isAmber,
      source: fe.source,
      target: fe.target
    });
  });

  // Direct Drug-Drug Interactions
  const ddiEdges = nonOrganEdges.filter(e => e.type === 'DIRECT_INTERACTION');
  ddiEdges.forEach((de, idx) => {
    conflictItems.push({
      id: `conf_ddi_${idx}`,
      title: 'Direct Drug Clash',
      pill: 'SEVERE INTERACTION',
      sub: de.notes ? de.notes.substring(0, 30) + '...' : de.label,
      isAmber: false,
      source: de.source,
      target: de.target
    });
  });

  // Condition Contraindications
  const condEdges = nonOrganEdges.filter(e => e.type === 'CONTRAINDICATED_IN');
  condEdges.forEach((ce, idx) => {
    conflictItems.push({
      id: `conf_cond_${idx}`,
      title: 'Contraindication',
      pill: 'CLINICAL ALERT',
      sub: ce.label,
      isAmber: false,
      source: ce.source,
      target: ce.target
    });
  });

  // Active reverse symptom trace item if present
  if (activeTraceResult && activeTraceResult.culprits && activeTraceResult.culprits.length > 0) {
    conflictItems.push({
      id: `conf_sym_trace`,
      title: activeTraceResult.symptom,
      pill: 'ADVERSE SYMPTOM',
      sub: `Traced to ${activeTraceResult.culprits[0].medicine}`,
      isAmber: false,
      isSymptom: true
    });
  }

  conflictItems.forEach(item => {
    const card = document.createElement('div');
    card.className = `pathway-card card-conflict ${item.isAmber ? 'amber-gap' : ''}`;
    card.id = item.id;
    card.innerHTML = `
      <span class="card-category-pill">${item.pill}</span>
      <div class="card-main-title">${item.title}</div>
      <span class="card-subtext">${item.sub}</span>
    `;
    stackConflicts.appendChild(card);
  });

  // 4. COLUMN 4: RECOMMENDED SAFE ALTERNATIVES
  const safeAlts = data.safe_alternatives || [];
  safeAlts.forEach((alt, idx) => {
    const card = document.createElement('div');
    card.className = 'pathway-card card-alternative';
    card.id = `card_alt_${idx}`;
    card.innerHTML = `
      <span class="card-category-pill">SAFE SWAP</span>
      <div class="card-main-title">${alt.alternative}</div>
      <span class="card-subtext">Replaces ${alt.replaces}</span>
    `;
    stackAlternatives.appendChild(card);
  });

  // If there are selected items but zero conflicts found:
  if (conflictItems.length === 0 && safeAlts.length === 0) {
    safeState.style.display = 'block';
  } else {
    safeState.style.display = 'none';
  }

  // Draw smooth SVG connector curves with glow filters and pill labels
  setTimeout(() => {
    drawPathwayConnectors(data, conflictItems, safeAlts);
  }, 40);
}

function sanitizeId(str) {
  return String(str).replace(/[^a-zA-Z0-9_-]/g, '_');
}

// 9. DRAW GLOWING SVG CONNECTORS BETWEEN CARDS (ANIMATED FLOWING BEZIERS)
function drawPathwayConnectors(data = null, conflictItems = [], safeAlts = []) {
  const svg = document.getElementById('pathwaySvg');
  const canvas = document.getElementById('pathwayCanvas');
  if (!svg || !canvas) return;

  const defs = svg.querySelector('defs');
  svg.innerHTML = '';
  if (defs) svg.appendChild(defs);

  const canvasRect = canvas.getBoundingClientRect();

  // Helper to draw a smooth cubic Bezier between two card elements
  function drawConnection(el1, el2, styleClass = '', pillLabel = '') {
    if (!el1 || !el2) return;

    const r1 = el1.getBoundingClientRect();
    const r2 = el2.getBoundingClientRect();

    // Source: right middle of el1
    const x1 = r1.right - canvasRect.left + canvas.scrollLeft;
    const y1 = r1.top - canvasRect.top + r1.height / 2 + canvas.scrollTop;

    // Target: left middle of el2
    const x2 = r2.left - canvasRect.left + canvas.scrollLeft;
    const y2 = r2.top - canvasRect.top + r2.height / 2 + canvas.scrollTop;

    if (x2 <= x1 + 10) return;

    const dx = (x2 - x1) * 0.45;
    const pathD = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', pathD);
    path.setAttribute('class', `connector-line ${styleClass}`);

    // Apply glowing SVG filters
    if (styleClass.includes('conflict')) {
      path.setAttribute('filter', 'url(#glow-red)');
    } else if (styleClass.includes('spacing')) {
      path.setAttribute('filter', 'url(#glow-amber)');
    } else if (styleClass.includes('safe')) {
      path.setAttribute('filter', 'url(#glow-green)');
    }

    svg.appendChild(path);

    // Pill label in the middle
    if (pillLabel) {
      const mx = (x1 + x2) / 2;
      const my = (y1 + y2) / 2;

      const pillGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      pillGroup.setAttribute('transform', `translate(${mx}, ${my})`);

      const pillW = Math.max(50, pillLabel.length * 6.5 + 12);
      const pillH = 17;

      const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      bg.setAttribute('x', -pillW / 2);
      bg.setAttribute('y', -pillH / 2);
      bg.setAttribute('width', pillW);
      bg.setAttribute('height', pillH);
      bg.setAttribute('class', 'svg-pill-bg');

      const txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      txt.setAttribute('class', `svg-pill-text ${styleClass ? styleClass.replace('-curve', '') : ''}`);
      txt.textContent = pillLabel;

      pillGroup.appendChild(bg);
      pillGroup.appendChild(txt);
      svg.appendChild(pillGroup);
    }
  }

  // 1. Connect Col 1 (Medicine) -> Col 2 (Ingredient)
  const intakeCards = document.querySelectorAll('#stackIntake .pathway-card');
  const ingCards = document.querySelectorAll('#stackIngredients .pathway-card');

  intakeCards.forEach(c1 => {
    ingCards.forEach(c2 => {
      const medName = c1.querySelector('.card-main-title')?.textContent.trim();
      const ingName = c2.querySelector('.card-main-title')?.textContent.trim();
      if (medName && ingName && (medName.includes(ingName) || ingName.includes(medName) || isKnownPair(medName, ingName))) {
        drawConnection(c1, c2, '', 'Contains');
      }
    });
  });

  // 2. Connect Col 2 (Ingredients / Foods) -> Col 3 (Conflicts)
  const confCards = document.querySelectorAll('#stackConflicts .pathway-card');
  confCards.forEach(cc => {
    const isAmber = cc.classList.contains('amber-gap');
    const style = isAmber ? 'spacing-curve' : 'conflict-curve';
    const label = isAmber ? '3h Gap' : (cc.id.includes('cyp') || cc.textContent.includes('Enzyme') ? 'Blocks' : 'Conflict');

    ingCards.forEach(c2 => {
      drawConnection(c2, cc, style, label);
    });
  });

  // 3. Connect Col 3 (Conflicts) -> Col 4 (Safe Alternatives)
  const altCards = document.querySelectorAll('#stackAlternatives .pathway-card');
  altCards.forEach(ac => {
    confCards.forEach(cc => {
      drawConnection(cc, ac, 'safe-curve', 'Safe Swap');
    });
  });
}

function isKnownPair(med, ing) {
  const pairs = {
    'Plavix': 'Clopidogrel',
    'Prilosec': 'Omeprazole',
    'Cipro': 'Ciprofloxacin',
    'Zestril': 'Lisinopril',
    'Prinivil': 'Lisinopril',
    'Norvasc': 'Amlodipine',
    'Advil': 'Ibuprofen',
    'Motrin': 'Ibuprofen',
    'Aleve': 'Naproxen',
    'Naprosyn': 'Naproxen',
    'Lipitor': 'Atorvastatin',
    'Coumadin': 'Warfarin',
    'Tylenol': 'Acetaminophen',
    'Crestor': 'Rosuvastatin',
    'Eliquis': 'Apixaban',
    'Synthroid': 'Levothyroxine',
    'Pepcid': 'Famotidine',
    'Protonix': 'Pantoprazole'
  };
  return pairs[med] === ing;
}

// 10. RENDER CLINICAL WARNINGS & ALTERNATIVES
function renderClinicalWarnings(warnings, brandOverlaps, safeAlts) {
  // Double-Dose Overlaps
  const ddContainer = document.getElementById('doubleDoseContainer');
  ddContainer.innerHTML = '';
  if (brandOverlaps && brandOverlaps.length > 0) {
    brandOverlaps.forEach(dd => {
      const card = document.createElement('div');
      card.className = 'clinical-alert-card severe';
      card.innerHTML = `
        <div class="alert-head-row">
          <span class="alert-headline">⚠️ Accidental Double-Dose Overlap</span>
          <span class="alert-pill">OVERDOSE RISK</span>
        </div>
        <div class="alert-body-text">${dd.warning}</div>
      `;
      ddContainer.appendChild(card);
    });
  }

  // Warnings
  const wContainer = document.getElementById('warningsListContainer');
  const countBadge = document.getElementById('warningsCountBadge');
  wContainer.innerHTML = '';

  const totalWarnings = (warnings ? warnings.length : 0) + (brandOverlaps ? brandOverlaps.length : 0);
  countBadge.textContent = `${totalWarnings} alert${totalWarnings === 1 ? '' : 's'}`;

  if (warnings && warnings.length > 0) {
    warnings.forEach(w => {
      const card = document.createElement('div');
      const sevClass = w.severity === 'Severe' ? 'severe' : 'high';
      card.className = `clinical-alert-card ${sevClass}`;
      card.innerHTML = `
        <div class="alert-head-row">
          <span class="alert-headline">${w.title}</span>
          <span class="alert-pill">${w.severity}</span>
        </div>
        <div class="alert-body-text">${w.details}</div>
      `;
      wContainer.appendChild(card);
    });
  } else if (!brandOverlaps || brandOverlaps.length === 0) {
    wContainer.innerHTML = '<div class="empty-tab-text">No active clinical warnings. Patient regimen clear.</div>';
  }

  // Safe Alternatives
  const altContainer = document.getElementById('altsListContainer');
  const altBadge = document.getElementById('altsCountBadge');
  altContainer.innerHTML = '';

  const altCount = safeAlts ? safeAlts.length : 0;
  altBadge.textContent = `${altCount} option${altCount === 1 ? '' : 's'}`;

  if (safeAlts && safeAlts.length > 0) {
    safeAlts.forEach(alt => {
      const card = document.createElement('div');
      card.className = 'safe-alternative-card';
      card.innerHTML = `
        <div class="alt-headline">✅ Consider: ${alt.alternative}</div>
        <div class="alt-replaces">Replaces <strong>${alt.replaces}</strong> for <em>${alt.condition}</em></div>
        <div class="alt-explanation">${alt.reason}</div>
      `;
      altContainer.appendChild(card);
    });
  } else {
    altContainer.innerHTML = '<div class="empty-tab-text">Safe alternatives appear when blocked pathways are detected.</div>';
  }
}

// 11. RENDER 5-SLOT DAILY SCHEDULE
function renderSchedule(schedule) {
  const container = document.getElementById('scheduleTimeline');
  container.innerHTML = '';

  if (!schedule || schedule.length === 0) {
    container.innerHTML = '<div class="empty-tab-text">Select medications to generate an optimized daily timetable.</div>';
    return;
  }

  schedule.forEach(slotData => {
    const card = document.createElement('div');
    card.className = 'routine-slot-card';

    let itemsHtml = '';
    slotData.items.forEach(it => {
      itemsHtml += `
        <div class="slot-item-row">
          <div class="slot-med-title">${it.medicine}</div>
          <div class="slot-med-inst">${it.instructions}</div>
        </div>
      `;
    });

    card.innerHTML = `
      <div class="slot-name-row">
        <span class="slot-badge">${slotData.slot}</span>
        <span class="slot-count">${slotData.items.length} item${slotData.items.length === 1 ? '' : 's'}</span>
      </div>
      <div>${itemsHtml}</div>
    `;
    container.appendChild(card);
  });
}

// 12. RENDER CUMULATIVE ORGAN LOAD
function renderOrganLoad(loads) {
  const organs = ['Kidney', 'Liver', 'Stomach', 'Brain'];
  const maxScale = 12;

  let totalScore = 0;
  organs.forEach(org => {
    const key = org === 'Stomach' ? 'Stomach / GI' : (org === 'Brain' ? 'Brain / CNS' : org);
    const score = loads[key] || 0;
    totalScore += score;

    const valEl = document.getElementById(`val${org}`);
    const barEl = document.getElementById(`bar${org}`);

    if (valEl) valEl.textContent = score;
    if (barEl) {
      const pct = Math.min(100, Math.round((score / maxScale) * 100));
      barEl.style.width = `${pct}%`;
      barEl.className = 'meter-fill';
      if (score >= 8) barEl.classList.add('high');
      else if (score >= 4) barEl.classList.add('medium');
    }
  });

  const assessBox = document.getElementById('organAssessmentCard');
  if (totalScore >= 12) {
    assessBox.innerHTML = `<strong style="color:var(--glow-red);">⚠️ Critical Cumulative Organ Stress:</strong> Multiple concurrent medications place severe load on renal and GI filtration pathways.`;
  } else if (totalScore >= 6) {
    assessBox.innerHTML = `<strong style="color:var(--glow-amber);">Moderate Organ Burden:</strong> Regular metabolic monitoring advised.`;
  } else if (totalScore > 0) {
    assessBox.innerHTML = `<strong style="color:var(--glow-mint);">Low Organ Burden:</strong> Cumulative clearance remains within normal parameters.`;
  } else {
    assessBox.innerHTML = `Select medications to calculate cumulative physiological burden.`;
  }
}

// 13. RENDER RECENT CYPHER QUERIES
function renderExecutedQueries(queries) {
  const container = document.getElementById('recentQueriesContainer');
  container.innerHTML = '';
  if (!queries || queries.length === 0) return;

  queries.forEach(q => {
    const chip = document.createElement('div');
    chip.className = 'query-chip';
    chip.innerHTML = `
      <div class="query-name-tag">${q.name}</div>
      <div class="query-cypher-code">${q.query}</div>
    `;
    container.appendChild(chip);
  });
}

// 14. REVERSE SYMPTOM TRACER
async function traceSymptom() {
  const symptom = document.getElementById('symptomSelect').value;
  if (!symptom) {
    alert('Please select a symptom to trace.');
    return;
  }

  const resultBox = document.getElementById('traceResultBox');
  resultBox.style.display = 'block';
  resultBox.innerHTML = '<span style="color:var(--text-muted);">Traversing Relate graph backwards...</span>';

  try {
    const res = await fetch('/api/trace-symptom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symptom: symptom,
        active_medicines: Array.from(selectedMedicines)
      })
    });
    const data = await res.json();
    activeTraceResult = data;

    if (data.culprits && data.culprits.length > 0) {
      let html = `<strong>Culprit Pinpointed for "${symptom}":</strong><br>`;
      data.culprits.forEach(c => {
        html += `
          <div style="margin-top:5px;">
            ⚠️ <strong style="color:var(--glow-red);">${c.medicine}</strong> (${c.ingredient}) &middot; <em>${c.frequency}</em><br>
            <span style="font-size:0.68rem;opacity:0.9;">Mechanism: ${c.mechanism}</span>
          </div>
        `;
      });
      resultBox.innerHTML = html;
      triggerAnalysis();
    } else {
      resultBox.innerHTML = `No direct causal link found between "${symptom}" and your currently selected medications.`;
    }
  } catch (e) {
    console.error('Symptom trace failed', e);
    resultBox.innerHTML = 'Error executing symptom trace.';
  }
}

// 15. LIVE CYPHER REPL
async function runCustomCypher() {
  const query = document.getElementById('replInput').value.trim();
  if (!query) return;

  const outArea = document.getElementById('replOutputArea');
  outArea.style.display = 'block';
  outArea.innerHTML = '<span style="color:var(--text-muted);">Executing query against ./data/safemeds.rl...</span>';

  try {
    const res = await fetch('/api/cypher', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query })
    });
    const data = await res.json();

    if (res.status !== 200) {
      outArea.innerHTML = `<span style="color:var(--glow-red);">Error: ${data.detail || 'Query failed'}</span>`;
      return;
    }

    if (!data.rows || data.rows.length === 0) {
      outArea.innerHTML = `<span style="color:var(--glow-mint);">Query executed in ${data.elapsed_ms} ms (0 rows).</span>`;
      return;
    }

    let table = `<div style="color:var(--glow-lime);margin-bottom:4px;font-weight:600;">✓ Returned ${data.count} row(s) in ${data.elapsed_ms} ms:</div>`;
    table += '<table class="cypher-table"><thead><tr>';
    data.columns.forEach(c => table += `<th>${c}</th>`);
    table += '</tr></thead><tbody>';

    data.rows.slice(0, 15).forEach(row => {
      table += '<tr>';
      data.columns.forEach(c => table += `<td>${row[c] !== null ? row[c] : '<em>null</em>'}</td>`);
      table += '</tr>';
    });
    table += '</tbody></table>';

    if (data.count > 15) {
      table += `<div style="font-size:0.65rem;color:var(--text-muted);margin-top:4px;">Showing first 15 of ${data.count} rows.</div>`;
    }

    outArea.innerHTML = table;
  } catch (e) {
    outArea.innerHTML = `<span style="color:var(--glow-red);">Execution error: ${e.message}</span>`;
  }
}

function insertSampleCypher() {
  const samples = [
    "MATCH (m:Medicine)-[:CONTAINS]->(i:Ingredient)-[:REQUIRES_ENZYME]->(e:Enzyme) RETURN m.name AS medicine, i.name AS ingredient, e.name AS enzyme LIMIT 6",
    "MATCH (i:Ingredient)-[r:BINDS_OR_CONFLICTS_WITH]->(f:Food) RETURN i.name AS ingredient, f.name AS food, r.min_gap_hours AS gap_hours, r.severity AS severity",
    "MATCH (m:Medicine)-[r:SAFE_ALTERNATIVE_TO]->(target:Medicine) RETURN m.name AS alternative, target.name AS replaces, r.reason AS reason",
    "MATCH (s:Symptom)<-[r:CAN_CAUSE]-(i:Ingredient) RETURN s.name AS symptom, i.name AS ingredient, r.frequency AS frequency LIMIT 8"
  ];
  const choice = samples[Math.floor(Math.random() * samples.length)];
  document.getElementById('replInput').value = choice;
}

// 16. TAB SWITCHING (4 EQUAL TABS)
function switchTab(tabKey) {
  document.querySelectorAll('.tab-item').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(p => p.classList.remove('active'));

  const tabIndexMap = { 'clinical': 0, 'schedule': 1, 'organ': 2, 'cypher': 3 };
  const targetIndex = tabIndexMap[tabKey] !== undefined ? tabIndexMap[tabKey] : 0;

  const buttons = document.querySelectorAll('.tab-item');
  if (buttons[targetIndex]) buttons[targetIndex].classList.add('active');

  const paneIdMap = {
    'clinical': 'tabClinical',
    'schedule': 'tabSchedule',
    'organ': 'tabOrgan',
    'cypher': 'tabCypher'
  };
  const pane = document.getElementById(paneIdMap[tabKey]);
  if (pane) pane.classList.add('active');
}
