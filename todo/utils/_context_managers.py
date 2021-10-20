from asqlite import Cursor, Connection

__all__ = ["TransactionCursor"]


class TransactionCursor(Cursor):
    """A 'better' cursor for the asqlite wrapper"""

    @classmethod
    def from_cursor(cls, other: Cursor):
        if not isinstance(other, Cursor):
            raise TypeError(f"Expected 'Cursor' object not '{other.__class__!r}'")
        return cls(connection=other._conn, cursor=other._cursor)

    async def start(self):
        await self._conn.execute("BEGIN TRANSACTION;")

    async def rollback(self):
        await self._conn.rollback()

    async def commit(self):
        await self._conn.commit()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is None:
                await self.commit()
            else:
                await self.rollback()
        finally:
            pass # Don't need to do anything here tbh
