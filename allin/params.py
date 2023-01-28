from typing import Any, Iterable

from aiofiles.tempfile import SpooledTemporaryFile
from aiofiles.tempfile.temptypes import AsyncSpooledTemporaryFile
from msgspec import Struct


class BodyPart(Struct):
    """
    Part representation of the multipart/form-data request body

    Args:
        data: This is the value of the form parameter.
        content_type: Type of data (Defaults to None if not given)
        headers: Header of form parameters
    """

    data: str
    content_type: str = None
    headers: dict[str, Any] = None


class UploadFile:
    """
    Class for wrapping files sent via multipart/form-data requests.
    """

    def __init__(
        self,
        fp: AsyncSpooledTemporaryFile,
        *,
        filename: str = None,
        content_type: str = None,
        headers: dict[str, Any] = None
    ) -> None:
        self.fp = fp
        self.filename = filename
        self.content_type = content_type
        self.headers = headers

    @classmethod
    async def create(
        cls,
        max_size: int = 1024 * 10,
        filename: str = None,
        content_type: str = None,
        headers: dict[str, Any] = None,
    ):
        """
        Creates an instance object for the file container.

        NOTE:
            You should use this function instead of creating an instance object directly using 'UploadFile(...) `.
            Since we are using `AsyncSpooledTemporaryFile` from `aiofiles`
            we cannot call the `async` function inside `__init__`.
        """
        fp = await SpooledTemporaryFile(max_size)._coro
        instance = cls(
            fp, filename=filename, content_type=content_type, headers=headers
        )
        return instance

    async def write(self, data: bytes):
        return await self.fp.write(data)

    async def writelines(self, data: Iterable):
        return await self.fp.writelines(data)

    async def read(self, size: int = -1):
        return await self.fp.read(size)

    async def readline(self, limit: int = None):
        return await self.fp.readline(limit)

    async def readlines(self, hint: int = -1):
        return await self.fp.readlines(hint)

    async def isatty(self):
        return await self.fp.isatty()

    async def tell(self):
        return await self.fp.tell()

    async def fileno(self):
        return await self.fp.fileno()

    async def flush(self):
        return await self.fp.flush()

    async def close(self):
        return await self.fp.close()

    async def rollover(self):
        return await self.fp.rollover()

    async def seek(self, offset: int):
        return await self.fp.seek(offset)

    async def truncate(self, size: int = None):
        return await self.fp.truncate(size)
