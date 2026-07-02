"""Ventana de configuración (tkinter: incluido con Python, sin dependencias).

Se abre desde el menú de la bandeja. Estructura: Motor → Idioma → Voz
(con región y género), deslizadores de velocidad/volumen/tono, botón
"Probar voz". Guarda en config.json y aplica al instante (los atajos se
aplican al reiniciar).
"""

from __future__ import annotations

import threading

from loudvox.catalog import list_catalog
from loudvox.config import SUPPORTED_LANGUAGES, save

_open_lock = threading.Lock()
_is_open = False

LANG_NAMES = {"es": "Español", "en": "English", "it": "Italiano", "de": "Deutsch"}
ENGINE_LABELS = {"piper": "Piper (rápido)", "kokoro": "Kokoro (premium)"}

SAMPLES = {
    "es": "Hola, así voy a sonar cuando lea para vos.",
    "en": "Hello, this is how I will sound when reading.",
    "it": "Ciao, ecco come suonerò durante la lettura.",
    "de": "Hallo, so werde ich beim Vorlesen klingen.",
}


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
    catalog = list_catalog(cfg.resolved_voices_dir())
    engines = sorted({e["engine"] for e in catalog}) or ["piper"]

    root = tk.Tk()
    root.title("LoudVox — Configuración")
    root.geometry("480x620")
    root.attributes("-topmost", True)

    style = ttk.Style(root)
    style.configure(".", font=("Segoe UI", 12))
    style.configure("TLabel", font=("Segoe UI", 12))
    style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"))

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)

    def row(r, text):
        ttk.Label(frame, text=text).grid(row=r, column=0, sticky="w", pady=6)

    # --- motor ---
    row(0, "Motor")
    engine_box = ttk.Combobox(
        frame, state="readonly",
        values=[ENGINE_LABELS.get(e, e) for e in engines],
    )
    current_engine = cfg.engine if cfg.engine in engines else engines[0]
    engine_box.set(ENGINE_LABELS.get(current_engine, current_engine))
    engine_box.grid(row=0, column=1, sticky="ew", pady=6)

    # --- idioma ---
    row(1, "Idioma")
    lang_box = ttk.Combobox(
        frame, state="readonly",
        values=[f"{LANG_NAMES[c]} ({c})" for c in SUPPORTED_LANGUAGES],
    )
    lang_box.set(f"{LANG_NAMES[cfg.language]} ({cfg.language})")
    lang_box.grid(row=1, column=1, sticky="ew", pady=6)

    # --- voz (región + nombre + género, desde el catálogo) ---
    row(2, "Voz")
    voice_box = ttk.Combobox(frame, state="readonly")
    voice_box.grid(row=2, column=1, sticky="ew", pady=6)
    visible_entries: list[dict] = []

    def selected_engine() -> str:
        label = engine_box.get()
        for code, lbl in ENGINE_LABELS.items():
            if lbl == label:
                return code
        return label

    def selected_lang() -> str:
        return lang_box.get().rsplit("(", 1)[1].rstrip(")")

    def sync_voices(_event=None):
        nonlocal visible_entries
        eng, lang = selected_engine(), selected_lang()
        visible_entries = [e for e in catalog if e["engine"] == eng and e["lang"] == lang]
        if visible_entries:
            voice_box["values"] = [e["label"] for e in visible_entries]
            # preseleccionar la voz configurada si está en la lista
            current = [
                e for e in visible_entries
                if e["id"] == cfg.voice
                and (e["speaker"] is None
                     or e["speaker"] == cfg.voice_overrides.get(cfg.voice, {}).get("speaker"))
            ]
            voice_box.set(current[0]["label"] if current else visible_entries[0]["label"])
        else:
            voice_box["values"] = ["(no hay voces de este motor/idioma instaladas)"]
            voice_box.current(0)

    engine_box.bind("<<ComboboxSelected>>", sync_voices)
    lang_box.bind("<<ComboboxSelected>>", sync_voices)
    sync_voices()

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

    speed_var = slider(3, "Velocidad", 0.5, 3.0, cfg.speed, lambda v: f"{v:.1f}×")
    volume_var = slider(4, "Volumen", 0.1, 2.0, cfg.volume, lambda v: f"{int(v*100)}%")
    pitch_var = slider(
        5, "Tono", -6, 6, cfg.pitch,
        lambda v: "normal" if abs(v) < 0.5 else (f"{v:+.0f} (grave)" if v < 0 else f"{v:+.0f} (agudo)"),
    )

    status = ttk.Label(frame, text="", foreground="#666", wraplength=420)
    status.grid(row=6, column=0, columnspan=3, sticky="w")

    def chosen_entry() -> dict | None:
        label = voice_box.get()
        for e in visible_entries:
            if e["label"] == label:
                return e
        return None

    def apply_to_cfg() -> bool:
        entry = chosen_entry()
        if entry is None:
            status.config(
                text="No hay voces para ese motor/idioma. Descargá con: "
                     f"loudvox download {selected_lang()}"
            )
            return False
        cfg.engine = entry["engine"]
        cfg.language = selected_lang()
        cfg.voice = entry["id"]
        if entry["speaker"] is not None:
            cfg.voice_overrides.setdefault(entry["id"], {})["speaker"] = entry["speaker"]
        elif cfg.voice_overrides.get(entry["id"], {}).get("speaker") is not None:
            cfg.voice_overrides[entry["id"]].pop("speaker", None)
        cfg.speed = round(speed_var.get(), 2)
        cfg.volume = round(volume_var.get(), 2)
        cfg.pitch = round(pitch_var.get(), 1)
        return True

    def probar():
        if not apply_to_cfg():
            return
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
        if not apply_to_cfg():
            return
        try:
            save(cfg)
            app.reload_runtime()
            status.config(text="✔ Guardado y aplicado.")
        except Exception as exc:
            status.config(text=f"Error al guardar: {exc}")

    btns = ttk.Frame(frame)
    btns.grid(row=7, column=0, columnspan=3, pady=14)
    ttk.Button(btns, text="🔊 Probar voz", command=probar).pack(side="left", padx=6)
    ttk.Button(btns, text="💾 Guardar", command=guardar).pack(side="left", padx=6)
    ttk.Button(btns, text="Cerrar", command=root.destroy).pack(side="left", padx=6)

    # --- atajos ---
    ttk.Label(frame, text="Atajos de teclado", style="Header.TLabel").grid(
        row=8, column=0, columnspan=3, sticky="w", pady=(12, 4)
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
        row(9 + i, label)
        var = tk.StringVar(value=getattr(hk, attr))
        ttk.Entry(frame, textvariable=var).grid(row=9 + i, column=1, sticky="ew", pady=3)
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
        row=13, column=1, sticky="w", pady=8
    )

    frame.columnconfigure(1, weight=1)
    root.mainloop()
