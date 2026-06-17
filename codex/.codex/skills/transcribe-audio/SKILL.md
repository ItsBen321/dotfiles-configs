---
name: transcribe-audio
description: Use when the user attaches or references an audio file or voice memo and wants speech transcribed into text, saved to a transcript file, or used as the next prompt/input. Supports local file-based transcription for mp3, mp4, mpeg, mpga, m4a, wav, and webm audio with faster-whisper, with an optional OpenAI Audio API backend when explicitly requested.
---

# Audio Transcription

Transcribe voice memos and audio files with the bundled CLI, then route the transcript according to the user's requested action. Default to the local `faster-whisper` backend so no API key is required.

## Workflow

1. Identify the audio file from the attachment or local path. Supported extensions: `mp3`, `mp4`, `mpeg`, `mpga`, `m4a`, `wav`, `webm`.
2. Determine the requested action before transcribing:
   - Output in chat: run the CLI without `--out`, then paste the transcript in the response.
   - Save to file: run the CLI with `--out <path>`.
   - Use as prompt/input: run the CLI without `--out`, then treat the transcript as the user's prompt and answer it.
3. If the user provided only an audio file and no action, ask whether to output the transcript in chat, save it, or use it as the prompt before running transcription.
4. If the user says to save but gives no path, save to `output/transcripts/<audio-stem>.txt` in the active workspace.
5. For domain-specific vocabulary, names, acronyms, or desired transcript style, pass concise context with `--prompt` or `--prompt-file`.

## CLI

Use `scripts/transcribe_audio.py` for transcription.

```powershell
python "C:\Users\ben_h\.codex\skills\transcribe-audio\scripts\transcribe_audio.py" --file "memo.wav"
python "C:\Users\ben_h\.codex\skills\transcribe-audio\scripts\transcribe_audio.py" --file "memo.mp3" --out "output/transcripts/memo.txt"
python "C:\Users\ben_h\.codex\skills\transcribe-audio\scripts\transcribe_audio.py" --file "meeting.m4a" --model small --prompt "Project names include Codex, Roulette, and Godot."
```

Options:
- Required: `--file <path>`
- Common optional: `--out <path>`, `--model`, `--prompt`, `--prompt-file`, `--response-format text|json`, `--language`, `--force`, `--dry-run`
- Local optional: `--device cpu|cuda|auto`, `--compute-type int8|float16|float32`, `--beam-size <n>`
- Backend optional: `--backend local|openai`
- Default backend: `local`
- Default local model: `base`
- Default response format: `text`

## Local Backend

- Use local `faster-whisper` by default. This does not require `OPENAI_API_KEY` or API billing.
- Install missing local dependencies with `python -m pip install faster-whisper truststore`.
- `truststore` lets Python use the operating system certificate store for first-run model downloads on Windows.
- The first run downloads the selected model. Use `--model tiny` for a smaller/faster first download, `--model base` for the default balance, or `--model small`/`medium`/`large-v3` for higher quality at higher cost in time and disk.
- Default to `--device cpu --compute-type int8` for broad compatibility. Use `--device cuda --compute-type float16` only when CUDA is available.
- Local transcription has no OpenAI upload-size limit, but very large files can take a long time.

## OpenAI Backend

- Use `--backend openai` only when the user explicitly wants API-backed transcription.
- Require `OPENAI_API_KEY` for `--backend openai`.
- Never ask the user to paste the full API key in chat. Ask them to set it locally and confirm when ready.
- If the OpenAI Python SDK is missing, install it with `python -m pip install openai`.
- File uploads through `--backend openai` follow the OpenAI Audio API's current 25 MB limit. The CLI fails clearly for oversized files instead of chunking.

## Output Rules

- No `--out`: print the transcript to stdout so it can be copied into chat or used as the next prompt.
- With `--out`: create parent directories as needed and write the transcript to the requested path.
- Do not overwrite existing output files unless the user explicitly allows it; pass `--force` only when overwriting is intended.
- Keep transcript text faithful. Do not summarize, rewrite, translate, or clean it up unless the user asks for that separately.

## Sources

- Local backend: `https://github.com/SYSTRAN/faster-whisper`
- Optional API backend: `https://developers.openai.com/api/docs/guides/speech-to-text`
