import sqlite3
import os
import json

DB_PATH = 'ecommerce.db'
DATA_FILE = 'products_data.jsonl'

def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Updated schema: Remove description, Add currency_code, availability
    cursor.execute('''
    CREATE TABLE products (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        currency_code TEXT NOT NULL,
        image_url TEXT NOT NULL,
        availability TEXT NOT NULL
    )
    ''')

    products = []
    seen_ids = set()
    
    # Read from products_data.jsonl
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    
                    # Extract fields
                    p_id = item.get('id')
                    title = item.get('title')
                    
                    # Categories is a list, join them
                    categories_list = item.get('categories', [])
                    category = ', '.join(categories_list) if categories_list else 'Uncategorized'
                    
                    # priceInfo
                    price_info = item.get('priceInfo', {})
                    price = price_info.get('price', 0)
                    currency_code = price_info.get('currencyCode', 'USD')
                    
                    # images
                    images = item.get('images', [])
                    image_url = images[0].get('uri') if images else ''
                    
                    availability = item.get('availability', 'OUT_OF_STOCK')

                    if p_id not in seen_ids:
                        seen_ids.add(p_id)
                        products.append((p_id, title, category, price, currency_code, image_url, availability))
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON line: {line[:50]}...")
                except Exception as e:
                    print(f"Error processing line: {e}")

    cursor.executemany('INSERT INTO products (id, title, category, price, currency_code, image_url, availability) VALUES (?, ?, ?, ?, ?, ?, ?)', products)

    conn.commit()
    conn.close()
    print(f"Database {DB_PATH} initialized with {len(products)} products.")

if __name__ == '__main__':
    init_db()
