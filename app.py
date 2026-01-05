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
        # Use Vertex AI Search
        try:
            response = search_vertex_ai(query)
            attribution_token = response.attribution_token
            
            conn = get_db()
            for result in response.results:
                p = result.product
                
                # Check if product exists in SQLite
                # This ensures that the detail page link (which queries SQLite) will work.
                exists = conn.execute('SELECT 1 FROM products WHERE id = ?', (p.id,)).fetchone()
                
                if exists:
                    # Map API product to template expectation
                    product_data = {
                        'id': p.id,
                        'title': p.title,
                        'category': p.categories[0] if p.categories else 'General',
                        'price': p.price_info.price,
                        'currency_code': p.price_info.currency_code,
                        'image_url': p.images[0].uri if p.images else ''
                    }
                    products.append(product_data)
                
        except Exception as e:
            print(f"Error calling Vertex AI Search: {e}")
            # Fallback or empty? User requested replacing SQLite, so maybe just show error or empty.
            # We'll just leave products empty.
            pass
            
    else:
        # Default View - Show all products from SQLite as before
        conn = get_db()
        products = conn.execute('SELECT * FROM products').fetchall()
    
    return render_template('index.html', products=products, query=query, attribution_token=attribution_token)

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
    
    return render_template('cart.html', cart_items=cart_items, total_price=total_price, currency_code=currency_code)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id')
    # Default to 1 if not specified
    quantity = int(request.form.get('quantity', 1))
    
    cart_session = session.get('cart', {})
    current_qty = cart_session.get(product_id, 0)
    cart_session[product_id] = current_qty + quantity
    session['cart'] = cart_session
    
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
    # Capture revenue before clearing cart for GTM (if needed server side, but user asked for client side)
    # Actually client side needs product details for the purchase event.
    # To pass data to the GTM purchase event efficiently, we might want to pass the last purchase details to the template
    # But for now, we just clear the cart. 
    # WAIT: The prompt says Purchase Complete page needs to show "Thank you".
    # And the dataLayer event for purchase is triggered ON THE BUTTON CLICK in the Cart page.
    # So we don't necessarily need to pass data here for the event itself, but good practice might be to show summary.
    # User's requirement for GTM is specifically attached to the buttons.
    
    session.pop('cart', None)
    return render_template('complete.html')

@app.context_processor
def inject_gtm():
    return dict(gtm_id=app.config['GTM_ID'], visitor_id=app.config['VISITOR_ID'])

if __name__ == '__main__':
    app.run(debug=True, port=8000)
