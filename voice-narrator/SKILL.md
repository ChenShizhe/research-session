---
name: voice-narrator
description: >-
  Produce narrated slide videos from stable slide images and per-slide scripts:
  prepare exact TTS prompts, record or generate segmented audio through API TTS,
  Doubao desktop, Doubao mobile via scrcpy/ADB, or existing audio, package
  segments, assemble fixed-canvas videos, preserve language/voice/backend root
  separation, and report script or visual issues back upstream.
---

# Voice Narrator

## Purpose

Use this skill after slide images and narration text are stable enough for
production. It accepts Talk Creator handoffs or standalone inputs, generates or
records per-segment narration, packages each segment as slide video, and assembles
one local final video per language/voice/backend root.

Do not design the talk logic, draw slide visuals, or publish/upload final videos.
Agents only create local artifacts and report the final paths.

## Inputs

Accept any of these modes:

- **Talk Creator handoff**: stable slide labels, production numbers, slide images,
  `speaker-script.md`, timing/pronunciation notes, language, voice source, and
  production-readiness state.
- **Standalone input**: script, transcript, per-slide narration text, slide images,
  PDF/deck plus notes, user-described narration, or a partial production folder.

Before recording, identify segment labels, production order, target language,
voice source, backend, visual asset for each segment, output root, and blockers.
If standalone input is messy, create a manifest first and mark inferred narration
as `needs_review` instead of silently treating it as final.

## Output Root Contract

Keep one root per language, voice source, and backend. Never mix API TTS,
Doubao desktop, phone-cloned Doubao mobile, or existing-audio outputs in one
root.

Recommended shape:

```text
voice-outputs/
  <language>-<voice-source>-<backend>/
    manifest.json
    prompts/
    narration/
    slides/
    audio/raw/
    audio/trimmed/
    video/segments/
    video/final/
    logs/
```

The manifest should include project, language, voice_source, backend, canvas,
provider settings if any, and per-segment fields: label, production_number,
script_path, narration_text_path, slide_image_path, prompt_path, raw_audio_path,
trimmed_audio_path, segment_video_path, status, notes, and upstream_feedback.

## Backend Choice

- **API TTS**: preferred when credentials exist and the user accepts the voice,
  cost, privacy, and automation tradeoffs.
- **Doubao desktop**: use for natural Doubao desktop read-aloud voices.
- **Doubao mobile via `scrcpy`/ADB**: use for phone-only or cloned voices.
- **Existing audio**: use when clips already exist and need trimming, packaging,
  completion, or assembly.

Record the backend before production starts. Check required tools: API
credentials, Doubao app/session, `scrcpy`, ADB, `ffmpeg`, and native macOS
ScreenCaptureKit capture through `tools/CodexAudioCapture.app` when using Doubao.
BlackHole is not a default route because the reference workflow produced
unresolved electronic buzz/clicks; treat it as rejected unless the user explicitly
asks to experiment.

## Prompt Preparation

For every segment:

1. Extract only the narration body. Do not include headings, metadata, notes,
   timing, pronunciation guidance, Markdown labels, or prompt instructions in
   speakable narration.
2. Save the narration body under `narration/`.
3. Save backend prompts under `prompts/`.
4. For API TTS, pass only the narration body unless the provider supports
   non-spoken voice/style parameters separately.
5. For Doubao, wrap the narration in a strict plain-output prompt.

English Doubao wrapper:

```text
Please output only the following English narration text exactly as written, with no title, no Markdown heading, no explanation, and no extra words. I will click Doubao read-aloud after you respond.
```

Chinese Doubao wrapper:

```text
请只输出下面这段中文讲稿原文，不要加标题，不要加解释，不要加 Markdown，不要改写，也不要额外输出任何字。我会在你输出后点击朗读。
```

If a script uses `## Narration` or similar markers, use a suffix extraction
pattern such as `rsplit` so earlier instructions containing the same word are not
captured.

## Recording Routes

### API TTS

Confirm provider, model, voice, language, and output format. Send the narration
body only, save returned audio under `audio/raw/` or `audio/trimmed/` according to
whether it needs processing, record provider settings in the manifest, and do not
copy the clip into any Doubao root.

### Doubao Desktop

Safe order:

1. Open a fresh Doubao conversation for the segment.
2. Paste the strict prompt and send it.
3. Wait for Doubao to finish responding.
4. Visually verify the response contains only narration text.
5. Inspect current response-row controls. The common order is Copy first,
   speaker/read-aloud second, then feedback/regenerate/more.
6. Start ScreenCaptureKit capture with a generous duration.
7. Immediately click the verified speaker/read-aloud control once.
8. Let capture finish, then validate the raw capture.

Do not rely on fixed coordinates or stale accessibility indexes. UI inspection is
mandatory because clicking Copy, a suggestion, or the wrong row yields silent or
wrong captures.

### Doubao Mobile Via `scrcpy`/ADB

Safe order:

1. Confirm the phone is connected, unlocked, visible in `scrcpy`, and Doubao is
   focused.
2. Paste the strict prompt into the mobile input.
3. Tap Send and wait for the response to finish.
4. Confirm the read-aloud button is visible; use the bottom jump/reveal control if
   needed.
5. Start ScreenCaptureKit capture.
6. Tap read-aloud once.
7. Let capture finish, then validate raw capture and UI logs.

Useful Android resource IDs from the reference workflow:

- input field: `com.larus.nova:id/input_text`
- send button: `com.larus.nova:id/action_send`
- read-aloud button: `com.larus.nova:id/msg_action_re_tts`
- bottom jump/reveal: `com.larus.nova:id/bottom_floating_button_container`

Reference automation exists in the `ai-for-research-talk` project at
`scripts/mobile_doubao_record_voiceover.py`.
Adapt paths and segment counts before reuse.

## Postprocess And Package

Validate raw audio first. A good ScreenCaptureKit capture has leading silence, a
speech span, and trailing silence; an all-silent file means the route failed.

Default postprocess:

1. Detect leading/trailing silence.
2. Trim only outer silence with small pads.
3. Encode trimmed audio, usually AAC `.m4a`.
4. Combine trimmed audio with the matching slide image into a per-segment MP4.
5. Store raw audio, trimmed audio, and segment video in separate paths.
6. Update manifest status.

Do not denoise, normalize, compress, level, or repair successful ScreenCaptureKit
captures by default. Apply repair only for a diagnosed defect and record why.

## Final Assembly

Assemble only within one language/voice/backend root. Confirm every required
segment is valid, ordered, current with the intended slide export, and unblocked.
Normalize segment videos to one fixed canvas, concatenate them, re-encode final
audio if needed to avoid timestamp issues, save under `video/final/`, and update
the manifest. The prior project used `2120x1714`; choose or confirm the canvas
for each project.

Reference assembler (in the `ai-for-research-talk` project):
`scripts/assemble_voiceover_folder.py`.

## Upstream Feedback

Report issues upstream when they require canonical talk or visual changes:

- narration is too long, awkward, ambiguous, or hard for TTS to speak naturally;
- spoken text includes content that should not be read;
- slide image is stale, mismatched, visually overloaded, or missing a needed cue;
- slide/script order, labels, language, or pronunciation notes conflict.

For Talk Creator projects, append concise actionable entries to
`talk-creator/downstream-feedback.md` or the provided handoff path. Keep local
production issues inside this skill: wrong click, silent capture, trimming error,
missing local tool, or incomplete clip.

## Failure Catalog

| Failure | Detection | Recovery |
|---|---|---|
| Desktop wrong button | capture silent, clipboard changed, or no speech | Reopen/inspect row, verify speaker button, re-record segment only. |
| Mobile Send forgotten | capture has no speech or prompt remains in input | Send prompt, wait for response, then restart capture. |
| Phone lock/focus loss | `adb` or `scrcpy` UI dump stale/missing | Unlock phone, focus Doubao, dump UI again before recording. |
| Read-aloud hidden | no `msg_action_re_tts` in UI dump | Tap bottom jump/reveal, scroll to latest response, retry lookup. |
| Silent raw capture | silence detection shows no speech span | Treat take as failed; do not postprocess as success. |
| Prompt spoke headings | audio includes title/Markdown/instructions | Fix extraction/wrapper and regenerate the response. |
| Wrong root | manifest language/voice/backend conflicts with path | Move nothing blindly; create correct root and regenerate or relink deliberately. |
| Stale slide image | manifest visual revision or slide content mismatches script | Stop assembly and report upstream. |
| BlackHole buzz/clicks | raw capture has electronic artifacts | Use ScreenCaptureKit route; do not repair as default production path. |
| Visual export issue | Chinese/text layout or export artifact appears in segment | Report upstream to visual/talk workflow before final assembly. |

