# Dependency graph visualization

## Decision

The redesigned frontend uses Cytoscape.js for the first interactive dependency
graph implementation. It is a good fit for the current file-level graph because
it is framework-independent, supports graph analysis and event-driven
selection, and can consume the existing `{nodes, edges}` API response directly.
The built-in CoSE layout is used for an animated first stabilization and for
explicit user-triggered re-layouts.

Sigma.js remains the scale-up option if repositories routinely produce graphs
with thousands of visible nodes. Its WebGL renderer is designed for much larger
graphs, but it would introduce a second graph data/rendering model through
Graphology and is not needed for the current file-level experience.

## Interaction model

- The graph is focus-plus-context, not a permanently moving force simulation.
- The first layout animates once; the user can run it again with `Re-layout`.
- Selecting a file dims unrelated nodes and edges, keeps the direct neighborhood
  visible, and traces outgoing imports in amber and incoming dependants in teal.
- `Fit graph` restores the viewport; `Clear focus` restores the full context.
- Node size represents connection count. Node shapes/colors represent inferred
  layers, while the complete indexed-file list remains below the graph as the
  keyboard-friendly fallback and source-preview path.
- Labels are quiet by default and appear for the selected node and its direct
  neighbors to protect readability in dense repositories.
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
- [WCAG 2.2 animation from interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions)
