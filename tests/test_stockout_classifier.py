import pandas as pd
from prediction.stockout_classifier import train_classifier, predict_stockout_probability


def test_stockout_classifier_predicts_high_risk():
    df = pd.DataFrame({
        'current_stock': [0, 10],
        'predicted_demand': [5, 5],
        'will_stockout': [1, 0],
    })
    model = train_classifier(df)
    prob = predict_stockout_probability(model, 0, 5)
    assert prob >= 0.5
