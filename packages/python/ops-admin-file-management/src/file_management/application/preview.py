from __future__ import annotations

from file_management.application.ports import FilePreview, PreviewMode, PreviewProviderPort
from file_management.domain.models import ManagedFile


TEXT_PREVIEW_MAX_INLINE_BYTES = 2 * 1024 * 1024

TEXT_EXTENSIONS = {"csv", "json", "log", "md", "markdown", "txt"}
TEXT_MIME_TYPES = {
    "application/json",
    "application/x-ndjson",
    "text/csv",
    "text/markdown",
    "text/plain",
}


class NativePreviewProvider(PreviewProviderPort):
    engine = "native"

    def metadata_for(self, file: ManagedFile) -> FilePreview:
        mime_type = normalize_mime_type(file.mime_type)
        extension = file.extension.lower().strip(".")
        if mime_type.startswith("image/") and mime_type != "image/svg+xml":
            return self._preview("image", mime_type, file.id)
        if mime_type == "application/pdf" or extension == "pdf":
            return self._preview("pdf", "application/pdf", file.id)
        if mime_type.startswith("audio/"):
            return self._preview("audio", mime_type, file.id)
        if mime_type.startswith("video/"):
            return self._preview("video", mime_type, file.id)
        if mime_type.startswith("text/") or mime_type in TEXT_MIME_TYPES or extension in TEXT_EXTENSIONS:
            if file.size_bytes > TEXT_PREVIEW_MAX_INLINE_BYTES:
                return FilePreview(
                    previewable=False,
                    engine=self.engine,
                    mode="unsupported",
                    mime_type=mime_type,
                    reason="text_file_too_large",
                    max_inline_bytes=TEXT_PREVIEW_MAX_INLINE_BYTES,
                )
            return self._preview("text", mime_type, file.id, max_inline_bytes=TEXT_PREVIEW_MAX_INLINE_BYTES)
        return FilePreview(
            previewable=False,
            engine=self.engine,
            mode="unsupported",
            mime_type=mime_type,
            reason="unsupported_mime_type",
        )

    def _preview(
        self,
        mode: PreviewMode,
        mime_type: str,
        file_id: int,
        *,
        max_inline_bytes: int | None = None,
    ) -> FilePreview:
        return FilePreview(
            previewable=True,
            engine=self.engine,
            mode=mode,
            mime_type=mime_type,
            url=f"/files/{file_id}/preview",
            max_inline_bytes=max_inline_bytes,
        )


def normalize_mime_type(value: str) -> str:
    return str(value or "application/octet-stream").split(";", 1)[0].strip().lower() or "application/octet-stream"
