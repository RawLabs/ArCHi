"""Contracts shared by machine-specific ArCHi action adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


# ``attention`` means that the requested action was delivered, but the desktop
# still shows the target afterwards.  It is intentionally not a failure: for
# example, an application may be waiting on its own unsaved-changes dialog.
ActionStatus = Literal["success", "attention", "unsupported", "unavailable", "failed"]


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
