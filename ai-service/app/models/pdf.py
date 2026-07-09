from __future__ import annotations

from pydantic import BaseModel, Field


class PdfBlock(BaseModel):
    """A single text block on a PDF page with bounding-box coordinates."""

    x: float
    y: float
    width: float
    height: float
    text: str


class PdfPage(BaseModel):
    """Text and blocks extracted from one PDF page."""

    page_number: int = Field(..., ge=1)
    text: str
    blocks: list[PdfBlock]


class PdfTocEntry(BaseModel):
    """A table-of-contents entry with heading level and target page."""

    level: int = Field(..., ge=1)
    title: str
    page: int = Field(..., ge=1)


class PdfDocument(BaseModel):
    """Structured PDF extraction result."""

    resource_id: str
    total_pages: int = Field(..., ge=0)
    toc: list[PdfTocEntry]
    pages: list[PdfPage]


class PdfParseTask(BaseModel):
    """Request body for queuing a PDF parse task."""

    task_id: str
    resource_id: str
    pdf_url: str


class PdfParseResponse(BaseModel):
    """Response returned when a PDF parse task is accepted."""

    task_id: str
    status: str
    message: str = "PDF parse task queued"
