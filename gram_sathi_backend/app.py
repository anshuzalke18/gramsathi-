from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gram-sathi-secure-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gramsathi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='citizen')

with app.app_context():
    db.create_all()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('सफलतापूर्वक लॉगिन झाले! (Logged in successfully!)', 'success')
            return redirect(url_for('index'))
        else:
            flash('चुकीचे युजरनेम किंवा पासवर्ड. कृपया पुन्हा प्रयत्न करा.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'citizen')
        
        if not username or not email or not password:
            flash('सर्व फील्ड भरणे आवश्यक आहे.', 'danger')
            return redirect(url_for('register'))
            
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('हे युजरनेम किंवा ईमेल आधीपासून अस्तित्वात आहे.', 'danger')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password, method='scrypt')
        new_user = User(username=username, email=email, password_hash=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()
        
        flash('नोंदणी यशस्वी! आता लॉगिन करा.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('लॉगआउट यशस्वी झाले.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session.get('username'))

@app.route('/api/weather', methods=['GET'])
@login_required
def proxy_weather():
    city = request.args.get('city', 'Nagpur')
    try:
        geo_res = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json", timeout=5)
        geo_data = geo_res.json()
        if not geo_data.get('results'):
            return jsonify({'error': 'City not found'}), 404
        place = geo_data['results'][0]
        lat, lon = place['latitude'], place['longitude']
        
        weather_res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&timezone=auto", timeout=5)
        weather_data = weather_res.json()
        weather_data['place_name'] = place['name']
        weather_data['country'] = place.get('country', '')
        return jsonify(weather_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
