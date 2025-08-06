import sqlite3
import os

db_files = [
    'C:\\Users\\kanur\\OneDrive\\문서\\GitHub\\aaa\\code_outputs\\db\\category_predictions_dongyang.db',
    'C:\\Users\\kanur\\OneDrive\\문서\\GitHub\\aaa\\code_outputs\\db\\category_predictions_hoban.db',
    'C:\\Users\\kanur\\OneDrive\\문서\\GitHub\\aaa\\code_outputs\\db\\dongyang.db',
    'C:\\Users\\kanur\\OneDrive\\문서\\GitHub\\aaa\\code_outputs\\db\\hoban.db'
]

for db_file in db_files:
    dump_file = db_file.replace('.db', '_dump.sql')
    try:
        conn = sqlite3.connect(db_file)
        with open(dump_file, 'w', encoding='utf-8') as f:
            for line in conn.iterdump():
                f.write('%s;\n' % line) # Add semicolon for MySQL compatibility
        conn.close()
        print(f"Successfully dumped {db_file} to {dump_file}")
    except Exception as e:
        print(f"Error dumping {db_file}: {e}")
