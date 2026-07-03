"""E2E headless de la UI del visor (Playwright + Chromium).

Dos niveles:
  1. UI sola con una API simulada en JS (pestañas, recientes, resaltado,
     botones): rápido y sin motor.
  2. Punta a punta: la página habla con el ``ViewerApi`` REAL (bridge.py),
     que extrae párrafos de un PDF real y lee con el motor real (voz Piper),
     solo que el audio va a un sink falso (el sandbox no tiene parlantes).
     Los callbacks Python→JS pasan por una cola y se inyectan con
     ``page.evaluate``, igual que haría ``window.evaluate_js`` en pywebview.
"""

import json
import queue
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "engine"))

import pytest

pw = pytest.importorskip("playwright.sync_api")

UI = Path(__file__).resolve().parent.parent / "loudvox_desktop" / "viewer" / "ui"
VOICES = Path(__file__).resolve().parent.parent.parent / "engine" / "test-voices"
HAS_VOICE = (VOICES / "es_ES-davefx-medium.onnx").exists()


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        yield b
        b.close()


def wait_until(page, cond, timeout=30.0, pump=None):
    """Espera activa ejecutando ``pump()`` (drenar cola de JS) en cada vuelta."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pump:
            pump()
        if cond():
            return True
        page.wait_for_timeout(50)
    return False


# ---------------------------------------------------------------------------
# Nivel 1: UI con API simulada en JS
# ---------------------------------------------------------------------------

MOCK_API = """
window.__lvTestApi = {
  calls: [],
  docs: {
    '/a.txt':  {ok: true,  path: '/a.txt',  title: 'a.txt',
                paragraphs: ['Primer párrafo.', 'Segundo párrafo.', 'Tercero.']},
    '/b.txt':  {ok: true,  path: '/b.txt',  title: 'b.txt', paragraphs: ['Beta.']},
    '/mal.pdf':   {ok: false, path: '/mal.pdf', title: 'mal.pdf', error: 'archivo roto'},
    '/vacio.pdf': {ok: true, path: '/vacio.pdf', title: 'vacio.pdf', paragraphs: []},
  },
  async get_boot() {
    return {
      strings: {vw_title: 'LoudVox — Lector', vw_open: '📂 Abrir…',
                vw_read_all: '▶ Leer todo', vw_from_here: '⏩ Desde aquí',
                vw_read_sel: '🔊 Selección', vw_stop: '⏹ Detener',
                vw_recents: 'Archivos recientes', vw_no_recents: 'nada aún',
                vw_welcome: 'Abrí un documento.',
                vw_empty_doc: 'sin texto extraíble',
                vw_error_open: 'No se pudo abrir el archivo:',
                vw_close_tab: 'Cerrar pestaña'},
      recents: [{path: '/a.txt', title: 'a.txt'}],
      initial: null,
    };
  },
  async open_path(p) { this.calls.push(['open_path', p]); return this.docs[p]; },
  async open_file_dialog() { return this.docs['/b.txt']; },
  async read_document(p, i) { this.calls.push(['read_document', p, i]); return {ok: true}; },
  async read_text(t) { this.calls.push(['read_text', t]); return {ok: true}; },
  async stop() { this.calls.push(['stop']); return {ok: true}; },
  async get_recents() { return [{path: '/a.txt', title: 'a.txt'}]; },
};
"""


@pytest.fixture()
def page(browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.add_init_script(MOCK_API)
    page.goto((UI / "viewer.html").as_uri())
    page.wait_for_selector("#welcome:not([hidden])")
    yield page
    ctx.close()


def calls(page):
    return page.evaluate("window.__lvTestApi.calls")


def test_boot_aplica_strings_y_muestra_recientes(page):
    assert page.text_content("#read-all") == "▶ Leer todo"
    assert page.title() == "LoudVox — Lector"
    assert page.locator(".recent").count() == 1
    assert "a.txt" in page.text_content(".recent")


def test_abrir_reciente_crea_pestania_y_muestra_parrafos(page):
    page.click(".recent")
    page.wait_for_selector("#doc p[data-i='2']")
    assert page.locator("#tabs .tab").count() == 1
    assert "a.txt" in page.text_content("#tabs .tab.active")
    assert page.text_content("#doc p[data-i='0']") == "Primer párrafo."
    assert page.is_hidden("#welcome")


def test_pestanias_abrir_cambiar_cerrar(page):
    page.click(".recent")  # abre /a.txt
    page.wait_for_selector("#doc p[data-i='0']")
    page.click("#open-file")  # abre /b.txt (el diálogo simulado)
    page.wait_for_selector("#tabs .tab >> nth=1")
    assert page.locator("#tabs .tab").count() == 2
    assert "b.txt" in page.text_content("#tabs .tab.active")
    assert page.text_content("#doc p[data-i='0']") == "Beta."
    # volver a la primera pestaña
    page.click("#tabs .tab >> nth=0")
    assert page.text_content("#doc p[data-i='0']") == "Primer párrafo."
    # cerrar la activa -> queda la otra
    page.click("#tabs .tab.active .close")
    assert page.locator("#tabs .tab").count() == 1
    assert page.text_content("#doc p[data-i='0']") == "Beta."
    # cerrar todo -> vuelve la bienvenida con recientes
    page.click("#tabs .tab.active .close")
    page.wait_for_selector("#welcome:not([hidden])")
    assert page.is_hidden("#tabs")


def test_reabrir_mismo_archivo_no_duplica_pestania(page):
    page.click(".recent")
    page.wait_for_selector("#doc p")
    page.evaluate("lv.openDropped('/a.txt')")  # soltar el mismo archivo
    page.wait_for_timeout(100)
    assert page.locator("#tabs .tab").count() == 1


def test_documento_con_error_y_documento_vacio(page):
    page.evaluate("lv.openDropped('/mal.pdf')")
    page.wait_for_selector(".doc-error")
    assert "archivo roto" in page.text_content(".doc-error")
    page.evaluate("lv.openDropped('/vacio.pdf')")
    page.wait_for_selector(".doc-empty")
    assert "sin texto" in page.text_content(".doc-empty")


def test_leer_todo_resalta_y_detener_limpia(page):
    page.click(".recent")
    page.wait_for_selector("#doc p[data-i='0']")
    page.click("#read-all")
    page.wait_for_timeout(100)
    assert ["read_document", "/a.txt", 0] in calls(page)
    # Python avisaría lv.onParagraph: simularlo
    page.evaluate("lv.onParagraph(1)")
    assert page.locator("#doc p.reading").count() == 1
    assert page.get_attribute("#doc p.reading", "data-i") == "1"
    # cambiar de pestaña quita el resaltado; volver lo restaura
    page.click("#open-file")
    page.wait_for_selector("#tabs .tab >> nth=1")
    assert page.locator("#doc p.reading").count() == 0
    page.click("#tabs .tab >> nth=0")
    assert page.get_attribute("#doc p.reading", "data-i") == "1"
    # detener limpia
    page.click("#stop")
    page.wait_for_timeout(100)
    assert ["stop"] in calls(page)
    assert page.locator("#doc p.reading").count() == 0


def test_fin_de_lectura_limpia_resaltado(page):
    page.click(".recent")
    page.wait_for_selector("#doc p[data-i='0']")
    page.click("#read-all")
    page.evaluate("lv.onParagraph(0)")
    assert page.locator("#doc p.reading").count() == 1
    page.evaluate("lv.onEnd()")
    assert page.locator("#doc p.reading").count() == 0


def test_desde_aqui_usa_el_parrafo_de_la_seleccion(page):
    page.click(".recent")
    page.wait_for_selector("#doc p[data-i='2']")
    page.evaluate("""() => {
      const p = document.querySelector("#doc p[data-i='2']");
      const r = document.createRange();
      r.selectNodeContents(p);
      const s = window.getSelection();
      s.removeAllRanges();
      s.addRange(r);
    }""")
    page.click("#read-here")
    page.wait_for_timeout(100)
    assert ["read_document", "/a.txt", 2] in calls(page)


def test_leer_seleccion_manda_el_texto(page):
    page.click(".recent")
    page.wait_for_selector("#doc p[data-i='1']")
    page.evaluate("""() => {
      const p = document.querySelector("#doc p[data-i='1']");
      const r = document.createRange();
      r.selectNodeContents(p);
      const s = window.getSelection();
      s.removeAllRanges();
      s.addRange(r);
    }""")
    page.click("#read-sel")
    page.wait_for_timeout(100)
    assert ["read_text", "Segundo párrafo."] in calls(page)


def test_botones_de_letra(page):
    page.click(".recent")
    page.wait_for_selector("#doc p")
    before = page.evaluate(
        "parseFloat(getComputedStyle(document.documentElement)"
        ".getPropertyValue('--font-size'))"
    )
    page.click("#font-plus")
    after = page.evaluate(
        "parseFloat(getComputedStyle(document.documentElement)"
        ".getPropertyValue('--font-size'))"
    )
    assert after == before + 2


# ---------------------------------------------------------------------------
# Nivel 2: bridge REAL + motor REAL (voz Piper), audio a un sink falso
# ---------------------------------------------------------------------------


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


class QueueWindow:
    """Reemplaza a la ventana pywebview: junta los evaluate_js en una cola
    para que el hilo del test los inyecte con page.evaluate (Playwright no
    es thread-safe)."""

    def __init__(self):
        self.scripts = queue.Queue()

    def evaluate_js(self, script):
        self.scripts.put(script)


def make_pdf(path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    flow = []
    for texto in [
        "Primera oración del documento de prueba.",
        "Segundo párrafo con más contenido para leer.",
        "Tercero y último párrafo del PDF.",
    ]:
        flow.append(Paragraph(texto, styles["Normal"]))
        flow.append(Spacer(1, 24))
    doc.build(flow)


@pytest.fixture()
def real_page(browser, tmp_path, monkeypatch):
    """Página conectada al ViewerApi real (lector con FakeSink)."""
    from loudvox.config import Config
    from loudvox_desktop.player import Player
    from loudvox_desktop.viewer import recents
    from loudvox_desktop.viewer.bridge import ViewerApi
    from loudvox_desktop.viewer.reader import ParagraphReader

    monkeypatch.setattr(recents, "config_dir", lambda: tmp_path / "cfg")

    api = ViewerApi()
    api.cfg = Config(voice="es_ES-davefx-medium", voices_dir=str(VOICES))
    win = QueueWindow()
    api.set_window(win)
    sink = FakeSink(per_play=0.3)
    reader = ParagraphReader(
        api.cfg,
        on_paragraph=lambda i: api._js(f"lv.onParagraph({i})"),
        on_end=lambda: api._js("lv.onEnd()"),
    )
    reader.player = Player(reader._synthesize, sink=sink)
    api._reader = reader

    ctx = browser.new_context()
    page = ctx.new_page()
    page.expose_function(
        "py_call", lambda method, args: getattr(api, method)(*args)
    )
    page.add_init_script("""
      window.__lvTestApi = {
        get_boot: () => window.py_call('get_boot', []),
        open_path: (p) => window.py_call('open_path', [p]),
        open_file_dialog: () => null,
        read_document: (p, i) => window.py_call('read_document', [p, i]),
        read_text: (t) => window.py_call('read_text', [t]),
        stop: () => window.py_call('stop', []),
        get_recents: () => window.py_call('get_recents', []),
      };
    """)
    page.goto((UI / "viewer.html").as_uri())
    page.wait_for_selector("#welcome:not([hidden])")

    def pump():
        while True:
            try:
                page.evaluate(win.scripts.get_nowait())
            except queue.Empty:
                return

    yield page, api, sink, pump
    api.stop()
    ctx.close()


needs_voice = pytest.mark.skipif(not HAS_VOICE, reason="voz de prueba no instalada")


@needs_voice
def test_e2e_pdf_real_lee_resalta_y_termina(real_page, tmp_path):
    page, api, sink, pump = real_page
    pdf = tmp_path / "prueba.pdf"
    make_pdf(pdf)

    page.evaluate(f"lv.openDropped({json.dumps(str(pdf))})")
    page.wait_for_selector("#doc p[data-i='2']")  # 3 párrafos extraídos
    assert "Primera oración" in page.text_content("#doc p[data-i='0']")
    # quedó en recientes (bridge real)
    assert api.get_recents()[0]["title"] == "prueba.pdf"

    page.click("#read-all")
    # el resaltado avanza 0 -> 1 -> 2 con el motor real sintetizando
    seen = []

    def track():
        pump()
        el = page.query_selector("#doc p.reading")
        if el:
            i = int(el.get_attribute("data-i"))
            if not seen or seen[-1] != i:
                seen.append(i)
        return len(seen) == 3

    assert wait_until(page, track, timeout=120), f"resaltados vistos: {seen}"
    assert seen == [0, 1, 2]
    # al terminar, se limpia
    assert wait_until(
        page,
        lambda: page.locator("#doc p.reading").count() == 0,
        timeout=30,
        pump=pump,
    )
    assert sink.n == 3


@needs_voice
def test_e2e_detener_corta_y_limpia(real_page, tmp_path):
    page, api, sink, pump = real_page
    txt = tmp_path / "largo.txt"
    txt.write_text(
        "\n\n".join(f"Párrafo número {i} del documento." for i in range(8)),
        encoding="utf-8",
    )
    page.evaluate(f"lv.openDropped({json.dumps(str(txt))})")
    page.wait_for_selector("#doc p[data-i='7']")
    page.click("#read-all")
    assert wait_until(
        page,
        lambda: page.locator("#doc p.reading").count() == 1,
        timeout=90,
        pump=pump,
    )
    page.click("#stop")
    pump()
    assert page.locator("#doc p.reading").count() == 0
    n = sink.n
    page.wait_for_timeout(1500)
    pump()
    assert sink.n <= n + 1  # no siguió leyendo
    assert page.locator("#doc p.reading").count() == 0
