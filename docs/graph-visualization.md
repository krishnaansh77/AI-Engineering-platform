# Dependency graph visualization

## Decision

The repository page leads with a **Repository story map**, not a raw dependency
network. It adapts the C4 model's “maps of code at different zoom levels” idea
to an onboarding-friendly view: people first see the app's apparent journey,
then choose a section to reveal its files, and only open the full file graph
when exact imports matter.

The story map groups files using conservative path heuristics into plain-language
stages such as **Screens people use**, **Work after a click**, and **Shared
building blocks**. Test files and startup/configuration files are shown as
supporting parts rather than mixed into the main journey. It deliberately does
not claim that every visible arrow represents a literal source-code edge; the
arrows describe the usual conceptual path through an application.

The **Developer file map** remains available as the second tab. It uses
Cytoscape.js because it is framework-independent, supports graph analysis and
event-driven selection, and can consume the existing `{nodes, edges}` API
response directly. Its connected-file view uses stable, deterministic layer
columns rather than a continually moving force layout. Isolated files are
hidden by default and available through an explicit All files control.

Sigma.js remains the scale-up option if repositories routinely produce graphs
with thousands of visible nodes. Its WebGL renderer is designed for much larger
graphs, but it would introduce a second graph data/rendering model through
Graphology and is not needed for the current file-level experience.

## Interaction model

- **Simple story** is the default. A user picks a stage to see the exact files
  inside it, then can open any file's bounded source preview.
- **Developer file map** is an explicit opt-in. Each dot is a file and each
  arrow means that one file imports or uses another.
- Selecting a file dims unrelated nodes and edges, keeps the direct neighborhood
  visible, and traces outgoing imports in amber and incoming dependants in teal.
- `Fit map` restores the viewport; `Reset focus` restores the full context.
- Node size represents connection count. Node shapes/colors represent inferred
  layers, while the complete indexed-file list remains below the graph as the
  keyboard-friendly fallback and source-preview path.
- Connected files are the default scope; All files makes isolated files visible
  when an investigator needs completeness.
- Reduced-motion preferences disable layout animation and rely on immediate
  state changes instead.

## Relevant implementation files

- `frontend_v2/index.html` loads the pinned Cytoscape.js browser build.
- `frontend_v2/app.js` fetches `/repos/:id/graph/files`, mounts the graph, and
  owns selection/layout behavior.
- `frontend_v2/styles.css` contains the graph surface, legend, controls, and
  reduced-motion styling.
- `django_backend/api/graph.py` provides the native Django graph response.

## Research references

- [Cytoscape.js documentation](https://js.cytoscape.org/index.html)
- [Cytoscape.js layout guidance](https://blog.js.cytoscape.org/2020/05/11/layouts/)
- [Sigma.js rendering concepts](https://www.sigmajs.org/concepts/rendering/)
- [Sigma.js interaction events](https://www.sigmajs.org/how-to/interactivity/interactions-events/)
- [C4 model: maps of code at different zoom levels](https://c4model.com/introduction)
- [C4 model: diagram levels and audiences](https://c4model.com/diagrams)
- [WCAG 2.2 animation from interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions)
