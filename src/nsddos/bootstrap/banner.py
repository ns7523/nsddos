"""Hero renderables for terminal onboarding."""

from rich.panel import Panel

from .terminal import build_scene_frame

ASCII_SCENE = (
    "            .-^-.",
    "         .-'  |  '-.",
    "       .'   .-+-._  '.",
    "      /   .'  |   '.  \\",
    "     ;   /  .-^-._  \\  ;",
    "     |  |  /_/ \\_\\  |  |",
    "     |  |  \\__^__/  |  |",
    "     ;   \\  '---'  /  ;",
    "      \\   '._ | _.'  /",
    "       '.    \\|/   .'",
    "         '-.  | .-'",
    "            '---'",
)


def build_banner_panel() -> Panel:
    """Return onboarding hero panel."""

    return build_scene_frame(
        ASCII_SCENE,
        footer="Runtime fabric armed. Detection, mitigation, telemetry aligned.",
    )
