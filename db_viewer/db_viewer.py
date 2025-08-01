import sqlite3
import sys
import os
from datetime import datetime
from collections import defaultdict

def save_table_data_to_file(db_path, output_file_path):
    """
    Connects to an SQLite database. If prediction tables are found, it displays
    the total predicted sales for each category, followed by a list of recommended
    products with their quantities. Otherwise, it saves all table contents.
    """
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at '{db_path}'")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]

        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(f"Database: {db_path}\n\n")

            if 'category_predictions' in tables and 'category_prediction_items' in tables:
                print("Found prediction tables. Grouping items by category.")
                
                # Get category predictions and items
                cursor.execute("SELECT id, mid_name, predicted_sales FROM category_predictions")
                predictions = cursor.fetchall()
                
                cursor.execute("SELECT prediction_id, product_name, recommended_quantity FROM category_prediction_items WHERE recommended_quantity > 0")
                items = cursor.fetchall()

                # Group items by prediction_id
                items_by_prediction_id = defaultdict(list)
                for item in items:
                    prediction_id, product_name, rec_qty = item
                    items_by_prediction_id[prediction_id].append((product_name, rec_qty))

                # Write grouped data to file
                for pred_id, mid_name, predicted_sales in predictions:
                    f.write(f"--- Category: {mid_name} | Predicted Sales: {predicted_sales:.2f} ---\n")
                    
                    recommended_products = items_by_prediction_id.get(pred_id, [])
                    
                    f.write(f"Recommended Products ({len(recommended_products)} items):\n")
                    f.write("Product Name | Recommended Quantity\n")
                    f.write("------------------------------------\n")
                    
                    if not recommended_products:
                        f.write("(No recommended products with quantity > 0)\n")
                    else:
                        for product_name, rec_qty in recommended_products:
                            f.write(f"{product_name} | {rec_qty}\n")
                    f.write("\n")

            else:
                print("Standard table view.")
                for table_name in tables:
                    f.write(f"--- Table: {table_name} ---\n")
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [info[1] for info in cursor.fetchall()]
                    f.write(" | ".join(columns) + "\n")
                    f.write("-" * (len(" | ".join(columns)) + 2) + "\n")

                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()

                    if not rows:
                        f.write("(No data)\n")
                    else:
                        f.write("\n".join([" | ".join(map(str, row)) for row in rows]))
                    f.write("\n\n")

        print(f"Successfully saved database content to {output_file_path}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    script_dir = os.path.dirname(__file__)
    db_dir = os.path.abspath(os.path.join(script_dir, "..", "code_outputs", "db"))

    if not os.path.isdir(db_dir):
        print(f"Error: Directory not found at '{db_dir}'")
        sys.exit(1)

    db_files = [f for f in os.listdir(db_dir) if f.endswith('.db')]

    if not db_files:
        print(f"No .db files found in '{db_dir}'")
        sys.exit(1)

    print("Please select a database file to save:")
    for i, db_file in enumerate(db_files):
        print(f"[{i + 1}] {db_file}")

    while True:
        try:
            choice = input(f"Enter a number (1-{len(db_files)}): ")
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(db_files):
                selected_db_file = db_files[choice_index]
                db_file_path = os.path.join(db_dir, selected_db_file)
                
                today_str = datetime.now().strftime('%Y%m%d')
                db_name_without_ext = os.path.splitext(selected_db_file)[0]
                output_filename = f"{db_name_without_ext}_{today_str}.txt"
                output_file_path = os.path.join(script_dir, output_filename)

                save_table_data_to_file(db_file_path, output_file_path)
                break
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break