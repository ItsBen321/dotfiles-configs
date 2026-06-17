#!/usr/bin/env python3
"""Transcribe an audio file with a local model by default."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional

DEFAULT_BACKEND = "local"
DEFAULT_LOCAL_MODEL = "base"
DEFAULT_OPENAI_MODEL = "gpt-4o-transcribe"
DEFAULT_RESPONSE_FORMAT = "text"
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_BEAM_SIZE = 5
SUPPORTED_EXTENSIONS = {"mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"}
OPENAI_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def _die(message: str, code: int = 1) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(code)


def _ensure_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        _die("OPENAI_API_KEY is not set. Set it locally before using --backend openai.")


def _create_openai_client() -> Any:
    try:
        from openai import OpenAI
    except ImportError:
        _die("openai SDK is not installed. Install with `python -m pip install openai`.")
    return OpenAI()


def _enable_platform_truststore() -> None:
    try:
        import truststore
    except ImportError:
        return
    try:
        truststore.inject_into_ssl()
    except Exception:
        return


def _resolve_audio_file(value: str, backend: str) -> Path:
    path = Path(value).expanduser()
    if not path.exists():
        _die(f"Audio file not found: {path}")
    if not path.is_file():
        _die(f"Audio path is not a file: {path}")

    ext = path.suffix.lower().lstrip(".")
    if ext not in SUPPORTED_EXTENSIONS:
        _die(
            "Unsupported audio extension "
            f"'.{ext or '<none>'}'. Supported: "
            + ", ".join(sorted(SUPPORTED_EXTENSIONS))
        )

    if backend == "openai":
        size = path.stat().st_size
        if size > OPENAI_MAX_UPLOAD_BYTES:
            _die(
                f"Audio file is {size} bytes, which exceeds the 25 MB Audio API upload limit."
            )
    return path


def _read_prompt(prompt: Optional[str], prompt_file: Optional[str]) -> Optional[str]:
    if prompt and prompt_file:
        _die("Use --prompt or --prompt-file, not both.")
    if prompt_file:
        path = Path(prompt_file).expanduser()
        if not path.exists():
            _die(f"Prompt file not found: {path}")
        if not path.is_file():
            _die(f"Prompt path is not a file: {path}")
        text = path.read_text(encoding="utf-8").strip()
        return text or None
    if prompt:
        text = prompt.strip()
        return text or None
    return None


def _resolve_output_path(value: Optional[str], response_format: str) -> Optional[Path]:
    if not value:
        return None
    path = Path(value).expanduser()
    if path.exists() and path.is_dir():
        extension = ".json" if response_format == "json" else ".txt"
        return path / f"transcript{extension}"
    if not path.suffix:
        path = path.with_suffix(".json" if response_format == "json" else ".txt")
    return path


def _validate_output_path(path: Optional[Path], force: bool) -> None:
    if path is None:
        return
    if path.exists() and not force:
        _die(f"Output already exists: {path} (use --force to overwrite)")


def _selected_model(backend: str, model: Optional[str]) -> str:
    if model:
        return model
    if backend == "openai":
        return DEFAULT_OPENAI_MODEL
    return DEFAULT_LOCAL_MODEL


def _build_payload(
    audio_file: Path,
    *,
    backend: str,
    model: str,
    response_format: str,
    prompt: Optional[str],
    language: Optional[str],
    device: str,
    compute_type: str,
    beam_size: int,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "backend": backend,
        "file": str(audio_file),
        "model": model,
        "response_format": response_format,
    }
    if prompt:
        payload["prompt"] = prompt
    if language:
        payload["language"] = language
    if backend == "local":
        payload["device"] = device
        payload["compute_type"] = compute_type
        payload["beam_size"] = beam_size
    return payload


def _result_to_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        text = result.get("text")
        return text if isinstance(text, str) else json.dumps(result, ensure_ascii=False)
    text = getattr(result, "text", None)
    if isinstance(text, str):
        return text
    return str(result)


def _result_to_json(result: Any) -> str:
    if isinstance(result, str):
        data: Any = {"text": result}
    elif isinstance(result, dict):
        data = result
    elif hasattr(result, "model_dump"):
        data = result.model_dump()
    elif hasattr(result, "to_dict"):
        data = result.to_dict()
    else:
        data = {"text": _result_to_text(result)}
    return json.dumps(data, ensure_ascii=False, indent=2)


def _format_result(result: Any, response_format: str) -> str:
    if response_format == "json":
        return _result_to_json(result)
    return _result_to_text(result).strip()


def _transcribe_openai(payload: Dict[str, Any]) -> Any:
    _ensure_api_key()
    client = _create_openai_client()
    api_payload = {
        "model": payload["model"],
        "response_format": payload["response_format"],
    }
    if "prompt" in payload:
        api_payload["prompt"] = payload["prompt"]
    if "language" in payload:
        api_payload["language"] = payload["language"]

    file_path = Path(str(payload["file"]))
    with file_path.open("rb") as audio_file:
        return client.audio.transcriptions.create(file=audio_file, **api_payload)


def _transcribe_local(payload: Dict[str, Any]) -> Dict[str, Any]:
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    _enable_platform_truststore()
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        _die(
            "faster-whisper is not installed. Install with "
            "`python -m pip install faster-whisper`."
        )

    try:
        model = WhisperModel(
            payload["model"],
            device=payload["device"],
            compute_type=payload["compute_type"],
        )
        segments_iter, info = model.transcribe(
            payload["file"],
            language=payload.get("language"),
            initial_prompt=payload.get("prompt"),
            beam_size=int(payload["beam_size"]),
        )
    except Exception as exc:
        message = str(exc)
        if "CERTIFICATE_VERIFY_FAILED" in message or "LocalEntryNotFoundError" in message:
            _die(
                "Could not download the local transcription model. Install `truststore` "
                "with `python -m pip install truststore`, or download the faster-whisper "
                "model once on a network with working certificate validation."
            )
        _die(f"Local transcription failed: {message}")

    segments = [
        {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
        }
        for segment in segments_iter
    ]
    text = " ".join(segment["text"] for segment in segments).strip()
    return {
        "text": text,
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
        "duration": getattr(info, "duration", None),
        "segments": segments,
        "backend": "local",
        "model": payload["model"],
    }


def _write_or_print(text: str, out_path: Optional[Path]) -> None:
    if out_path is None:
        print(text)
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text + ("\n" if text and not text.endswith("\n") else ""), encoding="utf-8")
    print(f"Wrote {out_path}", file=sys.stderr)


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe an audio file locally by default, or with OpenAI when requested.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--file", required=True, help="Path to an audio file.")
    parser.add_argument("--out", help="Optional transcript output path.")
    parser.add_argument(
        "--backend",
        choices=("local", "openai"),
        default=DEFAULT_BACKEND,
        help="Transcription backend.",
    )
    parser.add_argument(
        "--model",
        help=(
            "Model name. For local: tiny, base, small, medium, large-v3, etc. "
            "For openai: gpt-4o-transcribe, gpt-4o-mini-transcribe, etc."
        ),
    )
    parser.add_argument(
        "--response-format",
        choices=("text", "json"),
        default=DEFAULT_RESPONSE_FORMAT,
        help="Transcript output format.",
    )
    parser.add_argument("--prompt", help="Optional transcription context prompt.")
    parser.add_argument("--prompt-file", help="Read transcription context prompt from a UTF-8 text file.")
    parser.add_argument("--language", help="Optional language code hint, such as en, nl, or fr.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and print the selected payload without transcribing.")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help="Local backend device: auto, cpu, cuda.")
    parser.add_argument("--compute-type", default=DEFAULT_COMPUTE_TYPE, help="Local backend compute type, such as int8, float16, or float32.")
    parser.add_argument("--beam-size", type=int, default=DEFAULT_BEAM_SIZE, help="Local backend beam size.")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    audio_file = _resolve_audio_file(args.file, args.backend)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    out_path = _resolve_output_path(args.out, args.response_format)
    _validate_output_path(out_path, args.force)
    model = _selected_model(args.backend, args.model)

    payload = _build_payload(
        audio_file,
        backend=args.backend,
        model=model,
        response_format=args.response_format,
        prompt=prompt,
        language=args.language,
        device=args.device,
        compute_type=args.compute_type,
        beam_size=args.beam_size,
    )

    if args.dry_run:
        dry_payload = dict(payload)
        if "prompt" in dry_payload:
            dry_payload["prompt"] = f"<{len(str(prompt))} chars>"
        print(json.dumps(dry_payload, indent=2, sort_keys=True))
        if out_path:
            print(f"Would write {out_path}", file=sys.stderr)
        return 0

    if args.backend == "openai":
        result = _transcribe_openai(payload)
    else:
        result = _transcribe_local(payload)
    output = _format_result(result, args.response_format)
    _write_or_print(output, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
