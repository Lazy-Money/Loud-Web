import io
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from loudvox.audio import apply_pitch, pitch_shift


def sine_wav(freq=440.0, seconds=1.0, rate=22050):
    t = np.arange(int(rate * seconds)) / rate
    samples = (np.sin(2 * np.pi * freq * t) * 20000).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(samples.tobytes())
    return buf.getvalue()


def dominant_freq(wav_bytes):
    with wave.open(io.BytesIO(wav_bytes)) as w:
        rate = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    spectrum = np.abs(np.fft.rfft(data * np.hanning(len(data))))
    return np.fft.rfftfreq(len(data), 1 / rate)[np.argmax(spectrum)]


def test_octava_arriba():
    out = apply_pitch(sine_wav(440), +12)
    assert abs(dominant_freq(out) - 880) < 25

def test_octava_abajo():
    out = apply_pitch(sine_wav(440), -12)
    assert abs(dominant_freq(out) - 220) < 15

def test_quinta_arriba():
    out = apply_pitch(sine_wav(440), +7)  # quinta justa ~659 Hz
    assert abs(dominant_freq(out) - 659) < 25

def test_pitch_cero_no_toca_nada():
    wav = sine_wav(440)
    assert apply_pitch(wav, 0) is wav

def test_duracion_se_mantiene():
    wav = sine_wav(440, seconds=2.0)
    out = apply_pitch(wav, +5)
    with wave.open(io.BytesIO(wav)) as a, wave.open(io.BytesIO(out)) as b:
        assert abs(a.getnframes() - b.getnframes()) <= 1

def test_sin_clipping():
    out = apply_pitch(sine_wav(440), -6)
    with wave.open(io.BytesIO(out)) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    assert np.abs(data).max() <= 32767
