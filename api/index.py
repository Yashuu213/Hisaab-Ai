import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import smtplib
import random
from email.mime.text import MIMEText
from sqlalchemy import text

# Vercel setup
# Go up one level from api/ directory to find 'dist'
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dist_folder = os.path.join(basedir, 'dist')
app = Flask(__name__, static_folder=dist_folder)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')

# Database Configuration
# Vercel Postgres automatically uses POSTGRES_URL, or DATABASE_URL
database_url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')

if not database_url:
    if os.environ.get('VERCEL'):
        # Vercel filesystem is read-only at runtime except for /tmp
        db_path = os.path.join('/tmp', 'upi.db')
    else:
        # Use a persistent local path in the project directory for local development
        db_path = os.path.join(basedir, 'upi.db') 
    database_url = f'sqlite:///{db_path}'

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Not actually used for JSON API but required by Flask-Login

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    transactions = db.relationship('Transaction', backref='owner', lazy=True)
    debts = db.relationship('Debt', backref='owner', lazy=True)

class OTPRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False)
    otp = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False) # 'income' or 'expense'
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Debt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False) # 'lent' or 'borrowed'
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class TrainingData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(20), nullable=False) # 'income', 'expense', 'lent', 'borrowed'
    target_category = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Nudge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float)
    message = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship('User', foreign_keys=[sender_id])

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship('User', foreign_keys=[sender_id])

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- API Routes ---

@app.route('/api/init_db')
def init_db():
    db.create_all()
    return jsonify({"message": "Database initialized"})

@app.route('/api/reset_db', methods=['POST'])
def reset_db():
    # Dangerous: clears everything. Use with caution.
    db.drop_all()
    db.create_all()
    return jsonify({"message": "All data cleared. Database reset successfully."})

# --- OTP and Auth Utilities ---
def send_email_async(receiver_email, otp, action_type="verification"):
    sender_email = os.environ.get('EMAIL_ID')
    app_password = os.environ.get('EMAIL_PASSWORD')
    
    if not sender_email or not app_password:
        print("WARNING: Email Credentials missing in environment.")
        return False
        
    subject = f"Your Hisaab.AI {action_type.capitalize()} Code"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
        <h2 style="color: #4f46e5; text-align: center; margin-bottom: 24px;">Hisaab.AI Security</h2>
        <p style="color: #334155; font-size: 16px;">Hello,</p>
        <p style="color: #334155; font-size: 16px;">You recently requested a secure code ({action_type}) for your Hisaab.AI account. Here is your One-Time Password:</p>
        <div style="background-color: #f8fafc; border: 1px dashed #cbd5e1; padding: 16px; text-align: center; border-radius: 8px; margin: 24px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #0f172a;">{otp}</span>
        </div>
        <p style="color: #64748b; font-size: 14px; text-align: center;">This code will expire in exactly 5 minutes. Do not share this code with anyone.</p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
        <p style="color: #94a3b8; font-size: 12px; text-align: center;">If you did not request this email, please ignore it.<br>&copy; {datetime.utcnow().year} Hisaab.AI Operations</p>
    </div>
    """
    
    msg = MIMEText(html_content, 'html')
    msg['Subject'] = subject
    msg['From'] = f"Hisaab.AI <{sender_email}>"
    msg['To'] = receiver_email
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False

@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    try:
        db.create_all()
        data = request.json
        email = data.get('email')
        action_type = data.get('type', 'register') # 'register' or 'reset'
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
            
        if action_type == 'register' and User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        if action_type == 'reset' and not User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email not found'}), 404
            
        otp_code = str(random.randint(100000, 999999))
        
        # Clear old OTPs for this email
        OTPRecord.query.filter_by(email=email).delete()
        new_otp = OTPRecord(email=email, otp=otp_code)
        db.session.add(new_otp)
        db.session.commit()
        
        success = send_email_async(email, otp_code, action_type)
        if success:
            return jsonify({'message': 'OTP sent successfully'}), 200
        else:
            return jsonify({'error': 'Failed to send email. Check credentials.'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/register', methods=['POST'])
def register():
    try:
        db.create_all()
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        otp = data.get('otp')
        
        if not all([username, email, password, otp]):
            return jsonify({'error': 'All fields are required'}), 400
        
        otp_record = OTPRecord.query.filter_by(email=email, otp=otp).first()
        if not otp_record:
            return jsonify({'error': 'Invalid OTP'}), 400
            
        if (datetime.utcnow() - otp_record.created_at) > timedelta(minutes=5):
            return jsonify({'error': 'OTP expired'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        
        OTPRecord.query.filter_by(email=email).delete()
        db.session.commit()
        
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        db.create_all()
        data = request.json
        email = data.get('email')
        password = data.get('password')
    
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return jsonify({'message': 'Login successful', 'username': user.username, 'email': user.email})
        
        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.json
        email = data.get('email')
        otp = data.get('otp')
        new_password = data.get('new_password')
        
        if not all([email, otp, new_password]):
            return jsonify({'error': 'Missing data fields'}), 400
            
        otp_record = OTPRecord.query.filter_by(email=email, otp=otp).first()
        if not otp_record or (datetime.utcnow() - otp_record.created_at) > timedelta(minutes=5):
            return jsonify({'error': 'Invalid or expired OTP'}), 400
            
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        user.password_hash = generate_password_hash(new_password)
        OTPRecord.query.filter_by(email=email).delete()
        db.session.commit()
        
        return jsonify({'message': 'Password reset successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-account', methods=['DELETE'])
@login_required
def delete_account():
    try:
        user_id = current_user.id
        
        # Explicit cascade deletions
        Transaction.query.filter_by(user_id=user_id).delete()
        Debt.query.filter_by(user_id=user_id).delete()
        TrainingData.query.filter_by(user_id=user_id).delete()
        
        # Delete user record
        db.session.delete(current_user)
        db.session.commit()
        
        logout_user() # Clear session
        return jsonify({'message': 'Account and all associated data permanently deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'})

@app.route('/api/check_auth', methods=['GET'])
def check_auth():
    if current_user.is_authenticated:
        return jsonify({'isAuthenticated': True, 'username': current_user.username})
    return jsonify({'isAuthenticated': False})

@app.route('/api/transactions', methods=['GET', 'POST'])
@login_required
def handle_transactions():
    if request.method == 'GET':
        transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).all()
        return jsonify([{
            'id': t.id,
            'amount': t.amount,
            'description': t.description,
            'type': t.type,
            'category': t.category,
            'date': t.date.isoformat()
        } for t in transactions])
    
    elif request.method == 'POST':
        data = request.json
        new_transaction = Transaction(
            amount=data['amount'],
            description=data['description'],
            type=data['type'],
            category=data['category'],
            date=datetime.fromisoformat(data['date'].replace('Z', '+00:00')) if 'date' in data else datetime.utcnow(),
            user_id=current_user.id
        )
        db.session.add(new_transaction)
        db.session.commit()
        return jsonify({'message': 'Transaction added', 'id': new_transaction.id}), 201

@app.route('/api/transactions/<int:id>', methods=['DELETE'])
@login_required
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(transaction)
    db.session.commit()
    return jsonify({'message': 'Transaction deleted'})

@app.route('/api/debts', methods=['GET', 'POST'])
@login_required
def handle_debts():
    if request.method == 'GET':
        debts = Debt.query.filter_by(user_id=current_user.id).order_by(Debt.date.desc()).all()
        return jsonify([{
            'id': d.id,
            'amount': d.amount,
            'name': d.name,
            'type': d.type,
            'description': d.description,
            'date': d.date.isoformat()
        } for d in debts])
    
    elif request.method == 'POST':
        data = request.json
        new_debt = Debt(
            amount=data['amount'],
            name=data['name'],
            type=data['type'],
            description=data.get('description', ''),
            date=datetime.fromisoformat(data['date'].replace('Z', '+00:00')) if 'date' in data else datetime.utcnow(),
            user_id=current_user.id
        )
        db.session.add(new_debt)
        db.session.commit()
        return jsonify({'message': 'Debt added', 'id': new_debt.id}), 201

@app.route('/api/debts/<int:id>', methods=['DELETE'])
@login_required
def delete_debt(id):
    debt = Debt.query.get_or_404(id)
    if debt.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(debt)
    db.session.commit()
    return jsonify({'message': 'Debt deleted'})

@app.route('/api/debts/clear/<name>', methods=['DELETE'])
@login_required
def clear_person_debts(name):
    try:
        # Delete all debts where name matches (case-insensitive-ish depending on DB) and user_id matches
        # Using a like or direct match based on how they were saved
        debts_to_delete = Debt.query.filter(
            Debt.user_id == current_user.id,
            Debt.name.ilike(name)
        ).all()
        
        count = len(debts_to_delete)
        for d in debts_to_delete:
            db.session.delete(d)
        
        db.session.commit()
        return jsonify({'message': f'Cleared {count} debt entries for {name}'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# --- AI "Bro-Bot" Parser ---
import re

@app.route('/api/train', methods=['POST'])
@login_required
def train_bot():
    data = request.json
    keyword = data.get('keyword', '').lower().strip()
    target_type = data.get('target_type')
    target_category = data.get('target_category')
    
    if not keyword:
        return jsonify({'error': 'Keyword required'}), 400
        
    # Check if exists, update or create
    entry = TrainingData.query.filter_by(user_id=current_user.id, keyword=keyword).first()
    if entry:
        entry.target_type = target_type
        entry.target_category = target_category
    else:
        entry = TrainingData(
            keyword=keyword,
            target_type=target_type,
            target_category=target_category,
            user_id=current_user.id
        )
        db.session.add(entry)
    
    db.session.commit()
    return jsonify({'message': f'Bot learned: {keyword} -> {target_type}'})

@app.route('/api/vocabulary', methods=['GET'])
@login_required
def get_vocabulary():
    vocab = TrainingData.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': v.id,
        'keyword': v.keyword,
        'target_type': v.target_type,
        'target_category': v.target_category
    } for v in vocab])

@app.route('/api/train/<int:id>', methods=['DELETE'])
@login_required
def delete_vocabulary(id):
    entry = TrainingData.query.get_or_404(id)
    if entry.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'message': 'Rule deleted'})

# --- Social & Connectivity Features ---

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    # Find all users except current one
    users = User.query.filter(User.id != current_user.id).all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email
    } for u in users])

@app.route('/api/nudges', methods=['GET', 'POST'])
@login_required
def handle_nudges():
    if request.method == 'POST':
        data = request.json
        receiver_id = data.get('receiver_id')
        if not receiver_id:
            return jsonify({'error': 'Receiver required'}), 400
            
        new_nudge = Nudge(
            sender_id=current_user.id,
            receiver_id=receiver_id,
            amount=data.get('amount'),
            message=data.get('message')
        )
        db.session.add(new_nudge)
        db.session.commit()
        return jsonify({'message': 'Nudge sent successfully'})
    
    else:
        # Get nudges for current user
        nudges = Nudge.query.filter_by(receiver_id=current_user.id, is_read=False).order_by(Nudge.created_at.desc()).all()
        return jsonify([{
            'id': n.id,
            'sender_name': n.sender.username,
            'amount': n.amount,
            'message': n.message,
            'date': n.created_at.isoformat()
        } for n in nudges])

@app.route('/api/nudges/read/<int:id>', methods=['POST'])
@login_required
def mark_nudge_read(id):
    nudge = Nudge.query.get_or_404(id)
    if nudge.receiver_id == current_user.id:
        nudge.is_read = True
        db.session.commit()
    return jsonify({'message': 'Nudge marked read'})

@app.route('/api/messages', methods=['POST'])
@login_required
def send_message():
    data = request.json
    receiver_id = data.get('receiver_id')
    content = data.get('content')
    
    if not receiver_id or not content:
        return jsonify({'error': 'Receiver and content required'}), 400
        
    new_msg = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content
    )
    db.session.add(new_msg)
    db.session.commit()
    return jsonify({
        'message': 'Message sent',
        'id': new_msg.id,
        'sender_id': new_msg.sender_id,
        'content': new_msg.content,
        'date': new_msg.created_at.isoformat()
    })

@app.route('/api/messages/<int:friend_id>', methods=['GET'])
@login_required
def get_messages(friend_id):
    try:
        # Fetch messages between current user and friend
        messages = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == friend_id)) |
            ((Message.sender_id == friend_id) & (Message.receiver_id == current_user.id))
        ).order_by(Message.created_at.asc()).all()
        
        result = [{
            'id': m.id,
            'sender_id': m.sender_id,
            'content': m.content,
            'date': m.created_at.isoformat()
        } for m in messages]
        
        # EPHEMERAL LOGIC: Delete messages sent to the current user once they are read
        received_messages = [m for m in messages if m.receiver_id == current_user.id]
        if received_messages:
            for m in received_messages:
                db.session.delete(m)
            db.session.commit()
            
        return jsonify(result)
    except Exception as e:
        db.session.rollback()
        print(f"Chat fetch error: {e}")
        return jsonify([]), 500

@app.route('/api/messages/cleanup', methods=['POST'])
@login_required
def cleanup_chat():
    # Explicitly clear messages for current user
    Message.query.filter_by(receiver_id=current_user.id).delete()
    db.session.commit()
    return jsonify({'message': 'Inbox cleared'})

@app.route('/api/ai_parse', methods=['POST'])
@login_required
def ai_parse():
    data = request.json
    text = data.get('text', '').lower()
    
    # 1. TEXT NORMALIZATION (Numbers & Units)
    number_replacements = {
        r'\bone hundred\b': '100', r'\bhundred\b': '100', r'\bek so\b': '100', r'\bek sau\b': '100', r'\bsau\b': '100', r'\bso\b': '100',
        r'\bdo so\b': '200', r'\bdo sau\b': '200', r'\btwo hundred\b': '200',
        r'\bteen so\b': '300', r'\bteen sau\b': '300', r'\bthree hundred\b': '300',
        r'\bchar so\b': '400', r'\bchar sau\b': '400', r'\bfour hundred\b': '400',
        r'\bpanch so\b': '500', r'\bpanch sau\b': '500', r'\bfive hundred\b': '500',
        r'\bche so\b': '600', r'\bche sau\b': '600', r'\bsix hundred\b': '600',
        r'\bsaat so\b': '700', r'\bsaat sau\b': '700', r'\bseven hundred\b': '700',
        r'\baath so\b': '800', r'\baath sau\b': '800', r'\beight hundred\b': '800',
        r'\bnau so\b': '900', r'\bnau sau\b': '900', r'\bnine hundred\b': '900',
        r'\bek hazar\b': '1000', r'\bhazar\b': '1000', r'\bone thousand\b': '1000', r'\bthousand\b': '1000',
        r'\bten\b': '10', r'\bdas\b': '10', r'\btwenty\b': '20', r'\bbees\b': '20', r'\bthirty\b': '30', r'\btees\b': '30',
        r'\bforty\b': '40', r'\bchalis\b': '40', r'\bfifty\b': '50', r'\bpachas\b': '50', r'\bsixty\b': '60', r'\bsaath\b': '60',
        r'\bseventy\b': '70', r'\bsattar\b': '70', r'\beighty\b': '80', r'\bassi\b': '80', r'\bninety\b': '90', r'\bnabbe\b': '90',
        r'\bone\b': '1', r'\bek\b': '1', r'\btwo\b': '2', r'\bdo\b': '2', r'\bthree\b': '3', r'\bteen\b': '3', r'\bfour\b': '4', r'\bchar\b': '4', r'\bfive\b': '5', r'\bpanch\b': '5',
    }
    for pattern, digit in number_replacements.items():
        text = re.sub(pattern, digit, text)
    
    # 2. DATASETS (Massive Powerhouse)
    CATEGORIES = {
        'Food': ['pizza', 'burger', 'momos', 'biryani', 'chai', 'tea', 'coffee', 'sandwich', 'thali', 'samosa', 'kachori', 'bread', 'milk', 'doodh', 'paneer', 'chicken', 'meat', 'egg', 'soda', 'pepsi', 'coke', 'maggi', 'pasta', 'zomato', 'swiggy', 'kfc', 'mcdonald', 'dominos', 'pizza hut', 'subway', 'starbucks', 'blinkit', 'zepto', 'khana', 'dinner', 'lunch', 'snack', 'restaurant', 'ice cream', 'pani', 'water', 'biscuit', 'cake', 'munch', 'chocolate'],
        'Transport': ['uber', 'ola', 'rapido', 'indriver', 'blusmart', 'auto', 'rickshaw', 'cab', 'taxi', 'metro', 'train', 'bus', 'ticket', 'flight', 'indigo', 'air india', 'akasa', 'spicejet', 'petrol', 'diesel', 'cng', 'fuel', 'toll', 'parking', 'mechanic', 'service', 'tyres', 'wash', 'cycle', 'bike', 'car'],
        'Shopping': ['amazon', 'flipkart', 'myntra', 'ajio', 'meesho', 'nykaa', 'lenskart', 'bigbasket', 'groceries', 'sabzi', 'fruits', 'market', 'mall', 'zara', 'pantaloons', 'reliance', 'h&m', 'max', 'westside', 'clothes', 'shoes', 'bags', 'electronics', 'mobile', 'laptop', 'gadget', 'rashan', 'kirana', 'delivery', 'courier'],
        'Bills': ['jio', 'airtel', 'vi', 'bsnl', 'recharge', 'wifi', 'broadband', 'electricity', 'bijli', 'water', 'gas', 'cylinder', 'piped gas', 'rent', 'maintenance', 'society', 'tax', 'insurance', 'lic', 'emi', 'loan'],
        'Health': ['medicine', 'dawai', 'doctor', 'fees', 'clinic', 'hospital', 'lab', 'apollo', 'pharmeasy', 'tata 1mg', 'physio', 'checkup', 'test', 'blood'],
        'Fun': ['cinema', 'pvr', 'inox', 'movie', 'netflix', 'prime', 'spotify', 'hotstar', 'youtube', 'gaming', 'ps5', 'xbox', 'steam', 'gym', 'fitness', 'club', 'party', 'drinks', 'beer', 'pub', 'trip', 'travel', 'gold'],
        'Personal': ['gift', 'birthday', 'wedding', 'shadi', 'donation', 'mandir', 'charity', 'stationary', 'books', 'xerox', 'print', 'fees']
    }
    
    # 100+ Common Indian Names for disambiguation
    INDIAN_NAMES = ['rahul', 'rohit', 'shyam', 'ram', 'aman', 'anjali', 'priya', 'pooja', 'neha', 'karan', 'arjun', 'aditya', 'deepa', 'shanti', 'sonu', 'monu', 'chintu', 'bittu', 'pinky', 'ravi', 'vijay', 'sanjay', 'ajay', 'suresh', 'mukesh', 'rajesh', 'dinesh', 'vinod', 'sunil', 'anil', 'pramod', 'manoj', 'ashok', 'laxmi', 'savita', 'kavita', 'rekha', 'suman', 'meena', 'sarita', 'kavya', 'ishan', 'aryan', 'kabir', 'vivaan', 'advait', 'anaya', 'shanaya', 'myra', 'kyra', 'saanvi', 'aavya', 'mummy', 'papa', 'bhai', 'behen', 'didi', 'bhaiya', 'uncle', 'aunty', 'dadi', 'dada', 'nani', 'nana', 'kapil', 'mohit', 'deepak', 'gaurav', 'vikas', 'pankaj', 'abhishek', 'sameer', 'isha', 'tanvi', 'ria', 'diya', 'manish', 'yogesh', 'akash', 'vishal', 'sandeep', 'nitin', 'tushar', 'nikhil', 'varun', 'kunal']
    
    STOP_WORDS = [
        'ko', 'ne', 'se', 'ka', 'ki', 'ke', 'liye', 'aur', 'and', 'me', 'par', 'per', 'to', 'from', 'for', 'with', 'by', 'the', 'is', 'at', 
        'gave', 'given', 'diya', 'diye', 'mila', 'mile', 'received', 'got', 'sent', 'bheja', 'bheje', 'pay', 'paid', 'transferred', 
        'dalya', 'dala', 'dal', 'add', 'added', 'put', 'rs', 'rupee', 'rupees', 'rupya', 'rupaye', 'bucks', 'rps', 'in', 'of',
        'main', 'maine', 'mere', 'hum', 'mujh', 'apne', 'yaaron', 'bro', 'yaar', 'guys', 'guyz', 'please', 'pls', 'tha', 'thi', 'the',
        'kal', 'aaj', 'parso', 'today', 'yesterday', 'now', 'now', 'abhi', 'sent', 'received', 'liya', 'diya', 'done', 'ok', 'yes', 'no',
        'paisa', 'paise', 'money', 'cash', 'upi', 'gpay', 'phonepay', 'paytm', 'bank', 'account'
    ]
    ALL_CAT_KEYWORDS = [kw for lst in CATEGORIES.values() for kw in lst]

    # 3. SEGMENTATION & PRE-PROCESSING (Advanced Multi-Entry)
    # Use Lookahead to split by separators ONLY if followed by a number or a category keyword
    # This prevents splitting "Rahul aur Aman" but allows splitting "100 burger aur 200 pizza"
    # Separators: and, aur, plus, or, bhi, phir, main, maine, also
    split_pattern = r'\s+(?:and|aur|plus|or|bhi|phir|main|maine|also)(?=\s+(?:\d+|' + '|'.join(ALL_CAT_KEYWORDS) + r'))\s*|\s*,\s*(?=\d+)'
    raw_segments = re.split(split_pattern, text)
    
    segments = []
    for s in raw_segments:
        s = s.strip()
        if not s: continue
        
        # Unit normalization (1.5k -> 1500)
        s = re.sub(r'((?:\d+\.?\d*)|(?:\.\d+))\s*k\b', lambda m: str(int(float(m.group(1)) * 1000)), s)
        s = re.sub(r'((?:\d+\.?\d*)|(?:\.\d+))\s*l\b', lambda m: str(int(float(m.group(1)) * 100000)), s)
        
        # Multi-Name Handling (Vocabulary-Agnostic)
        marker_match = re.search(r'(ko|ne|se)', s)
        if marker_match:
            marker = marker_match.group(1)
            prefix = s[:marker_match.start()].strip()
            # Split prefix by list separators
            parts = re.split(r'\s+(?:and|aur|or|plus|comma)\s*|\s*,\s*', prefix)
            found_names = []
            for p in parts:
                p_clean = p.strip().lower()
                # AGNOSTIC RULE: If not a stop word/category, it's a candidate name
                if p_clean and p_clean not in STOP_WORDS and p_clean not in ALL_CAT_KEYWORDS and not p_clean.isdigit():
                    found_names.append(p_clean.capitalize())
            
            if len(found_names) > 1:
                base_text = s[marker_match.start():].strip()
                for name in found_names:
                    segments.append(f"{name} {base_text}")
                continue
        
        # Split by multiple numbers (Fallback implicit split)
        nums = list(re.finditer(r'(?<![a-zA-Z])\d+(?![a-zA-Z])', s))
        if len(nums) > 1:
            last_pos = 0
            for i in range(1, len(nums)):
                if nums[i].group().startswith('20') and len(nums[i].group()) == 4: continue
                split_pos = nums[i].start()
                segments.append(s[last_pos:split_pos].strip())
                last_pos = split_pos
            segments.append(s[last_pos:].strip())
        else:
            segments.append(s.strip())

    results = []
    custom_rules = TrainingData.query.filter_by(user_id=current_user.id).all()
    rules_map = {r.keyword: (r.target_type, r.target_category) for r in custom_rules}

    # 4. UNIVERSAL EXTRACTION ENGINE
    for seg in segments:
        seg = seg.strip()
        if not seg: continue
            
        # A. EXTRACT AMOUNT
        amt_match = re.search(r'(\d+(?:\.\d+)?)', seg)
        if not amt_match: continue
        amount = float(amt_match.group(1))
        
        # B. INITIALIZE ENTITIES
        is_debt = False
        is_income = False
        person_name = None
        debt_type = None
        found_category = None
        found_via_marker = False
        
        # C. DETECT CATEGORY (Pre-Scan)
        for cat, keywords in CATEGORIES.items():
            if any(re.search(fr'\b{kw}\b', seg) for kw in keywords):
                found_category = cat
                break

        clean_seg = re.sub(r'\b(rs|rupee|rupees|rupya|rupaye)\b', '', seg).strip()
        words = re.findall(r'\b\s?[\w-]+\b', clean_seg)
        
        # Priority 1: Marker-based (Vocabulary-Agnostic)
        marker_match = re.search(r'([\w-]+)\s+(ko|ne|se)\b', clean_seg)
        if marker_match:
            potential = marker_match.group(1).lower()
            if potential not in STOP_WORDS and potential not in ALL_CAT_KEYWORDS and not potential.isdigit():
                person_name = potential.capitalize()
                found_via_marker = True

        # D. DETECT TYPE (Hinglish Decision Tree)
        if re.search(r'\bne\b.*(?:diya|diye|mila)\b', seg) or re.search(r'\bse\b.*\bliya\b', seg) or re.search(r'\bborrowed\b', seg) or re.search(r'\bse\b.*\bmile\b', seg):
            is_debt = True
            debt_type = 'borrowed'
        elif re.search(r'\bko\b.*(?:diya|diye)\b', seg) or re.search(r'\blent\b', seg) or re.search(r'\bdiye\b.*\bko\b', seg):
            if found_via_marker:
                is_debt = True
                debt_type = 'lent'
            elif found_category and not re.search(r'\b(lent|borrowed)\b', seg):
                is_debt = False # Treat as expense for someone
            else:
                is_debt = True
                debt_type = 'lent'
        elif re.search(r'\bmujhe\b.*(?:mila|diya|diye|mile)\b', seg) or any(re.search(fr'\b{kw}\b', seg) for kw in ['salary', 'income', 'profit', 'mila', 'aaye', 'credited']):
            is_income = True

        # E. POSITION-INDEPENDENT NAME EXTRACTION (Agnostic v4)
        # Priority 2: Vocabulary-based (Safety Net for marker-less)
        if not person_name:
            for w in words:
                w_clean = w.strip().lower()
                if w_clean in INDIAN_NAMES:
                    person_name = w_clean.capitalize()
                    break
        
        # Priority 3: Fallback (Contextual Fallback)
        if not person_name and (is_debt or re.search(r'\b(ne|ko|se)\b', seg)):
            for w in words:
                w_clean = w.strip().lower()
                if w_clean not in STOP_WORDS and w_clean not in ALL_CAT_KEYWORDS and not w_clean.isdigit():
                    person_name = w_clean.capitalize()
                    break

        # F. CLEAN DESCRIPTION (Segment Deletion)
        desc_parts = []
        for w in words:
            w_clean = w.strip().lower()
            # 1. Skip amount
            if w_clean == str(int(amount)) or w_clean == f"{amount:.1f}": continue
            # 2. Skip person_name
            if person_name and w_clean == person_name.lower(): continue
            # 3. Skip pure stop-words
            if w_clean in STOP_WORDS: continue
            # 4. Skip marker words
            if w_clean in ['liye', 'ke', 'ka', 'ki', 'ne', 'se', 'ko', 'diya', 'diye', 'liya', 'mila', 'mile']: continue
            desc_parts.append(w.strip())
        
        final_description = " ".join(desc_parts).strip()
        if not final_description:
            final_description = found_category or ("Debt" if is_debt else "Transaction")

        # G. CUSTOM RULE OVERRIDE
        for kw, (t_type, t_cat) in rules_map.items():
            if kw in seg:
                if t_type == 'income': is_income = True
                elif t_type in ['lent', 'borrowed']: 
                    is_debt = True
                    debt_type = t_type
                if t_cat: found_category = t_cat
                break

        # H. FINAL ASSEMBLY
        if is_debt and person_name:
            results.append({
                'is_debt': True,
                'amount': amount,
                'name': person_name,
                'type': debt_type,
                'description': final_description if final_description != "Debt" else f"{debt_type} transaction"
            })
        elif is_income:
            results.append({
                'is_debt': False,
                'amount': amount,
                'type': 'income',
                'category': found_category or 'General',
                'description': final_description or 'Income'
            })
        else:
            results.append({
                'is_debt': False,
                'amount': amount,
                'type': 'expense',
                'category': found_category or 'Other',
                'description': final_description or 'Expense'
            })

    return jsonify(results)

    return jsonify(results)

# --- Serve Frontend (Fallback for Local Dev) ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path.startswith('api/'):
        return jsonify({'error': 'Not Found'}), 404
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# No app.run() needed for Vercel
if __name__ == '__main__':
    app.run(debug=True, port=5001)
