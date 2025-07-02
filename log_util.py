import logging


def create_logger(module_name: str, log_file: str | None = None):
    """Return a state-based logger function for the given module.

    Parameters
    ----------
    module_name : str
        Name used as the logger name.
    log_file : str, optional
        If given, the logger also writes messages to this file using the same
        format as the console output.
    """

    logger = logging.getLogger(module_name)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        logger.addHandler(handler)

    if log_file and not any(
        isinstance(h, logging.FileHandler) and h.baseFilename == log_file
        for h in logger.handlers
    ):
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if not logger.level:
        logger.setLevel(logging.INFO)

    # Prevent duplicate log lines by stopping propagation to the root logger
    logger.propagate = False

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
