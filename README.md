# Local Audio & Video Transcriber

A lightweight, local-first Windows desktop app for converting meeting recordings
and media files into raw transcripts.

The app runs a Whisper-compatible model locally through `faster-whisper`. It is
designed for workflows like turning Zoom recordings into transcript files that
can be searched, cleaned up, summarized, or used later in other tools.

## Features

- Desktop UI with file picker, output folder picker, and transcript preview
- System, light, and dark themes
- Progress bar and live segment log during transcription
- Local audio/video transcription with `faster-whisper`
- Outputs `.txt`, `.srt`, `.vtt`, and `.json`
- Choose model size, language, task, runtime device, and compute type
- CLI mode for scripted use
- Local-first workflow with no paid transcription API

## Privacy

Media files are processed locally. The app does not upload audio or video to a
transcription service.

On first use, the selected model may be downloaded from Hugging Face and cached
on your machine. After the model is cached, transcription runs locally.

## Requirements

- Windows 10 or newer
- Python 3.11 or newer
- Enough disk space for Whisper model files and transcript outputs

GPU acceleration through this backend is CUDA-focused. NVIDIA CUDA systems can
use `--device cuda`; AMD Radeon systems generally fall back to CPU for now. An
AMD/Vulkan-friendly backend is on the roadmap.

## Setup

Install Python from:

https://www.python.org/downloads/windows/

During installation, enable:

```text
Add python.exe to PATH
```

Then open PowerShell in this folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run The Desktop App

```powershell
.\.venv\Scripts\Activate.ps1
python .\src\local_transcriber\gui.py
```

Choose your Zoom recording or exported audio/video file, pick an output folder,
and press `Start Transcription`.

## CLI Usage

Interactive mode:

```powershell
.\.venv\Scripts\Activate.ps1
python .\src\local_transcriber\transcribe.py
```

Direct file mode:

```powershell
python .\src\local_transcriber\transcribe.py "C:\path\to\video.mp4"
```

Useful examples:

```powershell
python .\src\local_transcriber\transcribe.py "C:\path\to\file.mp4" --model medium
python .\src\local_transcriber\transcribe.py "C:\path\to\file.mp4" --language en
python .\src\local_transcriber\transcribe.py "C:\path\to\file.mp4" --task translate
python .\src\local_transcriber\transcribe.py "C:\path\to\file.mp4" --output-dir "C:\path\to\transcripts"
```

Force CUDA, if you have a supported NVIDIA GPU:

```powershell
python .\src\local_transcriber\transcribe.py "C:\path\to\file.mp4" --device cuda --compute-type float16
```

Force CPU:

```powershell
python .\src\local_transcriber\transcribe.py "C:\path\to\file.mp4" --device cpu --compute-type int8
```

## Model Notes

Good starting choices:

- `small`: faster, lower accuracy
- `medium`: stronger balance for many meeting recordings
- `large-v3`: best accuracy, slower and larger

By default the app uses `--device auto` and `--compute-type auto`. It selects
CUDA with `float16` when available, otherwise CPU with `int8`.

## Packaging

Install packaging dependencies and build the Windows app:

```powershell
.\scripts\build_windows.ps1 -Clean
```

The packaged app is created at:

```text
dist\LocalTranscriber\LocalTranscriber.exe
```

For more detail, see [docs/PACKAGING.md](docs/PACKAGING.md).

## GitHub Release Notes

See [docs/GITHUB_RELEASE.md](docs/GITHUB_RELEASE.md) for a release checklist and
copy-ready release note template.

## Roadmap

- Drag-and-drop file selection
- Batch transcription
- Speaker diarization
- AMD-friendly GPU processing with Vulkan
- Signed Windows release build

## License

MIT. See [LICENSE](LICENSE).
