#!/usr/bin/env python3
"""Render a humanized spoken handoff locally with Kokoro text to speech."""

from __future__ import annotations

import argparse
import html
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SUPPORTED_OUTPUTS = {".wav", ".mp3", ".m4a", ".ogg", ".opus"}
DEFAULT_VOICE = "af_heart"
DEFAULT_LANGUAGE = "a"
DEFAULT_SPEED = 1.0
DEFAULT_MAX_CHARS = 1_600
SAMPLE_RATE = 24_000
KOKORO_REPO_ID = "hexgrad/Kokoro-82M"
LOCAL_ENVIRONMENT = Path.home() / ".local" / "share" / "codex" / "explain-tts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a Markdown handoff locally with Kokoro neural speech."
    )
    parser.add_argument("--input", required=True, type=Path, help="Markdown or text companion")
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output .wav, .mp3, .m4a, .ogg, or .opus file",
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"Kokoro voice (default: {DEFAULT_VOICE})",
    )
    parser.add_argument(
        "--lang-code",
        default=DEFAULT_LANGUAGE,
        help=f"Kokoro language code (default: {DEFAULT_LANGUAGE}, American English)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=DEFAULT_SPEED,
        help=f"Speech speed multiplier (default: {DEFAULT_SPEED})",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help=f"Maximum characters per local synthesis chunk (default: {DEFAULT_MAX_CHARS})",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect narration and dependency availability without loading the model",
    )
    return parser.parse_args()


def _humanize_raw_path(match: re.Match[str]) -> str:
    matched_path = match.group(0)
    raw_path = matched_path.rstrip(".,;!?)\"'")
    trailing = matched_path[len(raw_path) :]
    normalized = raw_path.replace("\\", "/")
    location = re.search(r":(\d+)(?:[-:](\d+))?$", normalized)
    if location:
        normalized = normalized[: location.start()]

    name = normalized.rstrip("/").rsplit("/", 1)[-1]
    if not name:
        name = "the referenced file"

    if not location:
        return name + trailing
    first_line = location.group(1)
    last_line = location.group(2)
    if last_line:
        return f"{name}, from line {first_line} to line {last_line}{trailing}"
    return f"{name}, around line {first_line}{trailing}"


def markdown_to_speech(source: str) -> str:
    """Turn a written companion into natural narration with useful navigation cues."""
    text = source.replace("\r\n", "\n")
    text = re.sub(
        r"<!--\s*speech:skip-start\s*-->.*?<!--\s*speech:skip-end\s*-->",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)
    text = re.sub(r"```[^\n]*\n.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<((?:https?|file)://[^>]+)>", "the linked page", text)
    text = re.sub(r"https?://\S+", "the linked page", text)

    # These are safeguards. The companion should normally keep exact revisions in
    # speech-skip blocks and full paths in Markdown destinations. Rewrite paths
    # before stripping Markdown emphasis so underscores in filenames survive.
    text = re.sub(
        r"\b(?:commit|revision|sha)\s+[0-9a-fA-F]{7,64}\b",
        "this commit",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b[0-9a-fA-F]{7,64}\b", "the commit", text)
    raw_path_pattern = re.compile(
        r"(?<![\w])(?:"
        r"[A-Za-z]:\\(?:[^\s<>\"'`]+\\)*[^\s<>\"'`]+|"
        r"(?:res|user|file)://[^\s<>\"'`]+|"
        r"(?:~?/|\./|\.\./)(?:[^\s<>\"'`]+/)*[^\s<>\"'`]+"
        r")"
    )
    text = raw_path_pattern.sub(_humanize_raw_path, text)

    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}(?:[-+*]|\d+[.)])\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"(`{1,2}|\*\*|__|~~)", "", text)
    text = re.sub(r"(?<!\*)\*(?!\*)", "", text)
    text = re.sub(r"(?<!\w)_(?=\S)|(?<=\S)_(?!\w)", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_oversized_sentence(sentence: str, max_chars: int) -> list[str]:
    words = sentence.split()
    pieces: list[str] = []
    current: list[str] = []
    current_length = 0
    for word in words:
        added = len(word) + (1 if current else 0)
        if current and current_length + added > max_chars:
            pieces.append(" ".join(current))
            current = [word]
            current_length = len(word)
        else:
            current.append(word)
            current_length += added
    if current:
        pieces.append(" ".join(current))
    return pieces


def split_narration(narration: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Split at paragraph and sentence boundaries for predictable local rendering."""
    if max_chars < 500:
        raise RuntimeError("--max-chars must be at least 500")

    units: list[str] = []
    for paragraph in re.split(r"\n\s*\n", narration):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= max_chars:
            units.append(paragraph)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) <= max_chars:
                units.append(sentence)
            else:
                units.extend(_split_oversized_sentence(sentence, max_chars))

    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for unit in units:
        separator_length = 2 if current else 0
        if current and current_length + separator_length + len(unit) > max_chars:
            chunks.append("\n\n".join(current))
            current = [unit]
            current_length = len(unit)
        else:
            current.append(unit)
            current_length += separator_length + len(unit)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def require_command(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise RuntimeError(f"Required command not found: {name}")
    return executable


def use_local_environment_if_available() -> None:
    environment_python = LOCAL_ENVIRONMENT / "bin" / "python"
    if importlib.util.find_spec("kokoro") is not None or not environment_python.is_file():
        return
    if Path(sys.executable).resolve() == environment_python.resolve():
        return
    os.execv(
        str(environment_python),
        [str(environment_python), str(Path(__file__).resolve()), *sys.argv[1:]],
    )


def load_local_speech() -> tuple[Any, Any, Any]:
    try:
        import numpy
        import soundfile
        from kokoro import KPipeline
    except ImportError as error:
        raise RuntimeError(
            "Local speech dependencies are missing. Create the isolated environment at "
            f"{LOCAL_ENVIRONMENT} and install `kokoro>=0.9.4` plus `soundfile`."
        ) from error
    return KPipeline, numpy, soundfile


def configure_espeak() -> None:
    if shutil.which("espeak-ng"):
        return
    try:
        import espeakng_loader
        from phonemizer.backend.espeak.wrapper import EspeakWrapper
    except ImportError as error:
        raise RuntimeError(
            "eSpeak NG is unavailable. Install the system `espeak-ng` package or add "
            "`espeakng-loader` to the isolated speech environment."
        ) from error
    EspeakWrapper.set_library(espeakng_loader.get_library_path())
    EspeakWrapper.set_data_path(espeakng_loader.get_data_path())


def synthesize_chunk(
    pipeline: Any,
    narration: str,
    output_path: Path,
    *,
    voice: str,
    speed: float,
    numpy: Any,
    soundfile: Any,
) -> None:
    audio_parts: list[Any] = []
    for _, _, audio in pipeline(narration, voice=voice, speed=speed):
        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()
        audio_parts.append(numpy.asarray(audio))

    if not audio_parts:
        raise RuntimeError("Kokoro produced no audio for a narration chunk")
    audio = audio_parts[0] if len(audio_parts) == 1 else numpy.concatenate(audio_parts)
    soundfile.write(str(output_path), audio, SAMPLE_RATE, subtype="PCM_16")


def codec_args(suffix: str) -> list[str]:
    return {
        ".wav": ["-codec:a", "pcm_s16le"],
        ".mp3": ["-codec:a", "libmp3lame", "-b:a", "96k"],
        ".m4a": ["-codec:a", "aac", "-b:a", "96k"],
        ".ogg": ["-codec:a", "libvorbis", "-q:a", "4"],
        ".opus": ["-codec:a", "libopus", "-b:a", "64k"],
    }[suffix]


def stitch_audio(parts: list[Path], output_path: Path, ffmpeg: str) -> None:
    concat_file = parts[0].parent / "parts.txt"
    concat_file.write_text(
        "".join(f"file '{part.as_posix()}'\n" for part in parts),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-vn",
            *codec_args(output_path.suffix.lower()),
            str(output_path),
        ],
        check=False,
    )
    if result.returncode != 0:
        output_path.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg failed to create {output_path.suffix.lower()} audio")


def _dependency_status() -> str:
    espeak_ready = (
        shutil.which("espeak-ng") is not None
        or importlib.util.find_spec("espeakng_loader") is not None
    )
    checks = {
        "kokoro": importlib.util.find_spec("kokoro") is not None,
        "soundfile": importlib.util.find_spec("soundfile") is not None,
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "espeak": espeak_ready,
    }
    return ", ".join(f"{name}={'ready' if ready else 'missing'}" for name, ready in checks.items())


def run() -> int:
    args = parse_args()
    use_local_environment_if_available()
    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    suffix = output_path.suffix.lower()

    if not input_path.is_file():
        raise RuntimeError(f"Input companion does not exist: {input_path}")
    if suffix not in SUPPORTED_OUTPUTS:
        supported = ", ".join(sorted(SUPPORTED_OUTPUTS))
        raise RuntimeError(f"Unsupported output extension {suffix!r}; choose one of: {supported}")
    if output_path.exists() and not args.force:
        raise RuntimeError(f"Output already exists (pass --force only with overwrite permission): {output_path}")
    if args.speed <= 0:
        raise RuntimeError("--speed must be greater than zero")

    source = input_path.read_text(encoding="utf-8")
    narration = markdown_to_speech(source)
    if not narration:
        raise RuntimeError("The companion contains no speakable text")
    chunks = split_narration(narration, args.max_chars)

    if args.dry_run:
        print(
            f"Ready to render {len(narration):,} spoken characters in {len(chunks)} "
            f"chunk{'s' if len(chunks) != 1 else ''} locally with Kokoro voice "
            f"{args.voice!r}. Dependencies: {_dependency_status()}."
        )
        return 0

    ffmpeg = require_command("ffmpeg")
    KPipeline, numpy, soundfile = load_local_speech()
    configure_espeak()
    pipeline = KPipeline(lang_code=args.lang_code, repo_id=KOKORO_REPO_ID)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="codex-explain-") as temporary:
        temp_dir = Path(temporary)
        parts: list[Path] = []
        for index, chunk in enumerate(chunks, start=1):
            part_path = temp_dir / f"part-{index:03d}.wav"
            print(f"Rendering speech part {index} of {len(chunks)} locally...", flush=True)
            synthesize_chunk(
                pipeline,
                chunk,
                part_path,
                voice=args.voice,
                speed=args.speed,
                numpy=numpy,
                soundfile=soundfile,
            )
            parts.append(part_path)

        rendered_path = temp_dir / f"rendered{suffix}"
        stitch_audio(parts, rendered_path, ffmpeg)
        if output_path.exists():
            output_path.unlink()
        shutil.move(str(rendered_path), str(output_path))

    print(f"Created locally generated AI narration at {output_path}")
    return 0


def main() -> int:
    try:
        return run()
    except (OSError, RuntimeError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
