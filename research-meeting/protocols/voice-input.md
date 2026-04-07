# Voice Input Protocol

- source: P5-D4
- status: active
- scope: Voice mode norms, domain glossary correction, hybrid input conventions

---

## Design Principle

**Voice input is an input modality enhancement, not a new feature.** It changes how the user contributes to the meeting, not what the meeting does. The research-meeting skill's behavior -- session protocols, specialist coordination, shared workspace, delegation -- is entirely unchanged. The user speaks instead of (or in addition to) typing. The agent never knows or cares whether the user's text arrived via keyboard or microphone.

Agent output remains text. Always. Research output must be searchable, copy-pasteable, skimmable, and archivable. This is not a temporary limitation -- it is a deliberate design choice that holds even if high-quality TTS becomes trivial.

| Aspect | Before voice | With voice |
|--------|-------------|------------|
| How the user enters discussion contributions | Typing | Speaking (push-to-talk) or typing, or both in the same turn |
| How the user enters equations, code, citations | Typing | Still typing -- voice is unsuited for precise notation |
| How agents respond | Text | Text (unchanged) |
| Shared workspace contributions | Text files | Text files (unchanged) |
| Session transcript | Text | Text (unchanged) |
| Session protocols (startup, close, checkpoint) | Text interaction | Text interaction (unchanged) |

---

## Tier 1: Voice Mode Conduct Norms (Zero Implementation Cost)

Tier 1 requires no code changes, no new files, no new dependencies. It documents `/voice` as a supported interaction mode and establishes session conduct norms.

Claude Code `/voice` provides push-to-talk via spacebar (hold to speak, release to send). Mixed input is supported: the user can type and speak in the same prompt. `/voice` is a terminal-only interactive feature -- not available via the SDK.

### V1: When to Speak vs. When to Type

| Speak | Type |
|-------|------|
| Brainstorming and open-ended discussion | Equations and mathematical notation |
| Explaining intuitions and research directions | Code snippets and variable names |
| Giving feedback on agent proposals | Exact paper titles and citations |
| Describing experimental results | Correcting a transcription error |
| Narrating thought process | File paths, URLs, and identifiers |
| Asking questions | Greek letters in symbolic context (voice says "lambda"; type `\lambda` if precision matters) |

### V2: Handling Transcription Errors

Transcription errors are expected, especially for domain-specific terminology. The user should:

1. **Let minor errors pass** if the intent is clear from context. The agent will likely interpret "hawks process" correctly given the research context.
2. **Correct critical errors inline** by typing a correction in the same prompt or the next one: "Correction: I said 'hawks process' -- I mean Hawkes process."
3. **Not re-speak** to correct. Re-speaking often produces the same error. Type the correction.

### V3: Voice in Multi-Agent Tmux Sessions

In tmux mode, `/voice` is active in whichever pane has keyboard focus. The user should:

1. Keep focus on the **group lead's pane** for primary discussion (the default interaction surface).
2. Use voice in the group lead's pane to speak discussion contributions.
3. Switch to a specialist's pane and **type** (not speak) for direct specialist interaction -- direct specialist messages are typically precise instructions or corrections, better suited to typing.

### V4: Push-to-Talk Is the Correct Default

Push-to-talk (spacebar hold) avoids capturing:

- Ambient room noise and side conversations.
- Keyboard sounds from typing in other panes.
- The user's "thinking out loud" that is not meant as agent input.

Always-on voice activity detection (VAD) is not recommended for research meetings. The explicit gesture of holding spacebar maps well to the conversational turn-taking model: the user decides when to take a turn.

---

## Tier 2: Domain Vocabulary Correction

### The Domain Jargon Problem

Cloud STT engines optimize for general English; statistical and mathematical terminology is systematically mis-transcribed:

| Spoken | Typical STT output | Correct |
|--------|-------------------|---------|
| "Hawkes process" | "hawks process", "Hawk's process" | Hawkes process |
| "cross-covariance" | "cross co-variance" | cross-covariance |
| "RKHS" | "R K H S", "are KHS" | RKHS |
| "i.i.d." | "IID", "I I D" | i.i.d. |
| "asymptotic" | "asymptomatic" | asymptotic |
| "eigenvalue" | "I can value" | eigenvalue |
| "heteroscedastic" | various garbled forms | heteroscedastic |

These errors are systematic -- the same term mis-transcribes the same way repeatedly -- making them amenable to a glossary-based correction approach.

### Domain Glossary File

Each research project maintains a domain glossary for voice correction at:

```
~/Documents/Research/<project-name>/voice-glossary.yaml
```

The glossary lives in the project's research directory (alongside `workspace/`, `pipeline/`, etc.), not in the skill directory. The glossary is project-specific because different projects have different specialized vocabulary.

### Glossary Schema (`voice-glossary.yaml`)

```yaml
version: 1
project: <project-name>
last_updated: <YYYY-MM-DD>

terms:
  - correct: "Hawkes process"
    mistranscriptions:
      - "hawks process"
      - "Hawk's process"
    category: model           # model | concept | acronym | method | notation
    expansion: ""             # optional; used for acronyms

authors:
  - correct: "Lu"
    mistranscriptions: ["Lou", "lieu", "Loo"]

notation:
  - correct: "K-hat"
    mistranscriptions: ["K hat", "cape hat"]
```

**Schema rules:**

1. **`terms`** is the primary list. Each entry has `correct` (canonical spelling), `mistranscriptions` (known STT errors), and `category` (for human organization). Optional `expansion` for acronyms.
2. **`authors`** is a separate list for proper noun author names that STT engines have no reason to know.
3. **`notation`** is a separate list for mathematical notation the user might speak aloud.
4. The glossary is **additive** -- new mis-transcriptions are added as they are discovered during sessions.
5. **Size expectation:** A mature project glossary will have 30-80 terms, 10-20 authors, and 5-15 notation entries (< 5 KB YAML).

A starter template is provided at `templates/voice-glossary.yaml`.

### LLM Correction via System Prompt Injection

When voice mode is active, the skill adds a correction instruction to the system prompt (~300-500 tokens). The agent uses the glossary and conversation context to silently fix transcription errors during its normal inference pass.

**System prompt block (added when `/voice` is activated):**

```
VOICE INPUT CORRECTION

Voice mode is active. The user's input may contain transcription errors from
speech-to-text. Before interpreting the user's message, silently correct any
domain-specific transcription errors using these rules:

1. Known term corrections (from project glossary):
   - "hawks process" -> "Hawkes process"
   - "cross co-variance" or "cross covariance" -> "cross-covariance"
   - "R K H S" or "are KHS" -> "RKHS"
   [... loaded from voice-glossary.yaml ...]

2. Use conversation context to resolve ambiguities.
3. Do not mention corrections to the user unless asked. Interpret the corrected
   version as if the user had typed it.
```

**Why system prompt injection, not a separate correction agent:** A separate agent would add 0.5-2 seconds of latency per turn and double the token cost of voice turns. The system prompt approach leverages the main agent's existing inference pass. The cost is ~300-500 tokens added to the system prompt (once). For systematic substitution errors that dominate domain jargon mis-transcription, this is sufficient.

### Voice Mode Detection

The correction glossary is loaded conditionally -- only when voice mode is active:

1. The user types `/voice` in the conversation.
2. The user mentions voice input ("I'm going to use voice").
3. The startup protocol's voice reminder prompts the user.

If no glossary file exists, voice mode still works -- the user handles transcription errors manually (Tier 1 behavior).

### Glossary Maintenance at Session Close

The glossary improves over time:

1. **During session:** When the user corrects a transcription error, the group lead notes the correction.
2. **At session close:** The close protocol includes an optional step: "If voice mode was used and new transcription errors were observed, offer to update `voice-glossary.yaml` with the new entries."
3. **Initial population:** When a project first enables voice input, the group lead helps populate the glossary by reviewing the project's `domain-prior.md` and extracting likely problematic terms.

---

## Hybrid Input Norms

Voice and text are complementary modalities with different strengths. The convention: **use voice for ideas, use text for precision.**

Claude Code supports mixed voice+text in the same prompt. The user can hold spacebar to speak a sentence, then type a formula, then speak again -- all in one turn. This seamless switching is the expected workflow, not an edge case.

### Modality-Task Mapping Table

| Task | Preferred Modality | Rationale |
|------|--------------------|-----------|
| Brainstorming new research directions | Voice | Speaking is 3-5x faster than typing; lower friction encourages exploratory thinking |
| Discussing experimental results | Voice | Narrative description flows naturally in speech |
| Giving feedback on agent proposals | Voice | Conversational responses are natural speech |
| Explaining intuitions | Voice | Internal monologue externalized -- speech's native mode |
| Narrating thought process | Voice | Stream-of-consciousness is speech's native mode |
| Asking clarifying questions | Voice | Quick back-and-forth is more natural verbally |
| Reacting to specialist contributions | Voice | Spontaneous reactions are natural speech |
| Equations and mathematical notation | Text | Voice cannot represent symbolic expressions precisely |
| Code snippets | Text | Syntax, indentation, and variable names require exact character input |
| Exact citations and paper titles | Text | Names and numbers must be precise for search |
| Variable names in symbolic context | Text | Exact strings that must be character-accurate |
| File paths and URLs | Text | Exact strings that must be character-accurate |
| Correcting transcription errors | Text | Typing the correct form is the fastest fix |
| Setting the session agenda | Either | Complexity determines which is faster |
| Requesting a literature search | Either | Works in either modality |
| Requesting delegation | Either | Works in either modality |

### Agent Behavior for Hybrid Input

The agent does not explicitly manage the user's modality choice. The norms are communicated once (at startup, in the conduct section) and then the user self-regulates.

**One exception:** If the agent detects repeated transcription errors in a turn involving precise notation (e.g., the user is trying to speak an equation), the agent may suggest: "Would you like to type the equation? Voice input struggles with mathematical notation."

---

## Multi-Agent Considerations

### Voice in the Tmux Architecture

```
+----------------------------+----------------------------+
|       Group Lead           |    Literature Specialist    |
|    (primary interaction)   |    (visible, background)    |
|                            |                             |
|   [/voice active here]     |   [text input only]         |
+----------------------------+----------------------------+
|    Theory/Proof Specialist |    Code Specialist          |
|    (visible, background)   |    (visible, background)    |
|                            |                             |
|   [text input only]        |   [text input only]         |
+----------------------------+----------------------------+
```

**Voice input goes to whichever pane has keyboard focus.** In practice, the group lead's pane has focus for 90%+ of the session. Voice input is therefore primarily a user-to-group-lead channel.

### Specialists Never Receive Raw Voice

Specialists receive text -- relayed by the group lead via the shared workspace or via direct inbox messages. There is no voice-to-specialist path:

1. **Group lead relays discussion contributions.** When the user speaks about a topic relevant to a specialist, the group lead processes the (corrected) text and writes a contribution or inbox message to the specialist. The specialist never sees the raw transcription.
2. **Direct specialist interaction is precise.** When the user switches to a specialist's pane, it is typically to give a specific instruction or correction -- better typed.
3. **The shared workspace is text-only.** All contributions, findings, transcripts, and inbox messages are text files. Input modality is invisible at the workspace level.

### Voice Correction Applies Only to Group Lead

The domain glossary correction (Tier 2) applies only in the group lead's session. The group lead's system prompt includes the glossary. When the group lead relays user input to specialists, the relayed text has already been corrected. Specialists do not need their own glossary.

### No Change to Shared Workspace Protocol

| Workspace artifact | Input modality impact |
|-------------------|----------------------|
| `transcript.md` | Group lead writes text entries regardless of how the user spoke |
| `contributions/` | Specialist contributions are always text |
| `findings.md` | Text entries written by group lead |
| `inboxes/` | JSONL entries, always text |
| `specialist-state/` | Text summaries written by specialists |
| `artifacts/` | Papers, proofs, code -- always text |

The workspace protocol is modality-agnostic by design. Voice input is absorbed at the user-to-agent boundary and converted to text before any workspace interaction occurs.

---

## Ergonomic Rationale

### RSI Prevention

A 2-3 hour research meeting with active typing involves thousands of keystrokes. Shifting 30-40% of input to voice cuts keystroke count proportionally. Alternating between typing and speaking creates natural micro-breaks for tendons and joints.

### Cognitive Flow

Speaking is the natural modality for explanatory and exploratory thought. Typing interposes a translation step (thought -> motor plan -> keystrokes) that can interrupt the flow of ideas. For brainstorming and discussion, voice preserves cognitive flow better than typing.

### Session Sustainability

A professor who can speak for the discussion portions and type only for equations and code can sustain longer, more productive sessions without physical fatigue. This is particularly relevant for multi-session research programs.

### Accessibility

Voice input makes sessions accessible to users who cannot sustain extended typing: temporary injuries, chronic conditions (carpal tunnel, tendonitis, RSI), and motor impairments that make typing difficult but speech unaffected.

---

## Deferred: Tier 3 and Tier 4

### Tier 3: Custom STT Pipeline (Deferred)

A custom speech-to-text pipeline using Deepgram Nova-3 (cloud) or faster-whisper (local) with voice activity detection (Silero VAD), keyword boosting from the domain glossary, and streaming partial results. Reported 5-15 point accuracy gains over generic STT for domain terms.

**Deferral rationale:** Claude Code `/voice` already provides the STT pipeline, and the glossary correction approach (Tier 2) may be sufficient. Tier 3 is warranted only if Tier 2 correction quality proves inadequate for the user's workflow. Estimated effort if pursued: 1-2 days implementation.

### Tier 4: TTS Agent Output (Deferred)

Adding text-to-speech output so agents "speak" their responses. Would require TTS engine integration, audio playback management, interruption handling, and multi-agent voice differentiation.

**Deferral rationale:** Text output is strictly superior for research content -- searchable, skimmable, archivable. Mathematical content, citations, and code are poorly served by speech. Multiple agents producing audio would create cacophony. TTS is a "nice to have" for the meeting metaphor but degrades the research workflow. Estimated effort if pursued: 1-2 weeks implementation.

### Fine-Tuned Domain-Specific STT Models (Deferred Indefinitely)

Fine-tuning Whisper on domain-specific audio data could reduce WER by 10-30%. **Deferred indefinitely** because it requires 10-100 hours of labeled audio data, significant ML engineering effort, and the improvement may not justify the cost when LLM correction is available.

### Cross-Project Shared Glossary (Deferred)

A shared base glossary for related projects (e.g., all involving point processes) with project-specific extensions. **Deferred** until there is evidence of the need. If pursued, would likely be stored in central memories rather than as an additional file in the Research directory.
