const app = document.querySelector("#app");
const API_BASE = window.__AISE_API_BASE__ || "/api";
const state = { user: null, authMode: "login", loading: false, graphData: null, graphRepoId: null, graphMode: "connected", cy: null, refreshTimer: null };

const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
const token = () => localStorage.getItem("aise_access_token");
const setLoading = (message = "Loading…") => `<div class="empty"><p>${escapeHtml(message)}</p></div>`;
const errorBox = (message) => `<div class="alert" role="alert">${escapeHtml(message)}</div>`;
const formatDate = (value) => value ? new Date(value).toLocaleString() : "—";

async function api(path, options = {}) {
  const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) };
  if (token()) headers.Authorization = `Bearer ${token()}`;
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("json") ? await response.json() : await response.text();
  if (!response.ok) {
    if (response.status === 401 && location.hash !== "#auth") {
      localStorage.removeItem("aise_access_token");
      state.user = null;
      location.hash = "auth";
    }
    const detail = typeof payload === "object" ? payload.detail : payload;
    throw new Error(typeof detail === "object" ? detail.message : detail || `Request failed (${response.status})`);
  }
  return payload;
}

function shell(content) {
  const signedIn = Boolean(token());
  return `<div class="app-shell"><header class="topbar"><a class="brand" href="#dashboard"><span class="brand-mark">AI</span><span>AISE Platform</span></a><nav class="nav" aria-label="Primary navigation"><a href="#dashboard">Dashboard</a><a href="#connect">Connect repo</a><a href="#docs">Docs</a>${signedIn ? `<a href="#account">Account</a><button data-action="signout" type="button">Sign out</button>` : `<a href="#auth">Sign in</a>`}</nav></header><main class="main">${content}</main><footer class="footer">AI Software Engineering Intelligence · Phase 4 migration build</footer></div>`;
}

async function dashboard() {
  if (!token()) return authView();
  try {
    const [user, repos] = await Promise.all([api("/auth/me"), api("/repos")]);
    state.user = user;
    const ready = repos.filter((repo) => repo.status === "ready").length;
    return shell(`<div class="hero"><div><p class="eyebrow">Engineering intelligence</p><h1>Understand your codebase before you change it.</h1><p class="lede">Search, explain, map, and review repositories with evidence-backed answers and actionable change context.</p></div><div class="actions"><a class="button primary" href="#connect">Connect repository</a></div></div><div class="grid stats"><div class="card"><span class="metric-label">Repositories</span><strong class="metric-value">${repos.length}</strong></div><div class="card"><span class="metric-label">Ready to query</span><strong class="metric-value">${ready}</strong></div><div class="card"><span class="metric-label">Access role</span><strong class="metric-value">${escapeHtml(user.role)}</strong></div><div class="card"><span class="metric-label">Account</span><strong class="metric-value" style="font-size:15px;word-break:break-word">${escapeHtml(user.email)}</strong></div></div><div class="section-head"><div><p class="eyebrow">Your workspace</p><h2>Repositories</h2></div></div>${repos.length ? `<div class="grid cards">${repos.map(repoCard).join("")}</div>` : `<div class="empty"><h3>No repositories connected</h3><p>Connect a GitHub repository to start indexing and asking questions.</p><a class="button primary" href="#connect">Connect your first repository</a></div>`}<div class="section-head"><div><p class="eyebrow">What works here</p><h2>One workspace for code intelligence</h2></div></div><div class="grid cards">${feature("01", "Evidence-backed Q&A", "Ask where behavior lives and get citations down to file and line ranges.")}${feature("02", "Change intelligence", "See history, dependency impact, related tests, and documentation risk before merging.")}${feature("03", "Quality signals", "Track retrieval quality, citation coverage, documentation gaps, technical debt, and secret-scan findings.")}</div>`);
  } catch (error) { return shell(errorBox(error.message)); }
}

const feature = (icon, title, text) => `<div class="card feature"><span class="feature-icon">${icon}</span><div><h3>${title}</h3><p>${text}</p></div></div>`;
const repoCard = (repo) => `<article class="card repo-card"><div><span class="status ${escapeHtml(repo.status)}">${escapeHtml(repo.status)}</span><h3 style="margin-top:15px">${escapeHtml(repo.name || repo.full_name)}</h3><p class="muted">${escapeHtml(repo.full_name)}</p></div><div class="repo-foot"><span class="muted">${repo.file_count || 0} files · ${repo.chunk_count || 0} chunks</span><a class="button secondary" href="#repo/${repo.id}">Open repo</a></div></article>`;
const previewButton = (repoId, filePath) => `<button class="button secondary compact-button" data-action="preview-source" data-id="${escapeHtml(repoId)}" data-path="${encodeURIComponent(filePath)}" type="button">Preview</button>`;

function authView() {
  const register = state.authMode === "register";
  return shell(`<div class="form-card card"><p class="eyebrow">Secure workspace access</p><h1 style="font-size:34px">${register ? "Create your account" : "Welcome back"}</h1><p class="lede" style="font-size:14px">${register ? "Create a workspace and start building repository intelligence." : "Sign in to access your repositories and engineering insights."}</p><div id="auth-error"></div><form id="auth-form"><div class="form-row"><label for="email">Email</label><input id="email" name="email" type="email" autocomplete="email" required /></div><div class="form-row"><label for="password">Password</label><input id="password" name="password" type="password" minlength="8" autocomplete="${register ? "new-password" : "current-password"}" required /></div><button class="button primary" type="submit">${register ? "Create account" : "Sign in"}</button></form><p class="muted" style="margin-top:18px">${register ? "Already have an account?" : "Need an account?"} <button class="button secondary" style="min-height:32px;padding:0 9px" data-action="toggle-auth" type="button">${register ? "Sign in" : "Register"}</button></p></div>`);
}

function connectView() {
  if (!token()) return authView();
  return shell(`<div class="form-card card"><p class="eyebrow">Repository onboarding</p><h1 style="font-size:34px">Connect a GitHub repository.</h1><p class="lede" style="font-size:14px">The indexer will detect languages, parse symbols, build relationships, and prepare cited Q&A.</p><div id="connect-error"></div><form id="connect-form"><div class="form-row"><label for="github_url">GitHub URL</label><input id="github_url" name="github_url" type="url" placeholder="https://github.com/org/repository" required /></div><div class="form-row"><label for="name">Display name <span class="muted">(optional)</span></label><input id="name" name="name" type="text" placeholder="Payments service" /></div><button class="button primary" type="submit">Connect and index</button></form></div>`);
}

async function repoView(id) {
  if (!token()) return authView();
  try {
    const [repo, stats, files, graph, architecture, debt, quality, tests, history, tour, latestChange] = await Promise.all(["/repos/" + id, "/repos/" + id + "/stats", "/repos/" + id + "/files", "/repos/" + id + "/graph/files", "/repos/" + id + "/architecture", "/repos/" + id + "/technical-debt", "/repos/" + id + "/documentation/quality", "/repos/" + id + "/test-intelligence", "/repos/" + id + "/history", "/repos/" + id + "/tour", "/repos/" + id + "/pr-analysis/latest"].map((path) => api(path).catch((error) => ({ unavailable: error.message }))));
    if (repo.unavailable) throw new Error(repo.unavailable);
    state.graphData = graph.unavailable ? null : graph;
    state.graphRepoId = id;
    state.graphMode = "connected";
    const unavailable = (data) => data?.unavailable ? `<p class="muted">Unavailable: ${escapeHtml(data.unavailable)}</p>` : null;
    const fileList = unavailable(files) || `<div class="data-list">${files.slice(0, 20).map((file) => `<div class="data-row"><span>${escapeHtml(file.file_path)}</span>${previewButton(id, file.file_path)}</div>`).join("") || "<p class='muted'>No indexed files available yet.</p>"}</div>${files.length > 20 ? `<p class="muted" style="margin-top:12px">Showing 20 of ${files.length} files.</p>` : ""}`;
    const graphPanel = unavailable(graph) || `<section class="card graph-card" aria-labelledby="dependency-graph-title"><div class="graph-head"><div><p class="eyebrow">Architecture map</p><h2 id="dependency-graph-title">Dependency graph</h2><p class="muted">The default map shows only files with relationships, arranged by inferred layer. Select a node to trace imports and dependants.</p></div><div class="graph-actions"><button class="button secondary" data-action="graph-reset" type="button">Reset focus</button><button class="button secondary" data-action="graph-fit" type="button">Fit map</button><button class="button secondary" data-action="graph-layout" type="button">Re-layout</button></div></div><div class="graph-toolbar"><div class="graph-view-switch" role="group" aria-label="Graph scope"><button class="button secondary graph-view-button is-active" data-action="graph-view" data-view="connected" type="button" aria-pressed="true">Connected map</button><button class="button secondary graph-view-button" data-action="graph-view" data-view="all" type="button" aria-pressed="false">All files</button></div><span id="graph-summary" class="graph-summary" role="status" aria-live="polite"></span></div><div id="dependency-graph" class="dependency-graph" role="img" aria-label="Interactive dependency graph of indexed files"></div><div class="graph-footer"><div class="graph-legend" aria-label="Graph legend"><span><i class="legend-dot backend"></i>Backend</span><span><i class="legend-dot frontend"></i>Frontend</span><span><i class="legend-dot tests"></i>Tests</span><span><i class="legend-dot configuration"></i>Config/docs</span><span><i class="legend-line outgoing"></i>Imports</span><span><i class="legend-line incoming"></i>Imported by</span></div><div id="graph-selection" class="graph-selection" role="status" aria-live="polite">Select a node to inspect its direct relationships.</div></div></section>`;
    const indexingNotice = ["indexing", "pending"].includes(repo.status) ? `<div class="indexing-notice" role="status" aria-live="polite"><span class="indexing-pulse" aria-hidden="true"></span><div><strong>Indexing in progress</strong><p>Repository intelligence will appear as files are parsed. This page refreshes automatically.</p></div></div>` : repo.status === "error" ? `<div class="alert" role="alert"><strong>Indexing needs attention.</strong> Re-index the repository to retry.</div>` : "";
    const tourPanel = unavailable(tour) || `<div class="data-list"><div class="data-row"><span>Connected files</span><strong>${tour.file_count || 0}</strong></div><div class="data-row"><span>Relationships</span><strong>${tour.relationship_count || 0}</strong></div>${(tour.key_files || []).slice(0, 5).map((item) => `<div class="data-row"><span><strong>${escapeHtml(item.file_path)}</strong><small>${escapeHtml(item.layer)} · ${item.connections} connections</small></span>${previewButton(id, item.file_path)}</div>`).join("")}</div>`;
    const latestPanel = unavailable(latestChange) || `<p class="muted">${escapeHtml(latestChange.short_sha || "")} · ${escapeHtml(latestChange.author || "Unknown")}</p><h3>${escapeHtml(latestChange.message || "Latest change")}</h3><div class="data-list"><div class="data-row"><span>Changes</span><strong>+${latestChange.insertions || 0} / −${latestChange.deletions || 0}</strong></div><div class="data-row"><span>Files changed</span><strong>${(latestChange.changed_files || []).length}</strong></div></div><p class="muted">${(latestChange.recommendations || []).map(escapeHtml).join(" ")}</p>`;
    return shell(`<div class="hero"><div><p class="eyebrow">Repository intelligence</p><h1>${escapeHtml(repo.name)}</h1><p class="lede">${escapeHtml(repo.full_name)} · indexed ${formatDate(repo.last_indexed_at)}</p></div><div class="actions"><button class="button secondary" data-action="reindex" data-id="${id}" type="button">Re-index</button><a class="button primary" href="#chat/${id}">Ask the codebase</a><button class="button danger" data-action="delete-repo" data-id="${id}" type="button">Delete</button></div></div>${indexingNotice}<div class="grid stats"><div class="card"><span class="metric-label">Status</span><strong class="metric-value" style="font-size:20px"><span class="status ${escapeHtml(repo.status)}">${escapeHtml(repo.status)}</span></strong></div><div class="card"><span class="metric-label">Files</span><strong class="metric-value">${stats.file_count ?? repo.file_count ?? 0}</strong></div><div class="card"><span class="metric-label">Code chunks</span><strong class="metric-value">${stats.chunk_count ?? repo.chunk_count ?? 0}</strong></div><div class="card"><span class="metric-label">Languages</span><strong class="metric-value" style="font-size:15px">${escapeHtml((stats.languages || repo.languages || []).join(", ") || "—")}</strong></div></div>${graphPanel}<div class="grid cards"><div class="card"><h3>Repository tour</h3>${tourPanel}</div><div class="card"><h3>Latest change</h3>${latestPanel}</div><div class="card"><h3>Indexed files</h3>${fileList}</div><div class="card"><h3>Architecture</h3>${unavailable(architecture) || `<div class="data-list">${(architecture.layers || []).map((layer) => `<div class="data-row"><span>${escapeHtml(layer.name)}</span><strong>${layer.file_count}</strong></div>`).join("") || "<p class='muted'>No architecture layers available yet.</p>"}</div>`}</div><div class="card"><h3>Documentation quality</h3>${unavailable(quality) || `<strong class="metric-value">${Math.round((quality.coverage || 0) * 100)}%</strong><p class="muted">${quality.documented_symbol_count || 0} documented of ${quality.symbol_count || 0} symbols.</p>`}</div><div class="card"><h3>Test intelligence</h3>${unavailable(tests) || `<strong class="metric-value">${tests.tested_file_count || 0}</strong><p class="muted">source files with related tests · ${tests.untested_file_count || 0} gaps</p>`}</div><div class="card"><h3>Technical debt</h3>${unavailable(debt) || `<strong class="metric-value">${debt.signals?.length || 0}</strong><p class="muted">ranked signals across ${debt.files_analyzed || 0} analyzed files.</p>`}</div><div class="card"><h3>Git history</h3>${unavailable(history) || `<strong class="metric-value">${history.count || history.commits?.length || 0}</strong><p class="muted">recent commits available for change analysis.</p>`}</div></div>`);
  } catch (error) { return shell(`<a class="muted" href="#dashboard">← Back to dashboard</a>${errorBox(error.message)}`); }
}

function graphLayer(filePath) {
  const normalized = String(filePath || "").toLowerCase().replaceAll("\\", "/");
  const parts = new Set(normalized.split("/"));
  const name = normalized.split("/").pop() || "";
  if (name.includes("test") || parts.has("tests") || parts.has("__tests__")) return "tests";
  if (parts.has("frontend") || normalized.startsWith("src/") || [...parts].some((part) => ["app", "components", "pages", "hooks", "lib"].includes(part)) && /\.(js|jsx|ts|tsx)$/.test(name)) return "frontend";
  if (parts.has("backend") || parts.has("api") || parts.has("services")) return "backend";
  if (name.endsWith(".md") || name.endsWith(".mdx") || ["package.json", "pyproject.toml", "dockerfile", "docker-compose.yml"].includes(name)) return "configuration";
  return "other";
}

function graphLabel(filePath) {
  const path = String(filePath || "");
  const parts = path.split("/").filter(Boolean);
  const label = parts.slice(-3).join("/") || path;
  return label.length > 30 ? `…${label.slice(-29)}` : label;
}

function prefersReducedMotion() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;
}

function clearGraphFocus() {
  if (!state.cy) return;
  state.cy.elements().removeClass("is-selected is-neighbor is-faded is-outgoing is-incoming is-hover");
  const selection = document.querySelector("#graph-selection");
  if (selection) selection.textContent = "Select a node to inspect its direct relationships.";
}

function describeGraphNode(node) {
  const data = node.data();
  const imports = node.outgoers("edge").length;
  const importedBy = node.incomers("edge").length;
  const selection = document.querySelector("#graph-selection");
  if (!selection) return;
  selection.innerHTML = `<strong>${escapeHtml(data.filePath)}</strong><span>${imports} imports · ${importedBy} dependants · ${escapeHtml(data.layer)} · ${data.symbols.length} symbols</span>${state.graphRepoId ? `<button class="button secondary" data-action="graph-preview" data-id="${escapeHtml(state.graphRepoId)}" data-path="${encodeURIComponent(data.filePath)}" type="button">Preview file</button>` : ""}`;
}

function focusGraphNode(node) {
  const cy = state.cy;
  if (!cy) return;
  cy.elements().removeClass("is-selected is-neighbor is-faded is-outgoing is-incoming").addClass("is-faded");
  const direct = node.closedNeighborhood();
  direct.removeClass("is-faded").addClass("is-neighbor");
  node.removeClass("is-neighbor").addClass("is-selected");
  node.outgoers("edge").removeClass("is-faded").addClass("is-outgoing");
  node.incomers("edge").removeClass("is-faded").addClass("is-incoming");
  describeGraphNode(node);
}

function runGraphLayout(animate = !prefersReducedMotion()) {
  if (!state.cy) return;
  const container = document.querySelector("#dependency-graph");
  const positions = buildGraphPositions(state.cy.nodes().toArray(), container);
  state.cy.layout({ name: "preset", positions, animate, animationDuration: animate ? 420 : 0, fit: true, padding: 48 }).run();
}

function buildGraphPositions(nodes, container) {
  const layerOrder = ["frontend", "backend", "tests", "configuration", "other"];
  const width = Math.max(container?.clientWidth || 820, 620);
  const height = Math.max(460, Math.min(760, 118 + Math.max(...layerOrder.map((layer) => nodes.filter((node) => node.data("layer") === layer).length), 1) * 72));
  const columns = layerOrder.filter((layer) => nodes.some((node) => node.data("layer") === layer));
  const sidePadding = 95;
  const columnGap = columns.length > 1 ? (width - sidePadding * 2) / (columns.length - 1) : 0;
  const positions = {};
  columns.forEach((layer, columnIndex) => {
    const group = nodes
      .filter((node) => node.data("layer") === layer)
      .sort((left, right) => (right.data("connections") - left.data("connections")) || left.data("filePath").localeCompare(right.data("filePath")));
    const rowGap = Math.min(78, (height - 104) / Math.max(group.length, 1));
    const startY = (height - rowGap * (group.length - 1)) / 2;
    group.forEach((node, rowIndex) => {
      positions[node.id()] = { x: columns.length === 1 ? width / 2 : sidePadding + columnIndex * columnGap, y: startY + rowIndex * rowGap };
    });
  });
  return positions;
}

function updateGraphViewControls(visibleNodeCount, visibleEdgeCount) {
  const summary = document.querySelector("#graph-summary");
  const totalNodes = state.graphData?.nodes?.length || 0;
  const hidden = Math.max(totalNodes - visibleNodeCount, 0);
  if (summary) summary.textContent = state.graphMode === "connected"
    ? `Showing ${visibleNodeCount} connected files · ${visibleEdgeCount} imports · ${hidden} isolated hidden`
    : `Showing all ${visibleNodeCount} indexed files · ${visibleEdgeCount} imports`;
  document.querySelectorAll("[data-action='graph-view']").forEach((button) => {
    const active = button.dataset.view === state.graphMode;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function mountDependencyGraph() {
  const container = document.querySelector("#dependency-graph");
  if (!container || !state.graphData || !window.cytoscape) return;
  const graph = state.graphData;
  const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph.edges) ? graph.edges : [];
  if (!nodes.length) {
    container.innerHTML = `<div class="graph-empty"><strong>No dependency edges yet.</strong><span>Re-index the repository after source files are available.</span></div>`;
    return;
  }
  const degree = new Map(nodes.map((node) => [node.id, 0]));
  edges.forEach((edge) => { degree.set(edge.source, (degree.get(edge.source) || 0) + 1); degree.set(edge.target, (degree.get(edge.target) || 0) + 1); });
  const visibleNodes = state.graphMode === "connected" ? nodes.filter((node) => (degree.get(node.id) || 0) > 0) : nodes;
  const visibleIds = new Set(visibleNodes.map((node) => node.id));
  const visibleEdges = edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target));
  updateGraphViewControls(visibleNodes.length, visibleEdges.length);
  if (!visibleNodes.length) {
    container.innerHTML = `<div class="graph-empty"><strong>No connected files yet.</strong><span>Switch to All files or re-index after source relationships are available.</span></div>`;
    return;
  }
  const elements = [
    ...visibleNodes.map((node) => {
      const connections = degree.get(node.id) || 0;
      return { group: "nodes", data: { id: node.id, filePath: node.file_path, label: graphLabel(node.file_path), layer: graphLayer(node.file_path), connections, size: Math.min(46, 25 + connections * 3), symbols: node.symbols || [] } };
    }),
    ...visibleEdges.map((edge, index) => ({ group: "edges", data: { id: `edge-${index}`, source: edge.source, target: edge.target, importText: edge.import || "" } })),
  ];
  state.cy = window.cytoscape({
    container,
    elements,
    minZoom: 0.2,
    maxZoom: 3.2,
    wheelSensitivity: 0.18,
    pixelRatio: "auto",
    style: [
      { selector: "node", style: { "background-color": "#7386b8", "border-color": "#ffffff", "border-width": 2, "height": "data(size)", "width": "data(size)", "label": "data(label)", "font-size": 10, "font-family": "Inter, system-ui, sans-serif", color: "#172033", "text-opacity": 1, "text-background-color": "#f9fbff", "text-background-opacity": 0.9, "text-background-padding": 3, "text-wrap": "ellipsis", "text-max-width": 150, "text-valign": "bottom", "text-margin-y": 8, "overlay-color": "#5c8cff", "overlay-opacity": 0, "z-index": 2, "transition-property": "background-color, border-color, border-width, opacity, text-opacity, overlay-opacity", "transition-duration": "220ms" } },
      { selector: "node[layer = 'backend']", style: { "background-color": "#5c8cff", shape: "round-rectangle" } },
      { selector: "node[layer = 'frontend']", style: { "background-color": "#4bb6a6", shape: "ellipse" } },
      { selector: "node[layer = 'tests']", style: { "background-color": "#f2af52", shape: "hexagon" } },
      { selector: "node[layer = 'configuration']", style: { "background-color": "#a579cf", shape: "diamond" } },
      { selector: "node[layer = 'other']", style: { "background-color": "#93a0b9", shape: "ellipse" } },
      { selector: "edge", style: { width: 1.25, "line-color": "#9aa8c4", "target-arrow-color": "#9aa8c4", "target-arrow-shape": "triangle", "curve-style": "bezier", "line-opacity": 0.58, "arrow-scale": 0.62, "transition-property": "line-color, line-opacity, width, opacity", "transition-duration": "240ms", "z-index": 1 } },
      { selector: ".is-faded", style: { opacity: 0.12, "text-opacity": 0 } },
      { selector: ".is-neighbor", style: { "border-color": "#ffffff", "border-width": 3, "text-opacity": 1, "z-index": 4 } },
      { selector: ".is-selected", style: { "background-color": "#172033", "border-color": "#78a0ff", "border-width": 4, "overlay-opacity": 0.22, "text-opacity": 1, "z-index": 6 } },
      { selector: ".is-hover", style: { "border-color": "#172033", "border-width": 3, "text-opacity": 1, "z-index": 5 } },
      { selector: ".is-outgoing", style: { "line-color": "#f3a94d", "target-arrow-color": "#f3a94d", "line-opacity": 0.95, width: 2.6, "z-index": 3 } },
      { selector: ".is-incoming", style: { "line-color": "#3bbdac", "target-arrow-color": "#3bbdac", "line-opacity": 0.95, width: 2.6, "z-index": 3 } },
    ],
    layout: { name: "preset", positions: buildGraphPositions(visibleNodes.map((node) => ({ id: () => node.id, data: (key) => ({ layer: graphLayer(node.file_path), connections: degree.get(node.id) || 0, filePath: node.file_path }[key]) })), container), animate: false, fit: true, padding: 48 },
  });
  state.cy.on("tap", "node", (event) => focusGraphNode(event.target));
  state.cy.on("mouseover", "node", (event) => event.target.addClass("is-hover"));
  state.cy.on("mouseout", "node", (event) => event.target.removeClass("is-hover"));
  state.cy.on("tap", (event) => { if (event.target === state.cy) clearGraphFocus(); });
}

function chatView(id) {
  if (!token()) return authView();
  return shell(`<div class="chat"><div><a class="muted" href="#repo/${id}">← Back to repository</a><p class="eyebrow" style="margin-top:28px">Cited code Q&A</p><h1 style="font-size:38px">Ask the codebase.</h1><p class="lede" style="font-size:14px">Answers are grounded in indexed source chunks and return file/symbol/line citations.</p></div><div id="chat-log"></div><form id="chat-form" class="card"><div class="form-row"><label for="question">Your question</label><textarea id="question" name="question" placeholder="Where is authentication implemented, and what calls it?" required></textarea></div><button class="button primary" type="submit">Ask with citations</button></form></div>`);
}

async function sourceView(id, encodedPath) {
  if (!token()) return authView();
  try { const source = await api(`/repos/${id}/source/${encodedPath}`); return shell(`<div><a class="muted" href="#repo/${id}">← Back to repository</a><p class="eyebrow" style="margin-top:28px">Secure source preview</p><h1 style="font-size:38px">${escapeHtml(source.file_path)}</h1><p class="muted">${escapeHtml(source.language)} · bounded preview</p><pre class="code">${escapeHtml(source.content)}</pre></div>`); } catch (error) { return shell(`<a class="muted" href="#repo/${id}">← Back to repository</a>${errorBox(error.message)}`); }
}

async function accountView() {
  if (!token()) return authView();
  try {
    const [user, usage, workspaces] = await Promise.all([api("/auth/me"), api("/auth/usage"), api("/auth/workspaces")]);
    const workspaceCards = workspaces.map((workspace) => `<div class="card"><div class="section-head" style="margin:0 0 12px"><div><h3>${escapeHtml(workspace.name)}</h3><p class="muted">${escapeHtml(workspace.role)} · ${escapeHtml(workspace.slug)}</p></div>${["owner", "admin"].includes(workspace.role) ? `<button class="button secondary" data-action="rename-workspace" data-id="${workspace.id}" data-name="${escapeHtml(workspace.name)}" type="button">Rename</button>` : ""}</div><div class="data-list"><div class="data-row"><span>Workspace ID</span><code>${escapeHtml(workspace.id)}</code></div></div></div>`).join("");
    return shell(`<div class="hero"><div><p class="eyebrow">Account and access</p><h1 style="font-size:38px">Your engineering workspace.</h1><p class="lede" style="font-size:14px">Manage identity, usage, and workspace membership.</p></div></div><div class="grid cards"><div class="card"><h3>Identity</h3><div class="data-list"><div class="data-row"><span>Email</span><strong>${escapeHtml(user.email)}</strong></div><div class="data-row"><span>Role</span><strong>${escapeHtml(user.role)}</strong></div></div></div><div class="card"><h3>AI usage</h3><strong class="metric-value">${usage.used ?? 0}</strong><p class="muted">of ${usage.daily_limit ?? "—"} daily provider requests used.</p></div><div class="card"><h3>Create workspace</h3><form id="workspace-form"><div class="form-row"><label for="workspace-name">Workspace name</label><input id="workspace-name" name="name" minlength="2" required placeholder="Platform team" /></div><button class="button primary" type="submit">Create workspace</button></form><div id="workspace-error" style="margin-top:10px"></div></div></div><div class="section-head"><div><p class="eyebrow">Workspace management</p><h2>Workspaces</h2></div></div><div class="grid cards">${workspaceCards || `<div class="empty"><p>No workspaces available.</p></div>`}</div>`);
  } catch (error) { return shell(errorBox(error.message)); }
}

function docsView() { return shell(`<div class="hero"><div><p class="eyebrow">Product guide</p><h1 style="font-size:42px">A clear map of your codebase.</h1><p class="lede">AISE combines repository indexing, structural analysis, history, and grounded AI answers in one engineering workspace.</p></div></div><div class="grid cards">${feature("A", "Connect", "Bring a GitHub repository into a workspace and follow its indexing progress.")}${feature("B", "Explore", "Inspect architecture, dependencies, history, tests, documentation, and technical-debt signals.")}${feature("C", "Ask", "Ask natural-language questions and inspect the exact source citations behind each answer.")}</div>`); }

async function render() {
  const hash = location.hash.replace(/^#/, "") || "dashboard";
  if (state.refreshTimer) window.clearTimeout(state.refreshTimer);
  state.refreshTimer = null;
  state.cy?.destroy();
  state.cy = null;
  state.graphData = null;
  state.graphRepoId = null;
  app.innerHTML = setLoading();
  if (hash === "auth") app.innerHTML = authView();
  else if (hash === "connect") app.innerHTML = connectView();
  else if (hash === "account") app.innerHTML = await accountView();
  else if (hash === "docs") app.innerHTML = docsView();
  else if (hash.startsWith("repo/")) app.innerHTML = await repoView(hash.split("/")[1]);
  else if (hash.startsWith("chat/")) app.innerHTML = chatView(hash.split("/")[1]);
  else if (hash.startsWith("source/")) { const parts = hash.split("/"); app.innerHTML = await sourceView(parts[1], parts.slice(2).join("/")); }
  else app.innerHTML = await dashboard();
  bindEvents();
  mountDependencyGraph();
  if (hash.startsWith("repo/") && document.querySelector(".indexing-notice")) {
    state.refreshTimer = window.setTimeout(() => {
      if (location.hash === `#${hash}`) render();
    }, 5000);
  }
}

function bindEvents() {
  document.querySelector("[data-action='toggle-auth']")?.addEventListener("click", () => { state.authMode = state.authMode === "login" ? "register" : "login"; render(); });
  document.querySelector("[data-action='signout']")?.addEventListener("click", () => { localStorage.removeItem("aise_access_token"); state.user = null; location.hash = "auth"; });
  document.querySelector("#workspace-form")?.addEventListener("submit", async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); try { await api("/auth/workspaces", { method: "POST", body: JSON.stringify({ name: form.get("name") }) }); render(); } catch (error) { document.querySelector("#workspace-error").innerHTML = errorBox(error.message); } });
  document.querySelectorAll("[data-action='rename-workspace']").forEach((button) => button.addEventListener("click", async () => { const name = window.prompt("New workspace name", button.dataset.name); if (!name || name.trim() === button.dataset.name) return; try { await api(`/auth/workspaces/${button.dataset.id}`, { method: "PATCH", body: JSON.stringify({ name: name.trim() }) }); render(); } catch (error) { window.alert(error.message); } }));
  document.querySelector("#auth-form")?.addEventListener("submit", async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); const endpoint = state.authMode === "register" ? "/auth/register" : "/auth/login"; try { const result = await api(endpoint, { method: "POST", body: JSON.stringify({ email: form.get("email"), password: form.get("password") }) }); localStorage.setItem("aise_access_token", result.access_token); location.hash = "dashboard"; } catch (error) { document.querySelector("#auth-error").innerHTML = errorBox(error.message); } });
  document.querySelector("#connect-form")?.addEventListener("submit", async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); const button = event.currentTarget.querySelector("button[type='submit']"); button.disabled = true; button.textContent = "Connecting and indexing…"; try { const repo = await api("/repos/connect", { method: "POST", body: JSON.stringify({ github_url: form.get("github_url"), name: form.get("name") || null }) }); location.hash = `repo/${repo.id}`; } catch (error) { button.disabled = false; button.textContent = "Connect and index"; document.querySelector("#connect-error").innerHTML = errorBox(error.message); } });
  document.querySelector("[data-action='reindex']")?.addEventListener("click", async (event) => { const button = event.currentTarget; button.disabled = true; button.textContent = "Starting…"; try { await api(`/repos/${button.dataset.id}/reindex`, { method: "POST" }); button.textContent = "Indexing started"; } catch (error) { button.disabled = false; button.textContent = error.message; } });
  document.querySelector("[data-action='delete-repo']")?.addEventListener("click", async (event) => { const button = event.currentTarget; if (!window.confirm("Delete this repository and its indexed data?")) return; button.disabled = true; try { await api(`/repos/${button.dataset.id}`, { method: "DELETE" }); location.hash = "dashboard"; } catch (error) { button.disabled = false; window.alert(error.message); } });
  document.querySelectorAll("[data-action='preview-source']").forEach((button) => button.addEventListener("click", () => { location.hash = `source/${button.dataset.id}/${button.dataset.path}`; }));
  document.querySelector("[data-action='graph-reset']")?.addEventListener("click", clearGraphFocus);
  document.querySelector("[data-action='graph-fit']")?.addEventListener("click", () => state.cy?.fit(undefined, 38));
  document.querySelector("[data-action='graph-layout']")?.addEventListener("click", () => runGraphLayout());
  document.querySelectorAll("[data-action='graph-view']").forEach((button) => button.addEventListener("click", () => {
    if (button.dataset.view === state.graphMode) return;
    state.graphMode = button.dataset.view === "all" ? "all" : "connected";
    state.cy?.destroy();
    state.cy = null;
    mountDependencyGraph();
  }));
  document.querySelector("#graph-selection")?.addEventListener("click", (event) => { const button = event.target.closest("[data-action='graph-preview']"); if (button) location.hash = `source/${button.dataset.id}/${button.dataset.path}`; });
  document.querySelector("#chat-form")?.addEventListener("submit", async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); const id = location.hash.split("/")[1]; const log = document.querySelector("#chat-log"); log.innerHTML += `<div class="message user">${escapeHtml(form.get("question"))}</div>${setLoading("Retrieving and synthesizing cited code…")}`; event.currentTarget.querySelector("button").disabled = true; try { const answer = await api(`/repos/${id}/query`, { method: "POST", body: JSON.stringify({ question: form.get("question"), top_k: 5 }) }); log.innerHTML = `<div class="message user">${escapeHtml(form.get("question"))}</div><div class="message"><p>${escapeHtml(answer.answer).replace(/\n/g, "<br />")}</p><p class="muted">${answer.model} · ${answer.retrieval_count} retrieved chunks · ${(answer.citation_coverage * 100).toFixed(0)}% citation coverage</p><div>${(answer.citations || []).map((citation) => `<span class="citation">${escapeHtml(citation.file_path)}:${citation.start_line}-${citation.end_line}</span>`).join("")}</div></div>`; } catch (error) { log.innerHTML += errorBox(error.message); } finally { event.currentTarget.querySelector("button").disabled = false; } });
}

window.addEventListener("hashchange", render);
render();
