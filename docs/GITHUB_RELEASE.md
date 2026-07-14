# GitHub Release Checklist

Use this checklist when publishing a release.

## Before Publishing

- Confirm the README is current.
- Run the app from source.
- Build the Windows package:

```powershell
.\scripts\build_windows.ps1 -Clean
```

- Launch `dist\LocalTranscriber\LocalTranscriber.exe`.
- Transcribe a short audio file.
- Confirm `.txt`, `.srt`, `.vtt`, and `.json` files are written.

You can also run the `Windows Build` GitHub Actions workflow and use the uploaded
artifact as the release asset.

## Suggested Release Assets

- Zip the full `dist\LocalTranscriber` folder.
- Attach the zip to the GitHub release.
- Include a short note that the first transcription may download model files.

## Suggested Release Notes

```markdown
## Local Audio & Video Transcriber

Local-first Windows desktop app for turning meeting recordings into raw
transcripts.

### Highlights

- Desktop UI with light/dark/system theme
- Local faster-whisper transcription
- Outputs `.txt`, `.srt`, `.vtt`, and `.json`
- Runtime auto-selects CUDA when available, otherwise CPU

### Notes

- First use may download the selected Whisper model from Hugging Face.
- Audio and video files are processed locally.
- AMD/Vulkan acceleration is planned for future exploration.
```
