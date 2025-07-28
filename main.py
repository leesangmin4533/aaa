from analysis.jumeokbap_prediction import (
    get_configured_db_path,
    predict_jumeokbap_quantity,
    recommend_product_mix,
)

db_path = get_configured_db_path()
tomorrow_forecast = predict_jumeokbap_quantity(db_path)
mix_recommendations = recommend_product_mix(db_path)

print(f"예상 주문량: {tomorrow_forecast:.2f}개")
print("추천 상품 조합:", mix_recommendations)
