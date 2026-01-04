import sqlite3
import os

DB_PATH = 'ecommerce.db'

def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE products (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        price INTEGER NOT NULL,
        image_url TEXT NOT NULL
    )
    ''')

    products = [
        (
            'p001',
            'organic_cotton_tshirt',
            'オーガニックコットン Tシャツ',
            'Tops',
            '肌触りの良い100%オーガニックコットンを使用した、シンプルで着心地の良いTシャツです。',
            3500,
            'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80'
        ),
        (
            'p002',
            'slim_fit_denim',
            'スリムフィット デニムパンツ',
            'Bottoms',
            'ストレッチ素材で動きやすく、シルエットが美しいスリムフィットデニム。どんなスタイルにも合わせやすい一本。',
            8900,
            'https://images.unsplash.com/photo-1542272454315-4c01d7abdf4a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80'
        ),
        (
            'p003',
            'linen_shirt_white',
            'リネンお出かけシャツ (白)',
            'Tops',
            '通気性抜群のリネン素材。夏のカジュアルスタイルから、ちょっとしたお出かけまで幅広く活躍します。',
            6500,
            'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80'
        ),
        (
            'p004',
            'casual_jacket_navy',
            'カジュアルジャケット (ネイビー)',
            'Outerwear',
            '軽量かつ洗練されたデザインのジャケット。オフィスでもプライベートでも使える万能アイテム。',
            12000,
            'https://images.unsplash.com/photo-1591047139829-d91aecb6caea?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80'
        ),
        (
            'p005',
            'canvas_sneakers',
            'キャンバススニーカー',
            'Shoes',
            'クラシックなデザインのキャンバススニーカー。長時間歩いても疲れにくいクッション性の高いインソールを採用。',
            5800,
            'https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80'
        )
    ]

    cursor.executemany('INSERT INTO products (id, name, title, category, description, price, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)', products)

    conn.commit()
    conn.close()
    print(f"Database {DB_PATH} initialized with {len(products)} products.")

if __name__ == '__main__':
    init_db()
