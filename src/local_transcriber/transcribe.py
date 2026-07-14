from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

import ctranslate2
from faster_whisper import WhisperModel


DEFAULT_MODEL = "small"
DEFAULT_OUTPUT_DIR = "transcripts"
MODEL_CHOICES = ("tiny", "base", "small", "medium", "large-v3")


@dataclass(frozen=True)
class TranscriptSegment:
    index: int
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TranscriptOptions:
    input_path: Path
    output_dir: Path
    model: str = DEFAULT_MODEL
    language: str | None = None
    task: str = "transcribe"
    device: str = "auto"
    compute_type: str = "auto"
    beam_size: int = 5
    overwrite: bool = False


@dataclass(frozen=True)
class TranscriptResult:
    output_paths: dict[str, Path]
    metadata: dict[str, object]
    segments: list[TranscriptSegment]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe an audio or video file locally with faster-whisper."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to an audio or video file. Omit this to use interactive mode.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=(
            "Whisper model size/name. Examples: tiny, base, small, medium, "
            "large-v3. Default: small."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Folder where transcript files will be written. Default: transcripts.",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Optional spoken language code, for example en, hi, es. Auto-detects if omitted.",
    )
    parser.add_argument(
        "--task",
        choices=("transcribe", "translate"),
        default="transcribe",
        help="Use transcribe to keep original language or translate for English output.",
    )
    parser.add_argument(
        "--device",
        choices=("cpu", "cuda", "auto"),
        default="auto",
        help="Processing device. Auto uses CUDA if available, otherwise CPU. Default: auto.",
    )
    parser.add_argument(
        "--compute-type",
        default="auto",
        help="Model compute type. Auto uses float16 on CUDA and int8 on CPU. Default: auto.",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Higher can improve accuracy but may be slower. Default: 5.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing transcript files.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Ask for settings interactively.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.interactive or not args.input:
        args = prompt_for_args(args)

    try:
        result = transcribe_file(
            TranscriptOptions(
                input_path=Path(args.input),
                output_dir=Path(args.output_dir),
                model=args.model,
                language=args.language,
                task=args.task,
                device=args.device,
                compute_type=args.compute_type,
                beam_size=args.beam_size,
                overwrite=args.overwrite,
            ),
            progress=print,
        )
    except FileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return 2
    except FileExistsError as error:
        print(str(error), file=sys.stderr)
        return 3

    print("Done. Wrote:")
    for path in result.output_paths.values():
        print(f"  {path}")

    return 0


def transcribe_file(
    options: TranscriptOptions,
    *,
    progress: Callable[[str], None] | None = None,
    progress_percent: Callable[[float], None] | None = None,
) -> TranscriptResult:
    input_path = options.input_path.expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    output_dir = options.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths = build_output_paths(input_path, output_dir)

    if not options.overwrite:
        existing = [path for path in output_paths.values() if path.exists()]
        if existing:
            existing_list = "\n".join(f"  {path}" for path in existing)
            raise FileExistsError(
                "Transcript output already exists. Enable overwrite to replace:\n"
                f"{existing_list}"
            )

    runtime_device, runtime_compute_type = resolve_runtime(
        options.device,
        options.compute_type,
        progress=progress,
    )

    report_percent(progress_percent, 2)
    report(progress, f"Loading model: {options.model}")
    report(progress, f"Runtime: device={runtime_device}, compute_type={runtime_compute_type}")
    model = WhisperModel(
        options.model,
        device=runtime_device,
        compute_type=runtime_compute_type,
    )

    report_percent(progress_percent, 8)
    report(progress, f"Transcribing: {input_path}")
    segments_iter, info = model.transcribe(
        str(input_path),
        beam_size=options.beam_size,
        language=options.language,
        task=options.task,
        vad_filter=True,
    )

    report_percent(progress_percent, 10)
    segments = collect_segments(
        segments_iter,
        progress=progress,
        progress_percent=progress_percent,
        duration=info.duration,
    )
    metadata = {
        "input": str(input_path),
        "model": options.model,
        "requested_device": options.device,
        "requested_compute_type": options.compute_type,
        "device": runtime_device,
        "compute_type": runtime_compute_type,
        "task": options.task,
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
    }

    write_txt(output_paths["txt"], segments)
    write_srt(output_paths["srt"], segments)
    write_vtt(output_paths["vtt"], segments)
    write_json(output_paths["json"], metadata, segments)

    report_percent(progress_percent, 100)
    return TranscriptResult(output_paths=output_paths, metadata=metadata, segments=segments)


def build_output_paths(input_path: Path, output_dir: Path) -> dict[str, Path]:
    output_base = output_dir / safe_output_stem(input_path)
    return {
        "txt": output_base.with_suffix(".txt"),
        "srt": output_base.with_suffix(".srt"),
        "vtt": output_base.with_suffix(".vtt"),
        "json": output_base.with_suffix(".json"),
    }


def report(progress: Callable[[str], None] | None, message: str) -> None:
    if progress is not None:
        progress(message)


def report_percent(progress_percent: Callable[[float], None] | None, value: float) -> None:
    if progress_percent is not None:
        progress_percent(max(0, min(100, value)))


def resolve_runtime(
    requested_device: str,
    requested_compute_type: str,
    *,
    progress: Callable[[str], None] | None = None,
) -> tuple[str, str]:
    cuda_available = ctranslate2.get_cuda_device_count() > 0

    if requested_device == "cuda" and not cuda_available:
        report(progress, "CUDA was requested, but no CUDA device was detected. Falling back to CPU.")

    if requested_device == "cuda" and cuda_available:
        device = "cuda"
    elif requested_device == "auto" and cuda_available:
        device = "cuda"
    else:
        device = "cpu"

    if requested_compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"
    else:
        compute_type = requested_compute_type

    return device, compute_type


def prompt_for_args(args: argparse.Namespace) -> argparse.Namespace:
    print()
    print("Local Audio & Video Transcriber")
    print("Press Enter to accept the default shown in brackets.")
    print()

    args.input = prompt_existing_file("Audio/video file")
    args.output_dir = prompt_text("Output folder", args.output_dir)
    args.model = prompt_choice("Model", MODEL_CHOICES, args.model)
    args.language = prompt_optional_text(
        "Language code, for example en, hi, es. Leave blank for auto-detect",
        args.language,
    )
    args.task = prompt_choice("Task", ("transcribe", "translate"), args.task)
    args.device = prompt_choice("Device", ("cpu", "auto", "cuda"), args.device)
    args.compute_type = prompt_text("Compute type", args.compute_type)
    args.beam_size = prompt_int("Beam size", args.beam_size, minimum=1)
    args.overwrite = prompt_yes_no("Overwrite existing outputs", args.overwrite)
    print()
    return args


def prompt_existing_file(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip().strip('"')
        if not value:
            print("Please enter a file path.")
            continue

        path = Path(value).expanduser()
        if path.exists() and path.is_file():
            return str(path)

        print(f"File not found: {path}")


def prompt_text(label: str, default: str) -> str:
    value = input(f"{label} [{default}]: ").strip().strip('"')
    return value or default


def prompt_optional_text(label: str, default: str | None) -> str | None:
    default_display = default or "auto"
    value = input(f"{label} [{default_display}]: ").strip()
    if not value:
        return default
    if value.lower() in {"auto", "none"}:
        return None
    return value


def prompt_choice(label: str, choices: tuple[str, ...], default: str) -> str:
    choices_display = ", ".join(choices)
    while True:
        value = input(f"{label} ({choices_display}) [{default}]: ").strip()
        if not value:
            return default
        if value in choices:
            return value
        print(f"Choose one of: {choices_display}")


def prompt_int(label: str, default: int, *, minimum: int) -> int:
    while True:
        value = input(f"{label} [{default}]: ").strip()
        if not value:
            return default
        try:
            number = int(value)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if number >= minimum:
            return number
        print(f"Please enter {minimum} or higher.")


def prompt_yes_no(label: str, default: bool) -> bool:
    default_display = "y" if default else "n"
    while True:
        value = input(f"{label}? y/n [{default_display}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please enter y or n.")


def collect_segments(
    segments: Iterable[object],
    *,
    progress: Callable[[str], None] | None = None,
    progress_percent: Callable[[float], None] | None = None,
    duration: float | None = None,
) -> list[TranscriptSegment]:
    collected: list[TranscriptSegment] = []
    for index, segment in enumerate(segments, start=1):
        text = segment.text.strip()
        collected.append(
            TranscriptSegment(
                index=index,
                start=float(segment.start),
                end=float(segment.end),
                text=text,
            )
        )
        report(progress, f"[{format_timestamp(segment.start)} -> {format_timestamp(segment.end)}] {text}")
        if duration and duration > 0:
            report_percent(progress_percent, 10 + (float(segment.end) / duration * 85))
    return collected


def write_txt(path: Path, segments: list[TranscriptSegment]) -> None:
    text = "\n".join(segment.text for segment in segments)
    path.write_text(text + "\n", encoding="utf-8")


def write_srt(path: Path, segments: list[TranscriptSegment]) -> None:
    blocks = []
    for segment in segments:
        blocks.append(
            "\n".join(
                [
                    str(segment.index),
                    f"{format_timestamp(segment.start, srt=True)} --> {format_timestamp(segment.end, srt=True)}",
                    segment.text,
                ]
            )
        )
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def write_vtt(path: Path, segments: list[TranscriptSegment]) -> None:
    blocks = ["WEBVTT", ""]
    for segment in segments:
        blocks.append(
            "\n".join(
                [
                    f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}",
                    segment.text,
                ]
            )
        )
        blocks.append("")
    path.write_text("\n".join(blocks), encoding="utf-8")


def write_json(path: Path, metadata: dict[str, object], segments: list[TranscriptSegment]) -> None:
    payload = {
        "metadata": metadata,
        "segments": [asdict(segment) for segment in segments],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def format_timestamp(seconds: float, *, srt: bool = False) -> str:
    milliseconds = round(seconds * 1000)
    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000
    minutes = milliseconds // 60_000
    milliseconds %= 60_000
    whole_seconds = milliseconds // 1000
    milliseconds %= 1000
    separator = "," if srt else "."
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}{separator}{milliseconds:03d}"


def safe_output_stem(input_path: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", input_path.stem).strip("._-")
    return stem or "transcript"


if __name__ == "__main__":
    raise SystemExit(main())
