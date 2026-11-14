// SafeMeds - Interactive Client-side Graph Application

let catalog = { medicines: [], foods: [], conditions: [], symptoms: [] };
let selectedMedicines = new Set();
let selectedFoods = new Set();
let selectedConditions = new Set();
let simulation = null;
let svg = null;
let g = null;
let zoom = null;

// Initialize upon DOM load
document.addEventListener('DOMContentLoaded', async () => {
  initGraph();
  await loadHealth();
  await loadCatalog();
  setupSearch();
  // Auto-load preset 1 by default so judges see an immediate result!
  loadPreset('preset_1');
});

// 1. HEALTH STATUS & DB BADGE
async function loadHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    if (data.status === 'healthy') {
      const dbPathEl = document.getElementById('dbPathDisplay');
      dbPathEl.textContent = `${data.database.rel_path} (${data.database.size_kb} KB)`;
    }
  } catch (e) {
    console.error('Health check failed', e);
  }
}

// 2. LOAD CATALOG
async function loadCatalog() {
  try {
    const res = await fetch('/api/catalog');
    catalog = await res.json();

    renderMedicines(catalog.medicines);
    renderFoods(catalog.foods);
    renderConditions(catalog.conditions);
    renderSymptoms(catalog.symptoms);
  } catch (e) {
    console.error('Failed to load catalog', e);
  }
}

function renderMedicines(meds) {
  const container = document.getElementById('medList');
  container.innerHTML = '';
  meds.forEach(m => {
    const pill = document.createElement('div');
    pill.className = `pill-item ${selectedMedicines.has(m.name) ? 'active' : ''}`;
    pill.dataset.name = m.name;
    const badge = m.is_brand ? `<span style="font-size:0.6rem;opacity:0.75;background:rgba(255,255,255,0.1);padding:1px 4px;border-radius:3px;">Brand</span>` : '';
    pill.innerHTML = `<span>${m.name}</span> ${badge}`;
    pill.onclick = () => toggleMedicine(m.name);
    container.appendChild(pill);
  });
  updateCounters();
}

function renderFoods(foods) {
  const container = document.getElementById('foodList');
  container.innerHTML = '';
  foods.forEach(f => {
    const pill = document.createElement('div');
    pill.className = `pill-item food-pill ${selectedFoods.has(f.name) ? 'active' : ''}`;
    pill.textContent = f.name;
    pill.title = f.notes || '';
    pill.onclick = () => toggleFood(f.name);
    container.appendChild(pill);
  });
  updateCounters();
}

function renderConditions(conds) {
  const container = document.getElementById('condList');
  container.innerHTML = '';
  conds.forEach(c => {
    const pill = document.createElement('div');
    pill.className = `pill-item cond-pill ${selectedConditions.has(c.name) ? 'active' : ''}`;
    pill.textContent = c.name;
    pill.onclick = () => toggleCondition(c.name);
    container.appendChild(pill);
  });
  updateCounters();
}

function renderSymptoms(symptoms) {
  const select = document.getElementById('symptomSelect');
  select.innerHTML = '<option value="">-- Choose a symptom to trace --</option>';
  symptoms.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.name;
    opt.textContent = `${s.name} (${s.severity})`;
    select.appendChild(opt);
  });
}

function setupSearch() {
  const search = document.getElementById('medSearch');
  search.addEventListener('input', (e) => {
    const term = e.target.value.toLowerCase();
    const pills = document.querySelectorAll('#medList .pill-item');
    pills.forEach(p => {
      const name = p.dataset.name.toLowerCase();
      p.style.display = name.includes(term) ? 'inline-flex' : 'none';
    });
  });
}

// TOGGLE HANDLERS
function toggleMedicine(name) {
  if (selectedMedicines.has(name)) {
    selectedMedicines.delete(name);
  } else {
    selectedMedicines.add(name);
  }
  updatePillClasses('#medList', selectedMedicines);
  updateCounters();
  triggerAnalysis();
}

function toggleFood(name) {
  if (selectedFoods.has(name)) {
    selectedFoods.delete(name);
  } else {
    selectedFoods.add(name);
  }
  updatePillClasses('#foodList', selectedFoods);
  updateCounters();
  triggerAnalysis();
}

function toggleCondition(name) {
  if (selectedConditions.has(name)) {
    selectedConditions.delete(name);
  } else {
    selectedConditions.add(name);
  }
  updatePillClasses('#condList', selectedConditions);
  updateCounters();
  triggerAnalysis();
}

function updatePillClasses(containerSelector, set) {
  const pills = document.querySelectorAll(`${containerSelector} .pill-item`);
  pills.forEach(p => {
    const name = p.dataset.name || p.textContent.trim();
    if (set.has(name)) {
      p.classList.add('active');
    } else {
      p.classList.remove('active');
    }
  });
}

function updateCounters() {
  document.getElementById('medCounter').textContent = `${selectedMedicines.size} selected`;
  document.getElementById('foodCounter').textContent = `${selectedFoods.size} selected`;
  document.getElementById('condCounter').textContent = `${selectedConditions.size} selected`;
}

function clearAllSelections() {
  selectedMedicines.clear();
  selectedFoods.clear();
  selectedConditions.clear();
  updatePillClasses('#medList', selectedMedicines);
  updatePillClasses('#foodList', selectedFoods);
  updatePillClasses('#condList', selectedConditions);
  updateCounters();
  document.getElementById('traceResult').style.display = 'none';
  triggerAnalysis();
}

// 3. PRESETS
async function loadPreset(presetId) {
  try {
    const res = await fetch('/api/presets');
    const presets = await res.json();
    const p = presets.find(x => x.id === presetId);
    if (!p) return;

    selectedMedicines = new Set(p.medicines);
    selectedFoods = new Set(p.foods);
    selectedConditions = new Set(p.conditions);

    updatePillClasses('#medList', selectedMedicines);
    updatePillClasses('#foodList', selectedFoods);
    updatePillClasses('#condList', selectedConditions);
    updateCounters();

    if (p.symptom) {
      document.getElementById('symptomSelect').value = p.symptom;
    }

    triggerAnalysis();
  } catch (e) {
    console.error('Failed to load preset', e);
  }
}

// 4. TRIGGER COMPREHENSIVE ANALYSIS
async function triggerAnalysis() {
  const reqBody = {
    medicines: Array.from(selectedMedicines),
    foods: Array.from(selectedFoods),
    conditions: Array.from(selectedConditions)
  };

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reqBody)
    });
    const data = await res.json();

    renderGraph(data.graph);
    renderClinicalWarnings(data.warnings, data.brand_overlaps, data.safe_alternatives);
    renderSchedule(data.schedule);
    renderOrganLoad(data.organ_load);
    renderExecutedQueries(data.queries_executed);
  } catch (e) {
    console.error('Analysis failed', e);
  }
}

// 5. GRAPH RENDERING (D3.JS FOCUS VIEW)
function initGraph() {
  const wrapper = document.getElementById('graphWrapper');
  const width = wrapper.clientWidth || 600;
  const height = wrapper.clientHeight || 500;

  svg = d3.select('#graphSvg')
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', [0, 0, width, height]);

  // Arrow markers for relationships
  svg.append('defs').selectAll('marker')
    .data(['normal', 'conflict', 'spacing', 'alternative'])
    .join('marker')
    .attr('id', d => `arrow-${d}`)
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 22)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('fill', d => {
      if (d === 'conflict') return '#ef4444';
      if (d === 'spacing') return '#f59e0b';
      if (d === 'alternative') return '#10b981';
      return '#64748b';
    })
    .attr('d', 'M0,-5L10,0L0,5');

  g = svg.append('g');

  zoom = d3.zoom()
    .scaleExtent([0.3, 3])
    .on('zoom', (event) => {
      g.attr('transform', event.transform);
    });

  svg.call(zoom);
}

function resetGraphZoom() {
  if (svg && zoom) {
    svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
  }
}

function renderGraph(graphData) {
  const emptyState = document.getElementById('emptyGraphState');
  if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
    emptyState.style.display = 'block';
    g.selectAll('*').remove();
    return;
  }
  emptyState.style.display = 'none';

  const wrapper = document.getElementById('graphWrapper');
  const width = wrapper.clientWidth || 600;
  const height = wrapper.clientHeight || 500;

  // D3 force simulation
  if (simulation) simulation.stop();

  g.selectAll('*').remove();

  const nodes = graphData.nodes.map(d => Object.assign({}, d));
  const edges = graphData.edges.map(d => Object.assign({}, d));

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id).distance(110))
    .force('charge', d3.forceManyBody().strength(-380))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(36));

  // Edges
  const link = g.append('g')
    .selectAll('line')
    .data(edges)
    .join('line')
    .attr('stroke', d => {
      if (d.severity === 'conflict' || d.type === 'DIRECT_INTERACTION' || d.type === 'BRAND_OVERLAP') return '#ef4444';
      if (d.severity === 'spacing') return '#f59e0b';
      if (d.type === 'SAFE_ALTERNATIVE_TO') return '#10b981';
      return '#334155';
    })
    .attr('stroke-width', d => (d.severity === 'conflict' || d.type === 'SAFE_ALTERNATIVE_TO') ? 2.5 : 1.5)
    .attr('stroke-dasharray', d => d.severity === 'spacing' ? '4 3' : 'none')
    .attr('marker-end', d => `url(#arrow-${d.type === 'SAFE_ALTERNATIVE_TO' ? 'alternative' : (d.severity === 'conflict' ? 'conflict' : (d.severity === 'spacing' ? 'spacing' : 'normal'))})`);

  // Edge Labels
  const edgeLabel = g.append('g')
    .selectAll('text')
    .data(edges)
    .join('text')
    .attr('font-size', '8px')
    .attr('font-family', 'sans-serif')
    .attr('fill', d => d.severity === 'conflict' ? '#fca5a5' : '#94a3b8')
    .attr('text-anchor', 'middle')
    .text(d => d.label || d.type);

  // Nodes
  const node = g.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended));

  node.append('circle')
    .attr('r', d => d.label === 'Medicine' ? 18 : 14)
    .attr('fill', d => {
      if (d.label === 'Medicine') return d.extra && d.extra.is_alt ? '#10b981' : '#06b6d4';
      if (d.label === 'Ingredient') return '#8b5cf6';
      if (d.label === 'Enzyme') return '#eab308';
      if (d.label === 'Food') return '#f59e0b';
      if (d.label === 'Condition') return '#ef4444';
      if (d.label === 'Organ') return '#ec4899';
      if (d.label === 'Symptom') return '#f97316';
      return '#64748b';
    })
    .attr('stroke', '#0f172a')
    .attr('stroke-width', 2);

  node.append('text')
    .attr('dy', d => d.label === 'Medicine' ? 28 : 24)
    .attr('text-anchor', 'middle')
    .attr('fill', '#f1f5f9')
    .attr('font-size', '10px')
    .attr('font-weight', '600')
    .text(d => d.title);

  // Tooltip
  const tooltip = d3.select('#graphTooltip');
  node.on('mouseover', (event, d) => {
    tooltip.style('display', 'block')
      .html(`<strong>${d.title}</strong> <span style="opacity:0.7">(${d.label})</span><br>${d.category || ''}`);
  })
  .on('mousemove', (event) => {
    tooltip.style('left', (event.pageX + 12) + 'px')
      .style('top', (event.pageY - 20) + 'px');
  })
  .on('mouseout', () => tooltip.style('display', 'none'));

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);

    edgeLabel
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2 - 3);

    node
      .attr('transform', d => `translate(${d.x},${d.y})`);
  });

  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
  }
  function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
  }
  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
  }
}

// 6. RENDER CLINICAL WARNINGS & ALTERNATIVES
function renderClinicalWarnings(warnings, brandOverlaps, safeAlts) {
  // Brand Overlap
  const ddContainer = document.getElementById('doubleDoseAlerts');
  ddContainer.innerHTML = '';
  if (brandOverlaps && brandOverlaps.length > 0) {
    brandOverlaps.forEach(dd => {
      const card = document.createElement('div');
      card.className = 'alert-card double-dose';
      card.innerHTML = `
        <div class="alert-title-row">
          <span class="alert-title">⚠️ HIDDEN DOUBLE DOSE DETECTED</span>
          <span class="alert-sev-badge">OVERDOSE RISK</span>
        </div>
        <div class="alert-desc">${dd.warning}</div>
      `;
      ddContainer.appendChild(card);
    });
  }

  // Warnings
  const wContainer = document.getElementById('warningsList');
  wContainer.innerHTML = '';
  if (warnings && warnings.length > 0) {
    warnings.forEach(w => {
      const card = document.createElement('div');
      const sevClass = w.severity === 'Severe' ? 'severe' : 'high';
      card.className = `alert-card ${sevClass}`;
      card.innerHTML = `
        <div class="alert-title-row">
          <span class="alert-title">${w.title}</span>
          <span class="alert-sev-badge">${w.severity}</span>
        </div>
        <div class="alert-desc">${w.details}</div>
      `;
      wContainer.appendChild(card);
    });
  } else {
    wContainer.innerHTML = '<p class="placeholder-text">No active conflicts detected. Select medicines or load a preset.</p>';
  }

  // Safe Alternatives
  const altContainer = document.getElementById('alternativesList');
  altContainer.innerHTML = '';
  if (safeAlts && safeAlts.length > 0) {
    safeAlts.forEach(alt => {
      const card = document.createElement('div');
      card.className = 'alt-card';
      card.innerHTML = `
        <h4>✅ Consider: ${alt.alternative}</h4>
        <p style="color:#94a3b8;margin-bottom:4px;font-size:0.72rem;">Replaces: <strong>${alt.replaces}</strong> for <em>${alt.condition}</em></p>
        <p style="color:#cbd5e1;line-height:1.35;">${alt.reason}</p>
      `;
      altContainer.appendChild(card);
    });
  } else {
    altContainer.innerHTML = '<p class="placeholder-text">Alternatives appear automatically when a blocked pathway or conflict is detected.</p>';
  }
}

// 7. RENDER 5-SLOT TIMELINE
function renderSchedule(schedule) {
  const container = document.getElementById('scheduleTimeline');
  container.innerHTML = '';
  if (!schedule || schedule.length === 0) {
    container.innerHTML = '<p class="placeholder-text">Select medications to generate an optimized daily routine.</p>';
    return;
  }

  schedule.forEach(slotData => {
    const card = document.createElement('div');
    card.className = 'slot-card';
    
    let itemsHtml = '';
    slotData.items.forEach(it => {
      itemsHtml += `
        <div class="slot-item">
          <div class="slot-item-med">${it.medicine}</div>
          <div class="slot-item-note">${it.instructions}</div>
        </div>
      `;
    });

    card.innerHTML = `
      <div class="slot-header">
        <span class="slot-title">${slotData.slot}</span>
        <span style="font-size:0.68rem;color:#94a3b8;">${slotData.items.length} item(s)</span>
      </div>
      <div>${itemsHtml}</div>
    `;
    container.appendChild(card);
  });
}

// 8. RENDER ORGAN LOAD
function renderOrganLoad(loads) {
  const organs = ['Kidney', 'Liver', 'Stomach', 'Brain'];
  const maxScale = 12; // visual ceiling

  let totalScore = 0;
  organs.forEach(org => {
    const key = org === 'Stomach' ? 'Stomach / GI' : (org === 'Brain' ? 'Brain / CNS' : org);
    const score = loads[key] || 0;
    totalScore += score;

    const valEl = document.getElementById(`score${org}`);
    const barEl = document.getElementById(`bar${org}`);

    if (valEl) valEl.textContent = score;
    if (barEl) {
      const pct = Math.min(100, Math.round((score / maxScale) * 100));
      barEl.style.width = `${pct}%`;
      barEl.className = 'meter-bar-fill';
      if (score >= 8) barEl.classList.add('high');
      else if (score >= 4) barEl.classList.add('medium');
    }
  });

  const summary = document.getElementById('organSummary');
  if (totalScore >= 12) {
    summary.innerHTML = `<span style="color:#ef4444;font-weight:600;">⚠️ High Cumulative Organ Strain:</span> Multiple organs face simultaneous metabolic load. Monitor renal function and GI tolerance.`;
  } else if (totalScore >= 6) {
    summary.innerHTML = `<span style="color:#f59e0b;font-weight:600;">Moderate Cumulative Burden:</span> Standard clinical monitoring advised.`;
  } else {
    summary.innerHTML = `<span style="color:#10b981;font-weight:600;">Low Cumulative Burden:</span> Organ clearance within typical physiological parameters.`;
  }
}

// 9. RENDER EXECUTED QUERIES
function renderExecutedQueries(queries) {
  const container = document.getElementById('executedQueriesList');
  container.innerHTML = '';
  if (!queries || queries.length === 0) return;

  queries.forEach(q => {
    const div = document.createElement('div');
    div.className = 'cypher-snippet';
    div.innerHTML = `
      <span class="cypher-tag">${q.name}</span>
      <div class="cypher-code">${q.query}</div>
    `;
    container.appendChild(div);
  });
}

// 10. REVERSE SYMPTOM TRACER
async function traceSymptom() {
  const symptom = document.getElementById('symptomSelect').value;
  if (!symptom) {
    alert('Please select a symptom to trace.');
    return;
  }

  const resultBox = document.getElementById('traceResult');
  resultBox.style.display = 'block';
  resultBox.innerHTML = '<span style="color:#94a3b8;">Traversing Relate graph backwards...</span>';

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

    if (data.culprits && data.culprits.length > 0) {
      let culpritHtml = `<strong>Tracing Culprits for "${symptom}":</strong><br>`;
      data.culprits.forEach(c => {
        culpritHtml += `
          <div style="margin-top:4px;">
            ⚠️ <strong>${c.medicine}</strong> (${c.ingredient}) - <span style="color:#cbd5e1">${c.frequency}</span><br>
            <span style="color:#94a3b8;font-size:0.68rem;">Mechanism: ${c.mechanism}</span>
          </div>
        `;
      });
      resultBox.innerHTML = culpritHtml;

      // Render the symptom trace subgraph in the center view!
      if (data.graph) {
        renderGraph(data.graph);
      }
    } else {
      resultBox.innerHTML = `No direct causal link found between "${symptom}" and your currently selected medications.`;
    }
  } catch (e) {
    console.error('Symptom trace failed', e);
    resultBox.innerHTML = 'Error executing symptom trace.';
  }
}

// 11. LIVE CYPHER REPL
async function executeCustomCypher() {
  const query = document.getElementById('customCypherInput').value.trim();
  if (!query) return;

  const resultArea = document.getElementById('replResult');
  resultArea.style.display = 'block';
  resultArea.innerHTML = '<span style="color:#94a3b8;">Executing query against ./data/safemeds.rl...</span>';

  try {
    const res = await fetch('/api/cypher', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query })
    });
    const data = await res.json();

    if (res.status !== 200) {
      resultArea.innerHTML = `<span style="color:#ef4444;">Error: ${data.detail || 'Query execution failed'}</span>`;
      return;
    }

    if (!data.rows || data.rows.length === 0) {
      resultArea.innerHTML = `<span style="color:#10b981;">Query returned 0 rows (${data.elapsed_ms} ms).</span>`;
      return;
    }

    let tableHtml = `<div style="color:#10b981;margin-bottom:6px;">✓ Returned ${data.count} row(s) in ${data.elapsed_ms} ms:</div>`;
    tableHtml += '<table class="repl-table"><thead><tr>';
    data.columns.forEach(c => tableHtml += `<th>${c}</th>`);
    tableHtml += '</tr></thead><tbody>';

    data.rows.slice(0, 15).forEach(row => {
      tableHtml += '<tr>';
      data.columns.forEach(c => tableHtml += `<td>${row[c] !== null ? row[c] : '<em>null</em>'}</td>`);
      tableHtml += '</tr>';
    });
    tableHtml += '</tbody></table>';

    if (data.count > 15) {
      tableHtml += `<div style="font-size:0.65rem;color:#94a3b8;margin-top:4px;">Showing first 15 of ${data.count} rows.</div>`;
    }

    resultArea.innerHTML = tableHtml;
  } catch (e) {
    resultArea.innerHTML = `<span style="color:#ef4444;">Failed to execute Cypher: ${e.message}</span>`;
  }
}

function loadSampleCypher() {
  const samples = [
    "MATCH (m:Medicine)-[:CONTAINS]->(i:Ingredient)-[:REQUIRES_ENZYME]->(e:Enzyme) RETURN m.name AS med, i.name AS ingredient, e.name AS enzyme LIMIT 8",
    "MATCH (i:Ingredient)-[r:BINDS_OR_CONFLICTS_WITH]->(f:Food) RETURN i.name AS ingredient, f.name AS food, r.min_gap_hours AS gap_hours, r.severity AS severity",
    "MATCH (m:Medicine)-[r:SAFE_ALTERNATIVE_TO]->(target:Medicine) RETURN m.name AS alternative, target.name AS target_drug, r.reason AS reason",
    "MATCH (s:Symptom)<-[r:CAN_CAUSE]-(i:Ingredient) RETURN s.name AS symptom, i.name AS ingredient, r.frequency AS frequency LIMIT 10"
  ];
  const choice = samples[Math.floor(Math.random() * samples.length)];
  document.getElementById('customCypherInput').value = choice;
}

// 12. TAB SWITCHING
function switchRightTab(tabName) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

  if (tabName === 'clinical') {
    document.querySelectorAll('.tab-btn')[0].classList.add('active');
    document.getElementById('tabClinical').classList.add('active');
  } else if (tabName === 'schedule') {
    document.querySelectorAll('.tab-btn')[1].classList.add('active');
    document.getElementById('tabSchedule').classList.add('active');
  } else if (tabName === 'organ') {
    document.querySelectorAll('.tab-btn')[2].classList.add('active');
    document.getElementById('tabOrgan').classList.add('active');
  } else if (tabName === 'cypher') {
    document.querySelectorAll('.tab-btn')[3].classList.add('active');
    document.getElementById('tabCypher').classList.add('active');
  }
}
