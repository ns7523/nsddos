"""Premium terminal onboarding for NSDDOS."""

from nsddos.bootstrap.environment import EnvironmentSnapshot, ToolStatus, detect_environment
from nsddos.bootstrap.doctor import run_doctor_command
from nsddos.bootstrap.reset import run_reset_command
from nsddos.bootstrap.setup import collect_environment_scan
from nsddos.bootstrap.start import run_startup_command
from nsddos.bootstrap.state import (
    ComposeBackend,
    DiagnosticFinding,
    DependencyPlan,
    DeploymentProfile,
    DoctorResult,
    EnvironmentScan,
    InstallRequirement,
    RepairAction,
    ResetResult,
    SetupState,
    StackHealthWaitResult,
    StartupResult,
    StartupSession,
    UILaunchResult,
)
from nsddos.bootstrap.welcome import render_welcome_screen
from nsddos.bootstrap.wizard import render_setup_wizard as run_setup_wizard

__all__ = [
    "ComposeBackend",
    "DiagnosticFinding",
    "DependencyPlan",
    "DeploymentProfile",
    "DoctorResult",
    "EnvironmentScan",
    "EnvironmentSnapshot",
    "InstallRequirement",
    "RepairAction",
    "ResetResult",
    "SetupState",
    "StackHealthWaitResult",
    "StartupResult",
    "StartupSession",
    "collect_environment_scan",
    "detect_environment",
    "run_doctor_command",
    "run_reset_command",
    "run_startup_command",
    "run_setup_wizard",
    "render_welcome_screen",
    "ToolStatus",
    "UILaunchResult",
]
