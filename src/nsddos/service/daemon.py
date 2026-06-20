"""Runtime service daemon facade."""

from __future__ import annotations

from nsddos.service.manager import RuntimeServiceManager


class RuntimeServiceDaemon:
    """Controlled daemon lifecycle with explicit calls."""

    def __init__(self, config: dict) -> None:
        self.manager = RuntimeServiceManager(config)

    def start(self, owner: str = "daemon") -> dict:
        return self.manager.start(owner=owner).to_dict()

    def stop(self) -> dict:
        return self.manager.stop().to_dict()

    def status(self) -> dict:
        return self.manager.status()

    def synchronize(self) -> dict:
        return self.manager.synchronize()
