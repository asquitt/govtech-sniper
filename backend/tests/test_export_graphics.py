"""Unit tests for graphics-aware export rendering helpers."""

from app.api.routes.export import _render_html_to_docx


class _FakeRunFont:
    def __init__(self):
        self.name = None


class _FakeRun:
    def __init__(self):
        self.font = _FakeRunFont()


class _FakeParagraph:
    def __init__(self, text: str):
        self.text = text
        self.runs = [_FakeRun()]


class _FakeDocument:
    def __init__(self):
        self.paragraphs: list[_FakeParagraph] = []
        self.headings: list[tuple[str, int]] = []

    def add_paragraph(self, text: str = "", style: str | None = None):
        paragraph = _FakeParagraph(text)
        self.paragraphs.append(paragraph)
        return paragraph

    def add_heading(self, text: str, level: int):
        self.headings.append((text, level))


def test_render_html_to_docx_includes_mermaid_code_block():
    doc = _FakeDocument()
    html = """
    <h4>Graphic: Timeline</h4>
    <pre><code class=\"language-mermaid\">flowchart TD\nA-->B\nB-->C</code></pre>
    """

    _render_html_to_docx(doc, html)

    assert ("Graphic: Timeline", 4) in doc.headings
    assert any("flowchart TD" in paragraph.text for paragraph in doc.paragraphs)
    # Code blocks should use monospace font in DOCX render path.
    assert any(
        run.font.name == "Courier New" for paragraph in doc.paragraphs for run in paragraph.runs
    )
