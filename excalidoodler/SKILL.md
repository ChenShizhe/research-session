---
name: excalidoodler
description: >-
  Author and iteratively edit component-based figures — causal diagrams, DAGs,
  schematics, plots, model illustrations — with properly typeset LaTeX math, in
  Excalidraw (including Excalidraw Plus) by driving a browser with computer use.
  Use this whenever a user wants to build or revise a diagram/figure/illustration
  in Excalidraw that contains mathematical notation, or wants a figure assembled
  from separately-editable pieces (so they and their collaborators can keep tuning
  it by hand). Also trigger for the spoken/written alias "Excalidoodle." Trigger even when the user doesn't say "Excalidraw" explicitly — if
  they want an editable, math-bearing figure on a whiteboard-style canvas, or ask
  to tweak labels/panels/sizes on an existing one, reach for this skill. Excalidraw
  cannot render LaTeX itself, so naive approaches produce raw "$x$" text or flat
  images; this skill solves that and the human-in-the-loop editing problem.
---

# Excalidoodler — Excalidraw figure authoring

## Why this skill exists

Excalidraw is a fast, hand-drawn-feel canvas that researchers and their
collaborators love for figures. But it has two properties that make math-bearing
figures tricky, and this skill exists to handle both:

1. **Excalidraw does not typeset LaTeX.** A plain text element containing `$x_i$`
   shows the literal characters, not the math. So math must be pre-rendered to
   vector graphics before it reaches the canvas.
2. **The figure is edited by humans, not just you.** The user opens the same scene
   and nudges labels, resizes panels, recolors boxes — often between your turns,
   and often with collaborators. If you rebuild the figure from scratch you destroy
   their work. The figure must therefore be made of **independent, individually
   editable pieces**, and you must edit *around* the human, never over them.

The core idea: build the figure as many small components (each typeset expression
is its own vector image; each data panel is its own image; boxes/arrows are native
shapes), bring them onto the canvas as separate elements, and from then on make
**targeted** edits only.

## When to use it

- Building a new diagram/DAG/schematic/plot in Excalidraw that has math labels.
- Revising such a figure: changing a label, resizing or swapping a panel, adjusting
  a caption, adding a node — without disturbing the rest.
- Works in either Excalidraw Plus or the free public Excalidraw — see Workspace.

## Workspace — Excalidraw Plus or plain Excalidraw

This skill **never requires Excalidraw Plus.** Use whichever the user has:

- **Excalidraw Plus (preferred when available).** If the user is logged in, use it:
  a stable, named, cloud-synced workspace gives the figure a permanent home the user
  and collaborators can reopen. Use it for anything meant to last.
- **Plain Excalidraw (free, always works).** If there is no Excalidraw Plus, use the
  free public Excalidraw. Authoring and editing are **fully supported** — nothing in
  this skill depends on Plus. Only persistence is weaker: the scene lives in that
  browser's local storage, so save it explicitly with "Save to file" (a
  `.excalidraw` file the user keeps) and/or "Export to Link" for a shareable
  read-only snapshot.

Detect a logged-in Plus session or ask the user which they have; never block on Plus.
Either way, keep the source files locally (see Persistence) so the scene can be
rebuilt regardless.

## Dependencies

- A TeX distribution providing `latex` and `dvisvgm` (TeX Live ships both). This is
  the math→SVG path and is required for typeset labels.
- Optional: Python with `matplotlib`, or R, for data panels.
- A computer-use browser to drive Excalidraw.
- A clipboard mechanism: on macOS, `pbcopy`; otherwise an in-page button that calls
  `navigator.clipboard.writeText` under a real click (see Import).

## Component taxonomy — what becomes one element

The decomposition rule. **The smallest unit is a complete expression, never a
fragment of one.** Over-fragmenting (splitting `N = (N_1, N_2)` into `N`, `=`,
`(`, ...) makes the figure impossible to edit sensibly; under-fragmenting (one flat
image) makes it impossible to edit at all. So:

1. **Math expression unit.** Any LaTeX expression that must stay aligned together
   on one line is ONE element, rendered whole. Example: `$N = (N_1, N_2)$` stays
   intact.
2. **Floating symbol / short text.** A standalone symbol or short label that can
   move independently is its own element: `$Z$`, `$Y$`, `$\lambda_Y(t)$`.
3. **Data panel.** Each generated plot (an intensity curve, a spike train, a latent
   trajectory) is one image = one element.
4. **Structural shape.** Node boxes, arrows, tick marks, axis lines: native
   Excalidraw elements (rectangle, arrow, line) — not pre-rendered images, so they
   stay fully editable as shapes.
5. **Captions are editable LaTeX *source text*, not compiled images.** Put the
   LaTeX code into a normal text element (code font reads well). The user and their
   collaborators will edit the wording in place; a baked image screenshot cannot be
   edited. Captions are non-negotiable — a figure ships with a caption.

## Step 1 — Render each math unit to SVG

For every expression and floating symbol, write a minimal standalone LaTeX document
and convert it to a tight-bounding-box SVG with glyphs traced as paths (so the file
is portable and renders anywhere, independent of fonts).

Use `scripts/math_to_svg.py` (one expression per call), or do it directly:

```latex
% expr.tex
\documentclass[border=1pt]{standalone}
\usepackage{amsmath,amssymb,xcolor}
\begin{document}
$N = (N_1, N_2)$
\end{document}
```

```bash
latex -interaction=nonstopmode expr.tex
dvisvgm --no-fonts --exact-bbox expr.dvi -o expr.svg
```

- `standalone` + `--exact-bbox` crops tightly so the SVG drops in cleanly.
- `--no-fonts` traces glyphs to paths; no font support needed downstream.
- Color via `\color{...}` (xcolor) if you want a colored label, or leave black and
  recolor in Excalidraw after import.
- Name each file by role (`label-Z.svg`, `expr-N.svg`) so the component set is a
  stable, re-runnable manifest.

## Step 2 — Render each data panel

One file per panel (one panel = one element). Prefer **SVG** for crisp scaling;
use **PNG** for panels with dense filled regions (thousands of points), where SVG
balloons in size. With matplotlib, `fig.savefig("panel.svg")` (or `.png`); with R,
an SVG device.

## Step 3 — Assemble an Excalidraw clipboard payload

Excalidraw's own copy/paste format is a JSON object:

```json
{ "type": "excalidraw/clipboard", "elements": [ ... ], "files": { ... } }
```

- One `image` element per rendered unit: `{type:"image", id, x, y, width, height,
  fileId, status:"saved", scale:[1,1], ...}`. Set approximate coordinates for
  layout; the user fine-tunes later.
- Each rendered SVG/PNG is embedded in `files`, keyed by its `fileId`:
  `{mimeType, id, dataURL:"data:<mime>;base64,<...>", created}`.
- Native shapes (rectangles, arrows, lines) go in the same `elements` array.

`scripts/assemble_payload.py` builds this from a small component manifest (see its
header). It reads each file's intrinsic size (SVG `viewBox`, or PNG IHDR) so image
elements keep the right aspect ratio.

## Step 4 — Import onto the canvas

Goal: every component lands as its own editable element.

1. **Put the payload on the system clipboard.**
   - *macOS (simplest, validated):* `pbcopy < payload.json`.
   - *Browser-general:* a clipboard write from a page needs a real user gesture
     (transient activation). Inject a temporary button whose click handler calls
     `navigator.clipboard.writeText(payload)`, then click it with a trusted click.
     A bare scripted `writeText` hangs because it lacks activation.
2. **Focus the canvas and paste** (`Cmd/Ctrl+V`). Every component arrives as its own
   editable element; relative offsets are preserved (Excalidraw shifts the pasted
   group toward the cursor), so design with relative coordinates.

**Paste APPENDS — it does not clear the scene.** This is what lets you add a single
new element (e.g., a caption) to an already-populated, human-edited scene without
destroying anything: paste a one-element payload, then position it.

> Neither plain Excalidraw nor Excalidraw Plus renders LaTeX, so all math must
> already be SVG by this point. Never move live "math-subtype" elements (from a
> math-rendering Excalidraw fork) into either canvas — they revert to raw `$...$`.

## Iterative editing protocol — the core discipline

**You are not the only editor.** The human (and their collaborators) edit the same
scene between your turns. This single fact drives the whole protocol:

- **Detect before you touch.** Before making any change, determine whether the scene
  was modified since your last snapshot (see next section). Assume it may have been.
- **Never revert.** If the scene changed, treat the *current* state as ground truth,
  record it as your new baseline, and build the requested change on top of it. Do
  not restore a previous version, and **never clear-and-repaste a populated scene** —
  that is the single most destructive thing you can do here and it erases the
  human's manual work.
- **Targeted only.** Apply exactly the change the user named, to the elements they
  named. Nothing else.
- **Ask before widening scope.** If the requested change forces touching other
  elements, stop and ask permission first. Don't "improve" adjacent things on your
  own initiative — the user is pacing the work and adjacent changes are theirs to
  request.
- **Full clear-and-repaste is allowed only** on a fresh/empty scene, or to recover a
  scene that was genuinely lost.

The reason this matters: a figure like this gets touched dozens of times by several
people. A skill that silently overwrites edits is worse than useless — it destroys
trust and work. Edit like a careful collaborator, not a regenerator.

## Detecting human edits (mechanism — prototype per environment)

You need to know whether the scene changed since you last touched it. This is the
one piece that depends on how you can read the live scene; treat it as something to
establish for your environment, then reuse. Options, roughly in order of robustness:

- **Element-version snapshot.** Excalidraw elements carry `version` and
  `versionNonce` that bump on every edit. After each of your operations, record the
  set of element ids with their `version`/`versionNonce` and the total count. Next
  turn, read the live scene and diff: any new/removed id, changed version, or count
  change means a human edited it.
- **Scene-JSON diff.** Read the current scene JSON (via the app's export /
  "Save to file", or an in-page store if exposed) and diff element ids/geometry
  against your last assembled/saved payload.
- **Serialized hash.** Hash the serialized scene after each of your ops; recompute
  and compare next turn (cheap, but tells you *that* it changed, not *what*).

The open sub-problem is **reading the live scene state programmatically** in your
environment (especially Excalidraw Plus). Establish that once. Decision rule once
you can read it: if a diff is detected, mark the scene "human-edited," reset your
baseline to the current state, and switch to targeted-edit-only mode.

If you cannot reliably detect edits in a given environment, **default to the safe
assumption that the human has edited the scene** and behave accordingly (targeted
edits only, no repaste).

## Targeted-edit mechanics

- **Edit an existing element:** locate it (by content/position, e.g., via a
  screenshot or a find tool), select it, and change it in place — move, resize,
  recolor, retype. Not by repasting.
- **Add an element:** append via paste of a one-element payload (non-destructive),
  then position it (it may land at its payload coordinates rather than your cursor;
  if so, select it and drag it where it belongs).
- **Never** select-all + delete on a populated, human-touched scene.

## Persistence & reproducibility

- **Wait for cloud sync.** Cloud editors (e.g., Excalidraw Plus) auto-save but need
  a few seconds to sync. Closing the tab right after an edit can lose it. Wait, and
  to be safe verify by reloading the scene; the scene-list timestamp updating is a
  good sync signal.
- **Keep the sources.** Keep the per-expression `.tex`, the panel scripts, the
  rendered SVGs/PNGs, and the assembled payload JSON. A lost scene can then be
  recreated instantly: `pbcopy < payload.json` + paste into a fresh scene. (Full
  repaste is fine here — the scene is empty.)
- The figure should rebuild from these sources without manual redrawing.

## Sharing the figure with the user

A clickable link is the most reliable way to hand the figure back — it works across
devices (the user is often reviewing on a phone) and is easy to forward to
collaborators. After building or updating the figure, offer a link, and pick the
kind that matches their workspace:

- **Excalidraw Plus:** the scene URL is the link. It opens for the user on any
  device **once they are logged in** to their Plus account — so tell them they need
  to be signed in to view it (and collaborators need workspace access).
- **Plain Excalidraw:** use **"Export to Link"** to publish a **public, read-only**
  snapshot. Anyone can click it and view it without logging in — the right choice
  when there is no Plus account.

Also offer to **save the scene as a `.excalidraw` file** ("Save to file") — a
portable file the user keeps and can reopen or import anywhere.

Don't assume which they want: **ask** whether to send a link, the `.excalidraw`
file, or both. Re-issue a fresh link whenever the scene changes — an old link is a
stale snapshot.

## Helper scripts

- `scripts/math_to_svg.py` — render one LaTeX expression to a tight SVG
  (standalone LaTeX → `dvisvgm`). Supports an optional color.
- `scripts/assemble_payload.py` — read a component manifest (images + native
  shapes) and emit the `excalidraw/clipboard` JSON with files embedded as base64
  data-URLs. Reads each image's intrinsic size to preserve aspect ratio.

Both are generic utilities; read their headers for usage.
