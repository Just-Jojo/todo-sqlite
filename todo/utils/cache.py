# Copyright (c) 2021 - Jojo#7791
# Licensed under MIT

from typing import Any, Dict, Optional, Union, AsyncContextManager
import asyncio

import discord # type:ignore

import json
import asqlite

from redbot.core import commands
from redbot.core.data_manager import cog_data_path

from contextlib import asynccontextmanager

from ._statements import *
import logging


log = logging.getLogger("red.JojoCogs.todo.cache")
User = Union[int, discord.Member, discord.User]
__all__ = [
    "TodoApi",
]

@asynccontextmanager
async def dbcommit(connection: asqlite.Connection):
    try:
        yield
    finally:
        await connection.commit()


CREATE_TABLE = """CREATE TABLE IF NOT EXISTS todo (
    user_id INT PRIMARY KEY,
    todos TEXT NOT NULL,
    completed TEXT NOT NULL,
    user_settings TEXT NOT NULL
);
"""
_keys = {
    "todos": [],
    "completed": [],
    "user_settings": {
        "autosorting": False,
        "colour": None,
        "combine_lists": False,
        "extra_details": False,
        "number_todos": True,
        "pretty_todos": False,
        "private": False,
        "reverse_sort": False,
        "use_embeds": False,
        "use_markdown": False,
        "use_timestamps": False,
        "managers": [],
    }
}


class TodoApi:
    def __init__(self):
        self._connection: asqlite.Connection
        self._cursor: asqlite.Cursor
        self._started: bool = False
        self._data: Dict[str, Dict[str, Any]] = {}
        self._cog: Cog
        self._commit_lock = asyncio.Lock()
        self._get_lock = asyncio.Lock()

    @classmethod
    async def init(cls, cog: commands.Cog):
        self = cls()
        self._cog = cog
        data_path = cog_data_path(cog)
        self._connection = await asqlite.connect(f"{data_path}/todo.db") # type:ignore
        self._cursor = await self._connection.cursor() # type:ignore
        await self._fill_cache()
        return self

    async def teardown(self):
        if self._commit_lock.locked():
            self._commit_lock.release() # release the lock here
        await self._cursor.close()
        await self._connection.close()

    @property
    def _commit_cm(self) -> AsyncContextManager:
        return dbcommit(self._connection)

    @_commit_cm.setter
    def _commit_cm(self):
        raise RuntimeError("Hahahahahahaha.... no")

    async def _fill_cache(self, *, user_id: int = None):
        if not self._started:
            async with self._commit_cm:
                await self._cursor.execute(CREATE_TABLE)
            self._started = True

        if user_id:
            if not isinstance(user_id, int):
                raise TypeError(f"'user_id' must be type int not {user_id.__class__!r}")
            async with self._get_lock:
                await self._cursor.execute(SELECT_DATA, user_id)
                data = await self._cursor.fetchone()
            payload = {}
            for key, value in zip(_keys.keys(), data):
                payload[key] = json.loads(value)
            self._data[user_id] = payload # type:ignore
            return payload
        await self._cursor.execute("SELECT * FROM todo")
        data = await self._cursor.fetchall() # type:ignore
        for row in data:
            row = list(row)
            uid = row.pop(0)
            self._data[uid] = {}
            for key, value in zip(_keys.keys(), row):
                value = json.loads(value)
                self._data[uid][key] = value

    async def get_user_data(self, user: User) -> Dict[str, Any]:
        uid = self._get_user_id(user)
        try:
            ret = self._data.get(uid, await self._fill_cache(user_id=uid)) # type:ignore
        except Exception as e:
            print(type(e))
            data = [uid] + [json.dumps(v) for v in _keys.values()] # type:ignore
            async with self._commit_cm:
                await self._cursor.execute(CREATE_USER_DATA, *data)
            await self._fill_cache(user_id=uid)
            ret = self._data.get(uid) # type:ignore
        return ret

    async def get_user_item(self, user: User, item: str) -> Optional[Dict[str, Any]]:
        data = await self.get_user_data(user)
        try:
            return data[str(item)]
        except KeyError:
            raise KeyError(f"'{item}' is not a valid key in the user config") from None

    async def get_user_setting(self, user: User, key: str) -> Optional[Any]:
        key = str(key)
        settings = await self.get_user_item(user, "user_settings")
        if key not in settings.keys():
            raise KeyError(f"The key '{key}' is not a user setting")
        return settings[key]

    async def set_user_data(self, user: User, data: Dict[str, Any]) -> None:
        if not data.keys() == _keys.keys():
            raise ValueError("The new data's keys must be the same as the original keys.")
        uid = self._get_user_id(user)
        async with self._commit_lock:
            payload = [json.dumps(value) for value in data.values()]
            payload.append(uid) # type:ignore
            async with self._commit_cm:
                await self._cursor.execute(UPDATE_USER, *payload)
            await self._fill_cache(user_id=uid)

    async def set_user_item(self, user: User, key: str, item: Any) -> None:
        key = str(key)
        if key not in _keys.keys():
            raise KeyError(f"The key '{key}' is not in the original keys")
        data = await self.get_user_data(user)
        data[key] = item
        await self.set_user_data(user, data)

    async def set_user_setting(self, user: User, key: str, data: Any) -> None:
        key = str(key)
        settings = await self.get_user_item(user, "user_settings")
        if key not in settings.keys(): # type:ignore
            raise KeyError(f"The key '{key}' is not a user setting")
        settings[key] = data # type:ignore
        await self.set_user_item(user, "user_settings", settings)

    async def delete_user_data(self, user: User) -> None:
        uid = self._get_user_id(user)
        if uid in self._data.keys():
            self._data.pop(uid) # type:ignore
        try:
            async with self._commit_lock:
                async with self._commit_cm:
                    await self._cursor.execute("DELETE FROM todo WHERE user_id = ?", uid)
        except Exception as e:
            print(type(e))

    @staticmethod
    def _get_user_id(user: Union[User, int]) -> int:
        if hasattr(user, "id"):
            return user.id # type:ignore
        elif isinstance(user, int):
            return user
        raise TypeError
