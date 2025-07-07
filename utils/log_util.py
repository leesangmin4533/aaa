def create_logger(module_name: str):
    def log(tag: str, level: str, message: str):
        print(f"[{module_name}][{tag}][{level}] {message}")
    return log
