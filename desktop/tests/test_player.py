import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loudvox_desktop.player import Player


class FakeSink:
    """Simula reproducción con duración controlable."""

    def __init__(self, per_play=0.05):
        self.played = []
        self.per_play = per_play
        self._stop = threading.Event()

    def play(self, wav):
        self._stop.clear()  # como el sink real: cada play arranca limpio
        self.played.append(wav)
        self._stop.wait(self.per_play)

    def stop(self):
        self._stop.set()


def test_reproduce_en_orden():
    sink = FakeSink()
    player = Player(lambda t: f"wav:{t}".encode(), sink=sink)
    player.play_text_chunks(["uno", "dos", "tres"])
    player.wait(timeout=5)
    assert sink.played == [b"wav:uno", b"wav:dos", b"wav:tres"]

def test_stop_corta_la_cola():
    sink = FakeSink(per_play=0.3)
    player = Player(lambda t: t.encode(), sink=sink)
    player.play_text_chunks([f"c{i}" for i in range(20)])
    time.sleep(0.4)
    player.stop()
    player.wait(timeout=5)
    assert len(sink.played) < 20

def test_error_de_sintesis_no_detiene_el_resto():
    def synth(t):
        if t == "malo":
            raise RuntimeError("boom")
        return t.encode()

    sink = FakeSink()
    player = Player(synth, sink=sink)
    player.play_text_chunks(["bueno", "malo", "final"])
    player.wait(timeout=5)
    assert sink.played == [b"bueno", b"final"]

def test_nueva_lectura_cancela_anterior():
    sink = FakeSink(per_play=0.3)
    player = Player(lambda t: t.encode(), sink=sink)
    player.play_text_chunks([f"a{i}" for i in range(10)])
    time.sleep(0.35)
    player.play_text_chunks(["b0"])
    player.wait(timeout=5)
    assert b"b0" in sink.played
    assert sum(1 for p in sink.played if p.startswith(b"a")) < 10

def test_on_chunk_callback():
    seen = []
    sink = FakeSink()
    player = Player(lambda t: t.encode(), sink=sink)
    player.play_text_chunks(["x", "y"], on_chunk=lambda i, c: seen.append((i, c)))
    player.wait(timeout=5)
    assert seen == [(0, "x"), (1, "y")]


def test_wav_duration():
    import io, wave
    from loudvox_desktop.player import wav_duration

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x00\x00" * 22050)  # 1 segundo
    assert abs(wav_duration(buf.getvalue()) - 1.0) < 0.01
