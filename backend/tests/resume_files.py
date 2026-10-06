"""Файлы резюме для тестов: DOCX собирается в памяти, PDF — минимальный с текстовым слоем."""

import io
import zipfile
from xml.sax.saxutils import escape

RESUME_TEXT = """Анна Смирнова
Senior Backend-разработчик
Город: Казань
Email: anna.dev@example.org, телефон +7 (900) 123-45-67, Telegram @anna_backend
Опыт работы 6 лет, готова к удалённой работе.
Желаемая зарплата: от 350 000 ₽

О себе
Строю высоконагруженные сервисы на Python и Go, люблю PostgreSQL.
Капитан команды на соревнованиях ФСП.
Наставник для стажёров, выступаю с докладами, ответственный и коммуникабельный.

Навыки
Python, FastAPI, golang, Postgres, Docker, React
"""


def docx(text: str = RESUME_TEXT) -> bytes:
    paragraphs = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{escape(line)}</w:t></w:r></w:p>'
        for line in text.split("\n")
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{paragraphs}</w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def pdf(lines: list[str]) -> bytes:
    """Одностраничный PDF со шрифтом Helvetica (латиница)."""
    content = (
        "BT /F1 12 Tf 50 750 Td " + " ".join(f"({line}) Tj 0 -16 Td" for line in lines) + " ET"
    )
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1"))
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return out.getvalue()
