import logging


def create_logger(module_name: str):
    """Return a state-based logger function for the given module."""

    logger = logging.getLogger(module_name)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    def log(step: str, state: str, msg: str = "") -> None:
        symbol = {
            "진입": "➡",
            "실행": "▶",
            "완료": "✅",
            "오류": "❌",
        }.get(state, "•")

        message = f"[{module_name} > {step}] {symbol} {state}"
        if msg:
            message += f": {msg}"

        logger.info(message)

    return log
