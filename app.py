from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3
import os
import google.auth
from google.cloud.retail import SearchRequest, SearchServiceClient

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_demo'  # Replace in production
DB_PATH = 'ecommerce.db'

# GTM Settings
app.config['GTM_ID'] = 'GTM-NFMZ6FZJ' # Updated based on user request
app.config['VISITOR_ID'] = 'visitor-12345' # Demo visitor ID

# Vertex AI Search Settings
PROJECT_ID = google.auth.default()[1] # Try to get from ADC
DEFAULT_SEARCH_PLACEMENT = f"projects/{PROJECT_ID}/locations/global/catalogs/default_catalog/placements/default_search"

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def search_vertex_ai(query):
    search_request = SearchRequest()
    search_request.placement = DEFAULT_SEARCH_PLACEMENT
    search_request.query = query
    search_request.visitor_id = app.config['VISITOR_ID']
    search_request.page_size = 10
    
    client = SearchServiceClient()
    response = client.search(search_request)
    return response

@app.route('/')
def index():
    query = request.args.get('q', '')
    products = []
    attribution_token = None
    
    if query:
        try:
            print(f"Searching for: {query}")
            response = search_vertex_ai(query)
            attribution_token = response.attribution_token
            
            # 1. IDの取得先を result.id に修正
            # 文字列としてリスト化します
            vertex_ids = [str(result.id) for result in response.results]
            print(f"Extracted IDs: {vertex_ids}")

            if vertex_ids:
                conn = get_db()
                # SQLのIN句で一括取得
                placeholders = ', '.join(['?'] * len(vertex_ids))
                query_sql = f'SELECT * FROM products WHERE id IN ({placeholders})'
                
                db_results = conn.execute(query_sql, vertex_ids).fetchall()
                
                # 2. 検索結果の順序（Vertex AIのスコア順）を維持するための処理
                # DBから取得した行をIDをキーにした辞書に変換
                product_map = {str(row['id']): row for row in db_results}
                
                for v_id in vertex_ids:
                    if v_id in product_map:
                        row = product_map[v_id]
                        # テンプレートに渡す形式に変換する
                        products.append({
                            'id': row['id'],
                            'title': row['title'],
                            'category': row['category'],
                            'price': row['price'],
                            'image_url': row['image_url']
                        })
                    else:
                        print(f"ID {v_id} found in Vertex AI but NOT in Local DB")

            print(f"Final products count: {len(products)}")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            
    else:
        # デフォルト表示（クエリなしの場合）
        conn = get_db()
        db_products = conn.execute('SELECT * FROM products').fetchall()
        products = [dict(row) for row in db_products]
    
    return render_template('index.html', 
                           products=products, 
                           query=query, 
                           attribution_token=attribution_token,
                           visitor_id=app.config.get('VISITOR_ID'))

@app.route('/product/<product_id>')
def detail(product_id):
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if product is None:
        return "Product not found", 404
    return render_template('detail.html', product=product)

@app.route('/cart')
def cart():
    cart_session = session.get('cart', {})
    cart_items = []
    total_price = 0
    conn = get_db()
    
    # We need to know the currency code. Assuming all products have the same currency for now,
    # or we can pass it per item. But for total, we need to be careful if currencies mix.
    # The dataset seems to be all USD.
    currency_code = 'USD' # Default fallback
    
    for pid, qty in cart_session.items():
        if qty > 0:
            product = conn.execute('SELECT * FROM products WHERE id = ?', (pid,)).fetchone()
            if product:
                item_total = product['price'] * qty
                total_price += item_total
                cart_items.append({
                    'product': product,
                    'quantity': qty,
                    'item_total': item_total
                })
                # Capture currency from one of the products
                currency_code = product['currency_code']
    
    # Check for last_added_item for GTM event
    last_added_item = session.pop('last_added_item', None)
    
    return render_template('cart.html', 
                           cart_items=cart_items, 
                           total_price=total_price, 
                           currency_code=currency_code,
                           last_added_item=last_added_item)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id')
    # Default to 1 if not specified
    quantity = int(request.form.get('quantity', 1))
    
    cart_session = session.get('cart', {})
    current_qty = cart_session.get(product_id, 0)
    cart_session[product_id] = current_qty + quantity
    session['cart'] = cart_session
    
    # Store added item details in session for GTM event on next page load
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if product:
        session['last_added_item'] = {
            'id': product['id'],
            'price': product['price'],
            'name': product['title'],
            'category': product['category'],
            'currency_code': product['currency_code'],
            'quantity': quantity
        }
    
    return redirect(url_for('cart'))

@app.route('/update_cart', methods=['POST'])
def update_cart():
    product_id = request.form.get('product_id')
    action = request.form.get('action')
    
    cart_session = session.get('cart', {})
    
    if product_id in cart_session:
        if action == 'delete':
            del cart_session[product_id]
        elif action == 'update':
            try:
                new_qty = int(request.form.get('quantity'))
                if new_qty > 0:
                    cart_session[product_id] = new_qty
                else:
                    del cart_session[product_id]
            except ValueError:
                pass
    
    session['cart'] = cart_session
    return redirect(url_for('cart'))

@app.route('/complete')
def complete():
    # Capture revenue and items before clearing cart for GTM purchase event
    cart_session = session.get('cart', {})
    conn = get_db()
    
    order_items = []
    total_price = 0
    currency_code = 'USD'
    
    for pid, qty in cart_session.items():
        if qty > 0:
            product = conn.execute('SELECT * FROM products WHERE id = ?', (pid,)).fetchone()
            if product:
                item_total = product['price'] * qty
                total_price += item_total
                order_items.append({
                    'product': dict(product), # Convert Row to dict for safer template usage if needed
                    'quantity': qty
                })
                currency_code = product['currency_code']

    session.pop('cart', None)
    
    return render_template('complete.html', 
                           order_items=order_items, 
                           total_price=total_price, 
                           currency_code=currency_code)

@app.context_processor
def inject_gtm():
    return dict(gtm_id=app.config['GTM_ID'], visitor_id=app.config['VISITOR_ID'])

if __name__ == '__main__':
    app.run(debug=True, port=8000)
