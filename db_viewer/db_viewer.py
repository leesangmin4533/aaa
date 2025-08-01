import sqlite3
import sys
import os
from datetime import datetime
from collections import defaultdict

def save_table_data_to_file(db_path, output_file_path):
    """
    Connects to an SQLite database. If prediction tables are found, it groups
    items by category and includes the count of items in the category header.
    Otherwise, it saves all table contents to a text file, excluding rows
    where 'sales' or 'recommended_quantity' is 0.
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
                
                cursor.execute("SELECT id, mid_name FROM category_predictions")
                prediction_id_to_mid_name = {pred[0]: pred[1] for pred in cursor.fetchall()}

                cursor.execute("SELECT prediction_id, product_name, recommended_quantity FROM category_prediction_items")
                items = cursor.fetchall()

                grouped_items = defaultdict(list)
                for item in items:
                    prediction_id, product_name, rec_qty = item
                    if int(rec_qty) == 0:
                        continue
                    
                    mid_name = prediction_id_to_mid_name.get(prediction_id, "Unknown Category")
                    grouped_items[mid_name].append((product_name, rec_qty))

                for mid_name, products in sorted(grouped_items.items()):
                    f.write(f"--- Category: {mid_name} ({len(products)} items) ---\n")
                    f.write("Product Name | Recommended Quantity\n")
                    f.write("------------------------------------\n")
                    for product_name, rec_qty in products:
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

                    sales_col_index = columns.index('sales') if 'sales' in columns else -1
                    rec_qty_col_index = columns.index('recommended_quantity') if 'recommended_quantity' in columns else -1

                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()

                    if not rows:
                        f.write("(No data)\n")
                    else:
                        rows_written = 0
                        for row in rows:
                            if sales_col_index != -1 and float(row[sales_col_index]) == 0:
                                continue
                            if rec_qty_col_index != -1 and int(row[rec_qty_col_index]) == 0:
                                continue
                            f.write(" | ".join(map(str, row)) + "\n")
                            rows_written += 1
                        if rows_written == 0:
                             f.write("(All rows had a value of 0 in the filtered columns or the table was empty)\n")
                    f.write("\n")

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
