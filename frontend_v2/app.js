const app = document.querySelector("#app");
const API_BASE = window.__AISE_API_BASE__ || "/api";
const state = { user: null, authMode: "login", loading: false, graphData: null, graphRepoId: null, graphMode: "connected", graphView: "story", storyMap: null, storyStage: null, chatAnswer: null, selectedVersion: "default", cy: null, refreshTimer: null, versionPollTimer: null };

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
    const [user, repos, dependencyMap] = await Promise.all([api("/auth/me"), api("/repos"), api("/repos/graph/cross-repository").catch(() => null)]);
    state.user = user;
    const ready = repos.filter((repo) => repo.status === "ready").length;
    const dependencyMapPanel = dependencyMap ? `<section class="card dependency-map-card"><div><p class="eyebrow">Package relationships</p><h2>How your repositories depend on each other</h2><p class="muted">${escapeHtml(dependencyMap.note)}</p></div>${dependencyMap.edges.length ? `<div class="dependency-map-list">${dependencyMap.edges.map((edge) => { const from = dependencyMap.nodes.find((node) => node.id === edge.source); const to = dependencyMap.nodes.find((node) => node.id === edge.target); return `<div class="dependency-map-edge"><a href="#repo/${edge.source}">${escapeHtml(from?.full_name || "Repository")}</a><span>depends on <strong>${escapeHtml(edge.package)}</strong> from</span><a href="#repo/${edge.target}">${escapeHtml(to?.full_name || "Repository")}</a></div>`; }).join("")}</div>` : `<p class="muted">No direct package dependencies between the ${dependencyMap.repository_count} ready accessible repositories were found.</p>`}</section>` : "";
    return shell(`<div class="hero"><div><p class="eyebrow">Engineering intelligence</p><h1>Understand your codebase before you change it.</h1><p class="lede">Search, explain, map, and review repositories with evidence-backed answers and actionable change context.</p></div><div class="actions"><a class="button primary" href="#connect">Connect repository</a></div></div><div class="grid stats"><div class="card"><span class="metric-label">Repositories</span><strong class="metric-value">${repos.length}</strong></div><div class="card"><span class="metric-label">Ready to query</span><strong class="metric-value">${ready}</strong></div><div class="card"><span class="metric-label">Access role</span><strong class="metric-value">${escapeHtml(user.role)}</strong></div><div class="card"><span class="metric-label">Account</span><strong class="metric-value" style="font-size:15px;word-break:break-word">${escapeHtml(user.email)}</strong></div></div><section class="card workspace-search"><div><p class="eyebrow">Across your repositories</p><h2>Search code once.</h2><p class="muted">Find matching code in up to 10 ready repositories you can access.</p></div><form id="workspace-search-form"><label class="sr-only" for="workspace-search-query">Search all repositories</label><input id="workspace-search-query" name="q" maxlength="500" required placeholder="Try: password reset, invoice status, feature flag…"/><button class="button primary" type="submit">Search code</button></form><div id="workspace-search-results" class="workspace-search-results" aria-live="polite"></div></section>${dependencyMapPanel}<div class="section-head"><div><p class="eyebrow">Your workspace</p><h2>Repositories</h2></div></div>${repos.length ? `<div class="grid cards">${repos.map(repoCard).join("")}</div>` : `<div class="empty"><h3>No repositories connected</h3><p>Connect a GitHub repository to start indexing and asking questions.</p><a class="button primary" href="#connect">Connect your first repository</a></div>`}<div class="section-head"><div><p class="eyebrow">What works here</p><h2>One workspace for code intelligence</h2></div></div><div class="grid cards">${feature("01", "Evidence-backed Q&A", "Ask where behavior lives and get citations down to file and line ranges.")}${feature("02", "Change intelligence", "See history, dependency impact, related tests, and documentation risk before merging.")}${feature("03", "Quality signals", "Track retrieval quality, citation coverage, documentation gaps, technical debt, and secret-scan findings.")}</div>`);
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

const storyStages = [
  { key: "screens", icon: "◉", title: "Screens people use", description: "The pages a person can open and use." },
  { key: "work", icon: "⚡", title: "Work after a click", description: "The jobs the app does after someone taps a button or sends a form." },
  { key: "building", icon: "▦", title: "Shared building blocks", description: "Reusable pieces that help many parts of the app." },
  { key: "data", icon: "◆", title: "Data and outside services", description: "Where the app saves, reads, or sends information." },
  { key: "safety", icon: "✓", title: "Safety checks", description: "Tests that help make sure changes do not break the app." },
  { key: "setup", icon: "⚙", title: "App setup", description: "Instructions that help the app start, build, and run." },
  { key: "other", icon: "⌂", title: "App frame and helpers", description: "The pieces that start, guard, or support the app." },
];
const screenPageFiles = new Set(["page.js", "page.jsx", "page.ts", "page.tsx"]);
const screenEntryFiles = new Set(["index.js", "index.jsx", "index.ts", "index.tsx", "home.js", "home.jsx", "home.ts", "home.tsx"]);

function storyStageForFile(filePath) {
  const path = String(filePath || "").toLowerCase().replaceAll("\\", "/");
  const name = path.split("/").pop() || "";
  const segments = path.split("/").filter(Boolean);
  const parts = new Set(segments);
  if (name.includes("test") || parts.has("tests") || parts.has("__tests__") || parts.has("spec")) return "safety";
  const parent = segments.at(-2);
  if ((screenPageFiles.has(name) && segments.slice(0, -1).some((part) => part === "app" || part === "pages")) || (screenEntryFiles.has(name) && (parent === "app" || parent === "pages"))) return "screens";
  if ([...parts].some((part) => ["actions", "api", "services", "controllers", "use-cases", "handlers"].includes(part))) return "work";
  if ([...parts].some((part) => ["components", "hooks", "ui", "lib", "utils", "helpers"].includes(part))) return "building";
  if ([...parts].some((part) => ["models", "database", "repositories", "providers", "schemas", "migrations", "store", "stores"].includes(part)) || /(stripe|supabase|firebase|prisma|mongoose|sequelize)/.test(path)) return "data";
  if (name.endsWith(".md") || name.endsWith(".mdx") || ["package.json", "pyproject.toml", "dockerfile", "docker-compose.yml", "vercel.json"].includes(name)) return "setup";
  return "other";
}

function buildStoryMap(graph) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];
  const stageById = new Map(nodes.map((node) => [node.id, storyStageForFile(node.file_path)]));
  const degree = new Map(nodes.map((node) => [node.id, 0]));
  edges.forEach((edge) => {
    degree.set(edge.source, (degree.get(edge.source) || 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) || 0) + 1);
  });
  const groups = new Map(storyStages.map((stage) => [stage.key, []]));
  nodes.forEach((node) => groups.get(stageById.get(node.id))?.push({ ...node, connections: degree.get(node.id) || 0 }));
  groups.forEach((group) => group.sort((left, right) => right.connections - left.connections || left.file_path.localeCompare(right.file_path)));
  return { groups, stageById, edgeCount: edges.length };
}

function storyStageButton(key, compact = false) {
  const stage = storyStages.find((item) => item.key === key);
  const files = state.storyMap?.groups.get(key) || [];
  const examples = files.slice(0, compact ? 2 : 3).map((file) => graphLabel(file.file_path)).join(" · ");
  return `<button class="architecture-card${state.storyStage === key ? " is-selected" : ""}${compact ? " is-support" : ""}" data-action="story-stage" data-stage="${key}" type="button" aria-pressed="${state.storyStage === key}"><span class="architecture-icon" aria-hidden="true">${stage.icon}</span><span class="architecture-card-content"><strong>${escapeHtml(stage.title)}</strong><span>${files.length} ${files.length === 1 ? "file" : "files"}</span><small>${escapeHtml(stage.description)}</small><em>${escapeHtml(examples)}</em></span></button>`;
}

function storySummary(storyMap) {
  const count = (key) => storyMap.groups.get(key)?.length || 0;
  const sentences = [`This is a ${count("screens") ? "front-end" : "software"} app with ${count("screens") || storyMap.groups.get("other")?.length || 0} ${count("screens") === 1 ? "screen" : "screens"}.`];
  if (count("work")) sentences.push(`Those screens can ask ${count("work")} app actions to do work.`);
  if (count("building")) sentences.push(`${count("building")} shared pieces are reused to build the experience.`);
  return sentences.join(" ");
}

function connectorLabel(from, to) {
  if (from === "screens" && to === "work") return "asks for help";
  if (from === "work" && to === "data") return "uses data";
  return "works with";
}

function renderStoryMap(storyMap) {
  if (!storyMap) return "";
  const mainStages = ["screens", "work", "data"].filter((key) => storyMap.groups.get(key)?.length);
  const supportStages = ["building", "other", "safety", "setup"].filter((key) => storyMap.groups.get(key)?.length);
  const mainFlow = mainStages.map((key, index) => {
    const next = mainStages[index + 1];
    return `${storyStageButton(key)}${next ? `<span class="architecture-connector" aria-hidden="true"><b>→</b><small>${connectorLabel(key, next)}</small></span>` : ""}`;
  }).join("");
  const supportLabel = supportStages.includes("building") ? "These pieces are reused across the app" : "Supporting parts of the app";
  return `<div class="story-intro"><strong>In one sentence:</strong> ${escapeHtml(storySummary(storyMap))}</div><section class="architecture-blueprint" aria-label="Simple repository architecture"><div class="architecture-blueprint-head"><strong>How the pieces fit</strong><span>Pick any box to see its files.</span></div><div class="architecture-main-flow">${mainFlow || `<p class="muted">We found files, but not enough folder clues to draw a simple architecture yet.</p>`}</div>${supportStages.length ? `<div class="architecture-support"><p>${escapeHtml(supportLabel)}</p><div class="architecture-support-grid">${supportStages.map((key) => storyStageButton(key, true)).join("")}</div></div>` : ""}</section><div id="story-detail" class="story-detail" role="status" aria-live="polite">Pick a box above to see the exact files. Use <strong>Developer file map</strong> only when you need every import.</div>`;
}

function showStoryStage(stageKey) {
  if (!state.storyMap) return;
  state.storyStage = stageKey;
  document.querySelectorAll("[data-action='story-stage']").forEach((button) => {
    const active = button.dataset.stage === stageKey;
    button.classList.toggle("is-selected", active);
    button.setAttribute("aria-pressed", String(active));
  });
  const stage = storyStages.find((item) => item.key === stageKey);
  const files = state.storyMap.groups.get(stageKey) || [];
  const detail = document.querySelector("#story-detail");
  if (!detail || !stage) return;
  detail.innerHTML = `<strong>${escapeHtml(stage.title)}</strong><span>${escapeHtml(stage.description)}</span><div class="story-files">${files.map((file) => `<button class="story-file" data-action="preview-source" data-id="${escapeHtml(state.graphRepoId)}" data-path="${encodeURIComponent(file.file_path)}" type="button">${escapeHtml(file.file_path)}${file.connections ? `<small>${file.connections} links</small>` : ""}</button>`).join("")}</div>`;
  detail.querySelectorAll("[data-action='preview-source']").forEach((button) => button.addEventListener("click", () => { location.hash = `source/${button.dataset.id}/${button.dataset.path}`; }));
}

function setGraphView(view) {
  state.graphView = view === "details" ? "details" : "story";
  const story = document.querySelector("#graph-story-panel");
  const details = document.querySelector("#graph-detail-panel");
  if (story) story.hidden = state.graphView !== "story";
  if (details) details.hidden = state.graphView !== "details";
  document.querySelectorAll("[data-action='graph-view-tab']").forEach((button) => {
    const active = button.dataset.view === state.graphView;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", String(active));
  });
  if (state.graphView === "details") {
    state.cy?.destroy();
    state.cy = null;
    mountDependencyGraph();
  } else {
    state.cy?.destroy();
    state.cy = null;
  }
}

async function repoView(id) {
  if (!token()) return authView();
  try {
    const [repo, stats, files, graph, architecture, debt, quality, tests, history, tour, latestChange, feedback] = await Promise.all(["/repos/" + id, "/repos/" + id + "/stats", "/repos/" + id + "/files", "/repos/" + id + "/graph/files", "/repos/" + id + "/architecture", "/repos/" + id + "/technical-debt", "/repos/" + id + "/documentation/quality", "/repos/" + id + "/test-intelligence", "/repos/" + id + "/history", "/repos/" + id + "/tour", "/repos/" + id + "/pr-analysis/latest", "/repos/" + id + "/feedback/summary"].map((path) => api(path).catch((error) => ({ unavailable: error.message }))));
    if (repo.unavailable) throw new Error(repo.unavailable);
    state.graphData = graph.unavailable ? null : graph;
    state.graphRepoId = id;
    state.graphMode = "connected";
    state.graphView = "story";
    state.storyMap = graph.unavailable ? null : buildStoryMap(graph);
    state.storyStage = state.storyMap && storyStages.find((stage) => state.storyMap.groups.get(stage.key)?.length)?.key;
    const unavailable = (data) => data?.unavailable ? `<p class="muted">Unavailable: ${escapeHtml(data.unavailable)}</p>` : null;
    const fileList = unavailable(files) || `<div class="data-list">${files.slice(0, 20).map((file) => `<div class="data-row"><span>${escapeHtml(file.file_path)}</span>${previewButton(id, file.file_path)}</div>`).join("") || "<p class='muted'>No indexed files available yet.</p>"}</div>${files.length > 20 ? `<p class="muted" style="margin-top:12px">Showing 20 of ${files.length} files.</p>` : ""}`;
    const graphPanel = unavailable(graph) || `<section class="card graph-card" aria-labelledby="dependency-graph-title"><div class="graph-head"><div><p class="eyebrow">How this app works</p><h2 id="dependency-graph-title">Repository story map</h2><p class="muted">Start with the simple story. Open the developer map only when you need exact import connections.</p></div></div><div class="story-tabs" role="tablist" aria-label="Repository map detail"><button class="button secondary graph-view-button is-active" id="story-map-tab" data-action="graph-view-tab" data-view="story" role="tab" aria-controls="graph-story-panel" aria-selected="true" type="button">Simple story</button><button class="button secondary graph-view-button" id="developer-map-tab" data-action="graph-view-tab" data-view="details" role="tab" aria-controls="graph-detail-panel" aria-selected="false" type="button">Developer file map</button></div><div id="graph-story-panel" role="tabpanel" aria-labelledby="story-map-tab">${renderStoryMap(state.storyMap, id)}</div><div id="graph-detail-panel" role="tabpanel" aria-labelledby="developer-map-tab" hidden><div class="graph-head graph-head-detail"><p class="muted">Each dot is a file. Arrows mean “this file uses that file.” Choose a dot to trace the direct connections.</p><div class="graph-actions"><button class="button secondary" data-action="graph-reset" type="button">Reset focus</button><button class="button secondary" data-action="graph-fit" type="button">Fit map</button><button class="button secondary" data-action="graph-layout" type="button">Re-layout</button></div></div><div class="graph-toolbar"><div class="graph-view-switch" role="group" aria-label="File-map scope"><button class="button secondary graph-view-button is-active" data-action="graph-view" data-view="connected" type="button" aria-pressed="true">Connected files</button><button class="button secondary graph-view-button" data-action="graph-view" data-view="all" type="button" aria-pressed="false">All files</button></div><span id="graph-summary" class="graph-summary" role="status" aria-live="polite"></span></div><div id="dependency-graph" class="dependency-graph" role="img" aria-label="Interactive dependency graph of indexed files"></div><div class="graph-footer"><div class="graph-legend" aria-label="Graph legend"><span><i class="legend-dot backend"></i>Backend</span><span><i class="legend-dot frontend"></i>Frontend</span><span><i class="legend-dot tests"></i>Tests</span><span><i class="legend-dot configuration"></i>Config/docs</span><span><i class="legend-line outgoing"></i>Uses</span><span><i class="legend-line incoming"></i>Used by</span></div><div id="graph-selection" class="graph-selection" role="status" aria-live="polite">Select a file to inspect its direct relationships.</div></div></div></section>`;
    const indexingNotice = ["indexing", "pending"].includes(repo.status) ? `<div class="indexing-notice" role="status" aria-live="polite"><span class="indexing-pulse" aria-hidden="true"></span><div><strong>Indexing in progress</strong><p>Repository intelligence will appear as files are parsed. This page refreshes automatically.</p></div></div>` : repo.status === "error" ? `<div class="alert" role="alert"><strong>Indexing needs attention.</strong> Re-index the repository to retry.</div>` : "";
    const tourPanel = unavailable(tour) || `<div class="data-list"><div class="data-row"><span>Connected files</span><strong>${tour.file_count || 0}</strong></div><div class="data-row"><span>Relationships</span><strong>${tour.relationship_count || 0}</strong></div>${(tour.key_files || []).slice(0, 5).map((item) => `<div class="data-row"><span><strong>${escapeHtml(item.file_path)}</strong><small>${escapeHtml(item.layer)} · ${item.connections} connections</small></span>${previewButton(id, item.file_path)}</div>`).join("")}</div>`;
    const latestPanel = unavailable(latestChange) || `<p class="muted">${escapeHtml(latestChange.short_sha || "")} · ${escapeHtml(latestChange.author || "Unknown")}</p><h3>${escapeHtml(latestChange.message || "Latest change")}</h3><div class="data-list"><div class="data-row"><span>Changes</span><strong>+${latestChange.insertions || 0} / −${latestChange.deletions || 0}</strong></div><div class="data-row"><span>Files changed</span><strong>${(latestChange.changed_files || []).length}</strong></div></div><p class="muted">${(latestChange.recommendations || []).map(escapeHtml).join(" ")}</p><button class="button secondary" data-action="cross-impact" data-id="${id}" type="button">Check downstream repositories</button><div id="cross-impact-results" class="security-results" role="status" aria-live="polite"></div>`;
    const feedbackPanel = unavailable(feedback) || `<strong class="metric-value">${feedback.total ? Math.round((feedback.helpful_rate || 0) * 100) + "%" : "—"}</strong><p class="muted">${feedback.total ? `${feedback.helpful} helpful of ${feedback.total} ratings.` : "Rate answers in chat to build a quality signal."}</p>`;
    const evaluationPanel = `<div class="card evaluation-card"><h3>Retrieval evaluation</h3><p class="muted">Check whether code search retrieves files you expect. This uses embeddings only; it does not generate an AI answer.</p><form data-action="evaluation-form" data-id="${id}"><div class="form-row"><label for="eval-question">Test question</label><input id="eval-question" name="question" maxlength="1000" required placeholder="Where is login handled?" /></div><div class="form-row"><label for="eval-files">Expected file paths (one per line)</label><textarea id="eval-files" name="expected_files" required placeholder="backend/app/api/auth.py"></textarea></div><button class="button secondary" type="submit">Run retrieval check</button></form><div id="evaluation-results" class="evaluation-results" aria-live="polite"></div></div>`;
    const securityPanel = `<div class="card security-card"><div class="security-head"><div><h3>Security quick check</h3><p class="muted">Opt-in heuristic scan for likely committed secrets. Values are never displayed.</p></div><button class="button secondary" data-action="security-scan" data-id="${id}" type="button">Run scan</button></div><div id="security-scan-results" class="security-results" role="status" aria-live="polite"></div></div>`;
    return shell(`<div class="hero"><div><p class="eyebrow">Repository intelligence</p><h1>${escapeHtml(repo.name)}</h1><p class="lede">${escapeHtml(repo.full_name)} · indexed ${formatDate(repo.last_indexed_at)}</p></div><div class="actions"><button class="button secondary" data-action="reindex" data-id="${id}" type="button">Re-index</button><a class="button primary" href="#chat/${id}">Ask the codebase</a><button class="button danger" data-action="delete-repo" data-id="${id}" type="button">Delete</button></div></div>${indexingNotice}<div class="grid stats"><div class="card"><span class="metric-label">Status</span><strong class="metric-value" style="font-size:20px"><span class="status ${escapeHtml(repo.status)}">${escapeHtml(repo.status)}</span></strong></div><div class="card"><span class="metric-label">Files</span><strong class="metric-value">${stats.file_count ?? repo.file_count ?? 0}</strong></div><div class="card"><span class="metric-label">Code chunks</span><strong class="metric-value">${stats.chunk_count ?? repo.chunk_count ?? 0}</strong></div><div class="card"><span class="metric-label">Languages</span><strong class="metric-value" style="font-size:15px">${escapeHtml((stats.languages || repo.languages || []).join(", ") || "—")}</strong></div></div>${graphPanel}<div class="grid cards"><div class="card"><h3>Repository tour</h3>${tourPanel}</div><div class="card"><h3>Latest change</h3>${latestPanel}</div><div class="card"><h3>Indexed files</h3>${fileList}</div><div class="card"><h3>Architecture</h3>${unavailable(architecture) || `<div class="data-list">${(architecture.layers || []).map((layer) => `<div class="data-row"><span>${escapeHtml(layer.name)}</span><strong>${layer.file_count}</strong></div>`).join("") || "<p class='muted'>No architecture layers available yet.</p>"}</div>`}</div><div class="card"><h3>Documentation quality</h3>${unavailable(quality) || `<strong class="metric-value">${Math.round((quality.coverage || 0) * 100)}%</strong><p class="muted">${quality.documented_symbol_count || 0} documented of ${quality.symbol_count || 0} symbols.</p>`}</div><div class="card"><h3>Test intelligence</h3>${unavailable(tests) || `<strong class="metric-value">${tests.tested_file_count || 0}</strong><p class="muted">source files with related tests · ${tests.untested_file_count || 0} gaps</p>`}</div><div class="card"><h3>Answer feedback</h3>${feedbackPanel}</div><div class="card"><h3>Technical debt</h3>${unavailable(debt) || `<strong class="metric-value">${debt.signals?.length || 0}</strong><p class="muted">ranked signals across ${debt.files_analyzed || 0} analyzed files.</p>`}</div><div class="card"><h3>Git history</h3>${unavailable(history) || `<strong class="metric-value">${history.count || history.commits?.length || 0}</strong><p class="muted">recent commits available for change analysis.</p>`}</div>${securityPanel}${evaluationPanel}</div>`);
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
  if (state.graphView !== "details" || !container || !state.graphData || !window.cytoscape) return;
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

function renderChatAnswer(question, answer) {
  const citations = (answer.citations || []).map((citation) => `<span class="citation">${escapeHtml(citation.file_path)}:${citation.start_line}-${citation.end_line}</span>`).join("");
  return `<div class="message"><p>${escapeHtml(answer.answer).replace(/\n/g, "<br />")}</p><p class="muted">Version ${escapeHtml(answer.version_ref || "default")} · ${escapeHtml(answer.model)} · ${answer.retrieval_count} retrieved chunks · ${(answer.citation_coverage * 100).toFixed(0)}% citation coverage${answer.tools_used?.length ? ` · Tools: ${answer.tools_used.map(escapeHtml).join(", ")}` : ""}</p><div>${citations}</div><div class="chat-feedback" role="group" aria-label="Answer feedback"><span>Was this answer helpful?</span><button class="feedback-button" data-action="answer-feedback" data-rating="helpful" type="button" aria-label="Mark answer helpful">👍 Helpful</button><button class="feedback-button" data-action="answer-feedback" data-rating="not_helpful" type="button" aria-label="Mark answer not helpful">👎 Not helpful</button><span id="feedback-status" class="feedback-status" role="status" aria-live="polite"></span></div></div>`;
}

async function loadChatVersions(repoId, preferredVersion = state.selectedVersion) {
  const picker = document.querySelector("#chat-version");
  const status = document.querySelector("#version-status");
  if (!picker || !status) return;
  try {
    const versions = await api(`/repos/${repoId}/versions`);
    if (location.hash !== `#chat/${repoId}`) return;
    picker.innerHTML = versions.map((version) => {
      const label = version.version_ref === "default"
        ? `Default branch · ${version.ref_name}`
        : `${version.ref_type} · ${version.ref_name}`;
      const availability = version.status === "ready" ? "ready" : version.status;
      return `<option value="${escapeHtml(version.version_ref)}" ${version.status === "ready" ? "" : "disabled"}>${escapeHtml(label)} · ${escapeHtml(availability)}</option>`;
    }).join("");
    const selected = versions.find((version) => version.version_ref === preferredVersion && version.status === "ready")
      || versions.find((version) => version.version_ref === "default" && version.status === "ready");
    if (selected) {
      picker.value = selected.version_ref;
      state.selectedVersion = selected.version_ref;
    }
    const readyVersions = versions.filter((version) => version.status === "ready");
    const compareOptions = readyVersions.map((version) => {
      const label = version.version_ref === "default"
        ? `Default · ${version.ref_name}`
        : `${version.ref_type} · ${version.ref_name}`;
      return `<option value="${escapeHtml(version.version_ref)}">${escapeHtml(label)}</option>`;
    }).join("");
    const basePicker = document.querySelector("#compare-base-version");
    const headPicker = document.querySelector("#compare-head-version");
    if (basePicker && headPicker) {
      basePicker.innerHTML = compareOptions;
      headPicker.innerHTML = compareOptions;
      basePicker.value = readyVersions.some((version) => version.version_ref === "default") ? "default" : (readyVersions[0]?.version_ref || "");
      headPicker.value = readyVersions.find((version) => version.version_ref === preferredVersion && version.version_ref !== basePicker.value)?.version_ref
        || readyVersions.find((version) => version.version_ref !== basePicker.value)?.version_ref
        || basePicker.value;
      const compareButton = document.querySelector("[data-action='compare-versions']");
      if (compareButton) compareButton.disabled = readyVersions.length < 2;
    }
    const inProgress = versions.some((version) => ["pending", "indexing"].includes(version.status));
    const failed = versions.find((version) => version.version_ref === preferredVersion && version.status === "error");
    status.textContent = failed?.error_message || (inProgress ? "A version is indexing. This list refreshes automatically." : "Only indexed versions can be queried.");
    if (inProgress && !state.versionPollTimer) {
      state.versionPollTimer = window.setTimeout(() => {
        state.versionPollTimer = null;
        loadChatVersions(repoId, preferredVersion);
      }, 2500);
    }
  } catch (error) {
    status.textContent = `Could not load versions: ${error.message}`;
  }
}

async function submitAnswerFeedback(button) {
  const answer = state.chatAnswer;
  if (!answer || button.disabled) return;
  const controls = document.querySelectorAll("[data-action='answer-feedback']");
  controls.forEach((control) => { control.disabled = true; });
  const status = document.querySelector("#feedback-status");
  if (status) { status.classList.remove("is-error"); status.textContent = "Saving…"; }
  try {
    await api(`/repos/${state.graphRepoId || location.hash.split("/")[1]}/feedback`, {
      method: "POST",
      body: JSON.stringify({
        question: answer.question,
        rating: button.dataset.rating,
        model: answer.model,
        retrieval_count: answer.retrieval_count,
        citation_count: answer.citations.length,
      }),
    });
    controls.forEach((control) => control.classList.toggle("is-selected", control === button));
    if (status) status.textContent = "Thanks — feedback recorded.";
  } catch (error) {
    controls.forEach((control) => { control.disabled = false; });
    if (status) { status.classList.add("is-error"); status.textContent = `Could not save feedback: ${error.message}`; }
  }
}

function chatView(id) {
  if (!token()) return authView();
  return shell(`<div class="chat"><div><a class="muted" href="#repo/${id}">← Back to repository</a><p class="eyebrow" style="margin-top:28px">Cited code Q&A</p><h1 style="font-size:38px">Ask the codebase.</h1><p class="lede" style="font-size:14px">Choose an indexed branch or tag for version-specific answers and citations.</p></div><div id="chat-log"></div><form id="chat-form" class="card"><div class="form-row"><label for="chat-version">Answer from this version</label><select id="chat-version" name="version_ref"><option value="default">Loading indexed versions…</option></select><small id="version-status" class="muted" role="status" aria-live="polite">Loading version list…</small></div><div class="version-index-form"><strong>Index another branch or tag</strong><div class="version-index-fields"><label><span class="sr-only">Reference type</span><select id="version-ref-type" name="ref_type"><option value="branch">Branch</option><option value="tag">Tag</option></select></label><label class="sr-only" for="version-ref-name">Branch or tag name</label><input id="version-ref-name" name="ref_name" maxlength="200" placeholder="feature/new-search or v1.2.0"/><button class="button secondary" data-action="index-version" type="button">Index version</button></div></div><section class="version-compare"><div><strong>Compare indexed versions</strong><p class="muted">Review exact file changes between two ready snapshots. No AI request is used.</p></div><div class="version-compare-fields"><label for="compare-base-version">From<select id="compare-base-version"><option value="">Loading…</option></select></label><label for="compare-head-version">To<select id="compare-head-version"><option value="">Loading…</option></select></label><button class="button secondary" data-action="compare-versions" type="button" disabled>Compare</button></div><div id="version-compare-result" aria-live="polite"></div></section><div class="form-row"><label for="question">Your question</label><textarea id="question" name="question" placeholder="Where is authentication implemented, and what calls it?" required></textarea></div><div class="actions"><button class="button primary" type="submit">Ask with citations</button><button class="button secondary" data-action="ask-agent" type="button">Ask agent with tools</button></div></form></div>`);
}

function renderVersionComparison(comparison) {
  const base = comparison.base_version?.version_ref || "base";
  const head = comparison.head_version?.version_ref || "head";
  const files = comparison.changes.map((change) => {
    const citationFor = (item, version) => {
      if (!item) return "";
      const ranges = item.line_ranges.length ? `:${item.line_ranges.join(",")}` : "";
      return `<span class="citation">${escapeHtml(version)} · ${escapeHtml(item.file_path)}${escapeHtml(ranges)}</span>`;
    };
    const citation = `${citationFor(change.base_citation, base)}${citationFor(change.head_citation, head)}`;
    const diff = change.diff ? `<pre class="version-diff">${escapeHtml(change.diff)}</pre>` : `<p class="muted">${escapeHtml(change.omitted_reason || "No text diff available.")}</p>`;
    return `<details class="version-change"><summary><strong>${escapeHtml(change.file_path)}</strong><span class="version-change-status">${escapeHtml(change.status)}</span></summary>${citation}${diff}</details>`;
  }).join("");
  const limitNote = comparison.truncated ? `<p class="muted">Some file contents were omitted by the display limit. The changed-file count still includes them.</p>` : "";
  return `<div class="version-compare-summary"><strong>${comparison.changed_file_count} changed ${comparison.changed_file_count === 1 ? "file" : "files"}</strong><span>${escapeHtml(base)} → ${escapeHtml(head)}</span></div>${limitNote}${files || `<p class="muted">These indexed versions contain identical files.</p>`}`;
}

async function runSecurityScan(button) {
  const results = document.querySelector("#security-scan-results");
  if (!results || button.disabled) return;
  button.disabled = true;
  button.textContent = "Scanning…";
  results.textContent = "Checking indexed source files for redacted secret patterns…";
  try {
    const result = await api(`/repos/${button.dataset.id}/security/secrets/scan`, { method: "POST" });
    const findings = result.findings || [];
    results.innerHTML = findings.length
      ? `<strong class="text-destructive">${findings.length} possible finding${findings.length === 1 ? "" : "s"}</strong><div class="security-finding-list">${findings.slice(0, 12).map((finding) => `<div class="security-finding"><strong>${escapeHtml(finding.pattern)}</strong><span>${escapeHtml(finding.file_path)}:${finding.line} · ${escapeHtml(finding.confidence)} confidence</span><code>${escapeHtml(finding.redacted_preview || "[redacted]")}</code><p><b>Why it matters:</b> ${escapeHtml(finding.why_it_matters || "A credential-like value may be committed in source.")}</p><p><b>Suggested fix:</b> ${escapeHtml(finding.suggested_fix || "Rotate the credential and move it to a secret manager.")}</p></div>`).join("")}</div>${findings.length > 12 ? `<p class="muted">Showing 12 of ${findings.length} findings.</p>` : ""}`
      : `<strong class="text-success">No likely secrets found.</strong><p class="muted">Scanned ${result.scanned_files || 0} files with heuristic rules.</p>`;
  } catch (error) {
    results.innerHTML = errorBox(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Run again";
  }
}

async function sourceView(id, encodedPath) {
  if (!token()) return authView();
  try { const source = await api(`/repos/${id}/source/${encodedPath}`); return shell(`<div><a class="muted" href="#repo/${id}">← Back to repository</a><p class="eyebrow" style="margin-top:28px">Secure source preview</p><h1 style="font-size:38px">${escapeHtml(source.file_path)}</h1><p class="muted">${escapeHtml(source.language)} · bounded preview</p><pre class="code">${escapeHtml(source.content)}</pre></div>`); } catch (error) { return shell(`<a class="muted" href="#repo/${id}">← Back to repository</a>${errorBox(error.message)}`); }
}

async function accountView() {
  if (!token()) return authView();
  try {
    const [user, usage, workspaces, repos, health] = await Promise.all([api("/auth/me"), api("/auth/usage"), api("/auth/workspaces"), api("/repos"), api("/health")]);
    const repoMetrics = await Promise.all(repos.map(async (repo) => {
      const [metrics, feedback] = await Promise.all([
        api(`/repos/${repo.id}/query-metrics`).catch(() => null),
        api(`/repos/${repo.id}/feedback/summary`).catch(() => null),
      ]);
      return { metrics, feedback };
    }));
    const metricRows = repoMetrics.map((item) => item.metrics).filter(Boolean);
    const feedbackRows = repoMetrics.map((item) => item.feedback).filter(Boolean);
    const queryCount = metricRows.reduce((sum, item) => sum + (item.total_queries || 0), 0);
    const weightedLatency = queryCount ? metricRows.reduce((sum, item) => sum + (item.average_total_latency_ms || 0) * (item.total_queries || 0), 0) / queryCount : 0;
    const totalTokens = metricRows.reduce((sum, item) => sum + (item.total_tokens || 0), 0);
    const estimatedCost = metricRows.reduce((sum, item) => sum + (item.estimated_cost_usd || 0), 0);
    const ratingCount = feedbackRows.reduce((sum, item) => sum + (item.total || 0), 0);
    const helpfulCount = feedbackRows.reduce((sum, item) => sum + (item.helpful || 0), 0);
    const healthStatus = health?.status === "healthy" ? "Healthy" : "Needs attention";
    const workspaceCards = workspaces.map((workspace) => `<div class="card"><div class="section-head" style="margin:0 0 12px"><div><h3>${escapeHtml(workspace.name)}</h3><p class="muted">${escapeHtml(workspace.role)} · ${escapeHtml(workspace.slug)}</p></div>${["owner", "admin"].includes(workspace.role) ? `<button class="button secondary" data-action="rename-workspace" data-id="${workspace.id}" data-name="${escapeHtml(workspace.name)}" type="button">Rename</button>` : ""}</div><div class="data-list"><div class="data-row"><span>Workspace ID</span><code>${escapeHtml(workspace.id)}</code></div></div></div>`).join("");
    const observabilityPanel = `<div class="section-head"><div><p class="eyebrow">Phase 4 observability</p><h2>System signals</h2><p class="muted">A lightweight view of the live API, query performance, provider usage, and answer quality.</p></div></div><div class="grid cards"><div class="card"><h3>API health</h3><strong class="metric-value"><span class="status ${health?.status === "healthy" ? "ready" : "error"}">${healthStatus}</span></strong><p class="muted">Database: ${escapeHtml(health?.database || "unknown")} · Redis: ${escapeHtml(health?.redis || "unknown")}</p></div><div class="card"><h3>Queries</h3><strong class="metric-value">${queryCount}</strong><p class="muted">Across ${repos.length} accessible ${repos.length === 1 ? "repository" : "repositories"} · ${weightedLatency ? `${Math.round(weightedLatency)} ms average` : "no latency sample yet"}.</p></div><div class="card"><h3>Provider usage</h3><strong class="metric-value">${totalTokens.toLocaleString()}</strong><p class="muted">Recorded tokens · estimated cost $${estimatedCost.toFixed(4)}.</p></div><div class="card"><h3>Answer quality</h3><strong class="metric-value">${ratingCount ? Math.round((helpfulCount / ratingCount) * 100) + "%" : "—"}</strong><p class="muted">${ratingCount ? `${helpfulCount} helpful of ${ratingCount} ratings.` : "No answer ratings yet."}</p></div></div>`;
    return shell(`<div class="hero"><div><p class="eyebrow">Account and access</p><h1 style="font-size:38px">Your engineering workspace.</h1><p class="lede" style="font-size:14px">Manage identity, usage, workspace membership, and the live Phase 4 signals.</p></div></div><div class="grid cards"><div class="card"><h3>Identity</h3><div class="data-list"><div class="data-row"><span>Email</span><strong>${escapeHtml(user.email)}</strong></div><div class="data-row"><span>Role</span><strong>${escapeHtml(user.role)}</strong></div></div></div><div class="card"><h3>AI usage</h3><strong class="metric-value">${usage.used ?? 0}</strong><p class="muted">of ${usage.daily_limit ?? "—"} daily provider requests used.</p></div><div class="card"><h3>Create workspace</h3><form id="workspace-form"><div class="form-row"><label for="workspace-name">Workspace name</label><input id="workspace-name" name="name" minlength="2" required placeholder="Platform team" /></div><button class="button primary" type="submit">Create workspace</button></form><div id="workspace-error" style="margin-top:10px"></div></div></div>${observabilityPanel}<div class="section-head"><div><p class="eyebrow">Workspace management</p><h2>Workspaces</h2></div></div><div class="grid cards">${workspaceCards || `<div class="empty"><p>No workspaces available.</p></div>`}</div>`);
  } catch (error) { return shell(errorBox(error.message)); }
}

function docsView() { return shell(`<div class="hero"><div><p class="eyebrow">Product guide</p><h1 style="font-size:42px">A clear map of your codebase.</h1><p class="lede">AISE combines repository indexing, structural analysis, history, and grounded AI answers in one engineering workspace.</p></div></div><div class="grid cards">${feature("A", "Connect", "Bring a GitHub repository into a workspace and follow its indexing progress.")}${feature("B", "Explore", "Inspect architecture, dependencies, history, tests, documentation, and technical-debt signals.")}${feature("C", "Ask", "Ask natural-language questions and inspect the exact source citations behind each answer.")}</div>`); }

async function render() {
  const hash = location.hash.replace(/^#/, "") || "dashboard";
  if (state.refreshTimer) window.clearTimeout(state.refreshTimer);
  if (state.versionPollTimer) window.clearTimeout(state.versionPollTimer);
  state.refreshTimer = null;
  state.versionPollTimer = null;
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
  if (hash.startsWith("chat/")) await loadChatVersions(hash.split("/")[1]);
  bindEvents();
  if (hash.startsWith("repo/") && state.storyStage) showStoryStage(state.storyStage);
  mountDependencyGraph();
  if (hash.startsWith("repo/") && document.querySelector(".indexing-notice")) {
    state.refreshTimer = window.setTimeout(() => {
      if (location.hash === `#${hash}`) render();
    }, 5000);
  }
}

async function submitAgentQuestion(button) {
  const form = document.querySelector("#chat-form");
  const question = String(new FormData(form).get("question") || "").trim();
  if (!question) { form.querySelector("textarea").focus(); return; }
  const log = document.querySelector("#chat-log");
  const versionRef = document.querySelector("#chat-version")?.value || "default";
  const sendButton = form.querySelector("button[type='submit']");
  button.disabled = true;
  sendButton.disabled = true;
  button.textContent = "Agent working…";
  state.chatAnswer = null;
  log.innerHTML = `<div class="message user">${escapeHtml(question)}</div>${setLoading("Selecting repository tools and collecting evidence…")}`;
  try {
    const response = await api(`/repos/${location.hash.split("/")[1]}/agent`, { method: "POST", body: JSON.stringify({ question, top_k: 5, version_ref: versionRef }) });
    state.chatAnswer = { question, model: response.model, retrieval_count: response.retrieval_count, citations: response.citations || [], version_ref: response.version_ref };
    log.innerHTML = `<div class="message user">${escapeHtml(question)}</div>${renderChatAnswer(question, response)}`;
    document.querySelectorAll("[data-action='answer-feedback']").forEach((control) => control.addEventListener("click", () => submitAnswerFeedback(control)));
  } catch (error) {
    log.innerHTML = errorBox(error.message);
  } finally {
    button.disabled = false;
    sendButton.disabled = false;
    button.textContent = "Ask agent with tools";
  }
}

function bindEvents() {
  document.querySelector("[data-action='ask-agent']")?.addEventListener("click", (event) => submitAgentQuestion(event.currentTarget));
  document.querySelector("#chat-version")?.addEventListener("change", (event) => { state.selectedVersion = event.currentTarget.value; });
  document.querySelector("[data-action='compare-versions']")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const result = document.querySelector("#version-compare-result");
    const repoId = location.hash.split("/")[1];
    const baseRef = document.querySelector("#compare-base-version").value;
    const headRef = document.querySelector("#compare-head-version").value;
    if (!baseRef || !headRef || baseRef === headRef) { result.innerHTML = errorBox("Choose two different indexed versions."); return; }
    button.disabled = true;
    button.textContent = "Comparing…";
    result.innerHTML = setLoading("Comparing indexed file snapshots…");
    try {
      const comparison = await api(`/repos/${repoId}/versions/compare`, { method: "POST", body: JSON.stringify({ base_ref: baseRef, head_ref: headRef }) });
      result.innerHTML = renderVersionComparison(comparison);
    } catch (error) {
      result.innerHTML = errorBox(error.message);
    } finally {
      button.disabled = false;
      button.textContent = "Compare";
    }
  });
  document.querySelector("[data-action='index-version']")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const refName = document.querySelector("#version-ref-name").value.trim();
    const refType = document.querySelector("#version-ref-type").value;
    const status = document.querySelector("#version-status");
    if (!refName) { document.querySelector("#version-ref-name").focus(); status.textContent = "Enter a branch or tag name first."; return; }
    button.disabled = true;
    button.textContent = "Starting…";
    try {
      const response = await api(`/repos/${location.hash.split("/")[1]}/versions/index`, { method: "POST", body: JSON.stringify({ ref_type: refType, ref_name: refName }) });
      state.selectedVersion = response.version_ref;
      await loadChatVersions(location.hash.split("/")[1], response.version_ref);
    } catch (error) {
      status.textContent = `Could not index version: ${error.message}`;
    } finally {
      button.disabled = false;
      button.textContent = "Index version";
    }
  });
  document.querySelector("[data-action='evaluation-form']")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const expectedFiles = String(values.get("expected_files") || "").split(/\r?\n/).map((path) => path.trim()).filter(Boolean);
    const resultBox = document.querySelector("#evaluation-results");
    const button = form.querySelector("button[type='submit']");
    if (!expectedFiles.length || expectedFiles.length > 20) {
      resultBox.innerHTML = errorBox("Enter between 1 and 20 expected file paths, one per line.");
      return;
    }
    button.disabled = true;
    button.textContent = "Evaluating retrieval…";
    resultBox.textContent = "Searching indexed code and comparing expected files…";
    try {
      const report = await api(`/repos/${form.dataset.id}/evaluate`, {
        method: "POST",
        body: JSON.stringify({ cases: [{ question: String(values.get("question") || "").trim(), expected_files: expectedFiles }], top_k: 5 }),
      });
      const summary = report.summary;
      const result = report.cases[0];
      resultBox.innerHTML = `<div class="evaluation-metrics"><div><span>Recall@K</span><strong>${Math.round(summary.recall_at_k * 100)}%</strong></div><div><span>MRR</span><strong>${summary.mrr.toFixed(2)}</strong></div><div><span>Expected-file hit</span><strong>${Math.round(summary.expected_file_hit_rate * 100)}%</strong></div><div><span>Retrieval time</span><strong>${Math.round(summary.average_retrieval_latency_ms)} ms</strong></div></div><p><strong>Matched:</strong> ${result.matched_files.length ? result.matched_files.map(escapeHtml).join(", ") : "None of the expected files appeared in the results."}</p><p class="muted"><strong>Retrieved:</strong> ${result.retrieved_files.length ? result.retrieved_files.map(escapeHtml).join(", ") : "No files returned."}</p>`;
    } catch (error) {
      resultBox.innerHTML = errorBox(error.message);
    } finally {
      button.disabled = false;
      button.textContent = "Run retrieval check";
    }
  });
  document.querySelector("[data-action='cross-impact']")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const resultBox = document.querySelector("#cross-impact-results");
    button.disabled = true;
    button.textContent = "Checking manifests…";
    try {
      const report = await api(`/repos/${button.dataset.id}/impact/cross-repository`);
      resultBox.innerHTML = `<p class="muted">${escapeHtml(report.note)}</p>${report.impact_candidates.length ? `<div class="data-list">${report.impact_candidates.map((candidate) => `<div class="data-row"><span><strong>${escapeHtml(candidate.full_name)}</strong><br/>Matches: ${escapeHtml(candidate.matched_packages.join(", "))}<br/><small>${escapeHtml(candidate.assessment)}</small></span><a class="button secondary compact-button" href="#repo/${encodeURIComponent(candidate.repository_id)}">Open</a></div>`).join("")}</div>` : `<p>No declared dependencies matched across ${report.repositories_checked} accessible ready repositories.</p>`}`;
    } catch (error) {
      resultBox.innerHTML = errorBox(error.message);
    } finally {
      button.disabled = false;
      button.textContent = "Check downstream repositories";
    }
  });
  document.querySelector("#workspace-search-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const query = String(new FormData(form).get("q") || "").trim();
    const button = form.querySelector("button[type='submit']");
    const results = document.querySelector("#workspace-search-results");
    button.disabled = true;
    button.textContent = "Searching…";
    results.innerHTML = setLoading("Searching accessible repositories…");
    try {
      const response = await api(`/repos/search/all?q=${encodeURIComponent(query)}`);
      results.innerHTML = response.results.length
        ? `<p class="muted">${response.results.length} matches across ${response.repositories_searched} ready repositories.</p><div class="workspace-search-list">${response.results.map((item) => `<article class="workspace-search-result"><div><strong>${escapeHtml(item.repository_name)}</strong><span>${escapeHtml(item.full_name)} · ${escapeHtml(item.file_path)}:${item.start_line}-${item.end_line}</span></div><pre>${escapeHtml(item.snippet)}</pre><button class="button secondary compact-button" data-action="preview-source" data-id="${escapeHtml(item.repository_id)}" data-path="${encodeURIComponent(item.file_path)}" type="button">Open source</button></article>`).join("")}</div>`
        : `<p class="muted">No matches in ${response.repositories_searched} ready repositories.</p>`;
      results.querySelectorAll("[data-action='preview-source']").forEach((preview) => preview.addEventListener("click", () => { location.hash = `source/${preview.dataset.id}/${preview.dataset.path}`; }));
    } catch (error) {
      results.innerHTML = errorBox(error.message);
    } finally {
      button.disabled = false;
      button.textContent = "Search code";
    }
  });
  document.querySelector("[data-action='toggle-auth']")?.addEventListener("click", () => { state.authMode = state.authMode === "login" ? "register" : "login"; render(); });
  document.querySelector("[data-action='signout']")?.addEventListener("click", () => { localStorage.removeItem("aise_access_token"); state.user = null; location.hash = "auth"; });
  document.querySelector("#workspace-form")?.addEventListener("submit", async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); try { await api("/auth/workspaces", { method: "POST", body: JSON.stringify({ name: form.get("name") }) }); render(); } catch (error) { document.querySelector("#workspace-error").innerHTML = errorBox(error.message); } });
  document.querySelectorAll("[data-action='rename-workspace']").forEach((button) => button.addEventListener("click", async () => { const name = window.prompt("New workspace name", button.dataset.name); if (!name || name.trim() === button.dataset.name) return; try { await api(`/auth/workspaces/${button.dataset.id}`, { method: "PATCH", body: JSON.stringify({ name: name.trim() }) }); render(); } catch (error) { window.alert(error.message); } }));
  document.querySelector("#auth-form")?.addEventListener("submit", async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); const endpoint = state.authMode === "register" ? "/auth/register" : "/auth/login"; try { const result = await api(endpoint, { method: "POST", body: JSON.stringify({ email: form.get("email"), password: form.get("password") }) }); localStorage.setItem("aise_access_token", result.access_token); location.hash = "dashboard"; } catch (error) { document.querySelector("#auth-error").innerHTML = errorBox(error.message); } });
  document.querySelector("#connect-form")?.addEventListener("submit", async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); const button = event.currentTarget.querySelector("button[type='submit']"); button.disabled = true; button.textContent = "Connecting and indexing…"; try { const repo = await api("/repos/connect", { method: "POST", body: JSON.stringify({ github_url: form.get("github_url"), name: form.get("name") || null }) }); location.hash = `repo/${repo.id}`; } catch (error) { button.disabled = false; button.textContent = "Connect and index"; document.querySelector("#connect-error").innerHTML = errorBox(error.message); } });
  document.querySelector("[data-action='reindex']")?.addEventListener("click", async (event) => { const button = event.currentTarget; button.disabled = true; button.textContent = "Starting…"; try { await api(`/repos/${button.dataset.id}/reindex`, { method: "POST" }); button.textContent = "Indexing started"; } catch (error) { button.disabled = false; button.textContent = error.message; } });
  document.querySelector("[data-action='delete-repo']")?.addEventListener("click", async (event) => { const button = event.currentTarget; if (!window.confirm("Delete this repository and its indexed data?")) return; button.disabled = true; try { await api(`/repos/${button.dataset.id}`, { method: "DELETE" }); location.hash = "dashboard"; } catch (error) { button.disabled = false; window.alert(error.message); } });
  document.querySelector("[data-action='security-scan']")?.addEventListener("click", (event) => runSecurityScan(event.currentTarget));
  document.querySelectorAll("[data-action='preview-source']").forEach((button) => button.addEventListener("click", () => { location.hash = `source/${button.dataset.id}/${button.dataset.path}`; }));
  document.querySelector("[data-action='graph-reset']")?.addEventListener("click", clearGraphFocus);
  document.querySelector("[data-action='graph-fit']")?.addEventListener("click", () => state.cy?.fit(undefined, 38));
  document.querySelector("[data-action='graph-layout']")?.addEventListener("click", () => runGraphLayout());
  document.querySelectorAll("[data-action='graph-view-tab']").forEach((button) => button.addEventListener("click", () => setGraphView(button.dataset.view)));
  document.querySelectorAll("[data-action='story-stage']").forEach((button) => button.addEventListener("click", () => showStoryStage(button.dataset.stage)));
  document.querySelectorAll("[data-action='graph-view']").forEach((button) => button.addEventListener("click", () => {
    if (button.dataset.view === state.graphMode) return;
    state.graphMode = button.dataset.view === "all" ? "all" : "connected";
    state.cy?.destroy();
    state.cy = null;
    mountDependencyGraph();
  }));
  document.querySelector("#graph-selection")?.addEventListener("click", (event) => { const button = event.target.closest("[data-action='graph-preview']"); if (button) location.hash = `source/${button.dataset.id}/${button.dataset.path}`; });
  document.querySelectorAll("[data-action='answer-feedback']").forEach((button) => button.addEventListener("click", () => submitAnswerFeedback(button)));
  document.querySelector("#chat-form")?.addEventListener("submit", async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); const id = location.hash.split("/")[1]; const question = String(form.get("question") || "").trim(); const versionRef = String(form.get("version_ref") || "default"); const log = document.querySelector("#chat-log"); log.innerHTML = `<div class="message user">${escapeHtml(question)}</div>${setLoading("Retrieving and synthesizing cited code…")}`; event.currentTarget.querySelector("button[type='submit']").disabled = true; state.chatAnswer = null; try { const answer = await api(`/repos/${id}/query`, { method: "POST", body: JSON.stringify({ question, top_k: 5, version_ref: versionRef }) }); state.chatAnswer = { question, model: answer.model, retrieval_count: answer.retrieval_count, citations: answer.citations || [], version_ref: answer.version_ref }; log.innerHTML = `<div class="message user">${escapeHtml(question)}</div>${renderChatAnswer(question, answer)}`; document.querySelectorAll("[data-action='answer-feedback']").forEach((button) => button.addEventListener("click", () => submitAnswerFeedback(button))); } catch (error) { log.innerHTML = errorBox(error.message); } finally { event.currentTarget.querySelector("button[type='submit']").disabled = false; } });
}

window.addEventListener("hashchange", render);
render();
