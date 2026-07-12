from __future__ import annotations

from app.models.summary import SectionSummary


class SectionSplitter:
    def split_pdf(self, parsed: dict) -> list[SectionSummary]:
        toc = parsed.get("toc") or []
        pages = parsed.get("pages") or []
        if not toc or not pages:
            return []

        sections: list[SectionSummary] = []
        for index, entry in enumerate(toc):
            start_page = int(entry.get("page", 1))
            next_page = (
                int(toc[index + 1].get("page", len(pages) + 1))
                if index + 1 < len(toc)
                else len(pages) + 1
            )
            end_page = max(start_page, min(next_page - 1, len(pages)))
            content = "\n".join(
                str(page.get("text", "")) for page in pages[start_page - 1 : end_page]
            )
            sections.append(
                SectionSummary(
                    title=str(entry.get("title") or f"第 {index + 1} 节"),
                    content=content,
                    page_range=[start_page, end_page],
                )
            )
        return sections

    def split_audio(self, srt_segments: list[dict], chunk_minutes: int = 5) -> list[SectionSummary]:
        if not srt_segments:
            return []

        sections: list[SectionSummary] = []
        bucket: list[dict] = []
        bucket_start = float(srt_segments[0].get("start", 0))
        for segment in srt_segments:
            bucket.append(segment)
            end = float(segment.get("end", bucket_start))
            if end - bucket_start >= chunk_minutes * 60:
                sections.append(self._build_audio_section(bucket))
                bucket = []
                bucket_start = end
        if bucket:
            sections.append(self._build_audio_section(bucket))
        return sections

    def _build_audio_section(self, segments: list[dict]) -> SectionSummary:
        start = float(segments[0].get("start", 0))
        end = float(segments[-1].get("end", start))
        content = "\n".join(str(segment.get("text", "")) for segment in segments)
        return SectionSummary(
            title=f"{self._fmt(start)}-{self._fmt(end)}",
            content=content,
            timestamp_range=[start, end],
        )

    def _fmt(self, seconds: float) -> str:
        total = int(seconds)
        return f"{total // 60:02d}:{total % 60:02d}"
