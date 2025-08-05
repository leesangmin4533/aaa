from prediction.order_policy import adjust_order_quantity


def test_adjust_order_quantity_rounds_and_adds_safety():
    assert adjust_order_quantity(10.2, safety_stock=3, min_order_qty=5) == 15
