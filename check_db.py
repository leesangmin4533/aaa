import sqlite3
import pandas as pd
from datetime import datetime, timedelta

def analyze_predictions():
    db_path = r'C:\Users\kanur\OneDrive\문서\GitHub\aaa\code_outputs\db\dongyang.db'
    pred_db_path = r'C:\Users\kanur\OneDrive\문서\GitHub\aaa\code_outputs\db\category_predictions_dongyang.db'
    
    lookback_days = 7
    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')

    try:
        conn_sales = sqlite3.connect(db_path)
        conn_pred = sqlite3.connect(pred_db_path)

        sales_query = """
            SELECT 
                mid_code, 
                product_code, 
                SUM(CASE WHEN stock = 0 THEN 1 ELSE 0 END) AS stockout_count, 
                COUNT(*) AS total_days 
            FROM mid_sales 
            WHERE DATE(collected_at) >= ? 
            GROUP BY mid_code, product_code
        """
        stockout_df = pd.read_sql(sales_query, conn_sales, params=(start_date,))
        if not stockout_df.empty:
            stockout_df['stockout_rate'] = stockout_df.apply(
                lambda r: r['stockout_count'] / r['total_days'] if r['total_days'] > 0 else 0, 
                axis=1
            )
        else:
            stockout_df['stockout_rate'] = 0.0

        pred_query = "SELECT target_date, mid_code, mid_name, predicted_sales, id FROM category_predictions ORDER BY prediction_date DESC LIMIT 10"
        preds_df = pd.read_sql(pred_query, conn_pred)

        items_query = "SELECT prediction_id, product_code, recommended_quantity FROM category_prediction_items"
        items_df = pd.read_sql(items_query, conn_pred)

        merged_df = pd.merge(preds_df, items_df, left_on='id', right_on='prediction_id', how='left')

        summary = merged_df.groupby(['target_date', 'mid_code', 'mid_name', 'predicted_sales']).agg(
            recommended_items_count=('product_code', 'count'),
            total_recommended_quantity=('recommended_quantity', 'sum')
        ).reset_index()
        summary['total_recommended_quantity'] = summary['total_recommended_quantity'].fillna(0)

        if not stockout_df.empty:
            high_stockout_products = stockout_df[stockout_df['stockout_rate'] >= 0.5]
        else:
            high_stockout_products = pd.DataFrame(columns=stockout_df.columns)

        for index, row in summary.iterrows():
            print(f"\n--- 중분류: {row['mid_name']} ({row['mid_code']}) / 예측일: {row['target_date']} ---")
            print(f"  - 예측 판매량: {row['predicted_sales']:.2f}")
            print(f"  - 추천 상품 종류: {int(row['recommended_items_count'])}개")
            print(f"  - 총 추천 수량: {int(row['total_recommended_quantity'])}개")

            category_stockouts = high_stockout_products[high_stockout_products['mid_code'] == row['mid_code']]
            if not category_stockouts.empty:
                print("  - 높은 품절률(>=50%)로 추천에서 제외되었을 가능성이 있는 상품:")
                for _, so_row in category_stockouts.iterrows():
                    print(f"    - 상품코드: {so_row['product_code']}, 품절률: {so_row['stockout_rate']:.2%}")

            if row['recommended_items_count'] == 0 and row['predicted_sales'] > 0:
                print("  - [분석] 예측 판매량이 0보다 크지만 추천 상품이 없습니다. 해당 카테고리의 모든 상품이 품절률 임계치(50%)를 넘었거나, 판매 데이터가 없어 비율 계산에 실패했을 수 있습니다.")
            elif row['predicted_sales'] < 1.0 and row['recommended_items_count'] <= 1:
                print(f"  - [분석] 예측 판매량({row['predicted_sales']:.2f})이 1 미만으로 매우 낮습니다. 이로 인해 기본적으로 1개 또는 0개의 상품만 추천될 수 있습니다. 소수점 이하 값을 활용한 탐색적 추천 로직이 실행되지 않은 것으로 보입니다.")

    except sqlite3.Error as e:
        print(f"데이터베이스 오류: {e}")
    finally:
        if 'conn_sales' in locals():
            conn_sales.close()
        if 'conn_pred' in locals():
            conn_pred.close()

if __name__ == '__main__':
    analyze_predictions()