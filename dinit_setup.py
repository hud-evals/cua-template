"""Dinit and environment setup utilities."""

import logging
import os
from pathlib import Path

from manual_dinit import ServiceLoader, SimpleDinit

logger = logging.getLogger(__name__)

TEST_MODE = os.environ.get("MCP_TESTING_MODE", "1") in ["1", "true"]

if TEST_MODE:
    XFCE_STARTUP_DELAY = 5
    CHROMIUM_STARTUP_DELAY = 3
else:
    XFCE_STARTUP_DELAY = 30
    CHROMIUM_STARTUP_DELAY = 5


async def start_dinit():
    """Load and start all dinit services from /etc/dinit.d."""
    logger.info("Starting dinit")
    loader = ServiceLoader(Path("/etc/dinit.d"))
    services = loader.load_all()
    engine = SimpleDinit(services)
    engine.start("boot")
