from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import os
import mysql.connector

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MySQL Configuration (REPLACE WITH YOUR CREDENTIALS)
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="Cloud"
)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        mycursor = mydb.cursor()
        mycursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        existing_user = mycursor.fetchone()

        if existing_user:
            flash("Username or email already exists.", 'danger')
            return render_template('register.html')

        try:
            mycursor.execute("INSERT INTO users (username, email, phone, password) VALUES (%s, %s, %s, %s)", (username, email, phone, password))
            mydb.commit()
            user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
            os.makedirs(user_folder, exist_ok=True)
            flash("Registration successful. Please login.", 'success')
            return redirect(url_for('login'))
        except Exception as e:
            mydb.rollback()
            flash(f"An error occurred during registration: {e}", 'danger')
            return render_template('register.html')
        finally:
            mycursor.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['username_or_email']
        password = request.form['password']

        mycursor = mydb.cursor()
        mycursor.execute("SELECT * FROM users WHERE (username = %s OR email = %s) AND password = %s", (username_or_email, username_or_email, password))
        user = mycursor.fetchone()
        mycursor.close()

        if user:
            session['logged_in'] = True
            session['username'] = user[1]
            return redirect(url_for('index'))
        else:
            flash("Invalid username/email or password.", 'danger')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))

def requires_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index():
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], session.get('username'))
    os.makedirs(user_folder, exist_ok=True)
    filenames = os.listdir(user_folder)
    return render_template('index.html', filenames=filenames)

@app.route('/upload', methods=['POST'])
@requires_auth
def upload_file():
    if 'file' not in request.files:
        flash("No file part", 'danger')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash("No selected file", 'danger')
        return redirect(request.url)

    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], session.get('username'))
    filepath = os.path.join(user_folder, file.filename)

    try:
        file.save(filepath)
        flash("File uploaded successfully!", 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error uploading file: {e}", 'danger')
        return redirect(request.url)

@app.route('/download/<filename>')
@requires_auth
def download_file(filename):
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], session.get('username'))
    return send_from_directory(user_folder, filename)

if __name__ == '__main__':
    app.run(debug=True)