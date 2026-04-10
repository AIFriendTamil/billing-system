from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from datetime import datetime
from werkzeug.utils import secure_filename
import os

# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI()

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ── Database ───────────────────────────────────────────────────────────────────
DATABASE_URL = "sqlite:///./instance/billing.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Models ─────────────────────────────────────────────────────────────────────
class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)
    image = Column(String(200), default="placeholder.png")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "price": self.price,
            "image": self.image,
        }


class Order(Base):
    __tablename__ = "order"

    id = Column(Integer, primary_key=True)
    order_number = Column(String(20), unique=True, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)
    total_amount = Column(Float, nullable=False)
    payment_method = Column(String(20), default="Cash")
    items = relationship(
        "OrderItem", backref="order", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "order_number": self.order_number,
            "date_created": self.date_created.strftime("%Y-%m-%d %H:%M:%S"),
            "total_amount": self.total_amount,
            "payment_method": self.payment_method,
            "item_count": len(self.items),
        }


class OrderItem(Base):
    __tablename__ = "order_item"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("order.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=True)
    product_name = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)


# ── Routes: Pages ──────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
):
    query = db.query(Order)

    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            query = query.filter(Order.date_created.between(start, end))
        except ValueError:
            pass

    total_orders = query.count()
    orders = query.all()
    total_revenue = sum(o.total_amount for o in orders)
    total_products = db.query(Product).count()
    recent_orders = (
        query.order_by(Order.date_created.desc()).limit(5).all()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "total_products": total_products,
            "recent_orders": recent_orders,
            "active_page": "dashboard",
        },
    )


@app.get("/pos", response_class=HTMLResponse)
def pos(request: Request, db: Session = Depends(get_db)):
    products = db.query(Product).all()
    categories = [c[0] for c in db.query(Product.category).distinct().all()]
    return templates.TemplateResponse(
        "pos.html",
        {
            "request": request,
            "products": products,
            "categories": categories,
            "active_page": "pos",
        },
    )


@app.get("/products", response_class=HTMLResponse)
def products_page(request: Request, db: Session = Depends(get_db)):
    all_products = db.query(Product).all()
    return templates.TemplateResponse(
        "products.html",
        {"request": request, "products": all_products, "active_page": "products"},
    )


@app.get("/orders", response_class=HTMLResponse)
def orders_page(request: Request, db: Session = Depends(get_db)):
    all_orders = db.query(Order).order_by(Order.date_created.desc()).all()
    return templates.TemplateResponse(
        "orders.html",
        {"request": request, "orders": all_orders, "active_page": "orders"},
    )


# ── Routes: API ────────────────────────────────────────────────────────────────
@app.get("/api/products")
def get_products(db: Session = Depends(get_db)):
    return [p.to_dict() for p in db.query(Product).all()]


@app.post("/api/products")
async def create_product(
    name: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    image_path = "https://via.placeholder.com/150"
    if image and image.filename:
        filename = secure_filename(image.filename)
        dest = os.path.join(UPLOAD_FOLDER, filename)
        with open(dest, "wb") as f:
            f.write(await image.read())
        image_path = f"/static/uploads/{filename}"

    new_product = Product(name=name, category=category, price=price, image=image_path)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return {"message": "Product added!", "product": new_product.to_dict()}


@app.put("/api/products/{id}")
async def update_product(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    product = db.query(Product).get(id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        product.name = form.get("name", product.name)
        product.category = form.get("category", product.category)
        product.price = float(form.get("price", product.price))

        file = form.get("image")
        if file and hasattr(file, "filename") and file.filename:
            filename = secure_filename(file.filename)
            dest = os.path.join(UPLOAD_FOLDER, filename)
            with open(dest, "wb") as f:
                f.write(await file.read())
            product.image = f"/static/uploads/{filename}"
    else:
        data = await request.json()
        if data:
            product.name = data.get("name", product.name)
            product.category = data.get("category", product.category)
            product.price = float(data.get("price", product.price))

    db.commit()
    db.refresh(product)
    return {"message": "Product updated", "product": product.to_dict()}


@app.delete("/api/products/{id}")
def delete_product(id: int, db: Session = Depends(get_db)):
    product = db.query(Product).get(id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted"}


@app.post("/api/orders")
async def create_order(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    order_num = f"ORD-{int(datetime.utcnow().timestamp())}"
    total = sum(item["price"] * item["quantity"] for item in data["items"])

    new_order = Order(
        order_number=order_num,
        total_amount=total,
        payment_method=data.get("payment_method", "Cash"),
    )
    db.add(new_order)
    db.flush()

    for item in data["items"]:
        p = db.query(Product).get(item["product_id"])
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item["product_id"],
            product_name=p.name if p else "Unknown Product",
            quantity=item["quantity"],
            price=item["price"],
        )
        db.add(order_item)

    db.commit()
    return {"message": "Order created", "order_number": order_num}


@app.delete("/api/orders/{id}")
def delete_order(id: int, db: Session = Depends(get_db)):
    order = db.query(Order).get(id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return {"message": "Order deleted"}


@app.get("/api/analytics")
def analytics(db: Session = Depends(get_db)):
    daily_revenue = (
        db.query(
            func.date(Order.date_created).label("date"),
            func.sum(Order.total_amount).label("total"),
        )
        .group_by(func.date(Order.date_created))
        .order_by(func.date(Order.date_created))
        .limit(7)
        .all()
    )

    labels = [r.date for r in daily_revenue]
    data = [r.total for r in daily_revenue]

    if not labels:
        labels = ["No Data"]
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
            
    app.run(host='0.0.0.0', port=5000, debug=False)
