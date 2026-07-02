# Loud

Lector de pantalla (TTS) y dictado por voz (STT) **100% local y auditable**.
Sin nube, sin telemetría, sin límites de caracteres. Windows y Linux.

## Objetivo

1. **Leer texto en voz alta** con voces IA naturales y compactas:
   - Seleccionás texto y presionás una combinación de teclas → lo lee.
   - Otra combinación → lee desde ese punto en adelante.
   - En el navegador (Brave/Chrome) vía extensión, y en PDFs, docs, txt, md
     vía cliente de escritorio.
2. **Dictar por voz**: te posicionás sobre un campo de texto, presionás la
   combinación, hablás, y escribe lo que dijiste.

Idiomas soportados: **español, inglés, italiano y alemán**.

## Principios

- **Todo corre en tu máquina.** La única descarga es la de los modelos de voz,
  una sola vez y a pedido tuyo.
- **Código auditable, dependencias fijadas.** Sabés exactamente qué corre.
- **PC modesta primero.** Piper como motor por defecto (tiempo real en CPU);
  motores más pesados (Kokoro, clonación de voz) son opcionales y a elección
  del usuario.
- **Hotkeys personalizables** (mínimo 2 teclas, sin restricciones).
- **Diccionarios por idioma** para expandir abreviaturas ("10 m" → "10 metros"),
  editables por el usuario.

## Estructura

```
engine/      Motor TTS/STT local (Python). API en 127.0.0.1 + CLI.   [Fase 1 ✅]
extension/   Extensión Manifest V3 para Brave/Chrome.                [Fase 2]
desktop/     Cliente de escritorio: hotkeys globales, PDFs, dictado. [Fases 3-4]
colab/       Notebook para entrenar tu propia voz (export .onnx).    [Fase 5b]
Readvox/     Material de referencia (snapshot de readvox.com).
```

## Hoja de ruta

| Fase | Entregable | Estado |
|---|---|---|
| 1 | Motor TTS: Piper, 4 idiomas, velocidad, diccionarios, API local, CLI | ✅ |
| 2 | Extensión Brave: leer selección, leer desde aquí, resaltado | ✅ |
| 3 | Cliente escritorio: hotkeys globales, portapapeles, PDF/txt/md | ⏳ |
| 4 | Dictado: whisper.cpp local, escritura en el input activo | ⏳ |
| 5 | Tono de voz (grave/agudo), motor Kokoro opcional | ⏳ |
| 5b | Clonación de voz: entrenamiento en Colab gratuito → voz local `.onnx` | ⏳ |

## Empezar

Ver [engine/README.md](engine/README.md).

## Referencias estudiadas

- [Readvox](https://readvox.com) — UX de lectura (comercial, nube).
- [Verbify-TTS](https://github.com/MattePalte/Verbify-TTS) — hotkeys a nivel OS + diccionario CSV (MIT).
- [OpenWhispr](https://github.com/OpenWhispr/openwhispr) — arquitectura de dictado local (MIT).
- [Piper](https://github.com/OHF-Voice/piper1-gpl) — TTS liviano (GPL-3, por incluir espeak-ng). Motor por defecto.
- [Chatterbox](https://github.com/resemble-ai/chatterbox) — clonación de voz (MIT). Módulo opcional.
