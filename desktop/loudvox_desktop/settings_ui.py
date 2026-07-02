"""Ventana de configuración (tkinter: incluido con Python, sin dependencias).

Se abre desde el menú de la bandeja. Letra grande, controles simples,
botón "Probar voz". Guarda en config.json y aplica al instante (los
atajos de teclado se aplican al reiniciar).
"""

from __future__ import annotations

import threading

from loudvox.config import RECOMMENDED_VOICES, SUPPORTED_LANGUAGES, save

_open_lock = threading.Lock()
_is_open = False

LANG_NAMES = {"es": "Español", "en": "English", "it": "Italiano", "de": "Deutsch"}


def open_settings(app) -> None:
    """Abre la ventana (una sola a la vez), en su propio hilo con mainloop."""
    global _is_open
    with _open_lock:
        if _is_open:
            return
        _is_open = True
    threading.Thread(target=_run, args=(app,), daemon=True).start()


def _run(app) -> None:
    global _is_open
    try:
        _window(app)
    finally:
        _is_open = False


def _window(app) -> None:
    import tkinter as tk
    from tkinter import ttk

    cfg = app.cfg
    root = tk.Tk()
    root.title("LoudVox — Configuración")
    root.geometry("460x560")
    root.attributes("-topmost", True)

    style = ttk.Style(root)
    style.configure(".", font=("Segoe UI", 12))
    style.configure("TLabel", font=("Segoe UI", 12))
    style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"))

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)

    def row(r, text):
        ttk.Label(frame, text=text).grid(row=r, column=0, sticky="w", pady=6)

    # --- idioma ---
    row(0, "Idioma")
    lang_var = tk.StringVar(value=cfg.language)
    lang_box = ttk.Combobox(
        frame,
        state="readonly",
        values=[f"{code} — {LANG_NAMES[code]}" for code in SUPPORTED_LANGUAGES],
    )
    lang_box.set(f"{cfg.language} — {LANG_NAMES[cfg.language]}")
    lang_box.grid(row=0, column=1, sticky="ew", pady=6)

    # --- voz ---
    row(1, "Voz")
    installed = app.backend.list_voices()
    voice_box = ttk.Combobox(frame, state="readonly", values=installed or ["(sin voces)"])
    voice_box.set(cfg.resolved_voice() if installed else "(sin voces)")
    voice_box.grid(row=1, column=1, sticky="ew", pady=6)

    def sync_voice_options(_event=None):
        code = lang_box.get().split(" — ")[0]
        pref = {"es": ("es_",), "en": ("en_",), "it": ("it_",), "de": ("de_",)}[code]
        options = [v for v in installed if v.startswith(pref)] or installed
        voice_box["values"] = options or ["(sin voces)"]
        if options:
            rec = [v for v in RECOMMENDED_VOICES[code] if v in options]
            voice_box.set(rec[0] if rec else options[0])

    lang_box.bind("<<ComboboxSelected>>", sync_voice_options)

    # --- deslizadores ---
    def slider(r, text, frm, to, value, fmt):
        row(r, text)
        var = tk.DoubleVar(value=value)
        lbl = ttk.Label(frame, text=fmt(value))
        lbl.grid(row=r, column=2, padx=(8, 0))
        s = ttk.Scale(
            frame, from_=frm, to=to, variable=var,
            command=lambda _v: lbl.config(text=fmt(var.get())),
        )
        s.grid(row=r, column=1, sticky="ew", pady=6)
        return var

    speed_var = slider(2, "Velocidad", 0.5, 3.0, cfg.speed, lambda v: f"{v:.1f}×")
    volume_var = slider(3, "Volumen", 0.1, 2.0, cfg.volume, lambda v: f"{int(v*100)}%")
    pitch_var = slider(
        4, "Tono", -6, 6, cfg.pitch,
        lambda v: "normal" if abs(v) < 0.5 else (f"{v:+.0f} (grave)" if v < 0 else f"{v:+.0f} (agudo)"),
    )

    # --- probar ---
    status = ttk.Label(frame, text="", foreground="#666")
    status.grid(row=5, column=0, columnspan=3, sticky="w")

    SAMPLES = {
        "es": "Hola, así voy a sonar cuando lea para vos.",
        "en": "Hello, this is how I will sound when reading.",
        "it": "Ciao, ecco come suonerò durante la lettura.",
        "de": "Hallo, so werde ich beim Vorlesen klingen.",
    }

    def apply_to_cfg():
        cfg.language = lang_box.get().split(" — ")[0]
        if installed:
            cfg.voice = voice_box.get()
        cfg.speed = round(speed_var.get(), 2)
        cfg.volume = round(volume_var.get(), 2)
        cfg.pitch = round(pitch_var.get(), 1)

    def probar():
        apply_to_cfg()
        status.config(text="Generando prueba…")

        def go():
            try:
                app.reload_runtime()
                app._read(SAMPLES[cfg.language])
                status.config(text="Reproduciendo.")
            except Exception as exc:
                status.config(text=f"Error: {exc}")

        threading.Thread(target=go, daemon=True).start()

    def guardar():
        apply_to_cfg()
        try:
            save(cfg)
            app.reload_runtime()
            status.config(text="✔ Guardado y aplicado.")
        except Exception as exc:
            status.config(text=f"Error al guardar: {exc}")

    btns = ttk.Frame(frame)
    btns.grid(row=6, column=0, columnspan=3, pady=14)
    ttk.Button(btns, text="🔊 Probar voz", command=probar).pack(side="left", padx=6)
    ttk.Button(btns, text="💾 Guardar", command=guardar).pack(side="left", padx=6)
    ttk.Button(btns, text="Cerrar", command=root.destroy).pack(side="left", padx=6)

    # --- atajos (informativo + edición simple) ---
    ttk.Label(frame, text="Atajos de teclado", style="Header.TLabel").grid(
        row=7, column=0, columnspan=3, sticky="w", pady=(12, 4)
    )
    hk = cfg.hotkeys
    hk_vars = {}
    for i, (attr, label) in enumerate(
        [
            ("read_selection", "Leer selección"),
            ("read_from_here", "Leer portapapeles"),
            ("dictate", "Dictar"),
            ("stop", "Detener"),
        ]
    ):
        row(8 + i, label)
        var = tk.StringVar(value=getattr(hk, attr))
        ttk.Entry(frame, textvariable=var).grid(row=8 + i, column=1, sticky="ew", pady=3)
        hk_vars[attr] = var

    def guardar_atajos():
        from loudvox.config import validate_hotkey

        try:
            for attr, var in hk_vars.items():
                validate_hotkey(var.get())
            for attr, var in hk_vars.items():
                setattr(hk, attr, var.get().strip().lower())
            save(cfg)
            status.config(text="✔ Atajos guardados. Se aplican al reiniciar LoudVox.")
        except ValueError as exc:
            status.config(text=f"Atajo inválido: {exc}")

    ttk.Button(frame, text="Guardar atajos", command=guardar_atajos).grid(
        row=12, column=1, sticky="w", pady=8
    )

    frame.columnconfigure(1, weight=1)
    root.mainloop()
