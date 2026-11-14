// ==========================================================================
// SafeMeds — 3D Pharmaceutical Interactive Studio (Three.js)
// Sky-Blue, Deep Royal Blue, Crisp White & Bright Yellow Visual Experience
// ==========================================================================

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// Application State
let catalog = { medicines: [], foods: [], conditions: [], symptoms: [] };
let selectedMedicines = new Set();
let selectedFoods = new Set();
let selectedConditions = new Set();
let activeTraceResult = null;
let currentAnalysisData = null;
let activePresetId = 'preset_1';

// Three.js Scene Variables
let scene, camera, renderer, controls;
let threeObjects = []; // 3D node meshes
let pathwayTubes = []; // 3D pathway curves
let energyPulses = []; // Animated energy spheres
let lightRibbons = []; // Background drifting ribbons
let canvasContainer = null;
let raycaster, mouse;

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', async () => {
  canvasContainer = document.getElementById('centerStageWrapper');
  initThreeStage();
  setupAutocomplete();
  setupEventListeners();

  await loadHealth();
  await loadCatalog();

  // AUTO-LOAD PRESET 1 ON INITIAL PAGE LOAD (NEVER EMPTY)
  await switchPreset('preset_1');

  // Animation Loop
  animateStage();
});

// ==========================================================================
// 1. THREE.JS 3D STAGE SETUP
// ==========================================================================
function initThreeStage() {
  const canvas = document.getElementById('webglCanvas');
  const width = canvasContainer.clientWidth || 800;
  const height = canvasContainer.clientHeight || 600;

  // Scene
  scene = new THREE.Scene();

  // Camera
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
  camera.position.set(0, 0, 19.5);

  // Renderer
  renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance'
  });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  // OrbitControls
  controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.maxDistance = 34;
  controls.minDistance = 6;
  controls.maxPolarAngle = Math.PI * 0.85;
  controls.minPolarAngle = Math.PI * 0.15;
  controls.target.set(0, 0, 0);

  // 3-Point Studio Lighting
  const hemiLight = new THREE.HemisphereLight(0xFFFFFF, 0x0B3D91, 0.95);
  scene.add(hemiLight);

  const keyLight = new THREE.DirectionalLight(0xFFFFFF, 1.45);
  keyLight.position.set(9, 13, 11);
  scene.add(keyLight);

  const rimLight = new THREE.DirectionalLight(0x38BDF8, 1.1);
  rimLight.position.set(-11, -6, -9);
  scene.add(rimLight);

  const fillLight = new THREE.DirectionalLight(0xFDE047, 0.35);
  fillLight.position.set(0, -9, 8);
  scene.add(fillLight);

  // Ambient Drifting Light Stream Ribbons in Background
  createLightStreamRibbons();

  // Raycaster for 3D interactions
  raycaster = new THREE.Raycaster();
  mouse = new THREE.Vector2();

  window.addEventListener('resize', onWindowResize);
  canvas.addEventListener('click', onCanvasClick);
  document.getElementById('btnResetCamera').addEventListener('click', resetCameraView);
}

function onWindowResize() {
  if (!canvasContainer || !camera || !renderer) return;
  const width = canvasContainer.clientWidth;
  const height = canvasContainer.clientHeight;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}

function resetCameraView() {
  if (!controls || !camera) return;
  camera.position.set(0, 0, 19.5);
  controls.target.set(0, 0, 0);
  controls.update();
}

// Sweeping Translucent Background Light Streams
function createLightStreamRibbons() {
  const ribbonColors = [0x38BDF8, 0xBAE6FD, 0x0284C7];
  for (let i = 0; i < 3; i++) {
    const points = [];
    const baseY = (i - 1) * 4;
    for (let x = -14; x <= 14; x += 3.5) {
      points.push(new THREE.Vector3(
        x,
        baseY + Math.sin(x * 0.35 + i) * 2.2,
        -4.5 - i * 0.8
      ));
    }
    const curve = new THREE.CatmullRomCurve3(points);
    const geom = new THREE.TubeGeometry(curve, 64, 0.06, 8, false);
    const mat = new THREE.MeshBasicMaterial({
      color: ribbonColors[i % ribbonColors.length],
      transparent: true,
      opacity: 0.28,
      blending: THREE.AdditiveBlending
    });
    const ribbon = new THREE.Mesh(geom, mat);
    scene.add(ribbon);
    lightRibbons.push({ mesh: ribbon, speed: (i + 1) * 0.0015 });
  }
}

// ==========================================================================
// 2. PROCEDURAL 3D PHARMACEUTICAL MODELS (MeshPhysicalMaterial)
// ==========================================================================

// A. 3D Medicine Capsule (Upper Pharma Blue, Lower Pearl White)
function createMedicineCapsule(name, isBrand) {
  const group = new THREE.Group();

  const blueMat = new THREE.MeshPhysicalMaterial({
    color: 0x0284C7,
    roughness: 0.15,
    clearcoat: 1.0,
    clearcoatRoughness: 0.1,
    metalness: 0.05
  });

  const whiteMat = new THREE.MeshPhysicalMaterial({
    color: 0xFFFFFF,
    roughness: 0.15,
    clearcoat: 1.0,
    clearcoatRoughness: 0.1,
    metalness: 0.05
  });

  const ringMat = new THREE.MeshStandardMaterial({
    color: 0xBAE6FD,
    metalness: 0.6,
    roughness: 0.3
  });

  const radius = 0.38;
  const cylinderHeight = 0.38;

  // Upper Blue Half
  const topCyl = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, cylinderHeight, 32), blueMat);
  topCyl.position.y = cylinderHeight / 2;
  group.add(topCyl);

  const topDome = new THREE.Mesh(new THREE.SphereGeometry(radius, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), blueMat);
  topDome.position.y = cylinderHeight;
  group.add(topDome);

  // Lower White Half
  const botCyl = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, cylinderHeight, 32), whiteMat);
  botCyl.position.y = -cylinderHeight / 2;
  group.add(botCyl);

  const botDome = new THREE.Mesh(new THREE.SphereGeometry(radius, 32, 16, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), whiteMat);
  botDome.position.y = -cylinderHeight;
  group.add(botDome);

  // Central Seal Ring
  const ring = new THREE.Mesh(new THREE.CylinderGeometry(radius + 0.012, radius + 0.012, 0.04, 32), ringMat);
  group.add(ring);

  group.rotation.z = 0.38;
  group.rotation.x = 0.22;
  group.userData = { title: name, category: isBrand ? 'Brand Medication' : 'Generic Medicine', type: 'Medicine' };

  return group;
}

// B. 3D Dietary Amber Dropper Bottle
function createFoodDropper(name) {
  const group = new THREE.Group();

  const amberGlassMat = new THREE.MeshPhysicalMaterial({
    color: 0xD97706,
    roughness: 0.12,
    clearcoat: 1.0,
    transmission: 0.55,
    transparent: true,
    opacity: 0.88
  });

  const capMat = new THREE.MeshPhysicalMaterial({
    color: 0xFFFFFF,
    roughness: 0.2,
    clearcoat: 0.8
  });

  const rubberMat = new THREE.MeshStandardMaterial({
    color: 0x0F172A,
    roughness: 0.7
  });

  // Bottle Body
  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.38, 0.42, 0.85, 24), amberGlassMat);
  group.add(body);

  // Neck
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.22, 0.28, 24), amberGlassMat);
  neck.position.y = 0.54;
  group.add(neck);

  // Cap
  const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.24, 0.2, 24), capMat);
  cap.position.y = 0.74;
  group.add(cap);

  // Rubber bulb
  const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.15, 16, 16), rubberMat);
  bulb.position.y = 0.92;
  group.add(bulb);

  group.rotation.x = 0.15;
  group.userData = { title: name, category: 'Dietary Substance', type: 'Food' };
  return group;
}

// C. 3D Condition Hexagonal Prism
function createConditionPrism(name) {
  const group = new THREE.Group();

  const prismMat = new THREE.MeshPhysicalMaterial({
    color: 0x4338CA,
    roughness: 0.18,
    clearcoat: 1.0,
    clearcoatRoughness: 0.1
  });

  const coreMat = new THREE.MeshBasicMaterial({
    color: 0x818CF8,
    wireframe: true
  });

  const hexPrism = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 0.55, 6), prismMat);
  group.add(hexPrism);

  const innerCore = new THREE.Mesh(new THREE.IcosahedronGeometry(0.28, 0), coreMat);
  group.add(innerCore);

  group.rotation.x = 0.25;
  group.rotation.y = 0.35;
  group.userData = { title: name, category: 'Health Condition', type: 'Condition' };
  return group;
}

// D. 3D Active Molecule Cluster (Pearl-Cyan Core with 3 Bonded Orbiting Spheres)
function createMolecularCluster(name) {
  const group = new THREE.Group();

  const coreMat = new THREE.MeshPhysicalMaterial({
    color: 0x38BDF8,
    roughness: 0.1,
    clearcoat: 1.0,
    clearcoatRoughness: 0.08
  });

  const atomMat = new THREE.MeshPhysicalMaterial({
    color: 0xFFFFFF,
    roughness: 0.15,
    clearcoat: 0.9
  });

  const rodMat = new THREE.MeshStandardMaterial({
    color: 0x94A3B8,
    metalness: 0.8,
    roughness: 0.2
  });

  // Central Sphere
  const core = new THREE.Mesh(new THREE.SphereGeometry(0.38, 24, 24), coreMat);
  group.add(core);

  // Orbiting Atoms
  const bondOrbitGroup = new THREE.Group();
  for (let i = 0; i < 3; i++) {
    const angle = (i * Math.PI * 2) / 3;
    const dist = 0.72;
    const x = Math.cos(angle) * dist;
    const y = Math.sin(angle) * dist * 0.7;
    const z = Math.sin(angle) * 0.45;

    const atom = new THREE.Mesh(new THREE.SphereGeometry(0.18, 16, 16), atomMat);
    atom.position.set(x, y, z);
    bondOrbitGroup.add(atom);

    // Connecting Rod
    const rodCurve = new THREE.LineCurve3(new THREE.Vector3(0, 0, 0), new THREE.Vector3(x, y, z));
    const rod = new THREE.Mesh(new THREE.TubeGeometry(rodCurve, 8, 0.035, 8, false), rodMat);
    bondOrbitGroup.add(rod);
  }

  group.add(bondOrbitGroup);
  group.userData = { title: name, category: 'Generic Molecule', type: 'Ingredient', orbit: bondOrbitGroup };
  return group;
}

// E. 3D Crystalline Conflict Point with Halo Ring
function createConflictCrystal(title, isAmber) {
  const group = new THREE.Group();

  const colorHex = isAmber ? 0xFACC15 : 0xEF4444;

  const crystalMat = new THREE.MeshPhysicalMaterial({
    color: colorHex,
    roughness: 0.1,
    clearcoat: 1.0,
    emissive: colorHex,
    emissiveIntensity: 0.45
  });

  const haloMat = new THREE.MeshStandardMaterial({
    color: colorHex,
    emissive: colorHex,
    emissiveIntensity: 0.65,
    roughness: 0.3
  });

  const crystal = new THREE.Mesh(new THREE.IcosahedronGeometry(0.5, 0), crystalMat);
  group.add(crystal);

  // Rotating Warning Ring
  const halo = new THREE.Mesh(new THREE.TorusGeometry(0.85, 0.045, 16, 48), haloMat);
  halo.rotation.x = Math.PI / 2.5;
  group.add(halo);

  group.userData = { title: title, category: isAmber ? 'Time-Spacing Gap' : 'Clinical Collision', type: 'Conflict', halo: halo };
  return group;
}

// F. 3D Safe Alternative Capsule with Glowing Green Safety Ring
function createSafeAlternativeCapsule(name) {
  const group = new THREE.Group();

  const greenMat = new THREE.MeshPhysicalMaterial({
    color: 0x10B981,
    roughness: 0.15,
    clearcoat: 1.0,
    emissive: 0x059669,
    emissiveIntensity: 0.25
  });

  const whiteMat = new THREE.MeshPhysicalMaterial({
    color: 0xFFFFFF,
    roughness: 0.15,
    clearcoat: 1.0
  });

  const safetyRingMat = new THREE.MeshStandardMaterial({
    color: 0x34D399,
    emissive: 0x10B981,
    emissiveIntensity: 0.75,
    roughness: 0.2
  });

  const radius = 0.38;
  const cylinderHeight = 0.38;

  // Upper Green Half
  const topCyl = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, cylinderHeight, 32), greenMat);
  topCyl.position.y = cylinderHeight / 2;
  group.add(topCyl);

  const topDome = new THREE.Mesh(new THREE.SphereGeometry(radius, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), greenMat);
  topDome.position.y = cylinderHeight;
  group.add(topDome);

  // Lower White Half
  const botCyl = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, cylinderHeight, 32), whiteMat);
  botCyl.position.y = -cylinderHeight / 2;
  group.add(botCyl);

  const botDome = new THREE.Mesh(new THREE.SphereGeometry(radius, 32, 16, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), whiteMat);
  botDome.position.y = -cylinderHeight;
  group.add(botDome);

  // Outer Glowing Safety Ring
  const safetyRing = new THREE.Mesh(new THREE.TorusGeometry(0.95, 0.045, 16, 48), safetyRingMat);
  safetyRing.rotation.x = Math.PI / 3;
  group.add(safetyRing);

  group.rotation.z = -0.35;
  group.userData = { title: name, category: 'Recommended Safe Swap', type: 'Alternative', safetyRing: safetyRing };
  return group;
}

// ==========================================================================
// 3. ZERO-HAIRBALL 4-LANE 3D ARCHITECTURE
// ==========================================================================
function clearThreeStage() {
  threeObjects.forEach(obj => scene.remove(obj.mesh));
  threeObjects = [];

  pathwayTubes.forEach(t => scene.remove(t.mesh));
  pathwayTubes = [];

  energyPulses.forEach(p => scene.remove(p.mesh));
  energyPulses = [];

  const labelsOverlay = document.getElementById('labelsOverlay');
  if (labelsOverlay) labelsOverlay.innerHTML = '';
}

function renderThreeStage(data) {
  clearThreeStage();

  const notice = document.getElementById('stageAllClearNotice');
  if (!data || !data.graph || !data.graph.nodes) {
    if (notice) notice.style.display = 'none';
    return;
  }

  // Filter out Organ nodes & STRESSES_ORGAN edges
  const nonOrganNodes = data.graph.nodes.filter(n => n.label !== 'Organ');

  // Columns data
  const col1Nodes = nonOrganNodes.filter(n => ['Medicine', 'Food', 'Condition'].includes(n.label) && !n.extra?.is_alt);
  const col2Nodes = nonOrganNodes.filter(n => n.label === 'Ingredient');

  // Conflict points
  const col3Items = [];
  const enzymeNodes = nonOrganNodes.filter(n => n.label === 'Enzyme');
  enzymeNodes.forEach(e => col3Items.push({ title: `${e.title} Blocked`, isAmber: false, type: 'Enzyme' }));
  (data.brand_overlaps || []).forEach(bo => col3Items.push({ title: 'Double Dose Overdose', isAmber: false, type: 'BrandOverlap', sub: bo.ingredient }));
  (data.warnings || []).forEach(w => {
    if (w.type.includes('Food') || w.type.includes('Timing')) {
      col3Items.push({ title: '3h Food/Drug Gap', isAmber: true, type: 'TimingGap' });
    }
  });

  const col4Alts = data.safe_alternatives || [];

  // If no items
  if (col1Nodes.length === 0 && col2Nodes.length === 0) {
    if (notice) notice.style.display = 'none';
    return;
  }

  // All clear check
  if (col3Items.length === 0 && col4Alts.length === 0 && col1Nodes.length > 0) {
    if (notice) notice.style.display = 'block';
  } else {
    if (notice) notice.style.display = 'none';
  }

  // 1. Position Column 1: Intake (X = -7.5)
  col1Nodes.forEach((node, i) => {
    let mesh;
    if (node.label === 'Medicine') mesh = createMedicineCapsule(node.title, node.category?.includes('Brand'));
    else if (node.label === 'Food') mesh = createFoodDropper(node.title);
    else mesh = createConditionPrism(node.title);

    const y = calculateYPosition(i, col1Nodes.length);
    mesh.position.set(-7.5, y, Math.sin(i) * 0.4);
    scene.add(mesh);
    registerThreeNode(mesh, node.title, node.label, 1);
  });

  // 2. Position Column 2: Ingredients (X = -2.5)
  col2Nodes.forEach((node, i) => {
    const mesh = createMolecularCluster(node.title);
    const y = calculateYPosition(i, col2Nodes.length);
    mesh.position.set(-2.5, y, Math.cos(i) * 0.4);
    scene.add(mesh);
    registerThreeNode(mesh, node.title, 'Ingredient', 2);
  });

  // 3. Position Column 3: Conflicts / Enzyme Blocks (X = +2.5)
  col3Items.forEach((item, i) => {
    const mesh = createConflictCrystal(item.title, item.isAmber);
    const y = calculateYPosition(i, col3Items.length);
    mesh.position.set(2.5, y, Math.sin(i + 1) * 0.4);
    scene.add(mesh);
    registerThreeNode(mesh, item.title, item.isAmber ? 'Time-Spacing' : 'Conflict', 3);
  });

  // 4. Position Column 4: Safe Alternatives (X = +7.5)
  col4Alts.forEach((alt, i) => {
    const mesh = createSafeAlternativeCapsule(alt.alternative);
    const y = calculateYPosition(i, col4Alts.length);
    mesh.position.set(7.5, y, Math.cos(i + 2) * 0.4);
    scene.add(mesh);
    registerThreeNode(mesh, alt.alternative, 'Safe Alternative', 4);
  });

  // Build Glowing Curved 3D Pathways & Energy Pulses
  buildPathwayTubes(data, col3Items, col4Alts);
}

function calculateYPosition(index, total) {
  if (total <= 1) return 0;
  const spacing = Math.min(2.2, 7.0 / (total - 1));
  return ((total - 1) / 2 - index) * spacing;
}

function registerThreeNode(mesh, title, category, colIndex) {
  // Create 2D Projected HTML Label
  const overlay = document.getElementById('labelsOverlay');
  const labelDiv = document.createElement('div');
  labelDiv.className = 'node-projected-label';
  
  let tagClass = 'tag-med';
  if (category === 'Ingredient') tagClass = 'tag-ing';
  else if (category === 'Conflict') tagClass = 'tag-conf';
  else if (category === 'Time-Spacing') tagClass = 'tag-amber';
  else if (category === 'Safe Alternative') tagClass = 'tag-safe';

  labelDiv.innerHTML = `
    <span class="label-category-tag ${tagClass}">${category}</span>
    <div class="label-title-text">${title}</div>
  `;

  labelDiv.onclick = () => {
    highlightNodeInteractions(title);
  };

  overlay.appendChild(labelDiv);

  threeObjects.push({
    mesh: mesh,
    title: title,
    category: category,
    colIndex: colIndex,
    labelEl: labelDiv
  });
}

// 4. GLOWING 3D CURVED TUBES & ANIMATED MOVING ENERGY BEADS
function buildPathwayTubes(data, col3Items, col4Alts) {
  function addTubeConnection(srcObj, tgtObj, colorHex) {
    if (!srcObj || !tgtObj) return;

    const p1 = srcObj.mesh.position.clone();
    const p2 = tgtObj.mesh.position.clone();

    // Arch outward in Z
    const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
    mid.z += 1.1;

    const curve = new THREE.CatmullRomCurve3([p1, mid, p2]);
    const tubeGeom = new THREE.TubeGeometry(curve, 36, 0.045, 8, false);
    const tubeMat = new THREE.MeshStandardMaterial({
      color: colorHex,
      emissive: colorHex,
      emissiveIntensity: 0.55,
      roughness: 0.3
    });

    const tubeMesh = new THREE.Mesh(tubeGeom, tubeMat);
    scene.add(tubeMesh);
    pathwayTubes.push({ mesh: tubeMesh, src: srcObj, tgt: tgtObj, curve: curve });

    // Moving Glowing Energy Pulse Bead
    const pulseMat = new THREE.MeshBasicMaterial({ color: 0xFFFFFF });
    const pulseMesh = new THREE.Mesh(new THREE.SphereGeometry(0.12, 12, 12), pulseMat);
    scene.add(pulseMesh);
    energyPulses.push({ mesh: pulseMesh, curve: curve, t: Math.random(), speed: 0.007 + Math.random() * 0.004 });
  }

  // Connect Col 1 (Intake) -> Col 2 (Ingredient)
  const col1 = threeObjects.filter(o => o.colIndex === 1);
  const col2 = threeObjects.filter(o => o.colIndex === 2);
  const col3 = threeObjects.filter(o => o.colIndex === 3);
  const col4 = threeObjects.filter(o => o.colIndex === 4);

  col1.forEach(c1 => {
    col2.forEach(c2 => {
      if (c1.title.includes(c2.title) || c2.title.includes(c1.title) || isPharmacologicalPair(c1.title, c2.title)) {
        addTubeConnection(c1, c2, 0x38BDF8); // Translucent Cyan
      }
    });
  });

  // Connect Col 2 (Ingredient) -> Col 3 (Conflict)
  col2.forEach(c2 => {
    col3.forEach(c3 => {
      const color = c3.category === 'Time-Spacing' ? 0xFDE047 : 0xEF4444; // Yellow or Red
      addTubeConnection(c2, c3, color);
    });
  });

  // Connect Col 3 (Conflict) -> Col 4 (Safe Alternative)
  col3.forEach(c3 => {
    col4.forEach(c4 => {
      addTubeConnection(c3, c4, 0x10B981); // Emerald Green
    });
  });
}

function isPharmacologicalPair(med, ing) {
  const map = {
    'Plavix': 'Clopidogrel', 'Prilosec': 'Omeprazole', 'Cipro': 'Ciprofloxacin',
    'Zestril': 'Lisinopril', 'Prinivil': 'Lisinopril', 'Norvasc': 'Amlodipine',
    'Advil': 'Ibuprofen', 'Motrin': 'Ibuprofen', 'Aleve': 'Naproxen',
    'Lipitor': 'Atorvastatin', 'Coumadin': 'Warfarin', 'Tylenol': 'Acetaminophen',
    'Pepcid': 'Famotidine', 'Protonix': 'Pantoprazole'
  };
  return map[med] === ing;
}

// ==========================================================================
// 5. ANIMATION LOOP & PROJECTION
// ==========================================================================
function animateStage() {
  requestAnimationFrame(animateStage);

  const time = performance.now() * 0.001;

  // Orbit controls update
  controls.update();

  // Gentle floating bob & rotation on models
  threeObjects.forEach((obj, idx) => {
    const mesh = obj.mesh;
    mesh.position.y += Math.sin(time * 2 + idx) * 0.0015;

    // Specific rotations
    if (mesh.userData.orbit) {
      mesh.userData.orbit.rotation.z += 0.015;
    }
    if (mesh.userData.halo) {
      mesh.userData.halo.rotation.z += 0.02;
    }
    if (mesh.userData.safetyRing) {
      mesh.userData.safetyRing.rotation.z += 0.018;
    }
  });

  // Background light ribbons drift
  lightRibbons.forEach(r => {
    r.mesh.rotation.z += r.speed;
  });

  // Animate energy pulses along curves
  energyPulses.forEach(p => {
    p.t = (p.t + p.speed) % 1.0;
    const pt = p.curve.getPointAt(p.t);
    p.mesh.position.copy(pt);
  });

  // Update 2D Projected HTML Labels
  updateProjectedLabels();

  // Render Scene
  renderer.render(scene, camera);
}

function updateProjectedLabels() {
  if (!canvasContainer || !camera) return;
  const width = canvasContainer.clientWidth;
  const height = canvasContainer.clientHeight;

  threeObjects.forEach(obj => {
    const pos = obj.mesh.position.clone();
    pos.y -= 0.65; // Position pill directly below 3D model
    pos.project(camera);

    // Behind camera check
    if (pos.z > 1.0) {
      obj.labelEl.style.display = 'none';
      return;
    }

    const x = (pos.x * 0.5 + 0.5) * width;
    const y = (-pos.y * 0.5 + 0.5) * height;

    obj.labelEl.style.display = 'block';
    obj.labelEl.style.left = `${x}px`;
    obj.labelEl.style.top = `${y}px`;
  });
}

function onCanvasClick(event) {
  const rect = canvasContainer.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

  raycaster.setFromCamera(mouse, camera);
  const meshes = threeObjects.map(o => o.mesh);
  const intersects = raycaster.intersectObjects(meshes, true);

  if (intersects.length > 0) {
    let topParent = intersects[0].object;
    while (topParent.parent && topParent.parent !== scene) {
      topParent = topParent.parent;
    }
    const matched = threeObjects.find(o => o.mesh === topParent);
    if (matched) {
      highlightNodeInteractions(matched.title);
    }
  }
}

function highlightNodeInteractions(nodeTitle) {
  // Switch to clinical risks tab and highlight corresponding warning card
  switchRightTab('clinical');
  const alertCards = document.querySelectorAll('.alert-card-item');
  alertCards.forEach(c => {
    if (c.textContent.toLowerCase().includes(nodeTitle.toLowerCase())) {
      c.style.transform = 'scale(1.03)';
      c.style.boxShadow = '0 0 16px rgba(2, 132, 199, 0.4)';
      setTimeout(() => {
        c.style.transform = 'none';
        c.style.boxShadow = 'none';
      }, 1500);
      c.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  });
}

// ==========================================================================
// 6. CLINICAL PRESETS & YELLOW KEY ACTION BANNER
// ==========================================================================
async function switchPreset(presetId) {
  activePresetId = presetId;

  // Clear previous selections cleanly
  selectedMedicines.clear();
  selectedFoods.clear();
  selectedConditions.clear();
  activeTraceResult = null;

  document.getElementById('symptomSelect').value = '';
  document.getElementById('traceResultBox').style.display = 'none';

  // Highlight active preset button in Bright Yellow (#FDE047)
  const buttons = document.querySelectorAll('.preset-pill');
  buttons.forEach(btn => btn.classList.remove('active'));
  const activeBtnMap = {
    'preset_1': 'btnPreset1',
    'preset_2': 'btnPreset2',
    'preset_3': 'btnPreset3',
    'preset_4': 'btnPreset4'
  };
  const activeBtn = document.getElementById(activeBtnMap[presetId]);
  if (activeBtn) activeBtn.classList.add('active');

  // Load preset data
  try {
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
    resetCameraView();
  } catch (e) {
    console.error('Failed to load preset', e);
  }
}

// Formulation of the Bright Yellow "One Fact to Remember" Key Action
function updateKeyActionBanner(data) {
  const banner = document.getElementById('keyActionBanner');
  const actionText = document.getElementById('keyActionText');
  if (!banner || !actionText) return;

  if (activePresetId === 'preset_1' || (selectedMedicines.has('Clopidogrel') && selectedMedicines.has('Omeprazole'))) {
    actionText.textContent = "KEY ACTION: Swap Omeprazole for Famotidine or Pantoprazole to prevent CYP2C19 block and restore Clopidogrel's antiplatelet heart protection.";
    banner.style.display = 'block';
    return;
  }

  if (activePresetId === 'preset_2' || (selectedMedicines.has('Ciprofloxacin') && selectedFoods.has('Milk / Dairy'))) {
    actionText.textContent = "KEY ACTION: Keep a mandatory 3-hour gap between Ciprofloxacin and Dairy/Calcium to avoid insoluble chelation and 85% antibiotic failure.";
    banner.style.display = 'block';
    return;
  }

  if (activePresetId === 'preset_3' || (selectedMedicines.has('Advil') && selectedMedicines.has('Aleve'))) {
    actionText.textContent = "KEY ACTION: Discontinue dual NSAIDs (Advil + Aleve) immediately; additive COX-1/2 inhibition causes acute kidney injury and GI bleeding.";
    banner.style.display = 'block';
    return;
  }

  if (activePresetId === 'preset_4' || (selectedMedicines.has('Atorvastatin') && selectedFoods.has('Grapefruit Juice'))) {
    actionText.textContent = "KEY ACTION: Stop Grapefruit Juice immediately (inhibits CYP3A4, causing toxic statin accumulation and rhabdomyolysis muscle breakdown).";
    banner.style.display = 'block';
    return;
  }

  // General fallback
  if (data.warnings && data.warnings.length > 0) {
    actionText.textContent = `KEY ACTION: ${data.warnings[0].title} — ${data.warnings[0].details.substring(0, 110)}...`;
    banner.style.display = 'block';
  } else {
    actionText.textContent = "KEY ACTION: Regimen Clear — No critical metabolic collisions or timing gaps detected.";
    banner.style.display = 'block';
  }
}

// ==========================================================================
// 7. COMPREHENSIVE GRAPH ANALYSIS (RELATE ENGINE)
// ==========================================================================
async function triggerAnalysis() {
  const reqBody = {
    medicines: Array.from(selectedMedicines),
    foods: Array.from(selectedFoods),
    conditions: Array.from(selectedConditions)
  };

  if (reqBody.medicines.length === 0 && reqBody.foods.length === 0 && reqBody.conditions.length === 0) {
    clearThreeStage();
    renderClinicalWarnings([], [], []);
    renderSchedule([]);
    renderOrganLoad({ Kidney: 0, Liver: 0, 'Stomach / GI': 0, 'Brain / CNS': 0 });
    renderExecutedQueries([]);
    updateKeyActionBanner({ warnings: [] });
    return;
  }

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reqBody)
    });
    const data = await res.json();
    currentAnalysisData = data;

    // Render 3D Stage
    renderThreeStage(data);

    // Update Right Panel & Bright Yellow Banner
    updateKeyActionBanner(data);
    renderClinicalWarnings(data.warnings, data.brand_overlaps, data.safe_alternatives);
    renderSchedule(data.schedule);
    renderOrganLoad(data.organ_load);
    renderExecutedQueries(data.queries_executed);

  } catch (e) {
    console.error('Analysis failed', e);
  }
}

// ==========================================================================
// 8. RIGHT PANEL RENDERERS
// ==========================================================================

// A. Clinical Warnings & Safe Swaps (Red 'X' Badges)
function renderClinicalWarnings(warnings, brandOverlaps, safeAlts) {
  const ddContainer = document.getElementById('doubleDoseContainer');
  ddContainer.innerHTML = '';
  if (brandOverlaps && brandOverlaps.length > 0) {
    brandOverlaps.forEach(dd => {
      const card = document.createElement('div');
      card.className = 'alert-card-item';
      card.innerHTML = `
        <div class="alert-item-header">
          <span class="red-x-badge">&times;</span>
          <span class="alert-item-title">Accidental Double Dose Overdose</span>
          <span class="alert-severity-badge severity-severe">OVERDOSE</span>
        </div>
        <div class="alert-item-body">${dd.warning}</div>
      `;
      ddContainer.appendChild(card);
    });
  }

  const wContainer = document.getElementById('warningsListContainer');
  const countBadge = document.getElementById('warningsCountBadge');
  wContainer.innerHTML = '';

  const totalWarnings = (warnings ? warnings.length : 0) + (brandOverlaps ? brandOverlaps.length : 0);
  countBadge.textContent = `${totalWarnings} alert${totalWarnings === 1 ? '' : 's'}`;

  if (warnings && warnings.length > 0) {
    warnings.forEach(w => {
      const card = document.createElement('div');
      const isAmber = w.type.includes('Food') || w.type.includes('Timing');
      card.className = `alert-card-item ${isAmber ? 'amber-item' : ''}`;
      const sevClass = w.severity === 'Severe' ? 'severity-severe' : 'severity-high';
      card.innerHTML = `
        <div class="alert-item-header">
          <span class="red-x-badge">${isAmber ? '!' : '&times;'}</span>
          <span class="alert-item-title">${w.title}</span>
          <span class="alert-severity-badge ${sevClass}">${w.severity}</span>
        </div>
        <div class="alert-item-body">${w.details}</div>
      `;
      wContainer.appendChild(card);
    });
  } else if (!brandOverlaps || brandOverlaps.length === 0) {
    wContainer.innerHTML = '<div class="empty-state-text">No active clinical conflicts detected.</div>';
  }

  const altContainer = document.getElementById('altsListContainer');
  const altBadge = document.getElementById('altsCountBadge');
  altContainer.innerHTML = '';

  const altCount = safeAlts ? safeAlts.length : 0;
  altBadge.textContent = `${altCount} option${altCount === 1 ? '' : 's'}`;

  if (safeAlts && safeAlts.length > 0) {
    safeAlts.forEach(alt => {
      const card = document.createElement('div');
      card.className = 'safe-card-item';
      card.innerHTML = `
        <div class="safe-item-title">&check; Consider: ${alt.alternative}</div>
        <div class="safe-item-replaces">Replaces <strong>${alt.replaces}</strong> for <em>${alt.condition}</em></div>
        <div class="safe-item-reason">${alt.reason}</div>
      `;
      altContainer.appendChild(card);
    });
  } else {
    altContainer.innerHTML = '<div class="empty-state-text">Safe alternatives appear when blocked pathways are detected.</div>';
  }
}

// B. Visual 5-Slot Daily Routine Schedule Cards
function renderSchedule(schedule) {
  const container = document.getElementById('scheduleTimeline');
  container.innerHTML = '';

  if (!schedule || schedule.length === 0) {
    container.innerHTML = '<div class="empty-state-text">Select medications to generate an optimized daily timetable.</div>';
    return;
  }

  schedule.forEach(slotData => {
    const card = document.createElement('div');
    card.className = 'routine-slot-box';

    let itemsHtml = '';
    slotData.items.forEach(it => {
      const gapBadge = it.gap_hours > 0 ? `<span class="yellow-gap-callout">${it.gap_hours}h GAP</span>` : '';
      itemsHtml += `
        <div class="slot-med-row">
          <div class="slot-med-name">${it.medicine} ${gapBadge}</div>
          <div class="slot-med-instructions">${it.instructions}</div>
        </div>
      `;
    });

    card.innerHTML = `
      <div class="slot-heading-row">
        <span class="slot-title-text">${slotData.slot}</span>
        <span class="slot-count-text">${slotData.items.length} item${slotData.items.length === 1 ? '' : 's'}</span>
      </div>
      <div>${itemsHtml}</div>
    `;
    container.appendChild(card);
  });
}

// C. Cumulative Organ Load Progress Bars
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
      barEl.className = 'progress-bar-fill';
      if (score >= 8) barEl.classList.add('high');
      else if (score >= 4) barEl.classList.add('medium');
    }
  });

  const assessBox = document.getElementById('organAssessmentCard');
  if (totalScore >= 12) {
    assessBox.innerHTML = `<strong style="color:var(--clinical-red);">⚠️ High Cumulative Organ Strain:</strong> Concurrent medications heavily stress renal filtration and GI tolerance. Regular metabolic monitoring is critical.`;
  } else if (totalScore >= 6) {
    assessBox.innerHTML = `<strong style="color:var(--clinical-amber);">Moderate Organ Burden:</strong> Standard clinical monitoring advised.`;
  } else if (totalScore > 0) {
    assessBox.innerHTML = `<strong style="color:var(--clinical-emerald);">Low Organ Burden:</strong> Clearance within typical physiological margins.`;
  } else {
    assessBox.innerHTML = `Select medications to calculate cumulative physiological burden.`;
  }
}

// D. Executed Cypher Queries Log
function renderExecutedQueries(queries) {
  const container = document.getElementById('recentQueriesContainer');
  container.innerHTML = '';
  if (!queries || queries.length === 0) return;

  queries.forEach(q => {
    const chip = document.createElement('div');
    chip.className = 'query-log-chip';
    chip.innerHTML = `
      <div class="query-type-tag">${q.name}</div>
      <div class="query-code-snippet">${q.query}</div>
    `;
    container.appendChild(chip);
  });
}

// ==========================================================================
// 9. REVERSE SYMPTOM TRACER & CYPHER REPL
// ==========================================================================
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
            ⚠️ <strong>${c.medicine}</strong> (${c.ingredient}) &middot; <em>${c.frequency}</em><br>
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
      outArea.innerHTML = `<span style="color:var(--clinical-red);">Error: ${data.detail || 'Query failed'}</span>`;
      return;
    }

    if (!data.rows || data.rows.length === 0) {
      outArea.innerHTML = `<span style="color:var(--clinical-emerald);">Query executed in ${data.elapsed_ms} ms (0 rows).</span>`;
      return;
    }

    let table = `<div style="color:var(--royal-blue);margin-bottom:4px;font-weight:700;">&check; Returned ${data.count} row(s) in ${data.elapsed_ms} ms:</div>`;
    table += '<table class="cypher-grid-table"><thead><tr>';
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
    outArea.innerHTML = `<span style="color:var(--clinical-red);">Execution error: ${e.message}</span>`;
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

// ==========================================================================
// 10. CONTROLS & AUTOCOMPLETE HELPER SETUP
// ==========================================================================
function setupEventListeners() {
  window.switchPreset = switchPreset;
  window.switchRightTab = switchRightTab;
  window.clearAllSelections = clearAllSelections;
  window.handleAddFood = handleAddFood;
  window.handleAddCondition = handleAddCondition;
  window.removeMedicine = removeMedicine;
  window.removeFood = removeFood;
  window.removeCondition = removeCondition;
  window.traceSymptom = traceSymptom;
  window.runCustomCypher = runCustomCypher;
  window.insertSampleCypher = insertSampleCypher;
}

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
      dropdown.innerHTML = '<div class="dropdown-entry" style="color:var(--text-faint);font-style:italic;">No matching medicines found</div>';
      dropdown.style.display = 'block';
      return;
    }

    dropdown.innerHTML = '';
    matches.slice(0, 10).forEach(m => {
      const item = document.createElement('div');
      item.className = 'dropdown-entry';
      item.innerHTML = `
        <div>
          <span class="entry-main-name">${m.name}</span>
          ${m.is_brand ? `<span class="entry-brand-tag">Brand</span>` : ''}
        </div>
        <span class="entry-ingredient">${m.ingredient || m.generic_name}</span>
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

  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.style.display = 'none';
    }
  });
}

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

function clearAllSelections() {
  selectedMedicines.clear();
  selectedFoods.clear();
  selectedConditions.clear();
  activeTraceResult = null;
  currentAnalysisData = null;

  document.getElementById('symptomSelect').value = '';
  document.getElementById('traceResultBox').style.display = 'none';

  updateChipsUI();
  triggerAnalysis();
}

function updateChipsUI() {
  const container = document.getElementById('selectedChipsContainer');
  const totalCount = selectedMedicines.size + selectedFoods.size + selectedConditions.size;
  document.getElementById('activeItemsCount').textContent = `${totalCount} item${totalCount === 1 ? '' : 's'}`;

  if (totalCount === 0) {
    container.innerHTML = `<div class="empty-chips-notice">No items selected. Choose a preset or add medications above.</div>`;
    return;
  }

  container.innerHTML = '';

  selectedMedicines.forEach(med => {
    const chip = document.createElement('div');
    chip.className = 'regimen-chip chip-med';
    chip.innerHTML = `<span>💊 ${med}</span><span class="chip-x" onclick="removeMedicine('${med}')">&times;</span>`;
    container.appendChild(chip);
  });

  selectedFoods.forEach(food => {
    const chip = document.createElement('div');
    chip.className = 'regimen-chip chip-food';
    chip.innerHTML = `<span>🥛 ${food}</span><span class="chip-x" onclick="removeFood('${food}')">&times;</span>`;
    container.appendChild(chip);
  });

  selectedConditions.forEach(cond => {
    const chip = document.createElement('div');
    chip.className = 'regimen-chip chip-cond';
    chip.innerHTML = `<span>🩺 ${cond}</span><span class="chip-x" onclick="removeCondition('${cond}')">&times;</span>`;
    container.appendChild(chip);
  });
}

function switchRightTab(tabKey) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

  const tabBtnMap = {
    'clinical': 'tabBtnClinical',
    'schedule': 'tabBtnSchedule',
    'organ': 'tabBtnOrgan',
    'cypher': 'tabBtnCypher'
  };
  const tabPaneMap = {
    'clinical': 'tabPaneClinical',
    'schedule': 'tabPaneSchedule',
    'organ': 'tabPaneOrgan',
    'cypher': 'tabPaneCypher'
  };

  const btn = document.getElementById(tabBtnMap[tabKey]);
  const pane = document.getElementById(tabPaneMap[tabKey]);

  if (btn) btn.classList.add('active');
  if (pane) pane.classList.add('active');
}

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

async function loadCatalog() {
  try {
    const res = await fetch('/api/catalog');
    catalog = await res.json();

    const foodPicker = document.getElementById('foodSelectPicker');
    foodPicker.innerHTML = '<option value="">+ Add Dietary Intake / Supplement...</option>';
    catalog.foods.forEach(f => {
      const opt = document.createElement('option');
      opt.value = f.name;
      opt.textContent = `${f.name} (${f.category})`;
      foodPicker.appendChild(opt);
    });

    const condPicker = document.getElementById('condSelectPicker');
    condPicker.innerHTML = '<option value="">+ Add Health Condition...</option>';
    catalog.conditions.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.name;
      opt.textContent = `${c.name} (${c.category})`;
      condPicker.appendChild(opt);
    });

    const symSelect = document.getElementById('symptomSelect');
    symSelect.innerHTML = '<option value="">-- Choose Adverse Symptom --</option>';
    catalog.symptoms.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.name;
      opt.textContent = `${s.name} (${s.severity})`;
      symSelect.appendChild(opt);
    });
  } catch (e) {
    console.error('Failed to load catalog', e);
  }
}
