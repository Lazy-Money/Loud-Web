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
