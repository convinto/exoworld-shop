import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import re
from flask_mail import Mail, Message as MailMessage
from dotenv import load_dotenv
import os
from PIL import Image

load_dotenv()  # загружает переменные из .env

app = Flask(__name__)

@app.after_request
def add_cache_control(response):
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    return response

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'vbelarus2026')
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'   # ЭТА СТРОКА ОБЯЗАТЕЛЬНА

if os.environ.get('AMVERA'):
    db_path = '/data/shop.db'
else:
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'shop.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Настройки почты
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.mail.ru')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

db = SQLAlchemy(app)   # Теперь ошибки не будет
mail = Mail(app)

# UPLOAD_FOLDER = 'static/uploads'

if os.environ.get('AMVERA'):
    UPLOAD_FOLDER = '/data/uploads'
else:
    UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Модели ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    orders = db.relationship('Order', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    image = db.Column(db.String(200))
    category = db.Column(db.String(50))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.DateTime, server_default=db.func.now())
    total = db.Column(db.Float)
    status = db.Column(db.String(20), default='Новый')
    address = db.Column(db.Text)
    items = db.relationship('OrderItem', backref='order', lazy=True)
    phone = db.Column(db.String(20), nullable=False, default='')
    comment = db.Column(db.Text, default='')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    product = db.relationship('Product')

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), default='general')
    image = db.Column(db.String(200), default='default_article.jpg')
    date = db.Column(db.DateTime, server_default=db.func.now())
    views = db.Column(db.Integer, default=0)

class Consultation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    animal_type = db.Column(db.String(100), nullable=False)  # кого хочет
    budget = db.Column(db.String(100))                       # бюджет
    experience = db.Column(db.String(500))                   # опыт содержания
    comment = db.Column(db.Text)                             # доп. пожелания
    status = db.Column(db.String(20), default='Новая')       # Новая, В работе, Завершена
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class Ad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    # description = db.Column(db.Text, nullable=False)
    ad_type = db.Column(db.String(20), nullable=False)  # 'sale' или 'buy'
    price = db.Column(db.Float, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    status = db.Column(db.String(20), default='pending', index=True)
    ad_type = db.Column(db.String(20), index=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    # Удалено поле contacts и show_contacts
    image = db.Column(db.String(200), default='default_ad.jpg')
    # user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='ads')
    # status = db.Column(db.String(20), default='pending')  # pending, active, closed, rejected
    # created_at = db.Column(db.DateTime, server_default=db.func.now())
    admin_comment = db.Column(db.Text, default='')

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey('ad.id'), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())
    # Добавляем отношение к объявлению
    ad = db.relationship('Ad', backref='conversations', foreign_keys=[ad_id])

class ConversationParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # когда пользователь последний раз читал
    last_read_at = db.Column(db.DateTime)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    is_read = db.Column(db.Boolean, default=False)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='chat_messages')
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now(), index =True)

class TeamApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    telegram = db.Column(db.String(100))
    experience = db.Column(db.Text, nullable=False)   # опыт с экзотикой
    motivation = db.Column(db.Text, nullable=False)   # почему хочет в команду
    skills = db.Column(db.Text)                       # что умеет (писать, снимать и т.д.)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    status = db.Column(db.String(20), default='new')  # new, viewed, contacted

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Маршруты ---

@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            msg = ChatMessage(user_id=current_user.id, message=message)
            db.session.add(msg)
            db.session.commit()
        return redirect(url_for('chat'))
    
    messages = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).all()
    return render_template('chat.html', messages=messages)

@app.route('/chat/messages')
@login_required
def chat_messages():
    messages = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).all()
    data = []
    for msg in messages:
        data.append({
            'username': msg.user.username,
            'message': msg.message,
            'timestamp': msg.timestamp.strftime('%d.%m.%Y %H:%M')
        })
    return {'messages': data}

@app.route('/')
def index():
    products = Product.query.order_by(Product.id.desc()).limit(6).all()
    recent_articles = Article.query.order_by(Article.date.desc()).limit(3).all()
    return render_template('index.html', products=products, recent_articles=recent_articles)

@app.route('/product/<int:id>')
def product(id):
    product = Product.query.get_or_404(id)
    return render_template('product.html', product=product)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    cart = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    flash(f'Товар "{product.name}" добавлен в корзину', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/cart')
def cart():
    cart_items = []
    total = 0
    cart_data = session.get('cart', {})
    for product_id, quantity in cart_data.items():
        product = Product.query.get(int(product_id))
        if product:
            item_total = product.price * quantity
            total += item_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total
            })
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    if str(product_id) in cart:
        del cart[str(product_id)]
        session['cart'] = cart
        flash('Товар удален из корзины', 'info')
    return redirect(url_for('cart'))

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})
    if quantity <= 0:
        cart.pop(str(product_id), None)
    else:
        cart[str(product_id)] = quantity
    session['cart'] = cart
    flash('Корзина обновлена', 'info')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        address = request.form['address']
        phone = request.form['phone']
        comment = request.form.get('comment', '')
        
        # Проверка согласия
        agree = request.form.get('agree_privacy')
        if not agree:
            flash('Необходимо согласие с политикой конфиденциальности и пользовательским соглашением', 'danger')
            return redirect(url_for('checkout'))
        
        cart_data = session.get('cart', {})
        if not cart_data:
            flash('Корзина пуста', 'warning')
            return redirect(url_for('cart'))
        
        order = Order(user_id=current_user.id, total=0, address=address, phone=phone, comment=comment)
        db.session.add(order)
        db.session.commit()
        
        total = 0
        for product_id, quantity in cart_data.items():
            product = Product.query.get(int(product_id))
            if product and product.stock >= quantity:
                item_total = product.price * quantity
                total += item_total
                order_item = OrderItem(order_id=order.id, product_id=product.id, 
                                       quantity=quantity, price=product.price)
                db.session.add(order_item)
                product.stock -= quantity
            else:
                flash(f'Товара "{product.name}" недостаточно на складе', 'danger')
                db.session.rollback()
                return redirect(url_for('cart'))
        
        order.total = total
        db.session.commit()
        session.pop('cart', None)
        flash('Заказ успешно оформлен! Мы свяжемся с вами в ближайшее время.', 'success')
        return redirect(url_for('index'))
    
    cart_data = session.get('cart', {})
    if not cart_data:
        return redirect(url_for('cart'))
    return render_template('checkout.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        agree = request.form.get('agree_privacy')
        if not agree:
            flash('Необходимо согласие с политикой конфиденциальности и пользовательским соглашением', 'danger')
            return redirect(url_for('register'))

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Пользователь с таким именем уже существует', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Регистрация прошла успешно! Теперь вы можете войти', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Вы успешно вошли в систему', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

# --- Простая админ-панель ---
@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    products = Product.query.all()
    orders = Order.query.all()
    return render_template('admin/dashboard.html', products=products, orders=orders)

@app.route('/admin/product/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        category = request.form['category']
        
        # Обработка изображения
        image_file = request.files.get('image')
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            # Добавляем временную метку, чтобы избежать дублирования
            name_parts = os.path.splitext(filename)
            unique_name = f"{name_parts[0]}_{int(os.times().system)}{name_parts[1]}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            image_file.save(image_path)
            image_filename = unique_name
        else:
            image_filename = 'default.jpg'  # картинка-заглушка
        
        product = Product(name=name, description=description, price=price, 
                         stock=stock, category=category, image=image_filename)
        db.session.add(product)
        db.session.commit()
        flash('Товар добавлен', 'success')
        return redirect(url_for('admin_panel'))
    
    return render_template('admin/edit_product.html')

@app.route('/join', methods=['GET', 'POST'])
@login_required
def join_team():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        telegram = request.form.get('telegram', '')
        experience = request.form['experience']
        motivation = request.form['motivation']
        skills = request.form.get('skills', '')
        
        # Проверка согласия
        agree = request.form.get('agree_privacy')
        if not agree:
            flash('Необходимо согласие с политикой конфиденциальности и пользовательским соглашением', 'danger')
            return redirect(url_for('join_team'))

        application = TeamApplication(
            name=name, email=email, telegram=telegram,
            experience=experience, motivation=motivation, skills=skills
        )
        db.session.add(application)
        db.session.commit()

        try:
            msg = MailMessage(
            f'Новая заявка в команду от {name}',
            sender=app.config['MAIL_USERNAME'],
            recipients=['info-convinto@mail.ru']
            )
            msg.body = f"""
Имя: {name}
Email: {email}
Telegram: {telegram or 'не указан'}

Опыт с экзотическими животными:
{experience}

Мотивация:
{motivation}

Навыки (что умеет):
{skills or 'не указано'}

---
Заявка #{application.id} от {application.created_at.strftime('%d.%m.%Y %H:%M')}
            """
            mail.send(msg)
            flash('Спасибо! Ваша заявка принята. Мы свяжемся с вами в ближайшее время.', 'success')
        except Exception as e:
            app.logger.error(f'Ошибка отправки письма: {e}')
            flash('Заявка сохранена, но уведомление не отправлено. Мы свяжемся с вами.', 'warning')
        
        return redirect(url_for('join_team'))
    
    return render_template('join.html')

@app.route('/admin/team-application/<int:id>')
@login_required
def admin_team_application_detail(id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    app = TeamApplication.query.get_or_404(id)
    return render_template('admin/team_application_detail.html', application=app)

@app.route('/admin/team-application/<int:id>/status', methods=['POST'])
@login_required
def admin_update_application_status(id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    app = TeamApplication.query.get_or_404(id)
    new_status = request.form['status']
    app.status = new_status
    db.session.commit()
    flash('Статус обновлен', 'success')
    return redirect(url_for('admin_team_applications'))



@app.route('/admin/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = float(request.form['price'])
        product.stock = int(request.form['stock'])
        product.category = request.form['category']
        
        # Обработка нового изображения
        image_file = request.files.get('image')
        if image_file and allowed_file(image_file.filename):
            # Удаляем старый файл, если он не default.jpg
            if product.image and product.image != 'default.jpg':
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = secure_filename(image_file.filename)
            # Добавляем временную метку для уникальности
            name_parts = os.path.splitext(filename)
            unique_name = f"{name_parts[0]}_{int(os.times().system)}{name_parts[1]}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            image_file.save(image_path)
            product.image = unique_name
        
        db.session.commit()
        flash('Товар обновлен', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/edit_product.html', product=product)

@app.route('/admin/product/delete/<int:id>')
@login_required
def delete_product(id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    product = Product.query.get_or_404(id)
    # Удаляем файл изображения, если он не стандартный
    if product.image and product.image != 'default.jpg':
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image)
        if os.path.exists(image_path):
            os.remove(image_path)
    db.session.delete(product)
    db.session.commit()
    flash('Товар удален', 'warning')
    return redirect(url_for('admin_products'))  # перенаправляем на список товаров

@app.route('/admin/orders')
@login_required
def admin_orders():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    orders = Order.query.order_by(Order.date.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/order/<int:order_id>/status', methods=['POST'])
@login_required
def update_order_status(order_id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    order = Order.query.get_or_404(order_id)
    new_status = request.form['status']
    order.status = new_status
    db.session.commit()
    flash(f'Статус заказа №{order.id} изменён на "{new_status}"', 'success')
    return redirect(url_for('admin_orders'))

@app.route('/admin/order/<int:order_id>')
@login_required
def admin_order_detail(order_id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_detail.html', order=order)

@app.route('/admin/products')
@login_required
def admin_products():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template('admin/products.html', products=products)


@app.route('/encyclopedia')
def encyclopedia():
    articles = Article.query.order_by(Article.date.desc()).all()
    return render_template('encyclopedia.html', articles=articles)

@app.route('/encyclopedia/<string:slug>')
def article_detail(slug):
    article = Article.query.filter_by(slug=slug).first_or_404()
    article.views += 1
    db.session.commit()
    return render_template('article.html', article=article)

@app.route('/admin/articles')
@login_required
def admin_articles():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    articles = Article.query.order_by(Article.date.desc()).all()
    return render_template('admin/articles.html', articles=articles)

@app.route('/admin/article/add', methods=['GET', 'POST'])
@login_required
def add_article():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form['category']
        
        # Генерация slug из заголовка (транслитерация упрощённая)
        import re
        slug = re.sub(r'[\s_]+', '-', title.lower())
        slug = re.sub(r'[^a-zа-яё0-9-]', '', slug)
        # Проверка уникальности
        if Article.query.filter_by(slug=slug).first():
            slug = f"{slug}-{int(os.times().system)}"
        
        # Обработка изображения
        image_file = request.files.get('image')
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            name_parts = os.path.splitext(filename)
            unique_name = f"{name_parts[0]}_{int(os.times().system)}{name_parts[1]}"
            image_path = os.path.join('static/article_images', unique_name)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image_file.save(image_path)
            image = unique_name
        else:
            image = 'default_article.jpg'
        
        article = Article(title=title, slug=slug, content=content, category=category, image=image)
        db.session.add(article)
        db.session.commit()
        flash('Статья добавлена', 'success')
        return redirect(url_for('admin_articles'))
    
    return render_template('admin/edit_article.html')

@app.route('/admin/article/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_article(id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    article = Article.query.get_or_404(id)
    if request.method == 'POST':
        article.title = request.form['title']
        article.content = request.form['content']
        article.category = request.form['category']
        
        # Обновление slug, если изменился заголовок
        new_slug = re.sub(r'[\s_]+', '-', article.title.lower())
        new_slug = re.sub(r'[^a-zа-яё0-9-]', '', new_slug)
        if new_slug != article.slug and not Article.query.filter_by(slug=new_slug).first():
            article.slug = new_slug
        
        # Обработка нового изображения
        image_file = request.files.get('image')
        if image_file and allowed_file(image_file.filename):
            # Удаляем старое, если не дефолтное
            if article.image and article.image != 'default_article.jpg':
                old_path = os.path.join('static/article_images', article.image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = secure_filename(image_file.filename)
            name_parts = os.path.splitext(filename)
            unique_name = f"{name_parts[0]}_{int(os.times().system)}{name_parts[1]}"
            image_path = os.path.join('static/article_images', unique_name)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image_file.save(image_path)
            article.image = unique_name
        
        db.session.commit()
        flash('Статья обновлена', 'success')
        return redirect(url_for('admin_articles'))
    
    return render_template('admin/edit_article.html', article=article)

@app.route('/admin/article/delete/<int:id>')
@login_required
def delete_article(id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    article = Article.query.get_or_404(id)
    # Удаляем изображение, если не дефолтное
    if article.image and article.image != 'default_article.jpg':
        file_path = os.path.join('static/article_images', article.image)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.session.delete(article)
    db.session.commit()
    flash('Статья удалена', 'warning')
    return redirect(url_for('admin_articles'))

# --- Услуги подбора ---
@app.route('/consultation', methods=['GET', 'POST'])
def consultation():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        animal_type = request.form['animal_type']
        budget = request.form.get('budget', '')
        experience = request.form.get('experience', '')
        comment = request.form.get('comment', '')
        
        consultation = Consultation(
            name=name, email=email, phone=phone,
            animal_type=animal_type, budget=budget,
            experience=experience, comment=comment
        )
        db.session.add(consultation)
        db.session.commit()
        
        # Здесь можно отправить email администратору (опционально)
        msg = Message(subject='Новая заявка на подбор питомца',
              sender=app.config['MAIL_USERNAME'],
              recipients=['info-convinto@mail.ru'])
        msg.body = f"Имя: {name}\nEmail: {email}\nТелефон: {phone}\nЖивотное: {animal_type}\nБюджет: {budget}\nОпыт: {experience}\nКомментарий: {comment}"
        try:
            mail.send(msg)
        except Exception as e:
            app.logger.error(f'Ошибка отправки письма: {e}')
        flash('Спасибо! Ваша заявка принята. Мы свяжемся с вами в ближайшее время.', 'success')
        return redirect(url_for('consultation'))
    
    return render_template('consultation.html')

@app.route('/admin/consultations')
@login_required
def admin_consultations():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    consultations = Consultation.query.order_by(Consultation.created_at.desc()).all()
    return render_template('admin/consultations.html', consultations=consultations)

@app.route('/admin/consultation/<int:id>')
@login_required
def consultation_detail(id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    consultation = Consultation.query.get_or_404(id)
    return render_template('admin/consultation_detail.html', consultation=consultation)

@app.route('/admin/consultation/<int:id>/status', methods=['POST'])
@login_required
def update_consultation_status(id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    consultation = Consultation.query.get_or_404(id)
    new_status = request.form['status']
    consultation.status = new_status
    db.session.commit()
    flash(f'Статус заявки #{consultation.id} изменён на "{new_status}"', 'success')
    return redirect(url_for('admin_consultations'))


@app.route('/admin/consultation/delete/<int:id>')
@login_required
def delete_consultation(id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    consultation = Consultation.query.get_or_404(id)
    db.session.delete(consultation)
    db.session.commit()
    flash('Заявка удалена', 'warning')
    return redirect(url_for('admin_consultations'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Изменение пароля
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            flash('Заполните все поля для смены пароля', 'danger')
        elif not current_user.check_password(current_password):
            flash('Неверный текущий пароль', 'danger')
        elif new_password != confirm_password:
            flash('Новый пароль и подтверждение не совпадают', 'danger')
        elif len(new_password) < 6:
            flash('Новый пароль должен содержать не менее 6 символов', 'danger')
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Пароль успешно изменён!', 'success')
        
        return redirect(url_for('profile'))
    
    return render_template('profile.html', user=current_user)

@app.route('/my-orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date.desc()).all()
    return render_template('my_orders.html', orders=orders)

@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    # Проверяем, что заказ принадлежит текущему пользователю или пользователь - админ
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('my_orders'))
    return render_template('order_detail.html', order=order)

@app.route('/ads')
def ads_list():
    ad_type = request.args.get('type', 'all')  # all, sale, buy
    query = Ad.query.filter_by(status='active')  # показываем только активные
    if ad_type == 'sale':
        query = query.filter_by(ad_type='sale')
    elif ad_type == 'buy':
        query = query.filter_by(ad_type='buy')
    ads = query.order_by(Ad.created_at.desc()).all()
    return render_template('ads/list.html', ads=ads, current_type=ad_type)

@app.route('/ads/<int:id>')
def ad_detail(id):
    ad = Ad.query.get_or_404(id)
    show_contacts = request.form.get('show_contacts') == 'on'   # в POST
    ad.show_contacts = show_contacts
    # Только активные объявления может смотреть любой, свои – даже неактивные
    if ad.status != 'active' and (not current_user.is_authenticated or current_user.id != ad.user_id):
        flash('Объявление недоступно', 'danger')
        return redirect(url_for('ads_list'))
    return render_template('ads/detail.html', ad=ad)

@app.route('/ads/create', methods=['GET', 'POST'])
@login_required
def ad_create():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        ad_type = request.form['ad_type']
        price = request.form.get('price', type=float)

        # Обработка изображения
        image_file = request.files.get('image')
        image_filename = 'default_ad.jpg'

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            name_parts = os.path.splitext(filename)
            unique_name = f"{name_parts[0]}_{int(os.times().system)}{name_parts[1]}"
            temp_path = os.path.join('static/uploads/ads', unique_name)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            # Сжатие изображения
            img = Image.open(image_file)
            img.thumbnail((800, 800))
            img.save(temp_path, optimize=True, quality=85)
            
            image_filename = unique_name

        if ad_type == 'sale' and not price:
            flash('Для объявления о продаже укажите цену', 'danger')
            return redirect(url_for('ad_create'))

        ad = Ad(
            title=title,
            description=description,
            ad_type=ad_type,
            price=price,
            user_id=current_user.id,
            status='pending',
            image=image_filename
        )
        db.session.add(ad)
        db.session.commit()
        flash('Объявление отправлено на модерацию', 'success')
        return redirect(url_for('ads_list'))
    
    return render_template('ads/create.html')

@app.route('/ads/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def ad_edit(id):
    ad = Ad.query.get_or_404(id)
    if ad.user_id != current_user.id and not current_user.is_admin:
        flash('Нет прав', 'danger')
        return redirect(url_for('ads_list'))
    if ad.status != 'pending' and not current_user.is_admin:
        flash('Редактирование возможно только пока объявление на модерации', 'danger')
        return redirect(url_for('ad_detail', id=ad.id))

    if request.method == 'POST':
        ad.title = request.form['title']
        ad.description = request.form['description']
        ad.ad_type = request.form['ad_type']
        ad.price = request.form.get('price', type=float)

        # Обновление изображения
        image_file = request.files.get('image')
        if image_file and allowed_file(image_file.filename):
            # Удаляем старое, если не default
            if ad.image and ad.image != 'default_ad.jpg':
                old_path = os.path.join('static/uploads/ads', ad.image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = secure_filename(image_file.filename)
            name_parts = os.path.splitext(filename)
            unique_name = f"{name_parts[0]}_{int(os.times().system)}{name_parts[1]}"
            image_path = os.path.join('static/uploads/ads', unique_name)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            
            # Сжатие изображения
            img = Image.open(image_file)
            img.thumbnail((800, 800))
            img.save(image_path, optimize=True, quality=85)
            
            ad.image = unique_name

        db.session.commit()
        flash('Объявление обновлено', 'success')
        return redirect(url_for('ad_detail', id=ad.id))
    
    return render_template('ads/edit.html', ad=ad)

@login_required
def ad_edit(id):
    ad = Ad.query.get_or_404(id)
    if ad.user_id != current_user.id and not current_user.is_admin:
        flash('Нет прав', 'danger')
        return redirect(url_for('ads_list'))# и снимите ограничение на статус для админа
    if ad.status != 'pending' and not current_user.is_admin:
        flash('Редактирование возможно только пока объявление на модерации', 'danger')
        return redirect(url_for('ad_detail', id=ad.id))
    
    if request.method == 'POST':
        ad.title = request.form['title']
        ad.description = request.form['description']
        ad.ad_type = request.form['ad_type']
        ad.price = request.form.get('price', type=float)
        ad.contacts = request.form['contacts']
        db.session.commit()
        flash('Объявление обновлено', 'success')
        return redirect(url_for('ad_detail', id=ad.id))
    
    return render_template('ads/edit.html', ad=ad)

@app.route('/ads/delete/<int:id>')
@login_required
def ad_delete(id):
    ad = Ad.query.get_or_404(id)
    if ad.user_id != current_user.id and not current_user.is_admin:
        flash('Нет прав', 'danger')
        return redirect(url_for('ads_list'))
    db.session.delete(ad)
    db.session.commit()
    flash('Объявление удалено', 'info')
    return redirect(url_for('ads_list'))

@app.route('/admin/ads')
@login_required
def admin_ads():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    status_filter = request.args.get('status', 'pending')
    query = Ad.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    ads = query.order_by(Ad.created_at.desc()).all()
    return render_template('admin/ads.html', ads=ads, status_filter=status_filter)

@app.route('/admin/ads/<int:id>/moderate', methods=['POST'])
@login_required
def moderate_ad(id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    ad = Ad.query.get_or_404(id)
    new_status = request.form['status']
    admin_comment = request.form.get('admin_comment', '')
    if new_status in ['active', 'closed', 'rejected']:
        ad.status = new_status
        ad.admin_comment = admin_comment
        db.session.commit()
        flash(f'Статус объявления изменён на "{new_status}"', 'success')
    else:
        flash('Некорректный статус', 'danger')
    return redirect(url_for('admin_ads'))

@app.route('/messages')
@login_required
def messages_list():
    # Находим все диалоги, где участвует пользователь
    conv_ids = db.session.query(ConversationParticipant.conversation_id).filter_by(user_id=current_user.id)
    conversations = Conversation.query.filter(Conversation.id.in_(conv_ids)).order_by(Conversation.updated_at.desc()).all()
    
    # Для каждого диалога получаем последнее сообщение и непрочитанные
    dialogs = []
    for conv in conversations:
        last_msg = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at.desc()).first()
        # Количество непрочитанных сообщений для текущего пользователя
        unread = Message.query.filter(
            Message.conversation_id == conv.id,
            Message.is_read == False,
            Message.sender_id != current_user.id
        ).count()
        # Определяем собеседника
        participants = ConversationParticipant.query.filter_by(conversation_id=conv.id).all()
        other = None
        for p in participants:
            if p.user_id != current_user.id:
                other = User.query.get(p.user_id)
                break
        dialogs.append({
            'conversation': conv,
            'last_message': last_msg,
            'unread': unread,
            'other_user': other
        })
    return render_template('messages/list.html', dialogs=dialogs)

@app.route('/messages/<int:conv_id>', methods=['GET', 'POST'])
@login_required
def messages_detail(conv_id):
    conv = Conversation.query.get_or_404(conv_id)
    # Проверяем, участвует ли пользователь в диалоге
    participant = ConversationParticipant.query.filter_by(conversation_id=conv.id, user_id=current_user.id).first()
    if not participant and not current_user.is_admin:
        flash('Нет доступа к этому диалогу', 'danger')
        return redirect(url_for('messages_list'))
    
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            msg = Message(conversation_id=conv.id, sender_id=current_user.id, content=content)
            db.session.add(msg)
            # Обновляем время обновления диалога
            conv.updated_at = db.func.now()
            # Сбрасываем last_read_at для получателя (чтобы он видел непрочитанное)
            other_participant = ConversationParticipant.query.filter(
                ConversationParticipant.conversation_id == conv.id,
                ConversationParticipant.user_id != current_user.id
            ).first()
            if other_participant:
                # last_read_at остается старым, is_read = False для новых сообщений
                pass
            db.session.commit()
            flash('Сообщение отправлено', 'success')
        return redirect(url_for('messages_detail', conv_id=conv.id))
    
    # GET – показать диалог
    messages = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at).all()
    # Помечаем все сообщения, где получатель – текущий пользователь, как прочитанные
    for msg in messages:
        if msg.sender_id != current_user.id and not msg.is_read:
            msg.is_read = True
    # Обновляем last_read_at участника
    participant.last_read_at = db.func.now()
    db.session.commit()
    
    # Определяем другого участника
    other_user_id = [p.user_id for p in ConversationParticipant.query.filter_by(conversation_id=conv.id).all() if p.user_id != current_user.id]
    other_user = User.query.get(other_user_id[0]) if other_user_id else None
    
    return render_template('messages/detail.html', conversation=conv, messages=messages, other_user=other_user)

@app.route('/start-conversation/<int:ad_id>')
@login_required
def start_conversation(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    if ad.user_id == current_user.id:
        flash('Нельзя написать самому себе', 'warning')
        return redirect(url_for('ad_detail', id=ad.id))
    
    # Ищем существующий диалог между этими пользователями по этому объявлению
    conv = Conversation.query.filter_by(ad_id=ad.id).join(ConversationParticipant).filter(
        ConversationParticipant.user_id.in_([current_user.id, ad.user_id])
    ).group_by(Conversation.id).having(db.func.count(ConversationParticipant.user_id) == 2).first()
    
    if not conv:
        conv = Conversation(ad_id=ad.id)
        db.session.add(conv)
        db.session.commit()
        # Добавляем участников
        for uid in [current_user.id, ad.user_id]:
            cp = ConversationParticipant(conversation_id=conv.id, user_id=uid)
            db.session.add(cp)
        db.session.commit()
    
    return redirect(url_for('messages_detail', conv_id=conv.id))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contacts')
def contacts():
    return render_template('contacts.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

# @app.context_processor
# def utility_processor():
#     unread = 0
#     if current_user.is_authenticated:
#         from app import Message, ConversationParticipant, db  # или используйте глобальные переменные
#         unread = Message.query.filter(
#             Message.conversation_id.in_(
#                 db.session.query(ConversationParticipant.conversation_id).filter_by(user_id=current_user.id)
#             ),
#             Message.is_read == False,
#             Message.sender_id != current_user.id
#         ).count()
#     return dict(unread_messages_count=unread)



# --- Создание таблиц и администратора ---
with app.app_context():
    db.create_all()
    if not User.query.filter_by(is_admin=True).first():
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Создан администратор: admin / admin123")

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)

# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=5000)