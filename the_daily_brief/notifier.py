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
    """Send a native macOS notification via osascript using safe argv parameter passing."""
    script = (
        "on run argv\n"
        "  set msg to item 1 of argv\n"
        "  set ttl to item 2 of argv\n"
        "  set sub to item 3 of argv\n"
        "  set snd to item 4 of argv\n"
        '  if sub is not "" and snd is not "" then\n'
        "    display notification msg with title ttl subtitle sub sound name snd\n"
        '  else if sub is not "" then\n'
        "    display notification msg with title ttl subtitle sub\n"
        '  else if snd is not "" then\n'
        "    display notification msg with title ttl sound name snd\n"
        "  else\n"
        "    display notification msg with title ttl\n"
        "  end if\n"
        "end run"
    )
    cmd = [
        "osascript",
        "-e",
        script,
        message,
        title,
        subtitle or "",
        sound or "",
    ]

    try:
        result = subprocess.run(
            cmd,
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
