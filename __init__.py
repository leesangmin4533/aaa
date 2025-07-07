"""BGF Retail automation package."""

__all__ = [
    "analysis",
    "login",
    "utils",
    "main",
    "extract_product_info",
]

try:
    from .analysis import extract_product_info
except Exception:  # pragma: no cover - optional dependency may be missing
    extract_product_info = None

