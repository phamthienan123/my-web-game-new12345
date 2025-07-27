from flask import Flask, render_template, request, redirect, session, url_for
import json, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# Load users
import os, json

if os.path.exists('users.json'):
    try:
        with open('users.json', 'r') as f:
            USERS = json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Lỗi định dạng file users.json. Đang khởi tạo lại...")
        USERS = {
            "admin": {
                "password": "1234",
                "diamonds": 999,
                "inventory": [],
                "quests": {}
            }
        }
        with open('users.json', 'w') as f:
            json.dump(USERS, f, indent=2)
else:
    USERS = {
        "admin": {
            "password": "1234",
            "diamonds": 999,
            "inventory": [],
            "quests": {}
        }
    }
    with open('users.json', 'w') as f:
        json.dump(USERS, f, indent=2)
else:
    USERS = {
        "admin": {
            "password": "admin",
            "diamonds": 0,
            "inventory": [],
            "quests": {}
        }
    }
    with open('users.json', 'w') as f:
        json.dump(USERS, f, indent=2)

# Load items
if os.path.exists('items.json'):
    with open('items.json', 'r') as f:
        ITEMS = json.load(f)
else:
    ITEMS = {
        "kiếm rồng": {"buy": 20, "sell": 10},
        "giáp vàng": {"buy": 35, "sell": 17},
        "khiên băng": {"buy": 40, "sell": 20}
    }
    with open('items.json', 'w') as f:
        json.dump(ITEMS, f, indent=2)

# Load quests
if os.path.exists('quests.json'):
    with open('quests.json', 'r') as f:
        QUESTS = json.load(f)
else:
    QUESTS = {
        "daily_login": {
            "title": "Đăng nhập mỗi ngày",
            "reward": 5
        }
    }
    with open('quests.json', 'w') as f:
        json.dump(QUESTS, f, indent=2)

def save_users():
    with open('users.json', 'w') as f:
        json.dump(USERS, f, indent=2)

def save_items():
    with open('items.json', 'w') as f:
        json.dump(ITEMS, f, indent=2)

def save_quests():
    with open('quests.json', 'w') as f:
        json.dump(QUESTS, f, indent=2)

@app.route('/', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS and USERS[username]['password'] == password:
            session['username'] = username

            # Check daily login
            today = datetime.now().strftime('%Y-%m-%d')
            if 'last_login' not in USERS[username] or USERS[username]['last_login'] != today:
                USERS[username]['last_login'] = today
                USERS[username]['quests']['daily_login'] = 'pending'
                save_users()

            if username == 'admin':
                return redirect('/admin')
            return redirect('/dashboard')
        else:
            error = 'Sai tài khoản hoặc mật khẩu'
    return render_template('index.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS:
            error = 'Tên người dùng đã tồn tại.'
        else:
            USERS[username] = {
                "password": password,
                "diamonds": 0,
                "inventory": [],
                "quests": {}
            }
            save_users()
            return redirect('/')
    return render_template('register.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    user = USERS[session['username']]
    return render_template('dashboard.html', username=session['username'], diamonds=user['diamonds'])

@app.route('/shop')
def shop():
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    user = USERS[session['username']]
    return render_template('shop.html', items=ITEMS, inventory=user['inventory'], diamonds=user['diamonds'])

@app.route('/buy/<item>', methods=['POST'])
def buy(item):
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    user = USERS[session['username']]
    if item in ITEMS and item not in user['inventory'] and user['diamonds'] >= ITEMS[item]['buy']:
        user['diamonds'] -= ITEMS[item]['buy']
        user['inventory'].append(item)
        save_users()
    return redirect('/shop')

@app.route('/sell/<item>', methods=['POST'])
def sell(item):
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    user = USERS[session['username']]
    if item in user['inventory']:
        user['inventory'].remove(item)
        user['diamonds'] += ITEMS[item]['sell']
        save_users()
    return redirect('/shop')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    return render_template('admin.html', users=USERS, items=ITEMS, quests=QUESTS)

@app.route('/give/<username>', methods=['POST'])
def give_diamonds(username):
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    amount = int(request.form['amount'])
    if username in USERS:
        USERS[username]['diamonds'] += amount
        save_users()
    return redirect('/admin')

@app.route('/delete/<username>')
def delete_user(username):
    if 'username' in session and session['username'] == 'admin' and username in USERS:
        del USERS[username]
        save_users()
    return redirect('/admin')

@app.route('/update_price/<item>', methods=['POST'])
def update_price(item):
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    buy_price = int(request.form['buy'])
    sell_price = int(request.form['sell'])
    if item in ITEMS:
        ITEMS[item]['buy'] = buy_price
        ITEMS[item]['sell'] = sell_price
        save_items()
    return redirect('/admin')

@app.route('/create_quest', methods=['POST'])
def create_quest():
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    title = request.form['title']
    reward = int(request.form['reward'])
    QUESTS[title] = {"title": title, "reward": reward}
    save_quests()
    return redirect('/admin')

@app.route('/quests')
def user_quests():
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    username = session['username']
    user = USERS[username]
    return render_template('quests.html', quests=QUESTS, user_quests=user.get('quests', {}))

@app.route('/complete/<quest>', methods=['POST'])
def complete_quest(quest):
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    username = session['username']
    user = USERS[username]
    if quest in QUESTS:
        user['quests'][quest] = 'pending'
        save_users()
    return redirect('/quests')

@app.route('/approve/<username>/<quest>')
def approve_quest(username, quest):
    if 'username' in session and session['username'] == 'admin':
        if username in USERS and quest in USERS[username]['quests']:
            if USERS[username]['quests'][quest] == 'pending':
                USERS[username]['diamonds'] += QUESTS[quest]['reward']
                USERS[username]['quests'][quest] = 'approved'
                save_users()
    return redirect('/admin')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
