from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date


app = Flask(__name__)
from flask import session

app.secret_key = "pharmacy_secret"   # Add near top of file


# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ======================
# DATABASE MODELS
# ======================

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    expiry = db.Column(db.String(20), nullable=False)
    supplier = db.Column(db.String(100))


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medicine_name = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    total_price = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)


# ======================
# CREATE DATABASE
# ======================

with app.app_context():
    db.create_all()


# ======================
# ROUTES
# ======================

# Home / Dashboard
@app.route('/')
def index():

    medicines = Medicine.query.all()
    today = date.today()

    expired = []

    for m in medicines:
        exp = datetime.strptime(m.expiry, "%Y-%m-%d").date()

        if exp < today:
            expired.append(m.name)

    return render_template(
        'index.html',
        medicines=medicines,
        expired=expired
    )


# Add Medicine
@app.route('/add', methods=['GET', 'POST'])
def add_medicine():

    if request.method == 'POST':

        med = Medicine(
            name=request.form['name'],
            price=float(request.form['price']),
            quantity=int(request.form['quantity']),
            expiry=request.form['expiry'],
            supplier=request.form['supplier']
        )

        db.session.add(med)
        db.session.commit()

        return redirect('/')

    return render_template('add.html')


# Delete Medicine
@app.route('/delete/<int:id>')
def delete(id):

    med = Medicine.query.get_or_404(id)

    db.session.delete(med)
    db.session.commit()

    return redirect('/')


# Billing
@app.route('/bill', methods=['GET', 'POST'])
def bill():

    medicines = Medicine.query.all()

    if 'cart' not in session:
        session['cart'] = []

    total = 0


    # Add Item to Cart
    if request.method == 'POST':

        med_id = int(request.form['medicine'])
        qty = int(request.form['qty'])

        med = Medicine.query.get(med_id)

        if med and med.quantity >= qty:

            item = {
                'id': med.id,
                'name': med.name,
                'price': med.price,
                'qty': qty
            }

            session['cart'].append(item)
            session.modified = True


    # Calculate Total
    for item in session['cart']:
        total += item['price'] * item['qty']


    return render_template(
        'bill.html',
        medicines=medicines,
        cart=session['cart'],
        total=total
    )
@app.route('/finalize_bill')
def finalize_bill():

    if 'cart' not in session:
        return redirect('/bill')

    for item in session['cart']:

        med = Medicine.query.get(item['id'])

        if med:

            med.quantity -= item['qty']

            sale = Sale(
                medicine_name=item['name'],
                quantity=item['qty'],
                total_price=item['price'] * item['qty']
            )

            db.session.add(sale)

    db.session.commit()

    session['cart'] = []

    return redirect('/bill')


# Sales Report
@app.route('/sales')
def sales():

    records = Sale.query.order_by(Sale.date.desc()).all()

    return render_template(
        'sales.html',
        records=records
    )


# Search
@app.route('/search')
def search():

    q = request.args.get('q')

    results = Medicine.query.filter(
        Medicine.name.contains(q)
    ).all()

    return render_template(
        'index.html',
        medicines=results,
        expired=[]
    )
@app.route('/filter')
def filter_medicines():

    name = request.args.get('q')
    supplier = request.args.get('supplier')
    stock = request.args.get('stock')
    expiry = request.args.get('expiry')

    # Start query
    query = Medicine.query


    # Name Search
    if name:
        query = query.filter(Medicine.name.contains(name))


    # Supplier Filter
    if supplier and supplier != "all":
        query = query.filter(Medicine.supplier == supplier)


    # Low Stock
    if stock == "low":
        query = query.filter(Medicine.quantity < 10)


    # Expired
    if expiry == "expired":

        today = date.today().strftime("%Y-%m-%d")

        query = query.filter(Medicine.expiry < today)


    medicines = query.all()

    return render_template(
        'index.html',
        medicines=medicines,
        expired=[]
    )
@app.route('/live_search')
def live_search():

    q = request.args.get('q')

    results = Medicine.query.filter(
        Medicine.name.contains(q)
    ).all()

    data = []

    for m in results:

        data.append({
            'name': m.name,
            'price': m.price,
            'qty': m.quantity,
            'expiry': m.expiry,
            'supplier': m.supplier,
            'id': m.id
        })

    return {'medicines': data}



# ======================
# RUN APP
# ======================

if __name__ == '__main__':
    app.run(debug=True)
