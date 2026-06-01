from typing import Protocol, TypeVar


T = TypeVar("T")


class IRepository(Protocol[T]):
    async def save(self, entity: T) -> None:
        ...

    async def get_by_id(self, event_id: str) -> T | None:
        ...

    async def list_all(self) -> list[T]:
        ...
