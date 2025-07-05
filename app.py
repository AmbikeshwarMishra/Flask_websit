from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import sqlite3, os, csv
from io import StringIO, BytesIO
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, message TEXT)")
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO messages (name, email, message) VALUES (?, ?, ?)", (name, email, message))
        conn.commit()
        conn.close()
        return render_template('thankyou.html', name=name)
    return render_template('contact.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        flash("Account created successfully!", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):
            session['username'] = username
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials!", "error")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT name, email, message FROM messages ORDER BY id DESC")
        messages = c.fetchall()
        conn.close()
        return render_template('dashboard.html', username=session['username'], messages=messages)
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'username' not in session:
        flash("Login required!", "error")
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            flash("File uploaded successfully!", "success")
            return render_template('dashboard.html', username=session['username'], file_url=filepath)
        else:
            flash("Invalid file type!", "error")
    return render_template('upload.html')

@app.route('/export/csv')
def export_csv():
    if 'username' not in session:
        flash("Login required!", "error")
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT name, email, message FROM messages")
    data = c.fetchall()
    conn.close()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Name', 'Email', 'Message'])
    cw.writerows(data)
    output = si.getvalue()
    si.close()
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=messages.csv"})

@app.route('/export/pdf')
def export_pdf():
    if 'username' not in session:
        flash("Login required!", "error")
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT name, email, message FROM messages")
    data = c.fetchall()
    conn.close()
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    y = 800
    p.drawString(200, y, "Contact Messages")
    y -= 40
    for name, email, message in data:
        p.drawString(30, y, f"Name: {name}, Email: {email}")
        y -= 20
        p.drawString(30, y, f"Message: {message}")
        y -= 30
        if y < 100:
            p.showPage()
            y = 800
    p.save()
    buffer.seek(0)
    return Response(buffer, mimetype='application/pdf', headers={"Content-Disposition": "attachment;filename=messages.pdf"})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
