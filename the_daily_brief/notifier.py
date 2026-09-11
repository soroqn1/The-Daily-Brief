"""macOS notifications via osascript."""

import logging
import subprocess

logger = logging.getLogger(__name__)


def notify(
    message: str,
    title: str = "The Daily Brief",
    subtitle: str | None = None,
    sound: str | None = "default",
) -> bool:
    """Send a native macOS notification via osascript."""
    clean_msg = message.replace('"', '\\"')
    clean_title = title.replace('"', '\\"')

    script = f'display notification "{clean_msg}" with title "{clean_title}"'
    if subtitle:
        clean_sub = subtitle.replace('"', '\\"')
        script += f' subtitle "{clean_sub}"'
    if sound:
        clean_sound = sound.replace('"', '\\"')
        script += f' sound name "{clean_sound}"'

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            logger.warning("osascript notification failed: %s", result.stderr.strip())
            return False
        return True
    except Exception as exc:
        logger.warning("Failed to dispatch notification: %s", exc)
        return False
