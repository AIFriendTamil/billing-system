from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///billing.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# Models
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    # stock removed
    image = db.Column(db.String(200), default='placeholder.png')  # URL or path

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'price': self.price,
            'image': self.image
        }

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), default='Cash')
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'date_created': self.date_created.strftime('%Y-%m-%d %H:%M:%S'),
            'total_amount': self.total_amount,
            'payment_method': self.payment_method,
            'item_count': len(self.items)
        }

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    product_name = db.Column(db.String(100), nullable=False) 
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False) 

# Routes
@app.route('/')
def dashboard():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Order.query
    
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(Order.date_created.between(start, end))
        except ValueError:
            pass
            
    # Metrics
    total_orders = query.count()
    
    # Calculate revenue manually to account for filters correctly
    orders = query.all()
    total_revenue = sum(o.total_amount for o in orders)
    
    total_products = Product.query.count()
    
    # Recent orders
    recent_orders = query.order_by(Order.date_created.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                           total_orders=total_orders, 
                           total_revenue=total_revenue, 
                           total_products=total_products,
                           recent_orders=recent_orders,
                           active_page='dashboard')

@app.route('/pos')
def pos():
    products = Product.query.all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template('pos.html', products=products, categories=categories, active_page='pos')

@app.route('/products')
def products():
    all_products = Product.query.all()
    return render_template('products.html', products=all_products, active_page='products')

@app.route('/orders')
def orders_page():
    all_orders = Order.query.order_by(Order.date_created.desc()).all()
    return render_template('orders.html', orders=all_orders, active_page='orders')

@app.route('/api/products', methods=['GET', 'POST'])
def api_products():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        price = float(request.form.get('price'))
        
        image_path = 'https://via.placeholder.com/150'
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = url_for('static', filename='uploads/' + filename)

        new_product = Product(
            name=name,
            category=category,
            price=price,
            image=image_path
        )
        db.session.add(new_product)
        db.session.commit()
        return jsonify({'message': 'Product added!', 'product': new_product.to_dict()})
    
    # GET
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])

@app.route('/api/products/<int:id>', methods=['PUT', 'DELETE'])
def api_product_detail(id):
    product = Product.query.get_or_404(id)
    if request.method == 'DELETE':
        db.session.delete(product)
        db.session.commit()
        return jsonify({'message': 'Product deleted'})
    
    if request.method == 'PUT':
        # Handle update
        # If multipart/form-data
        if request.files or request.form:
             product.name = request.form.get('name', product.name)
             product.category = request.form.get('category', product.category)
             product.price = float(request.form.get('price', product.price))
             
             if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    product.image = url_for('static', filename='uploads/' + filename)
        else:
            data = request.json
            if data:
                product.name = data.get('name', product.name)
                product.category = data.get('category', product.category)
                product.price = float(data.get('price', product.price))
        
        db.session.commit()
        return jsonify({'message': 'Product updated', 'product': product.to_dict()})

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.json
    order_num = f"ORD-{int(datetime.utcnow().timestamp())}"
    total = sum(item['price'] * item['quantity'] for item in data['items'])
    
    new_order = Order(
        order_number=order_num,
        total_amount=total,
        payment_method=data.get('payment_method', 'Cash')
    )
    db.session.add(new_order)
    db.session.flush() 
    
    for item in data['items']:
        p = Product.query.get(item['product_id'])
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item['product_id'],
            product_name=p.name if p else "Unknown Product",
            quantity=item['quantity'],
            price=item['price']
        )
        db.session.add(order_item)
            
    db.session.commit()
    return jsonify({'message': 'Order created', 'order_number': order_num})

@app.route('/api/orders/<int:id>', methods=['DELETE'])
def delete_order(id):
    order = Order.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    return jsonify({'message': 'Order deleted'})

@app.route('/api/analytics')
def analytics():
    from sqlalchemy import func
    
    # 7 days default
    daily_revenue = db.session.query(
        func.date(Order.date_created).label('date'),
        func.sum(Order.total_amount).label('total')
    ).group_by(func.date(Order.date_created)).order_by(func.date(Order.date_created)).limit(7).all()
    
    labels = [r.date for r in daily_revenue]
    data = [r.total for r in daily_revenue]
    
    if not labels:
        labels = ['No Data']
        data = [0]
        
    return jsonify({
        'labels': labels,
        'data': data
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Product.query.first():
            # Seed with INR prices approx
            # Chicken Burger 5.5 -> 250 INR
            # Pizza 8.0 -> 400 INR
            # Cola 1.5 -> 60 INR
            db.session.add(Product(name='Chicken Burger', category='Fast Food', price=250.0, image='https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3'))
            db.session.add(Product(name='Veg Pizza', category='Pizza', price=400.0, image='https://images.unsplash.com/photo-1513104890138-7c749659a591?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3'))
            db.session.add(Product(name='Cola', category='Beverage', price=60.0, image='https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3'))
            db.session.commit()
            
    app.run(debug=True, port=5000)
