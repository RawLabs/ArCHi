"""Contracts shared by machine-specific ArCHi action adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


ActionStatus = Literal["success", "unsupported", "unavailable", "failed"]


@dataclass(frozen=True)
class ActionResult:
    status: ActionStatus
    provider_id: str
    capability: str
    detail: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == "success"


class DesktopAdapter(Protocol):
    provider_id: str

    def capabilities(self) -> frozenset[str]: ...

    def context(self) -> dict: ...

    def execute(self, capability: str, payload: dict) -> ActionResult: ...

    def feedback(self, state: str, message: str, duration_ms: int) -> None: ...
