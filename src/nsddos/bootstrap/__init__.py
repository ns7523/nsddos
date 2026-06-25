"""Premium terminal onboarding for NSDDOS."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "ComposeBackend": ("nsddos.bootstrap.state", "ComposeBackend"),
    "DiagnosticFinding": ("nsddos.bootstrap.state", "DiagnosticFinding"),
    "DependencyPlan": ("nsddos.bootstrap.state", "DependencyPlan"),
    "DeploymentProfile": ("nsddos.bootstrap.state", "DeploymentProfile"),
    "DoctorResult": ("nsddos.bootstrap.state", "DoctorResult"),
    "EnvironmentScan": ("nsddos.bootstrap.state", "EnvironmentScan"),
    "EnvironmentSnapshot": ("nsddos.bootstrap.environment", "EnvironmentSnapshot"),
    "InstallRequirement": ("nsddos.bootstrap.state", "InstallRequirement"),
    "RepairAction": ("nsddos.bootstrap.state", "RepairAction"),
    "ResetResult": ("nsddos.bootstrap.state", "ResetResult"),
    "SetupState": ("nsddos.bootstrap.state", "SetupState"),
    "StackHealthWaitResult": ("nsddos.bootstrap.state", "StackHealthWaitResult"),
    "StartupResult": ("nsddos.bootstrap.state", "StartupResult"),
    "StartupSession": ("nsddos.bootstrap.state", "StartupSession"),
    "ToolStatus": ("nsddos.bootstrap.environment", "ToolStatus"),
    "UILaunchResult": ("nsddos.bootstrap.state", "UILaunchResult"),
    "collect_environment_scan": ("nsddos.bootstrap.setup", "collect_environment_scan"),
    "detect_environment": ("nsddos.bootstrap.environment", "detect_environment"),
    "render_welcome_screen": ("nsddos.bootstrap.welcome", "render_welcome_screen"),
    "run_doctor_command": ("nsddos.bootstrap.doctor", "run_doctor_command"),
    "run_reset_command": ("nsddos.bootstrap.reset", "run_reset_command"),
    "run_setup_wizard": ("nsddos.bootstrap.wizard", "render_setup_wizard"),
    "run_startup_command": ("nsddos.bootstrap.start", "run_startup_command"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)
