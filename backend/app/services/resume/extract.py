"""Текст из файла резюме. Тип определяется по содержимому (сигнатуре), а не по имени файла.

Защита от вредных файлов: размер, число страниц PDF, распакованный размер DOCX (zip-бомба),
XML не разбирается парсером (нет сущностей и DTD) — текст берётся из тегов <w:t>.
Файл не сохраняется: обрабатывается в памяти и забывается.
"""

import html
import io
import re
import zipfile

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.errors import AppError

MAX_BYTES = 5 * 1024 * 1024
MAX_PAGES = 10
MAX_TEXT = 20_000
_MAX_DOCX_XML = 10 * 1024 * 1024
_PDF = b"%PDF-"
_ZIP = b"PK\x03\x04"
_DOCX_BODY = "word/document.xml"


class UnsupportedResumeError(AppError):
    status_code, code = 422, "unsupported_file"


def extract_text(data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise UnsupportedResumeError("файл больше 5 МБ")
    if data.startswith(_PDF):
        text = _pdf_text(data)
    elif data.startswith(_ZIP):
        text = _docx_text(data)
    else:
        raise UnsupportedResumeError("нужен файл PDF или DOCX")
    text = _normalize(text)
    if len(text) < 20:
        raise UnsupportedResumeError(
            "в файле нет текста — возможно, это скан; загрузите PDF с текстовым слоем или DOCX"
        )
    return text[:MAX_TEXT]


def _pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise UnsupportedResumeError("PDF защищён паролем")
        pages = reader.pages[:MAX_PAGES]
        return "\n".join(page.extract_text() or "" for page in pages)
    except UnsupportedResumeError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError) as exc:
        raise UnsupportedResumeError("не удалось прочитать PDF") from exc


def _docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            info = archive.getinfo(_DOCX_BODY)
            if info.file_size > _MAX_DOCX_XML:
                raise UnsupportedResumeError("слишком большой документ")
            xml = archive.read(info).decode("utf-8", errors="ignore")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise UnsupportedResumeError("нужен файл PDF или DOCX") from exc
    # абзацы и переносы -> новая строка, текст — из <w:t>; разметка и сущности XML не разбираются
    xml = re.sub(r"</w:p>|<w:br/>", "\n", xml).replace("<w:tab/>", "<w:t> </w:t>")
    chunks = re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>|(\n)", xml)
    return html.unescape("".join(text or newline for text, newline in chunks))


def _normalize(text: str) -> str:
    text = text.replace("\r", "\n").replace(" ", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
