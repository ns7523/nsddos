"""Typed setup wizard state models."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from nsddos.bootstrap.environment import ToolStatus


@dataclass(frozen=True)
class DeploymentProfile:
    """Selected deployment profile."""

    key: str
    label: str
    description: str


@dataclass(frozen=True)
class InstallRequirement:
    """Single planned setup action."""

    code: str
    title: str
    detail: str
    required: bool = True


@dataclass(frozen=True)
class DependencyPlan:
    """Ordered dependency plan."""

    profile: DeploymentProfile
    requirements: tuple[InstallRequirement, ...]
    summary: str


@dataclass(frozen=True)
class EnvironmentScan:
    """Extended environment scan for setup wizard."""

    os_name: str
    os_family: str
    python_version: str
    virtualenv_active: bool
    docker: ToolStatus
    docker_daemon_running: bool
    docker_compose: ToolStatus
    docker_permissions_ready: bool
    git: ToolStatus
    available_memory_bytes: int
    available_disk_bytes: int
    missing_runtime_directories: tuple[str, ...]
    runtime_assets_ready: bool
    runtime_assets_source: str
    runtime_assets_detail: str


@dataclass(frozen=True)
class SetupState:
    """Full setup wizard result."""

    scan: EnvironmentScan
    profile: DeploymentProfile
    plan: DependencyPlan


@dataclass(frozen=True)
class ComposeBackend:
    """Detected compose backend."""

    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class StartupPortBinding:
    """Startup session port binding."""

    name: str
    port: int

    def to_dict(self) -> dict[str, object]:
        """Serialize port binding."""

        return asdict(self)


@dataclass(frozen=True)
class StartupServiceStatus:
    """Compose service status for startup orchestration."""

    service_name: str
    container_name: str
    state: str
    health: str
    healthy: bool
    container_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize service status."""

        return asdict(self)


@dataclass(frozen=True)
class StackHealthWaitResult:
    """Result of waiting for stack health."""

    services: tuple[StartupServiceStatus, ...]
    success: bool
    timed_out: bool
    pending_services: tuple[str, ...]


@dataclass(frozen=True)
class StartupSession:
    """Persisted startup session."""

    started_at: str
    running_containers: tuple[str, ...]
    ports: tuple[StartupPortBinding, ...]
    health_state: str
    ui_url: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "StartupSession":
        """Build startup session from dict."""

        ports = tuple(
            StartupPortBinding(
                name=str(item.get("name", "")),
                port=int(item.get("port", 0)),
            )
            for item in payload.get("ports", [])
            if isinstance(item, dict)
        )
        return cls(
            started_at=str(payload.get("started_at", "")),
            running_containers=tuple(
                str(item) for item in payload.get("running_containers", [])
            ),
            ports=ports,
            health_state=str(payload.get("health_state", "unknown")),
            ui_url=str(payload.get("ui_url", "")),
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize startup session."""

        return {
            "started_at": self.started_at,
            "running_containers": list(self.running_containers),
            "ports": [port.to_dict() for port in self.ports],
            "health_state": self.health_state,
            "ui_url": self.ui_url,
        }


@dataclass(frozen=True)
class UILaunchResult:
    """UI launch outcome."""

    launched: bool
    reachable: bool
    ui_url: str


@dataclass(frozen=True)
class StartupResult:
    """Full startup orchestration result."""

    already_running: bool
    stack_started: bool
    runtime_valid: bool
    ui_launched: bool
    ui_url: str
    failed_checks: tuple[str, ...]
    session: StartupSession | None = None


@dataclass(frozen=True)
class DiagnosticFinding:
    """One doctor finding."""

    area: str
    check_name: str
    status: str
    detail: str
    repairable: bool = False
    critical: bool = False


@dataclass(frozen=True)
class RepairAction:
    """Typed repair action."""

    area: str
    title: str
    detail: str
    action_type: str
    command: tuple[str, ...] = ()
    repairable: bool = True
    confirmation_required: bool = True
    reversible: bool = False


@dataclass(frozen=True)
class DoctorResult:
    """Doctor execution result."""

    findings: tuple[DiagnosticFinding, ...]
    repair_plan: tuple[RepairAction, ...]
    applied_repairs: tuple[str, ...]
    unrepaired_failures: tuple[str, ...]


@dataclass(frozen=True)
class ResetResult:
    """Reset execution result."""

    stopped_services: tuple[str, ...]
    deleted_paths: tuple[str, ...]
    preserved_config_path: str
    success: bool
