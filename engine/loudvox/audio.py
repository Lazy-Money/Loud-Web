"""Post-procesado de audio: cambio de tono (pitch) sin alterar la velocidad.

Implementación con numpy puro (phase vocoder + remuestreo): sin dependencias
de DSP externas que auditar. Calidad muy buena en ±6 semitonos, el rango
útil para hacer una voz más grave o más aguda.
"""

from __future__ import annotations

import io
import wave

import numpy as np


def _stretch(x: np.ndarray, factor: float, n_fft: int = 1024, hop: int = 256) -> np.ndarray:
    """Estira la duración por ``factor`` manteniendo el tono (phase vocoder).

    Análisis con paso ``hop/factor`` y síntesis con paso ``hop``: la fase se
    propaga con la frecuencia instantánea medida sobre el paso de análisis
    REAL entre frames (usar el paso de síntesis ahí desafina el resultado).
    """
    window = np.hanning(n_fft)
    bin_freq = 2 * np.pi * np.arange(n_fft // 2 + 1) / n_fft  # rad/muestra
    phase = np.zeros(n_fft // 2 + 1)
    last_spec = None
    last_pos = 0
    out = []
    pos = 0.0
    while int(pos) + n_fft < len(x):
        ipos = int(pos)
        frame = x[ipos: ipos + n_fft] * window
        spec = np.fft.rfft(frame)
        mag = np.abs(spec)
        if last_spec is None:
            phase = np.angle(spec)
        else:
            ana_step = ipos - last_pos  # paso de análisis real (muestras)
            expected = np.angle(last_spec) + bin_freq * ana_step
            deviation = np.angle(spec) - expected
            deviation -= 2 * np.pi * np.round(deviation / (2 * np.pi))
            true_freq = bin_freq + deviation / max(ana_step, 1)
            phase = phase + hop * true_freq
        out.append(mag * np.exp(1j * phase))
        last_spec = spec
        last_pos = ipos
        pos += hop / factor
    if not out:
        return x.copy()

    result = np.zeros(len(out) * hop + n_fft)
    norm = np.zeros_like(result)
    for i, spec in enumerate(out):
        frame = np.fft.irfft(spec) * window
        result[i * hop: i * hop + n_fft] += frame
        norm[i * hop: i * hop + n_fft] += window**2
    norm[norm < 1e-8] = 1.0
    return result / norm


def pitch_shift(samples: np.ndarray, semitones: float) -> np.ndarray:
    """Cambia el tono de ``samples`` (float) en semitonos, misma duración."""
    if abs(semitones) < 0.01:
        return samples
    factor = 2 ** (semitones / 12)
    stretched = _stretch(samples.astype(np.float64), factor)
    # Remuestrear leyendo el audio estirado a paso `factor` exacto: el tono
    # cambia por `factor` y la duración vuelve a la original. (Usar la
    # longitud real del estirado arrastraría los redondeos del vocoder.)
    idx = np.minimum(np.arange(len(samples)) * factor, len(stretched) - 1)
    return np.interp(idx, np.arange(len(stretched)), stretched)


def apply_pitch(wav_bytes: bytes, semitones: float) -> bytes:
    """Aplica pitch_shift a un WAV completo (int16 mono) en memoria."""
    if abs(semitones) < 0.01:
        return wav_bytes
    with wave.open(io.BytesIO(wav_bytes)) as w:
        params = w.getparams()
        if params.sampwidth != 2 or params.nchannels != 1:
            return wav_bytes  # formato inesperado: devolver sin tocar
        data = np.frombuffer(w.readframes(params.nframes), dtype=np.int16)

    shifted = pitch_shift(data.astype(np.float64) / 32768.0, semitones)
    shifted = np.clip(shifted * 32768.0, -32768, 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(params.framerate)
        w.writeframes(shifted.tobytes())
    return buf.getvalue()
