import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loudvox_desktop.stt import DictationController


class FakeRecorder:
    def __init__(self):
        self.active = False

    def start(self):
        self.active = True

    def stop(self):
        self.active = False
        return [0.0] * 16000  # 1 "segundo" de audio


class BrokenRecorder:
    def start(self):
        raise OSError("sin micrófono")

    def stop(self):
        return []


def wait_for(cond, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cond():
            return True
        time.sleep(0.02)
    return False


def make(transcribe=None, recorder=None):
    written, events = [], []
    ctl = DictationController(
        recorder=recorder or FakeRecorder(),
        transcribe=transcribe or (lambda audio: "hola mundo"),
        write=written.append,
        feedback=events.append,
    )
    return ctl, written, events


def test_ciclo_completo():
    ctl, written, events = make()
    ctl.toggle()
    assert ctl.recording and events == ["start"]
    ctl.toggle()
    assert not ctl.recording
    assert wait_for(lambda: written == ["hola mundo"])
    assert events == ["start", "stop", "done"]


def test_transcripcion_vacia_no_escribe():
    ctl, written, events = make(transcribe=lambda a: "")
    ctl.toggle(); ctl.toggle()
    assert wait_for(lambda: "empty" in events)
    assert written == []


def test_error_de_transcripcion():
    def boom(a):
        raise RuntimeError("modelo roto")

    ctl, written, events = make(transcribe=boom)
    ctl.toggle(); ctl.toggle()
    assert wait_for(lambda: "error" in events)
    assert written == []
    assert not ctl.recording  # el estado quedó consistente


def test_microfono_roto():
    ctl, written, events = make(recorder=BrokenRecorder())
    ctl.toggle()
    assert not ctl.recording
    assert events == ["error"]


def test_toggles_concurrentes_no_rompen():
    ctl, written, events = make()
    threads = [threading.Thread(target=ctl.toggle) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    # 10 toggles -> termina no-grabando, sin excepciones
    assert not ctl.recording


def test_app_no_graba_hasta_que_el_modelo_este_listo(monkeypatch):
    """El primer Ctrl+Alt+D dispara la carga; recién tras el aviso de LISTO
    se acepta grabar (evita dictados perdidos durante la descarga)."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "engine"))
    from loudvox_desktop.app import DesktopApp

    app = DesktopApp.__new__(DesktopApp)  # sin cargar motor TTS
    from loudvox.config import Config

    app.cfg = Config()
    app._stt_state = "off"
    app._icon = None
    app._dictation = None

    class FakeTranscriber:
        def preload(self):
            pass

    events = []

    def fake_build():
        app._dictation = type(
            "D", (), {"toggle": lambda s: events.append("toggle"),
                      "recording": False}
        )()
        return FakeTranscriber()

    monkeypatch.setattr(app, "_build_dictation", fake_build)
    monkeypatch.setattr(app, "_beep", lambda e: events.append(f"beep:{e}"))

    app.toggle_dictation()  # dispara la carga en segundo plano
    assert wait_for(lambda: app._stt_state == "ready")
    assert "toggle" not in events  # no grabó durante la carga

    app.toggle_dictation()  # ahora sí
    assert "toggle" in events


def test_transcriber_real_tiene_su_api_completa():
    """Regresión del bug 'Transcriber object has no attribute transcribe':
    una edición rompió la clase real y los tests con fakes no lo vieron.
    Este test instancia la clase VERDADERA (sin cargar modelos)."""
    from loudvox_desktop.stt import Recorder, Transcriber, _CudaDlls

    t = Transcriber(model_size="small", language="es", device="cpu")
    assert callable(t.transcribe)
    assert callable(t.preload)
    assert callable(t._load)
    assert t.compute == "int8" and t.dll_dir == ""

    # configs viejas pueden traer None: no debe explotar
    t2 = Transcriber(model_size=None, language=None, device=None, dll_dir=None)
    assert t2.model_size == "small" and t2.device == "cpu" and t2.dll_dir == ""

    # la clase auxiliar de CUDA es independiente y tiene su propia API
    c = _CudaDlls("/no/existe", "")
    assert callable(c.preflight)
    assert not hasattr(Transcriber, "preflight"), "las clases se mezclaron"
    assert not hasattr(_CudaDlls, "transcribe"), "las clases se mezclaron"

    assert callable(Recorder().stop)


def test_app_build_dictation_cablea_la_clase_real(monkeypatch):
    """El wiring de DesktopApp debe construir un DictationController cuyo
    transcribe apunte al Transcriber real."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "engine"))
    from loudvox.config import Config
    from loudvox_desktop.app import DesktopApp

    app = DesktopApp.__new__(DesktopApp)
    app.cfg = Config()
    app._dictation = None
    transcriber = app._build_dictation()
    assert callable(transcriber.transcribe) and callable(transcriber.preload)
    assert app._dictation is not None
    # el controlador quedó conectado al método real
    assert app._dictation._transcribe == transcriber.transcribe
