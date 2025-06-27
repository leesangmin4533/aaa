from modules.data_parser.parse_and_save import parse_ssv


def test_parse_ssv_basic():
    ssv = (
        "Dataset:ds1\x1e"
        "H\x1fITEM_CD:STRING\x1fITEM_NM:STRING\x1fSTOCK_QTY:STRING\x1e"
        "N\x1f1001\x1fItem1\x1f0\x1e"
        "N\x1f1002\x1fItem2\x1f5\x1e"
    )
    rows = parse_ssv(ssv)
    assert rows == [
        {"ITEM_CD": "1001", "ITEM_NM": "Item1", "STOCK_QTY": "0"},
        {"ITEM_CD": "1002", "ITEM_NM": "Item2", "STOCK_QTY": "5"},
    ]


