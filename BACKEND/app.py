from __future__ import annotations

import csv
import hashlib
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# --------------------------------------
# App setup
# --------------------------------------
app = Flask(__name__)
# Configure CORS to allow requests from any origin during development
CORS(app, resources={
    r"/*": {
        "origins": "*",  # Allow all origins in development
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False
    }
})

# Database configuration
# Use SQLite in production (Vercel) and PostgreSQL in development
if os.environ.get('VERCEL'):
    # In Vercel, use SQLite with an in-memory database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
else:
    db_url = os.getenv('DATABASE_URL', 'sqlite:///astro_assistant.db')
    if isinstance(db_url, str) and db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    if isinstance(db_url, str) and db_url.startswith('postgresql://'):
        try:
            import psycopg2  # noqa: F401
        except Exception:
            db_url = 'sqlite:///astro_assistant.db'

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy()
db.init_app(app)

# Create tables if they don't exist
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Error creating database tables: {e}")

# Database Models
class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    search_query = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.String(100), default='default_user')  # In a real app, this would be linked to user auth

    def to_dict(self):
        return {
            'id': self.id,
            'search_query': self.search_query,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id
        }

# Create tables
with app.app_context():
    db.create_all()


# --------------------------------------
# Synthetic dataset loader (fast, in-memory)
# --------------------------------------
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'DATASETS'))
PRODUCTS_CSV = os.path.join(DATA_DIR, 'products.csv')


@dataclass
class ProductRow:
    product: str
    category: str
    base_price: float
    quality: int
    brand_strength: int
    availability: int
    support: int


PRODUCTS: List[ProductRow] = []


def _safe_int(v: str, default: int = 50) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def _safe_float(v: str, default: float = 9999.0) -> float:
    try:
        if v is None:
            return default
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        if not s:
            return default
        s = s.replace(',', '')
        m = re.search(r"-?\d+(?:\.\d+)?", s)
        if not m:
            return default
        return float(m.group(0))
    except Exception:
        return default


CATEGORY_PRICE_RANGES = {
    'Books': {'min': 100, 'max': 2000},
    'Electronics': {'min': 5000, 'max': 150000},
    'Accessories': {'min': 500, 'max': 10000},
    'Wearables': {'min': 5000, 'max': 50000},
    'Clothing': {'min': 300, 'max': 5000},
    'Home & Kitchen': {'min': 200, 'max': 25000},
    'General': {'min': 500, 'max': 50000},
}


def load_products():
    global PRODUCTS

    PRODUCTS = []

    if os.path.exists(PRODUCTS_CSV):
        try:
            with open(PRODUCTS_CSV, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row:
                        continue
                    base_price = _safe_float(row.get('base_price'))
                    if base_price <= 0:
                        continue
                    PRODUCTS.append(ProductRow(
                        product=(row.get('product') or '').strip(),
                        category=(row.get('category') or 'General').strip(),
                        base_price=base_price,
                        quality=_safe_int(row.get('quality') or ''),
                        brand_strength=_safe_int(row.get('brand_strength') or ''),
                        availability=_safe_int(row.get('availability') or ''),
                        support=_safe_int(row.get('support') or ''),
                    ))

            if PRODUCTS:
                for cat in {p.category for p in PRODUCTS}:
                    prices = [p.base_price for p in PRODUCTS if p.category == cat and p.base_price > 0]
                    if not prices:
                        continue
                    lo = min(prices)
                    hi = max(prices)
                    if hi <= lo:
                        hi = lo + 1.0
                    CATEGORY_PRICE_RANGES[cat] = {
                        'min': max(1.0, lo * 0.80),
                        'max': hi * 1.20,
                    }

                print(f"Loaded {len(PRODUCTS)} products from CSV")
                return
        except Exception as e:
            print(f"Error loading products from CSV: {str(e)}")
            PRODUCTS = []

    sample_products = [
        {
            'product': 'Laptop',
            'category': 'Electronics',
            'base_price': '50000',
            'quality': '85',
            'brand_strength': '90',
            'availability': '95',
            'support': '80'
        },
        {
            'product': 'Smartphone',
            'category': 'Electronics',
            'base_price': '25000',
            'quality': '80',
            'brand_strength': '85',
            'availability': '90',
            'support': '75'
        },
        {
            'product': 'Headphones',
            'category': 'Accessories',
            'base_price': '5000',
            'quality': '75',
            'brand_strength': '80',
            'availability': '85',
            'support': '70'
        },
        {
            'product': 'Smartwatch',
            'category': 'Wearables',
            'base_price': '15000',
            'quality': '80',
            'brand_strength': '85',
            'availability': '90',
            'support': '75'
        },
        {
            'product': 'Tablet',
            'category': 'Electronics',
            'base_price': '20000',
            'quality': '78',
            'brand_strength': '82',
            'availability': '88',
            'support': '72'
        },
        {
            'product': 'The Great Gatsby',
            'category': 'Books',
            'base_price': '350',
            'quality': '90',
            'brand_strength': '85',
            'availability': '95',
            'support': '70'
        },
        {
            'product': 'Python Programming',
            'category': 'Books',
            'base_price': '599',
            'quality': '88',
            'brand_strength': '80',
            'availability': '90',
            'support': '65'
        }
    ]
    
    try:
        for row in sample_products:
            PRODUCTS.append(ProductRow(
                product=row['product'].strip(),
                category=row['category'].strip(),
                base_price=_safe_float(row['base_price']),
                quality=_safe_int(row['quality']),
                brand_strength=_safe_int(row['brand_strength']),
                availability=_safe_int(row['availability']),
                support=_safe_int(row['support'])
            ))
        print(f"Loaded {len(PRODUCTS)} sample products")
    except Exception as e:
        print(f"Error loading sample products: {str(e)}")
        # Fallback to minimal default products
        default_products = [
            ProductRow("Laptop", "Electronics", 50000, 85, 90, 95, 80),
            ProductRow("Smartphone", "Electronics", 25000, 80, 85, 90, 75),
        ]
        PRODUCTS.extend(default_products)
        print(f"Using {len(PRODUCTS)} default products")


load_products()


# --------------------------------------
# Helpers
# --------------------------------------
def _find_candidates(query: str) -> List[ProductRow]:
    q = query.lower()
    scores = []
    for r in PRODUCTS:
        text = f"{r.product} {r.category}".lower()
        hit = 0
        if q in text:
            hit += 2
        # lightweight token overlap
        for tok in q.split():
            if tok in text:
                hit += 1
        if hit:
            scores.append((hit, r))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scores][:8]


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _score_row(r: ProductRow) -> Dict[str, float]:
    # Convert features to 0..1
    # Get price range based on category
    price_range = CATEGORY_PRICE_RANGES.get(r.category, CATEGORY_PRICE_RANGES['General'])
    min_price = price_range['min']
    max_price = price_range['max']
    denom = (max_price - min_price) if (max_price - min_price) != 0 else 1.0
    
    # Price score: cheaper is better within category range
    price_norm = 1.0 - _clamp01((r.base_price - min_price) / denom)
    quality_norm = _clamp01(r.quality / 100.0)
    brand_norm = _clamp01(r.brand_strength / 100.0)
    availability_norm = _clamp01(r.availability / 100.0)
    support_norm = _clamp01(r.support / 100.0)

    return {
        'Price': price_norm * 100,
        'Quality': quality_norm * 100,
        'Brand': brand_norm * 100,
        'Availability': availability_norm * 100,
        'Support': support_norm * 100,
    }


def _aggregate_scores(scores_list: List[Dict[str, float]]) -> Dict[str, float]:
    keys = ['Price', 'Quality', 'Brand', 'Availability', 'Support']
    agg = {k: 0.0 for k in keys}
    if not scores_list:
        return agg
    for sc in scores_list:
        for k in keys:
            agg[k] += sc.get(k, 0.0)
    n = float(len(scores_list))
    for k in keys:
        agg[k] /= n
    return agg


def _verdict_from_scores(name: str, agg: Dict[str, float]) -> Dict[str, Any]:
    # Weighted decision
    w = {
        'Price': 0.25,
        'Quality': 0.30,
        'Brand': 0.20,
        'Availability': 0.15,
        'Support': 0.10,
    }
    score = sum(agg[k] * w[k] for k in w)
    decision_buy = score >= 62
    rating = max(1, min(5, int(round(score / 20))))

    # Pie: pros vs cons vs neutral derived from dimensions
    pros = max(0.0, (agg['Quality'] + agg['Brand']) / 2)
    cons = max(0.0, 100 - agg['Price'])  # higher cons if Price score is low
    neutral = max(0.0, 100 - pros * 0.5 - cons * 0.3)
    total = pros + cons + neutral
    if total <= 0:
        pie = {'labels': ['Pros', 'Cons', 'Neutral'], 'data': [34, 33, 33]}
    else:
        pie = {
            'labels': ['Pros', 'Cons', 'Neutral'],
            'data': [round(pros / total * 100, 1), round(cons / total * 100, 1), round(neutral / total * 100, 1)],
        }

    bar = {
        'labels': ['Price', 'Quality', 'Brand', 'Availability', 'Support'],
        'data': [round(agg['Price'], 1), round(agg['Quality'], 1), round(agg['Brand'], 1), round(agg['Availability'], 1), round(agg['Support'], 1)],
    }

    verdict = (
        f"{name}: Strong overall value" if decision_buy else f"{name}: Consider alternatives"
    )
    lines = [
        f"Quality score around {round(agg['Quality'])}.",
        f"Brand trust around {round(agg['Brand'])}.",
        f"Availability score around {round(agg['Availability'])}.",
        f"Support score around {round(agg['Support'])}.",
        f"Price attractiveness around {round(agg['Price'])}.",
        "Decision is based on weighted historical signals.",
    ]

    return {
        'verdict': verdict,
        'lines': lines,
        'pie': pie,
        'bar': bar,
        'decisionBuy': decision_buy,
        'rating': rating,
    }


def _rand_for_product(product: str) -> random.Random:
    h = int(hashlib.md5(product.lower().encode('utf-8')).hexdigest()[:12], 16)
    return random.Random(h)


def _stable_int(s: str) -> int:
    return int(hashlib.md5(s.encode('utf-8')).hexdigest()[:12], 16)


def _store_url(store: str, product: str) -> str:
    from urllib.parse import quote_plus
    q = quote_plus(product)
    mapping = {
        'Amazon India': f'https://www.amazon.in/s?k={q}',
        'Flipkart': f'https://www.flipkart.com/search?q={q}',
        'Myntra': f'https://www.myntra.com/{q}',
        'Meesho': f'https://www.meesho.com/search?q={q}',
        'AJIO': f'https://www.ajio.com/search/?text={q}',
        'Nykaa': f'https://www.nykaa.com/search/result/?q={q}',
        'Tata CLiQ': f'https://www.tatacliq.com/search/?searchCategory=all&text={q}',
        'Snapdeal': f'https://www.snapdeal.com/search?keyword={q}',
        'ShopClues': f'https://www.shopclues.com/search?q={q}',
        'Shopsy': f'https://www.shopsy.in/search?q={q}',
        'Voonik': f'https://www.voonik.com/search?q={q}',
    }
    return mapping.get(store, f'https://www.google.com/search?q={q}')


# --------------------------------------
# Endpoints
# --------------------------------------
@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    product = data.get('product', '').strip()
    if not product:
        return jsonify({'error': 'Product name is required'}), 400
        
    # Log the search query
    log_search(product)

    t0 = time.perf_counter()
    cands = _find_candidates(product)
    # If not found, synthesize a pseudo-row using averages
    if not cands:
        baseline = ProductRow(product=product, category='General', base_price=25000, quality=65, brand_strength=60, availability=70, support=60)
        cands = [baseline]

    scores = [_score_row(r) for r in cands]
    agg = _aggregate_scores(scores)
    out = _verdict_from_scores(product, agg)
    out['latencyMs'] = int((time.perf_counter() - t0) * 1000)
    return jsonify(out)


@app.get('/api/offers')
def offers():
    product = (request.args.get('product') or '').strip()
    if not product:
        return jsonify({'error': 'Missing product'}), 400

    rnd = _rand_for_product(product)
    # Use nearest candidate price as anchor
    cands = _find_candidates(product)
    anchor_price = (cands[0].base_price if cands else 25000.0)

    stores = ['Amazon India','Flipkart','Myntra','Meesho','AJIO','Nykaa','Tata CLiQ','Snapdeal','ShopClues','Shopsy','Voonik']
    results = []
    for s in stores:
        # +/- up to 18% with small store-specific bias
        bias = (_stable_int(s) % 7) - 3  # -3..+3
        factor = 1.0 + rnd.uniform(-0.06, 0.06) + (bias / 200.0)
        price = max(299.0, int(round(anchor_price * factor)))
        results.append({
            'store': s,
            'price': price,
            'url': _store_url(s, product),
        })

    results.sort(key=lambda x: x['price'])
    
    # Initialize all items with empty tag
    for item in results:
        item['tag'] = ''
    
    # Add tags: "Cheapest" for the lowest price, "Better to buy" for similar-priced items
    if results:
        lowest_price = results[0]['price']
        results[0]['tag'] = 'Cheapest'
        
        # Mark items with small price differences as "Better to buy"
        # Group by price ranges to mark only one per range
        marked_ranges = set()
        
        for item in results[1:]:
            price = item['price']
            price_diff = price - lowest_price
            
            # Check if price difference is within reasonable ranges (1-1000)
            if 0 < price_diff < 1000:
                # Create price range key (e.g., 23900-24000, 24000-24100)
                range_key = int(price / 100) * 100
                
                # Mark only one item per price range
                if range_key not in marked_ranges:
                    item['tag'] = 'Better to buy'
                    marked_ranges.add(range_key)
    
    return jsonify(results)


@app.route('/api/health', methods=['GET'])
def health():
    try:
        # Simple health check without database
        return jsonify({
            "status": "Healthy",
            "message": "Service is running",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "status": "Error",
            "error": str(e)
        }), 500


@app.route('/')
def home():
    return "✅ Flask Backend is Running! Use /api/analyze or /api/offers"

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        # In a real app, filter by logged-in user
        history = SearchHistory.query.order_by(desc(SearchHistory.timestamp)).limit(50).all()
        return jsonify([item.to_dict() for item in history])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def log_search(query: str):
    """Helper to log a search query to the database"""
    try:
        if not query or len(query.strip()) == 0:
            return
            
        search = SearchHistory(
            search_query=query.strip(),
            user_id='default_user'  # Replace with actual user ID in a real app
        )
        db.session.add(search)
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Failed to log search: {str(e)}")
        db.session.rollback()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

