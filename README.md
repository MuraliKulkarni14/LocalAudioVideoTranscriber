# LocalAudioVideoTranscriber

Fast, offline AI-powered audio and video transcription for Windows using **faster-whisper**.

Convert recordings into searchable transcripts and subtitle files without uploading your data to any cloud service.

> **Privacy First:** All transcription is performed locally on your computer.

---

## Screenshot

> Add a screenshot here once available.

```text
docs/screenshots/main-window.png
```

---

## Features

- 🎙️ Local audio and video transcription
- 🔒 Fully offline after the selected model is downloaded
- 📄 Export transcripts as **TXT**, **SRT**, **VTT**, and **JSON**
- 🖥️ Modern desktop interface with light, dark, and system themes
- 📈 Live transcription progress and transcript preview
- ⚙️ Choose Whisper model, language, task, device, and compute type
- 💻 Command-line interface for scripting and automation
- 🚫 No paid APIs or cloud transcription services

---

## Supported Formats

### Input

- MP3
- WAV
- FLAC
- M4A
- AAC
- OGG
- MP4
- MKV
- MOV
- AVI

### Output

- TXT
- SRT
- VTT
- JSON

---

## Privacy

Media files are processed entirely on your local machine.

The application does **not** upload your files to any transcription service.

The selected Whisper model is downloaded once from Hugging Face and cached locally. After that, all transcription runs offline.

---

## Requirements

- Windows 10 or newer
- Python 3.11+
- Internet connection only for the first model download

### GPU Support

- ✅ NVIDIA CUDA
- ✅ CPU
- 🚧 AMD GPU support planned

---

# Installation

Clone the repository.

```bash
git clone https://github.com/MuraliKulkarni14/LocalAudioVideoTranscriber.git

cd LocalAudioVideoTranscriber
```

Create a virtual environment.

```powershell
python -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

pip install -r requirements.txt
```

---

# Run the Desktop Application

```powershell
python .\src\local_transcriber\gui.py
```

Select a media file, choose an output directory, and start transcription.

---

# Command-Line Usage

Interactive mode

```powershell
python .\src\local_transcriber\transcribe.py
```

Single file

```powershell
python .\src\local_transcriber\transcribe.py "C:\Videos\meeting.mp4"
```

Example

```powershell
python .\src\local_transcriber\transcribe.py `
"C:\Videos\meeting.mp4" `
--model medium `
--language en `
--output-dir "C:\Output"
```

CUDA

```powershell
python .\src\local_transcriber\transcribe.py `
"C:\Videos\meeting.mp4" `
--device cuda `
--compute-type float16
```

CPU

```powershell
python .\src\local_transcriber\transcribe.py `
"C:\Videos\meeting.mp4" `
--device cpu `
--compute-type int8
```

---

# Whisper Models

| Model | Speed | Accuracy |
|------|------|------|
| Small | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Medium | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Large-v3 | ⭐⭐ | ⭐⭐⭐⭐⭐ |

---

# Build From Source

```powershell
.\scripts\build_windows.ps1 -Clean
```

The executable will be generated in

```text
dist\LocalTranscriber\
```

---

# Roadmap

- Drag-and-drop support
- Batch transcription
- Speaker diarization
- AMD/Vulkan acceleration
- Signed Windows releases

---

# Third-Party Software

This project uses:

- faster-whisper
- CTranslate2
- FFmpeg
- Whisper models from OpenAI
- whisper.cpp (bundled for future/native support)

Please refer to their respective licenses.

---

# License

Released under the MIT License.

See the [LICENSE](LICENSE) file for details.
