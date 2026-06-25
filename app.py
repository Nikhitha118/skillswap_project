from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "skillswap_secret"


# ================= DATABASE =================
def create_database():
    conn = sqlite3.connect("skillswap.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT NOT NULL,
            description TEXT NOT NULL,
            username TEXT NOT NULL,
            email TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id INTEGER,
            from_user TEXT,
            to_user TEXT,
            message TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        receiver TEXT NOT NULL,
        message TEXT NOT NULL
    )
""")

    conn.commit()
    conn.close()


# ================= HOME =================
@app.route('/')
def home():
    return render_template('index.html')


# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect("skillswap.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users(username, email, password) VALUES(?,?,?)",
            (username, email, password)
        )

        conn.commit()
        conn.close()

        return render_template('register.html', success="Registration Successful! Please login.")

    return render_template('register.html')


# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        login_input = request.form['login_input']
        password = request.form['password']

        conn = sqlite3.connect("skillswap.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM users
            WHERE (email=? OR username=?)
            AND password=?
        """, (login_input, login_input, password))

        user = cursor.fetchone()
        conn.close()

        if user:
            session['username'] = user[1]
            session['email'] = user[2]
            return redirect('/dashboard')

        return "<h2>Invalid Username/Email or Password</h2>"

    return render_template('login.html')


# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():

    if 'username' not in session:
        return redirect('/login')

    return render_template('dashboard.html')


# ================= ADD SKILL =================
@app.route('/add-skill', methods=['GET', 'POST'])
def add_skill():

    if 'username' not in session:
        return redirect('/login')

    if request.method == 'POST':

        skill_name = request.form['skill_name']
        description = request.form['description']

        conn = sqlite3.connect("skillswap.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO skills(skill_name, description, username, email)
            VALUES(?, ?, ?, ?)
        """, (skill_name, description, session['username'], session['email']))

        conn.commit()
        conn.close()

        return redirect('/dashboard')

    return render_template('add_skill.html')


# ================= SKILLS =================
@app.route('/skills')
def skills():

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("skillswap.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM skills")
    skills = cursor.fetchall()

    cursor.execute("""
        SELECT skill_id
        FROM requests
        WHERE from_user=?
    """, (session['username'],))

    requested_skills = [row[0] for row in cursor.fetchall()]

    conn.close()

    return render_template(
        'skills.html',
        skills=skills,
        requested_skills=requested_skills
    )


# ================= PROFILE =================
@app.route('/profile')
def profile():

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("skillswap.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, skill_name, description
        FROM skills
        WHERE username=?
    """, (session['username'],))

    my_skills = cursor.fetchall()
    conn.close()

    return render_template(
        'profile.html',
        username=session['username'],
        email=session['email'],
        my_skills=my_skills
    )


# ================= DELETE SKILL =================
@app.route('/delete-skill/<int:skill_id>')
def delete_skill(skill_id):

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("skillswap.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM skills WHERE id=?", (skill_id,))

    conn.commit()
    conn.close()

    return redirect('/profile')


# ================= EDIT SKILL =================
@app.route('/edit-skill/<int:skill_id>', methods=['GET', 'POST'])
def edit_skill(skill_id):

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("skillswap.db")
    cursor = conn.cursor()

    if request.method == 'POST':

        skill_name = request.form['skill_name']
        description = request.form['description']

        cursor.execute("""
            UPDATE skills
            SET skill_name=?, description=?
            WHERE id=?
        """, (skill_name, description, skill_id))

        conn.commit()
        conn.close()

        return redirect('/profile')

    cursor.execute("SELECT * FROM skills WHERE id=?", (skill_id,))
    skill = cursor.fetchone()

    conn.close()

    return render_template('edit_skill.html', skill=skill)


# ================= REQUEST SKILL =================
@app.route('/request-skill/<int:skill_id>')
def request_skill(skill_id):

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("skillswap.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT username FROM skills WHERE id=?",
        (skill_id,)
    )

    row = cursor.fetchone()

    if not row:
        conn.close()
        return "Skill not found"

    owner = row[0]

    # Own skill request block
    if owner == session['username']:
        conn.close()
        return "You cannot request your own skill"

    # Duplicate request block
    cursor.execute("""
        SELECT *
        FROM requests
        WHERE skill_id=? AND from_user=?
    """, (skill_id, session['username']))

    existing_request = cursor.fetchone()

    if existing_request:
        conn.close()
        return "You already requested this skill"

    # Insert request
    cursor.execute("""
        INSERT INTO requests(skill_id, from_user, to_user, message, status)
        VALUES (?, ?, ?, ?, ?)
    """, (
        skill_id,
        session['username'],
        owner,
        "I want to learn this skill",
        "pending"
    ))

    conn.commit()
    conn.close()

    return redirect('/skills')

# ================= REQUESTS PAGE =================
@app.route('/requests')
def requests_page():

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("skillswap.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM requests
        WHERE to_user=?
    """, (session['username'],))

    requests = cursor.fetchall()

    conn.close()

    return render_template('requests.html', requests=requests)


# ================= ACCEPT =================
@app.route('/accept/<int:req_id>')
def accept(req_id):

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("skillswap.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE requests
        SET status='accepted'
        WHERE id=?
    """, (req_id,))

    conn.commit()
    conn.close()

    return redirect('/requests')


# ================= REJECT =================
@app.route('/reject/<int:req_id>')
def reject(req_id):

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("skillswap.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE requests
        SET status='rejected'
        WHERE id=?
    """, (req_id,))

    conn.commit()
    conn.close()

    return redirect('/requests')
@app.route('/my-requests')
def my_requests():

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("skillswap.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            requests.id,
            skills.skill_name,
            requests.to_user,
            requests.status
        FROM requests
        JOIN skills
        ON requests.skill_id = skills.id
        WHERE requests.from_user=?
    """, (session['username'],))

    requests = cursor.fetchall()

    conn.close()

    return render_template('my_requests.html', requests=requests)
@app.route('/chat/<username>', methods=['GET', 'POST'])
def chat(username):

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("skillswap.db")
    cursor = conn.cursor()

    if request.method == 'POST':

        message = request.form['message']

        cursor.execute("""
            INSERT INTO messages(sender, receiver, message)
            VALUES (?, ?, ?)
        """, (
            session['username'],
            username,
            message
        ))

        conn.commit()

    cursor.execute("""
        SELECT *
        FROM messages
        WHERE (sender=? AND receiver=?)
        OR (sender=? AND receiver=?)
        ORDER BY id
    """, (
        session['username'],
        username,
        username,
        session['username']
    ))

    messages = cursor.fetchall()

    conn.close()

    return render_template(
        'chat.html',
        messages=messages,
        username=username
    )
@app.route('/inbox')
def inbox():

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("skillswap.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT sender
        FROM messages
        WHERE receiver=?
    """, (session['username'],))

    users = cursor.fetchall()

    conn.close()

    return render_template(
        'inbox.html',
        users=users
    )

# ================= START APP =================
if __name__ == '__main__':
    create_database()
    app.run(debug=True)