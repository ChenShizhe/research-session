---
name: talk-creator
description: >-
  Coordinate creation and substantial revision of research talks, lectures,
  narrated slide decks, and research presentations from source materials, project
  artifacts, or rough ideas. Use inside Research Meeting sessions to build the
  starting brief, logic flow, grounding verification, outline, atomized slide
  cards, per-slide script, visual cue handoff, downstream feedback loop, and
  production-readiness gates. Do not use for isolated Excalidraw edits or pure
  voice/video production jobs.
---

# Talk Creator

## Mission

Create grounded research talks while preserving the user's intent, evidence, and
production state in durable project-local files. Research Meeting remains the
conducting session skill; `talk-creator` is a coordinator used inside that
session, not a replacement for session governance.

## When To Use

Use this skill when the user wants to create, reshape, or coordinate a whole
research talk, lecture, narrated slide deck, or research presentation from:

- source materials: papers, notes, PDFs, prior writing, or a research folder;
- existing workflow artifacts: scripts, logs, outputs, handoffs, demos, or
  partial decks;
- verbal ideas, including messy voice-transcribed concepts.

Route directly to Excalidoodler when only visual execution changes. Route
directly to Voice Narrator when only narration, recording, trimming, packaging, or
video assembly changes. If meaning or structure may change, start here.

## Project Artifacts

Keep canonical state under a project-local `talk-creator/` folder unless the
project already has an established convention.

Required durable artifacts:

```text
talk-creator/
  starting-brief.md
  logic-flow.md
  verification.md
  outline.md
  slide-cards/
    _index.md
    <stable-slide-label>.md
  speaker-script.md
  visual-cue-brief.md
  downstream-feedback.md
  production-readiness.md
```

Chat is for paced discussion. Files are the durable memory. Mirror important
decisions, corrections, open assumptions, and downstream feedback into the
artifacts as the talk evolves.

## Workflow

1. **Starting brief.** Record the working title/topic, audience, target length,
   delivery mode, input mode, target language, source materials, required
   examples, constraints, things to avoid, and open assumptions. Mark values as
   `[user-stated]`, `[inferred]`, or `UNKNOWN`. If project identity, audience, or
   delivery mode is unknown, ask one short clarification before moving on.
2. **Logic flow.** Draft the central promise, audience journey, ordered beats,
   evidence/examples, unsupported or weak beats, and things to avoid. Do not make
   slide cards until the logic flow is internally coherent.
3. **Grounding verification.** Extract checkable claims from `logic-flow.md` into
   `verification.md`. Classify claims as factual, literature, workflow/project,
   theoretical/mathematical, or framing. Attach sources, local artifact paths,
   theory-graph references, web checks when current facts are needed, or explicit
   user testimony. Mark weak claims as `[unsupported]`, `[needs-source]`, or
   `[human-framing]`, then revise `logic-flow.md` before proceeding. After two
   failed automatic revision cycles on the same claim or conflict, stop and ask
   for direction.
4. **Outline.** Convert verified logic into sections with section role, audience
   state before/after, candidate slides, evidence/examples, transitions, risks,
   and open questions. Preserve any user-supplied outline or venue routine as a
   first-class input.
5. **Slide cards.** Maintain `slide-cards/_index.md` as the order/catalog and
   create one file per slide card at `slide-cards/<stable-slide-label>.md`. Each
   card must include status, production slide number (`TBD` until late), purpose,
   audience takeaway, visible text, speaker point, visual cue, evidence/support,
   dependencies, risks, and revision notes.
6. **Speaker script.** Draft `speaker-script.md` after slide cards are stable
   enough. Key every segment by `slide:<stable-label>`, not final slide number.
   Separate exact narration from notes, timing, pronunciation, and pointing cues.
   If a slide card changes, mark its script segment `needs-review`.
7. **Visual cue brief.** Write `visual-cue-brief.md` for cards marked
   `visual-ready`. Include target surface, visual type, composition, exact visible
   text, asset references and asset-preparation tasks, style constraints,
   multilingual/export constraints, pointing cues, "do not" rules, and open
   questions.
8. **Downstream feedback.** Record issues from humans, verification,
   Excalidoodler, and Voice Narrator in `downstream-feedback.md`. Decide whether
   the owner is `talk-creator`, Excalidoodler, Voice Narrator, or human direction.
   Update canonical talk files before rerunning downstream production.
9. **Production readiness.** Maintain `production-readiness.md` with every stable
   slide label, late production slide-number mapping, readiness states, blockers,
   stale asset/script checks, and open blocking feedback.

## Slide Label Rules

- Use stable slide labels such as `opening-smartphone-contrast` or
  `verified-claims`; treat references as `slide:<label>`.
- Do not make final slide numbers canonical during design. Assign `slide-XX`
  production numbers only when the outline is stable enough for export,
  narration, and assembly.
- If a card is split or merged, keep old labels in revision notes so feedback does
  not become orphaned.
- The index determines draft order; labels provide stable identity.

## Readiness Gates

- `logic-ready`: argument flow is coherent enough for outline.
- `verified`: major factual and literature claims are sourced, softened, removed,
  or explicitly marked.
- `outline-ready`: slide sequence is stable enough for atomized cards.
- `visual-ready`: a card has enough visual information for Excalidoodler.
- `script-ready`: a card has enough speaking intent for narration drafting.
- `recording-ready`: slide image and narration body are stable and from the same
  revision.
- `production-ready`: final visual/narration assets passed downstream checks and
  no blocking feedback remains.

These gates prevent silent drift between logic, visuals, script, recording, and
final assembly. They are readiness labels, not bureaucracy.

## Downstream Handoffs

Excalidoodler receives `slide-cards/_index.md`, relevant one-file slide cards,
`visual-cue-brief.md`, assets or asset-preparation notes, outline context if order
matters, export constraints, and "do not" rules. Excalidoodler owns visual
execution only; if it finds overloaded, unclear, unbuildable, or export-unsafe
talk content, record feedback and revise the canonical card or cue here.

Voice Narrator receives final or near-final slide images, `speaker-script.md`,
stable slide labels mapped to production numbers when available, language and
voice-source roots, pronunciation/glossary notes, timing targets, and pointing
cues. Voice Narrator owns recording and video execution only; awkward narration or
stale script/slide mismatches come back to this skill.

## Boundaries

Do not draw or overwrite live Excalidraw scenes, record audio, assemble final
videos, publish or upload outputs, invent unsupported facts, promote unsupported
claims into central slide logic, silently override a user-provided talk routine,
or treat voice-transcription guesses as confirmed file names or skill names.

Do not replace live discussion with file-only updates. Keep chat concise, but make
sure durable files contain the decisions needed for a future agent to resume.
