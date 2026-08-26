## Purpose

Turns a recorded audio clip into text entirely on-device: local Whisper transcription,
automatic English/German language detection, and clipboard output.

## Requirements

### Requirement: Local audio transcription
The system SHALL transcribe a recorded audio clip to text entirely on-device, using a
local Whisper model, without sending audio or text to any external network service.

#### Scenario: Transcription with no network connection
- **WHEN** the system transcribes a recorded clip while the machine has no network
  connectivity and the model is already cached locally
- **THEN** transcription completes successfully and produces correct text

### Requirement: Automatic English/German language detection
The system SHALL automatically detect whether a recorded utterance is English or German
and transcribe it in the detected language, without requiring the user to manually select
a language.

#### Scenario: English utterance
- **WHEN** a user records a clip speaking English
- **THEN** the system detects the language as English and returns an accurate English
  transcription

#### Scenario: German utterance
- **WHEN** a user records a clip speaking German, including words with umlauts (ä, ö, ü)
  or ß
- **THEN** the system detects the language as German and returns an accurate German
  transcription with umlauts and ß preserved correctly

### Requirement: Audio capture format
The system SHALL capture microphone audio as 16kHz mono float32 samples, matching the
input format expected by the local Whisper model.

#### Scenario: Recording captured for transcription
- **WHEN** the system records audio from the default microphone
- **THEN** the resulting buffer is 16kHz mono float32 and can be passed directly to the
  transcription step without a separate resampling step

### Requirement: Clipboard output
The system SHALL copy the transcribed text to the system clipboard after transcription
completes.

#### Scenario: Successful transcription copied to clipboard
- **WHEN** transcription of a recorded clip completes successfully
- **THEN** the resulting text is placed on the system clipboard, ready to paste, with all
  Unicode characters (including umlauts and ß) preserved exactly

### Requirement: Minimum recording duration guard
The system SHALL discard a recorded clip without transcribing it if its duration is below a
configured minimum threshold, to avoid hallucinated output from accidental or near-instant
toggles.

#### Scenario: Clip shorter than the minimum duration
- **WHEN** a recorded clip's duration is below the configured minimum-duration threshold
- **THEN** the clip is discarded and no transcription is attempted, and nothing is pasted or
  copied to the clipboard

### Requirement: Silence energy guard
The system SHALL discard a recorded clip without transcribing it if its audio energy (RMS)
is below a configured silence floor, to avoid transcribing clips with no real speech.

#### Scenario: Clip is effectively silent
- **WHEN** a recorded clip's RMS energy is below the configured silence threshold
- **THEN** the clip is discarded and no transcription is attempted, and nothing is pasted or
  copied to the clipboard

### Requirement: Hallucination confidence guard
The system SHALL reject a transcription result whose Whisper-reported confidence signals
(`no_speech_prob`, `avg_logprob`, `compression_ratio`) indicate a likely hallucination,
rather than passing hallucinated text through to the clipboard or auto-paste.

#### Scenario: Low-confidence transcription is rejected
- **WHEN** a transcription result's confidence signals fall within the configured
  hallucination thresholds (e.g. high `no_speech_prob` combined with low `avg_logprob`)
- **THEN** the result is rejected, and nothing is pasted or copied to the clipboard

#### Scenario: Genuine speech is accepted
- **WHEN** a transcription result's confidence signals indicate real speech
- **THEN** the result is accepted and proceeds to clipboard/paste output as normal

### Requirement: Serialized transcription processing
The system SHALL process queued audio clips through transcription one at a time, without
running concurrent transcription calls, so that rapid consecutive recordings are neither
dropped nor corrupted. Clips are enqueued in the order they were captured; each clip
completes transcription fully before the next begins. Delivery/output order is not
guaranteed to match recording order if clips take different amounts of time to process —
this is a known, accepted limitation, not a defect (verified in practice: rapid
consecutive dictations are never dropped or garbled, but results can surface in
whichever order transcription happens to finish).

#### Scenario: Three rapid consecutive recordings
- **WHEN** the user records three separate short clips in quick succession, before earlier
  clips have finished transcribing
- **THEN** all three clips are transcribed, each fully completing before the next begins,
  none are dropped or corrupted, and the app remains responsive to new recordings
  throughout

#### Scenario: Recording remains available during transcription
- **WHEN** a previous clip is still being transcribed
- **THEN** the user can immediately start a new recording without being blocked or told to
  wait

### Requirement: Warm model at startup
The system SHALL preload the transcription model and perform a warm-up inference at startup,
so that model cold-start latency does not delay the user's first real utterance.

#### Scenario: First real utterance after startup
- **WHEN** the user records their first utterance after the app has finished starting up
- **THEN** transcription does not incur a first-call cold-start delay beyond normal
  processing time, because the model was already warmed up at launch

### Requirement: Microphone active only while recording
The system SHALL only open and capture from the microphone input stream while a recording is
actually in progress, and SHALL fully release the input stream (not merely pause it) between
recordings, so the microphone is never active while the app is idle.

#### Scenario: Idle app does not use the microphone
- **WHEN** the app is running but no recording is in progress
- **THEN** the microphone input stream is closed and the system's microphone-in-use
  indicator is not shown

#### Scenario: Microphone releases immediately after recording stops
- **WHEN** the user toggles off an active recording
- **THEN** the microphone input stream is closed promptly, and the microphone-in-use
  indicator is no longer shown

### Requirement: Maximum recording duration cap
The system SHALL automatically stop and finalize a recording if it exceeds a configured
maximum duration, so a forgotten toggle does not record indefinitely. The default maximum
duration SHALL be five minutes.

#### Scenario: Recording left running past the cap
- **WHEN** a recording has been running longer than the configured maximum duration without
  the user toggling it off
- **THEN** the system automatically stops the recording and hands off the captured clip for
  transcription as if the user had toggled off

### Requirement: Long transcription preserves valid speech
The system SHALL preserve valid portions of a long recording when other portions are silent or
rejected by confidence guards.

#### Scenario: Long recording has one rejected segment
- **WHEN** a long recording contains accepted speech segments and one segment rejected by a
  confidence guard
- **THEN** the accepted speech is delivered and the recording is not discarded as a whole

### Requirement: Serialized recording finalization
The system SHALL serialize hotkey, menu, duration-cap, and hotkey-loss stop requests so an active recording is finalized at most once. Every successful stop source SHALL close the microphone and submit the captured clip through the same transcription handoff.

#### Scenario: Concurrent stop sources
- **WHEN** two stop requests arrive for the same active recording
- **THEN** only the first request finalizes and submits the recording, and the later request has no effect on the microphone, clip, or transcription queue

#### Scenario: Hotkey-loss stop
- **WHEN** the event tap becomes unavailable while recording
- **THEN** the system closes the microphone and hands off the captured clip without waiting for the maximum recording duration

#### Scenario: Capture finalization fails
- **WHEN** microphone finalization or clip handoff raises an error
- **THEN** the recording ends without retrying microphone work, the app reports a capture failure state, and the diagnostic log records the sanitized failure stage and error type
