import asyncio
import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.http import StreamingHttpResponse
from django.utils._os import safe_join
from django.utils.http import content_disposition_header


class AsyncFileResponse(StreamingHttpResponse):
    """Stream a file through ASGI without consuming a synchronous iterator."""

    def __init__(self, file_object, *, filename=None, as_attachment=False, block_size=64 * 1024):
        async def stream_file():
            try:
                while True:
                    chunk = await asyncio.to_thread(file_object.read, block_size)
                    if not chunk:
                        break
                    yield chunk
            finally:
                await asyncio.to_thread(file_object.close)

        super().__init__(stream_file(), content_type=self._content_type(filename))
        self.headers["Content-Disposition"] = content_disposition_header(
            as_attachment, filename or Path(getattr(file_object, "name", "download")).name
        )

        try:
            self.headers["Content-Length"] = str(file_object.size)
        except (AttributeError, OSError, TypeError):
            pass

    @staticmethod
    def _content_type(filename):
        content_type, _ = mimetypes.guess_type(filename or "")
        return content_type or "application/octet-stream"


async def serve_media(request, path):
    """Serve development media through an async iterator under ASGI."""
    try:
        file_path = safe_join(settings.MEDIA_ROOT, path)
    except ValueError as exc:
        raise Http404 from exc

    if not Path(file_path).is_file():
        raise Http404

    file_object = await asyncio.to_thread(open, file_path, "rb")
    return AsyncFileResponse(file_object, filename=Path(file_path).name)
