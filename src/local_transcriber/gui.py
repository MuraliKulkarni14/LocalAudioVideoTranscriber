from __future__ import annotations

import queue
import threading
import tkinter as tk
import winreg
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from .transcribe import (
        DEFAULT_MODEL,
        DEFAULT_OUTPUT_DIR,
        MODEL_CHOICES,
        TranscriptOptions,
        TranscriptResult,
        transcribe_file,
    )
except ImportError:
    from transcribe import (
        DEFAULT_MODEL,
        DEFAULT_OUTPUT_DIR,
        MODEL_CHOICES,
        TranscriptOptions,
        TranscriptResult,
        transcribe_file,
    )


THEMES = {
    "light": {
        "bg": "#f5f5f2",
        "panel": "#ffffff",
        "panel_alt": "#eeece5",
        "text": "#1f1f1f",
        "muted": "#5f625d",
        "border": "#c9c7bd",
        "accent": "#1f6f68",
        "accent_active": "#185a55",
        "field": "#ffffff",
        "select": "#dfeeea",
    },
    "dark": {
        "bg": "#171a1d",
        "panel": "#202428",
        "panel_alt": "#2a3035",
        "text": "#f1f3f1",
        "muted": "#aeb7b1",
        "border": "#3a4248",
        "accent": "#58b8a9",
        "accent_active": "#6ecabb",
        "field": "#111416",
        "select": "#23413d",
    },
}


def get_windows_theme() -> str:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            apps_use_light_theme, _kind = winreg.QueryValueEx(key, "AppsUseLightTheme")
    except OSError:
        return "light"
    return "light" if apps_use_light_theme else "dark"


class TranscriberApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Local Audio & Video Transcriber")
        self.geometry("980x720")
        self.minsize(820, 620)

        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.language_var = tk.StringVar()
        self.task_var = tk.StringVar(value="transcribe")
        self.device_var = tk.StringVar(value="auto")
        self.compute_type_var = tk.StringVar(value="auto")
        self.beam_size_var = tk.IntVar(value=5)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_label_var = tk.StringVar(value="0%")
        self.theme_var = tk.StringVar(value="System")
        self.text_widgets: list[tk.Text] = []

        self.palette = THEMES[self.resolve_theme()]
        self.configure_style()
        self.build_layout()
        self.apply_theme()
        self.after(100, self.process_messages)

    def configure_style(self) -> None:
        palette = self.palette
        self.configure(bg=palette["bg"])
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background=palette["bg"])
        style.configure("Panel.TFrame", background=palette["panel"])
        style.configure("TLabelframe", background=palette["bg"], bordercolor=palette["border"])
        style.configure("TLabelframe.Label", background=palette["bg"], foreground=palette["text"])
        style.configure("TLabel", background=palette["bg"], foreground=palette["text"])
        style.configure("TButton", padding=(12, 7))
        style.configure("Accent.TButton", background=palette["accent"], foreground="#ffffff")
        style.map(
            "Accent.TButton",
            background=[("active", palette["accent_active"]), ("disabled", palette["border"])],
        )
        style.configure("Status.TLabel", foreground=palette["muted"])
        style.configure("TEntry", fieldbackground=palette["field"], foreground=palette["text"])
        style.configure("TCombobox", fieldbackground=palette["field"], foreground=palette["text"])
        style.configure("TSpinbox", fieldbackground=palette["field"], foreground=palette["text"])
        style.configure("TCheckbutton", background=palette["bg"], foreground=palette["text"])
        style.configure("TNotebook", background=palette["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=palette["panel_alt"], foreground=palette["text"], padding=(14, 8))
        style.map("TNotebook.Tab", background=[("selected", palette["panel"])])
        style.configure(
            "Horizontal.TProgressbar",
            background=palette["accent"],
            troughcolor=palette["panel_alt"],
            bordercolor=palette["border"],
            lightcolor=palette["accent"],
            darkcolor=palette["accent"],
        )

    def resolve_theme(self) -> str:
        selected = self.theme_var.get().lower()
        if selected in {"light", "dark"}:
            return selected
        return get_windows_theme()

    def apply_theme(self) -> None:
        self.palette = THEMES[self.resolve_theme()]
        self.configure_style()
        for text in self.text_widgets:
            text.configure(
                background=self.palette["panel"],
                foreground=self.palette["text"],
                insertbackground=self.palette["text"],
                selectbackground=self.palette["select"],
                selectforeground=self.palette["text"],
            )

    def build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=(18, 16, 18, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title = ttk.Label(header, text="Local Audio & Video Transcriber", font=("Segoe UI", 17, "bold"))
        title.grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(header, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

        theme_row = ttk.Frame(header)
        theme_row.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Label(theme_row, text="Theme").grid(row=0, column=0, sticky="e", padx=(0, 8))
        theme_combo = ttk.Combobox(
            theme_row,
            textvariable=self.theme_var,
            values=("System", "Light", "Dark"),
            state="readonly",
            width=10,
        )
        theme_combo.grid(row=0, column=1, sticky="e")
        theme_combo.bind("<<ComboboxSelected>>", lambda _event: self.apply_theme())

        body = ttk.Frame(self, padding=(18, 8, 18, 12))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=0, minsize=330)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        controls = ttk.Frame(body)
        controls.grid(row=0, column=0, sticky="nsw", padx=(0, 16))
        controls.columnconfigure(0, weight=1)

        self.build_file_controls(controls)
        self.build_settings_controls(controls)
        self.build_progress_controls(controls)
        self.build_action_controls(controls)

        output = ttk.Frame(body)
        output.grid(row=0, column=1, sticky="nsew")
        output.columnconfigure(0, weight=1)
        output.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(output)
        notebook.grid(row=0, column=0, sticky="nsew")

        self.log_text = self.build_text_tab(notebook, "Progress")
        self.preview_text = self.build_text_tab(notebook, "Transcript")

    def build_file_controls(self, parent: ttk.Frame) -> None:
        files = ttk.LabelFrame(parent, text="Files", padding=12)
        files.grid(row=0, column=0, sticky="ew")
        files.columnconfigure(0, weight=1)

        ttk.Label(files, text="Audio or video").grid(row=0, column=0, sticky="w")
        input_row = ttk.Frame(files)
        input_row.grid(row=1, column=0, sticky="ew", pady=(4, 12))
        input_row.columnconfigure(0, weight=1)
        ttk.Entry(input_row, textvariable=self.input_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(input_row, text="Browse", command=self.choose_input).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(files, text="Output folder").grid(row=2, column=0, sticky="w")
        output_row = ttk.Frame(files)
        output_row.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        output_row.columnconfigure(0, weight=1)
        ttk.Entry(output_row, textvariable=self.output_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(output_row, text="Browse", command=self.choose_output).grid(row=0, column=1, padx=(8, 0))

    def build_settings_controls(self, parent: ttk.Frame) -> None:
        settings = ttk.LabelFrame(parent, text="Settings", padding=12)
        settings.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        settings.columnconfigure(1, weight=1)

        self.add_combo(settings, 0, "Model", self.model_var, MODEL_CHOICES)
        self.add_entry(settings, 1, "Language", self.language_var)
        self.add_combo(settings, 2, "Task", self.task_var, ("transcribe", "translate"))
        self.add_combo(settings, 3, "Device", self.device_var, ("auto", "cpu", "cuda"))
        self.add_combo(settings, 4, "Compute", self.compute_type_var, ("auto", "int8", "float16", "float32"))

        ttk.Label(settings, text="Beam size").grid(row=5, column=0, sticky="w", pady=(9, 0))
        ttk.Spinbox(settings, from_=1, to=10, textvariable=self.beam_size_var, width=8).grid(
            row=5,
            column=1,
            sticky="w",
            pady=(9, 0),
        )

        ttk.Checkbutton(settings, text="Overwrite existing outputs", variable=self.overwrite_var).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(12, 0),
        )

    def build_action_controls(self, parent: ttk.Frame) -> None:
        actions = ttk.Frame(parent)
        actions.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        actions.columnconfigure(0, weight=1)

        self.start_button = ttk.Button(
            actions,
            text="Start Transcription",
            style="Accent.TButton",
            command=self.start_transcription,
        )
        self.start_button.grid(row=0, column=0, sticky="ew")

    def build_progress_controls(self, parent: ttk.Frame) -> None:
        progress = ttk.LabelFrame(parent, text="Run", padding=12)
        progress.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        progress.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(
            progress,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            style="Horizontal.TProgressbar",
        )
        self.progress.grid(row=0, column=0, sticky="ew")
        ttk.Label(progress, textvariable=self.progress_label_var, style="Status.TLabel").grid(
            row=0,
            column=1,
            sticky="e",
            padx=(10, 0),
        )

    def build_text_tab(self, notebook: ttk.Notebook, label: str) -> tk.Text:
        frame = ttk.Frame(notebook, padding=8)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        text = tk.Text(
            frame,
            wrap="word",
            relief="flat",
            padx=12,
            pady=12,
            font=("Segoe UI", 10),
            background="#ffffff",
            foreground="#1f1f1f",
            insertbackground="#1f1f1f",
        )
        self.text_widgets.append(text)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        notebook.add(frame, text=label)
        return text

    def add_combo(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        values: tuple[str, ...],
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(9, 0))
        combo = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly")
        combo.grid(row=row, column=1, sticky="ew", pady=(9, 0))

    def add_entry(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(9, 0))
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=(9, 0))

    def choose_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose audio or video",
            filetypes=[
                ("Media files", "*.mp3 *.mp4 *.m4a *.wav *.webm *.mov *.mkv *.aac *.flac"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.input_var.set(path)

    def choose_output(self) -> None:
        path = filedialog.askdirectory(title="Choose output folder")
        if path:
            self.output_var.set(path)

    def start_transcription(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        input_path = self.input_var.get().strip().strip('"')
        if not input_path:
            messagebox.showwarning("Missing file", "Choose an audio or video file first.")
            return

        output_dir = self.output_var.get().strip().strip('"') or DEFAULT_OUTPUT_DIR
        language = self.language_var.get().strip() or None

        options = TranscriptOptions(
            input_path=Path(input_path),
            output_dir=Path(output_dir),
            model=self.model_var.get(),
            language=language,
            task=self.task_var.get(),
            device=self.device_var.get(),
            compute_type=self.compute_type_var.get(),
            beam_size=int(self.beam_size_var.get()),
            overwrite=self.overwrite_var.get(),
        )

        self.log_text.delete("1.0", tk.END)
        self.preview_text.delete("1.0", tk.END)
        self.set_progress(0)
        self.start_button.state(["disabled"])
        self.status_var.set("Working")

        self.worker = threading.Thread(target=self.run_transcription, args=(options,), daemon=True)
        self.worker.start()

    def run_transcription(self, options: TranscriptOptions) -> None:
        try:
            result = transcribe_file(
                options,
                progress=self.enqueue_log,
                progress_percent=self.enqueue_progress,
            )
        except Exception as error:
            self.messages.put(("error", error))
        else:
            self.messages.put(("done", result))

    def enqueue_log(self, message: str) -> None:
        self.messages.put(("log", message))

    def enqueue_progress(self, value: float) -> None:
        self.messages.put(("progress", value))

    def process_messages(self) -> None:
        while True:
            try:
                kind, payload = self.messages.get_nowait()
            except queue.Empty:
                break

            if kind == "log":
                self.append_log(str(payload))
            elif kind == "progress":
                self.set_progress(float(payload))
            elif kind == "error":
                self.start_button.state(["!disabled"])
                self.status_var.set("Failed")
                self.set_progress(0)
                messagebox.showerror("Transcription failed", str(payload))
                self.append_log(f"Error: {payload}")
            elif kind == "done":
                self.finish_transcription(payload)

        self.after(100, self.process_messages)

    def append_log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def set_progress(self, value: float) -> None:
        rounded = max(0, min(100, round(value)))
        self.progress_var.set(rounded)
        self.progress_label_var.set(f"{rounded}%")

    def finish_transcription(self, result: TranscriptResult) -> None:
        self.start_button.state(["!disabled"])
        self.status_var.set("Done")
        self.set_progress(100)
        self.preview_text.insert(tk.END, "\n".join(segment.text for segment in result.segments))
        self.preview_text.see("1.0")
        self.append_log("Done. Wrote:")
        for path in result.output_paths.values():
            self.append_log(f"  {path}")
        messagebox.showinfo("Transcription complete", f"Wrote transcript files to:\n{result.output_paths['txt'].parent}")


def main() -> None:
    app = TranscriberApp()
    app.mainloop()


if __name__ == "__main__":
    main()
