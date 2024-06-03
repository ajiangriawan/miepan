from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from functools import wraps
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from os.path import join, dirname
from dotenv import load_dotenv
import hashlib
import jwt
import random
from datetime import datetime, timedelta
from collections import defaultdict

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

UPLOAD_FOLDER = 'static/img/profil'
MENU_FOLDER = 'static/img/menu'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MENU_FOLDER'] = MENU_FOLDER

# Create upload directories if they don't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['MENU_FOLDER']):
    os.makedirs(app.config['MENU_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

MONGODB_CONNECTION_STRING = os.environ.get("CONNECTION")
DB_NAME = os.environ.get("DATABASE_NAME")
JWT_SECRET_KEY = os.environ.get("SECRET_KEY")

client = MongoClient(MONGODB_CONNECTION_STRING)
db = client[DB_NAME]
jobs_collection = db.jobs
users_collection = db.users
menus_collection = db.menus
sales_collection = db.sales

def generate_fake_sales_data(num_days):
    sales_data = []
    base_date = datetime.now()
    for i in range(num_days):
        date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
        sales = random.randint(50, 150)
        sales_data.append({"date": date, "sales": sales})
    return sales_data

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            return redirect(url_for('login'))
        try:
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = users_collection.find_one({'email': data['email']})
            if current_user is None:
                return redirect(url_for('login'))
        except:
            return redirect(url_for('login'))
        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            return redirect(url_for('login'))
        try:
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = users_collection.find_one({'email': data['email']})
            if current_user is None or current_user.get('role') != 'admin':
                return redirect(url_for('login'))
        except:
            return redirect(url_for('login'))
        return f(current_user, *args, **kwargs)
    return decorated

def get_user_role():
    token = request.cookies.get('token')
    if token:
        try:
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            user = users_collection.find_one({'email': data['email']})
            if user:
                return user.get('role', 'user')
        except:
            return 'user'
    return 'user'

@app.route('/')
def index():
    user_role = get_user_role()
    return render_template('index.html', user_role=user_role)

@app.route("/login", methods=['GET', 'POST'])
def login():
    user_role = get_user_role()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users_collection.find_one({'email': email})

        if user and user['password'] == hashlib.sha256(password.encode()).hexdigest():
            token = jwt.encode({
                'email': email,
                'exp': datetime.utcnow() + timedelta(minutes=30)
            }, JWT_SECRET_KEY, algorithm='HS256')
            resp = redirect(url_for('profil'))
            resp.set_cookie('token', token)
            return resp
        else:
            flash('Email atau Password salah', 'danger')
            return redirect(url_for('login'))
    return render_template("login.html", user_role = user_role)

@app.route("/regis", methods=['GET', 'POST'])
def regis():
    user_role = get_user_role()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        passwordver = request.form['passwordver']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        nama = request.form['nama']

        if password == passwordver:
            if users_collection.find_one({'email': email}):
                flash('email sudah terdaftar', 'danger')
                return redirect(url_for('regis'))

            user = {
                'email': email,
                'password': hashed_password,
                'nama': nama,
                'notlp': 'silahkan edit profil',
                'alamat': 'silahkan edit profil',
                'fotoprofil': 'static/img/profil/profil.png',
                'role': 'pelanggan',
            }
            users_collection.insert_one(user)
            flash('Pendaftaran berhasil', 'success')
            return redirect(url_for('login'))
        else:
            flash('Password yang anda masukan tidak sama', 'danger')
            return redirect(url_for('regis'))
    return render_template("register.html", user_role = user_role)

@app.route('/logout')
def logout():
    resp = redirect(url_for('login'))
    resp.delete_cookie('token')
    return resp

@app.route("/menu")
def menu():
    user_role = get_user_role()
    return render_template("menu.html", user_role=user_role)

@app.route("/detail_menu")
def detailMenu():
    user_role = get_user_role()
    return render_template("detail_menu.html",user_role=user_role)

@app.route("/tentang")
def tentang():
    user_role = get_user_role()
    return render_template("tentang.html", user_role=user_role)

@app.route("/pesanan")
def pesanan():
    user_role = get_user_role()
    return render_template("pesanan.html", user_role=user_role)

@app.route("/bayar")
def bayar():
    user_role = get_user_role()
    return render_template("pembayaran.html",user_role=user_role)

@app.route("/keranjang")
def keranjang():
    user_role = get_user_role()
    return render_template("keranjang.html", user_role = user_role)

@app.route("/checkout")
def checkout():
    user_role = get_user_role()
    return render_template("checkout.html", user_role=user_role)

@app.route("/profil")
@token_required
def profil(current_user):
    user_role = get_user_role()
    return render_template("profil.html", user=current_user, user_role=user_role)

@app.route("/editProfil", methods=['GET', 'POST'])
@token_required
def editProfil(current_user):
    user_role = get_user_role()
    if request.method == 'POST':
        updated_user = {
            'nama': request.form['nama'],
            'email': request.form['email'],
            'notlp': request.form['notlp'],
            'alamat': request.form['alamat']
        }

        if 'fotoprofil' in request.files:
            file = request.files['fotoprofil']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                updated_user['fotoprofil'] = filepath

        users_collection.update_one({'_id': ObjectId(current_user['_id'])}, {'$set': updated_user})
        flash('Profil berhasil diperbarui', 'success')
        return redirect(url_for('profil'))

    return render_template("edit_profil.html", user=current_user, user_role=user_role)

@app.route("/dashboard")
@admin_required
def dashboard(current_user):
    user_role = get_user_role()

    users = users_collection.find()
    menus = menus_collection.find()
    sales = sales_collection.find()
    
    user_list = list(users)
    menu_list = list(menus)
    sale_list = list(sales)
    
    total_menus = 0
    total_sales = 0
    count_per_role = defaultdict(int)

    for user in user_list:
        role = user.get('role', 'Uncategorized')
        count_per_role[role] += 1
    
    for menu in menu_list:
        total_menus += 1

    for sales in sale_list:
        total_menus += 1
    
    return render_template("dashboard.html", user_role=user_role, menus=menu_list, total_menus=total_menus, count_per_role=count_per_role, total_sales=total_sales)


@app.route('/kelolaMenu')
@admin_required
def kelolaMenu(current_user):
    menus = menus_collection.find()
    menu_list = list(menus)
    
    # Initialize counts
    count_per_category = defaultdict(int)
    total_menus = 0
    
    for menu in menu_list:
        category = menu.get('kategorimenu', 'Uncategorized')
        count_per_category[category] += 1
        total_menus += 1
    
    return render_template('kelola_menu.html', menus=menu_list, count_per_category=count_per_category, total_menus=total_menus)


@app.route("/tambahMenu", methods=['POST'])
@admin_required
def tambahMenu(current_user):
    tambahmenu = {
        'namamenu' : request.form['namaMenu'],
        'hargamenu' : request.form['hargaMenu'],
        'deskripsimenu' : request.form['deskripsiMenu'],
        'kategorimenu' : request.form['kategoriMenu']
    }

    file = request.files['fotoMenu']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['MENU_FOLDER'], filename)
        file.save(filepath)
        tambahmenu['fotomenu'] = filepath

    menus_collection.insert_one(tambahmenu)
    flash('Tambah menu berhasil', 'success')
    return redirect(url_for('kelolaMenu'))

@app.route("/editMenu/<menu_id>", methods=['GET', 'POST'])
@admin_required
def editMenu(current_user, menu_id):
    user_role = get_user_role()
    menu = menus_collection.find_one({'_id': ObjectId(menu_id)})

    if request.method == 'POST':
        updated_menu = {
            'namamenu': request.form['namaMenu'],
            'hargamenu': request.form['hargaMenu'],
            'deskripsimenu': request.form['deskripsiMenu'],
            'kategorimenu': request.form['kategoriMenu']
        }

        if 'fotoMenu' in request.files:
            file = request.files['fotoMenu']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['MENU_FOLDER'], filename)
                file.save(filepath)
                updated_menu['fotomenu'] = filepath

        menus_collection.update_one({'_id': ObjectId(menu_id)}, {'$set': updated_menu})
        flash('Menu berhasil diperbarui', 'success')
        return redirect(url_for('kelolaMenu'))

    return render_template("edit_menu.html", user_role=user_role, menu=menu)

@app.route("/hapusMenu/<menu_id>", methods=['POST'])
@admin_required
def hapusMenu(current_user, menu_id):
    try:
        menus_collection.delete_one({'_id': ObjectId(menu_id)})
        flash('Menu berhasil dihapus', 'success')
    except Exception as e:
        flash(f'Gagal menghapus menu: {str(e)}', 'danger')
    return redirect(url_for('kelolaMenu'))


@app.route("/kelolaPesanan")
@admin_required
def kelolaPesanan(current_user):
    user_role = get_user_role()
    return render_template("kelola_pesanan.html", user_role)

@app.route("/kelolaRekening")
@admin_required
def kelolaRekening(currentuser):
    user_role = get_user_role()
    return render_template("kelola_rekening.html", user_role)

@app.route("/kelolaAdmin")
@admin_required
def kelolaAdmin(current_user):
    user_role = get_user_role()
    return render_template("kelola_admin.html", user_role=user_role)

@app.route('/sales_data')
def sales_data():
    period = request.args.get('period', 'weekly')
    if period == 'weekly':
        sales = generate_fake_sales_data(7)
    elif period == 'monthly':
        sales = generate_fake_sales_data(30)
    elif period == 'yearly':
        sales = generate_fake_sales_data(365)
    return jsonify(sales)

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
