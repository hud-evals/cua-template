"""Dinit and environment setup utilities."""

import logging
from pathlib import Path

from manual_dinit import ServiceLoader, SimpleDinit

logger = logging.getLogger(__name__)


async def start_dinit():
    """Load and start all dinit services from /etc/dinit.d."""
    logger.info("Starting dinit")
    loader = ServiceLoader(Path("/etc/dinit.d"))
    services = loader.load_all()
    engine = SimpleDinit(services)
    engine.start("boot")
