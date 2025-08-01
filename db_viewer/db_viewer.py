import sqlite3
import sys
import os
from datetime import datetime

def save_table_data_to_file(db_path, output_file_path):
    """
    Connects to an SQLite database, retrieves all table names,
    and saves the contents of each table to a text file.
    """
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at '{db_path}'")
        return

    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get a list of all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        with open(output_file_path, 'w', encoding='utf-8') as f:
            if not tables:
                f.write(f"No tables found in the database: {db_path}\n")
                print(f"No tables found in the database: {db_path}")
                return

            f.write(f"Database: {db_path}\n\n")

            # Iterate over the tables and write their contents
            for table_name in tables:
                table_name = table_name[0]
                f.write(f"--- Table: {table_name} ---\n")

                # Get the column names
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [info[1] for info in cursor.fetchall()]
                f.write(" | ".join(columns) + "\n")
                f.write("-" * (len(" | ".join(columns)) + 2) + "\n")

                # Fetch and write all rows from the table
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()

                if not rows:
                    f.write("(No data)\n")
                else:
                    for row in rows:
                        f.write(" | ".join(map(str, row)) + "\n")
                f.write("\n")
        
        print(f"Successfully saved database content to {output_file_path}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        # Close the connection
        if conn:
            conn.close()

if __name__ == "__main__":
    # The script is in 'db_viewer', dbs are in '../code_outputs/db'
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
                
                # Create the output filename
                today_str = datetime.now().strftime('%Y%m%d')
                db_name_without_ext = os.path.splitext(selected_db_file)[0]
                output_filename = f"{db_name_without_ext}_{today_str}.txt"
                # Save the output file in the same directory as the script
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