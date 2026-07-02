"""Ventana de configuración (tkinter: incluido con Python, sin dependencias).

Estructura: Motor → Idioma → Voz (región y género) + deslizadores + dictado
(modelo, CPU/GPU, con reinicio) + atajos. El idioma del menú es elegible y
por defecto sigue al idioma elegido en la instalación.
"""

from __future__ import annotations

import threading

from loudvox.catalog import list_catalog
from loudvox.config import SUPPORTED_LANGUAGES, save

from .i18n import strings_for

_open_lock = threading.Lock()
_is_open = False

LANG_NAMES = {"es": "Español", "en": "English", "it": "Italiano", "de": "Deutsch"}
ENGINE_LABELS = {"piper": "Piper", "kokoro": "Kokoro"}
# large-v2 y no v3: la v3 tiene problemas conocidos (más alucinaciones y
# repeticiones, especialmente fuera del inglés); v2 es la estable de facto.
STT_MODELS = ["base", "small", "medium", "large-v2"]


def open_settings(app) -> None:
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
    t = strings_for(cfg.resolved_ui_language())
    catalog = list_catalog(cfg.resolved_voices_dir())
    engines = sorted({e["engine"] for e in catalog}) or ["piper"]

    def refresh_catalog():
        nonlocal catalog
        catalog = list_catalog(cfg.resolved_voices_dir())

    root = tk.Tk()
    root.title(t["settings_title"])
    root.geometry("600x780")
    root.attributes("-topmost", True)

    style = ttk.Style(root)
    style.configure(".", font=("Segoe UI", 12))
    style.configure("TLabel", font=("Segoe UI", 12))
    style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"))

    outer = ttk.Frame(root, padding=16)
    outer.pack(fill="both", expand=True)
    frame = outer
    r = 0

    def row(text):
        nonlocal r
        ttk.Label(frame, text=text).grid(row=r, column=0, sticky="w", pady=5)

    def nextrow():
        nonlocal r
        r += 1

    status = None  # se define más abajo; funciones lo usan vía closure

    # --- idioma del menú -----------------------------------------------------
    row(t["menu_lang"])
    ui_lang_box = ttk.Combobox(
        frame, state="readonly",
        values=[f"{LANG_NAMES[c]} ({c})" for c in SUPPORTED_LANGUAGES],
    )
    ui_lang_box.set(f"{LANG_NAMES[cfg.resolved_ui_language()]} ({cfg.resolved_ui_language()})")
    ui_lang_box.grid(row=r, column=1, sticky="ew", pady=5)
    nextrow()

    def on_ui_lang(_e=None):
        cfg.ui_language = ui_lang_box.get().rsplit("(", 1)[1].rstrip(")")
        save(cfg)
        root.destroy()
        open_settings(app)  # reabrir traducida

    ui_lang_box.bind("<<ComboboxSelected>>", on_ui_lang)

    # --- motor ---------------------------------------------------------------
    row(t["engine"])
    engine_box = ttk.Combobox(
        frame, state="readonly", values=[ENGINE_LABELS.get(e, e) for e in engines]
    )
    current_engine = cfg.engine if cfg.engine in engines else engines[0]
    engine_box.set(ENGINE_LABELS.get(current_engine, current_engine))
    engine_box.grid(row=r, column=1, sticky="ew", pady=5)
    nextrow()

    # --- idioma de lectura ----------------------------------------------------
    row(t["language"])
    lang_box = ttk.Combobox(
        frame, state="readonly",
        values=[f"{LANG_NAMES[c]} ({c})" for c in SUPPORTED_LANGUAGES],
    )
    lang_box.set(f"{LANG_NAMES[cfg.language]} ({cfg.language})")
    lang_box.grid(row=r, column=1, sticky="ew", pady=5)
    nextrow()

    # --- voz -------------------------------------------------------------------
    row(t["voice"])
    voice_box = ttk.Combobox(frame, state="readonly")
    voice_box.grid(row=r, column=1, sticky="ew", pady=5)
    nextrow()
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
            current = [
                e for e in visible_entries
                if e["id"] == cfg.voice
                and (e["speaker"] is None
                     or e["speaker"] == cfg.voice_overrides.get(cfg.voice, {}).get("speaker"))
            ]
            voice_box.set(current[0]["label"] if current else visible_entries[0]["label"])
        else:
            voice_box["values"] = ["—"]
            voice_box.current(0)

    engine_box.bind("<<ComboboxSelected>>", sync_voices)
    lang_box.bind("<<ComboboxSelected>>", sync_voices)
    sync_voices()

    # --- deslizadores ------------------------------------------------------------
    def slider(text, frm, to, value, fmt):
        nonlocal r
        row(text)
        var = tk.DoubleVar(value=value)
        lbl = ttk.Label(frame, text=fmt(value))
        lbl.grid(row=r, column=2, padx=(8, 0))
        s = ttk.Scale(frame, from_=frm, to=to, variable=var,
                      command=lambda _v: lbl.config(text=fmt(var.get())))
        s.grid(row=r, column=1, sticky="ew", pady=5)
        nextrow()
        return var

    speed_var = slider(t["speed"], 0.5, 3.0, cfg.speed, lambda v: f"{v:.1f}×")
    volume_var = slider(t["volume"], 0.1, 2.0, cfg.volume, lambda v: f"{int(v*100)}%")
    pitch_var = slider(
        t["pitch"], -6, 6, cfg.pitch,
        lambda v: t["normal"] if abs(v) < 0.5
        else (f"{v:+.0f} ({t['low']})" if v < 0 else f"{v:+.0f} ({t['high']})"),
    )

    status = ttk.Label(frame, text="", foreground="#666", wraplength=540)
    status.grid(row=r, column=0, columnspan=3, sticky="w")
    nextrow()

    def chosen_entry():
        label = voice_box.get()
        for e in visible_entries:
            if e["label"] == label:
                return e
        return None

    def apply_to_cfg() -> bool:
        entry = chosen_entry()
        if entry is None:
            status.config(text=t["no_voices"])
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
        status.config(text=t["gen_test"])

        def go():
            try:
                app.reload_runtime()
                app._read(strings_for(cfg.language)["sample"])
                status.config(text=t["playing"])
            except Exception as exc:
                status.config(text=f"Error: {exc}")

        threading.Thread(target=go, daemon=True).start()

    def descargar_idioma():
        lang = selected_lang()
        status.config(text=t["downloading"])

        def go():
            try:
                from loudvox.downloader import download_language

                download_language(lang, cfg.resolved_voices_dir())
                refresh_catalog()
                app.reload_runtime()
                root.after(0, sync_voices)
                status.config(text=t["downloaded"])
            except Exception as exc:
                status.config(text=f"Error: {exc}")

        threading.Thread(target=go, daemon=True).start()

    # --- dictado -------------------------------------------------------------
    ttk.Label(frame, text=t["stt_header"], style="Header.TLabel").grid(
        row=r, column=0, columnspan=3, sticky="w", pady=(12, 4)
    )
    nextrow()

    row(t["stt_model"])
    is_path = cfg.stt_model not in STT_MODELS
    stt_box = ttk.Combobox(frame, state="readonly", values=STT_MODELS + [t["stt_custom"]])
    stt_box.set(t["stt_custom"] if is_path else cfg.stt_model)
    stt_box.grid(row=r, column=1, sticky="ew", pady=5)
    nextrow()

    stt_path_var = tk.StringVar(value=cfg.stt_model if is_path else "")
    stt_path_entry = ttk.Entry(frame, textvariable=stt_path_var)
    stt_path_entry.grid(row=r, column=1, sticky="ew", pady=3)
    nextrow()

    row(t["stt_device"])
    device_box = ttk.Combobox(frame, state="readonly", values=["CPU", "GPU (CUDA)"])
    device_box.set("GPU (CUDA)" if cfg.stt_device == "cuda" else "CPU")
    device_box.grid(row=r, column=1, sticky="ew", pady=5)
    nextrow()

    restart_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(frame, text=t["restart_note"], variable=restart_var).grid(
        row=r, column=0, columnspan=3, sticky="w", pady=3
    )
    nextrow()

    def stt_changed() -> bool:
        model = stt_path_var.get().strip() if stt_box.get() == t["stt_custom"] else stt_box.get()
        device = "cuda" if device_box.get().startswith("GPU") else "cpu"
        changed = model != cfg.stt_model or device != cfg.stt_device
        cfg.stt_model = model or cfg.stt_model
        cfg.stt_device = device
        return changed

    def guardar():
        if not apply_to_cfg():
            return
        need_restart = stt_changed()
        try:
            save(cfg)
            app.reload_runtime()
            status.config(text=t["saved"])
            if need_restart and restart_var.get():
                root.destroy()
                app.restart()
        except Exception as exc:
            status.config(text=f"Error: {exc}")

    btns = ttk.Frame(frame)
    btns.grid(row=r, column=0, columnspan=3, pady=12)
    nextrow()
    ttk.Button(btns, text=t["test"], command=probar).pack(side="left", padx=5)
    ttk.Button(btns, text=t["save"], command=guardar).pack(side="left", padx=5)
    ttk.Button(btns, text=t["dl_lang"], command=descargar_idioma).pack(side="left", padx=5)
    ttk.Button(btns, text=t["close"], command=root.destroy).pack(side="left", padx=5)

    # --- atajos ----------------------------------------------------------------
    ttk.Label(frame, text=t["hotkeys"], style="Header.TLabel").grid(
        row=r, column=0, columnspan=3, sticky="w", pady=(10, 4)
    )
    nextrow()
    hk = cfg.hotkeys
    hk_vars = {}
    for attr, label_key in [
        ("read_selection", "hk_read"),
        ("read_from_here", "hk_clip"),
        ("dictate", "hk_dictate"),
        ("stop", "hk_stop"),
    ]:
        row(t[label_key])
        var = tk.StringVar(value=getattr(hk, attr))
        ttk.Entry(frame, textvariable=var).grid(row=r, column=1, sticky="ew", pady=3)
        hk_vars[attr] = var
        nextrow()

    def guardar_atajos():
        from loudvox.config import validate_hotkey

        try:
            for attr, var in hk_vars.items():
                validate_hotkey(var.get())
            for attr, var in hk_vars.items():
                setattr(hk, attr, var.get().strip().lower())
            save(cfg)
            status.config(text=t["saved_hotkeys"])
        except ValueError as exc:
            status.config(text=f"{t['invalid_hotkey']} {exc}")

    ttk.Button(frame, text=t["save_hotkeys"], command=guardar_atajos).grid(
        row=r, column=1, sticky="w", pady=8
    )

    frame.columnconfigure(1, weight=1)
    root.mainloop()
