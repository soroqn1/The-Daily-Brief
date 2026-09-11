"""Orchestrator for The Daily Brief."""

import asyncio
import logging

from the_daily_brief.config import get_config
from the_daily_brief.state import load_state, too_early

logger = logging.getLogger(__name__)


async def run() -> None:
    """Run the daily brief pipeline."""
    config = get_config()
    state = load_state(config.state_file)

    if state.brief_generated_today or too_early(config.brief_after_hour):
        logger.info("Skipping brief generation (already generated today or too early).")
        return

    logger.info("Starting The Daily Brief...")
    # Pipeline stages will be executed here:
    # 1. Fetch items from connectors
    # 2. Generate brief with LLM
    # 3. Render HTML
    # 4. Save brief and mark state done
    # 5. Open in browser and cleanup old briefs


def main() -> None:
    """Main execution entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run())


if __name__ == "__main__":
    main()
