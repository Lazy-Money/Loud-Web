"""Tests del lector por párrafos del visor (motor real + sink falso)."""

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "engine"))

import pytest

from loudvox.config import Config
from loudvox_desktop.player import Player
from loudvox_desktop.viewer.reader import ParagraphReader


class FakeSink:
    def __init__(self, per_play=0.05):
        self.n = 0
        self.per_play = per_play
        self._stop = threading.Event()

    def play(self, wav):
        self._stop.clear()
        self.n += 1
        self._stop.wait(self.per_play)

    def stop(self):
        self._stop.set()


def wait_for(cond, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if cond():
            return True
        time.sleep(0.05)
    return False


VOICES = Path(__file__).resolve().parent.parent.parent / "engine" / "test-voices"
pytestmark = pytest.mark.skipif(
    not (VOICES / "es_ES-davefx-medium.onnx").exists(),
    reason="voz de prueba no instalada",
)


def make_reader(events, sink=None):
    cfg = Config(voice="es_ES-davefx-medium", voices_dir=str(VOICES))
    sink = sink or FakeSink()
    reader = ParagraphReader(
        cfg,
        on_paragraph=lambda i: events.append(("para", i)),
        on_end=lambda: events.append(("end",)),
    )
    reader.player = Player(reader._synthesize, sink=sink)
    return reader, sink


def test_lee_todos_los_parrafos_en_orden_y_avisa_fin():
    events = []
    reader, sink = make_reader(events)
    reader.read(["Hola mundo.", "Segundo párrafo corto.", "Tercero."])
    assert wait_for(lambda: ("end",) in events, timeout=90)
    paras = [i for kind, *rest in events if kind == "para" for i in rest]
    assert paras == [0, 1, 2]
    assert sink.n == 3


def test_desde_indice_intermedio():
    events = []
    reader, _ = make_reader(events)
    reader.read(["Cero.", "Uno.", "Dos."], start_index=1)
    assert wait_for(lambda: ("end",) in events, timeout=90)
    paras = [i for kind, *rest in events if kind == "para" for i in rest]
    assert paras == [1, 2]


def test_parrafo_largo_se_trocea_pero_resalta_una_vez():
    events = []
    reader, sink = make_reader(events)
    largo = "Una frase con contenido. " * 30  # > max_chars -> varios chunks
    reader.read([largo])
    assert wait_for(lambda: ("end",) in events, timeout=120)
    paras = [i for kind, *rest in events if kind == "para" for i in rest]
    assert paras == [0]          # un solo resaltado
    assert sink.n > 1            # pero varios fragmentos de audio


def test_stop_corta_y_no_avisa_fin():
    events = []
    reader, sink = make_reader(events, sink=FakeSink(per_play=0.5))
    reader.read(["Primero.", "Segundo.", "Tercero.", "Cuarto.", "Quinto."])
    assert wait_for(lambda: sink.n >= 1, timeout=60)
    reader.stop()
    time.sleep(1.0)
    assert ("end",) not in events
    assert sink.n < 5


def test_lista_vacia_avisa_fin_inmediato():
    events = []
    reader, _ = make_reader(events)
    reader.read([])
    assert wait_for(lambda: ("end",) in events, timeout=5)
