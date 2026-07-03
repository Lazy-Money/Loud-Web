"""Genera los iconos de LoudVox (reproducible y auditable, sin binarios opacos).

Corré ``python -m loudvox_desktop.assets.generate_icons`` para regenerar los
.ico/.png a partir de estas formas dibujadas con PIL. Se commitean los
resultados para que el instalador y PyInstaller los usen sin depender de PIL.

- loudvox        : cuadrado naranja + triangulo play (el mismo de la bandeja).
- loudvox_viewer : misma familia naranja, pero con un documento y un pequeno
                   play, para distinguir el visor del cliente principal.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ORANGE = (255, 140, 0, 255)
WHITE = (255, 255, 255, 255)
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
S = 256  # se dibuja grande y el .ico baja de escala


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([8, 8, S - 8, S - 8], radius=48, fill=ORANGE)
    return img, d


def make_main() -> Image.Image:
    """Play blanco sobre naranja (idéntico en proporciones al de la bandeja)."""
    img, d = _canvas()
    d.polygon([(96, 72), (96, 184), (192, 128)], fill=WHITE)
    return img


def make_viewer() -> Image.Image:
    """Documento blanco con renglones y un pequeño play (lectura de docs)."""
    img, d = _canvas()
    # Hoja con esquina doblada
    page = [(70, 46), (150, 46), (188, 84), (188, 210), (70, 210)]
    d.polygon(page, fill=WHITE)
    d.polygon([(150, 46), (188, 84), (150, 84)], fill=(230, 230, 230, 255))
    # Renglones de texto (naranjas)
    for y in (104, 128, 152, 176):
        d.rounded_rectangle([92, y, 166, y + 9], radius=4, fill=ORANGE)
    # Badge de play, abajo a la derecha
    d.ellipse([150, 150, 214, 214], fill=ORANGE, outline=WHITE, width=6)
    d.polygon([(174, 166), (174, 198), (196, 182)], fill=WHITE)
    return img


def save(img: Image.Image, name: str) -> None:
    img.save(HERE / f"{name}.png")
    img.save(HERE / f"{name}.ico", sizes=ICO_SIZES)
    print("escrito:", name + ".png /", name + ".ico")


def main() -> None:
    save(make_main(), "loudvox")
    save(make_viewer(), "loudvox_viewer")


if __name__ == "__main__":
    main()
