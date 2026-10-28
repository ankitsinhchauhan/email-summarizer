import os
import time
import logging
from typing import Dict, Any

logger = logging.getLogger("email_summarizer.timing")

ENABLE_TIMING_LOGS = os.getenv("ENABLE_TIMING_LOGS", "1").lower() in ("1", "true", "yes")


def log_timing(
    endpoint: str,
    total_duration: float,
    stages: Dict[str, float],
    **metadata: Any
) -> None:
    """Log structured execution timings for endpoint processing stages.
    
    Ensures document and email contents are never logged.
    """
    if not ENABLE_TIMING_LOGS:
        return

    stages_str = ", ".join(f"{name}={dur * 1000:.2f}ms" for name, dur in stages.items())
    meta_str = f" [{', '.join(f'{k}={v}' for k, v in metadata.items())}]" if metadata else ""
    logger.info(f"[TIMING] {endpoint}: {stages_str}, total={total_duration * 1000:.2f}ms{meta_str}")
