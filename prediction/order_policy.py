import math

def adjust_order_quantity(pred_demand: float, safety_stock: int = 0, min_order_qty: int = 1) -> int:
    """예측 수요에 안전재고 및 최소 주문 단위를 반영한 발주량을 계산합니다."""
    total = pred_demand + safety_stock
    if min_order_qty > 0:
        total = math.ceil(total / min_order_qty) * min_order_qty
    return int(total)
