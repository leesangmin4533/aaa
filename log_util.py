import logging


def create_logger(module_name: str):
    """Return a step-based logger function for the given module."""
    logger = logging.getLogger(module_name)

    def log(step: str, msg: str) -> None:
        logger.info(f"[{module_name} > {step}] {msg}")

    return log
