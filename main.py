from flask import Flask, render_template, request, redirect, session
import json, os

app = Flask(__name__)
app.secret_key = 'matkhau_bimat'

USER_FILE = 'users.json'
ITEM_FILE = 'items.json'

# Load users
if os.path.exists(USER_FILE):
    with open(USER_FILE, 'r') as f:
        USERS = json.load(f)
else:
    USERS = {
        "admin": {
            "password": "1234",
            "item": 0,
            "inventory": []
        }
    }
    with open(USER_FILE, 'w') as f:
        json.dump(USERS, f)

# Load items
if os.path.exists(ITEM_FILE):
    with open(ITEM_FILE, 'r') as f:
        ITEMS = json.load(f)
else:
    ITEMS = {
        "kiếm rồng": {"buy": 20, "sell": 10},
        "giáp vàng": {"buy": 35, "sell": 18},
        "khiên băng": {"buy": 40, "sell": 20}
        
    }
    with open(ITEM_FILE, 'w') as f:
        json.dump(ITEMS, f)

def save_users():
    with open(USER_FILE, 'w') as f:
        json.dump(USERS, f)

def save_items():
    with open(ITEM_FILE, 'w') as f:
        json.dump(ITEMS, f)

@app.route('/', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in USERS and USERS[username]['password'] == password:
            session['username'] = username
            if username == 'admin':
                return redirect('/admin')
            return redirect('/home')
        else:
            error = 'Sai tài khoản hoặc mật khẩu!'
    return render_template('index.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in USERS:
            error = 'Tài khoản đã tồn tại!'
        else:
            USERS[username] = {
                'password': password,
                'item': 0,
                'inventory': []
            }
            save_users()
            return redirect('/')
    return render_template('register.html', error=error)

@app.route('/home')
def home():
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    user = USERS[session['username']]
    return render_template('home.html', username=session['username'], diamonds=user['item'], inventory=user['inventory'], items=ITEMS)
@app.route('/shop')
def shop():
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    username = session['username']
    user_data = USERS[username]
    return render_template('shop.html',
                           username=username,
                           diamonds=user_data['diamonds'],
                           inventory=user_data['inventory'],
                           items=ITEMS)
@app.route('/buy/<item>', methods=['POST'])
def buy_item(item):
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    username = session['username']
    user = USERS[username]
    if item in ITEMS and item not in user['inventory']:
        cost = ITEMS[item]['buy']
        if user['diamonds'] >= cost:
            user['diamonds'] -= cost
            user['inventory'].append(item)
            save_users()
    return redirect('/shop')


@app.route('/sell/<item>', methods=['POST'])
def sell_item(item):
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    username = session['username']
    user = USERS[username]
    if item in ITEMS and item in user['inventory']:
        user['diamonds'] += ITEMS[item]['sell']
        user['inventory'].remove(item)
        save_users()
    return redirect('/shop')

@app.route('/admin')
def admin():
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    with open('users.json', 'r') as f:
        users = json.load(f)
    with open('items.json', 'r') as f:
        items = json.load(f)
    return render_template('admin.html', users=users, items=items)

@app.route('/give/<username>', methods=['POST'])
def give(username):
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    amount = int(request.form.get('amount', 0))
    if username in USERS and username != 'admin' and amount > 0:
        USERS[username]['item'] += amount
        save_users()
    return redirect('/admin')

@app.route('/update_item/<item_name>', methods=['POST'])
def update_item(item_name):
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    try:
        buy = float(request.form.get('buy', 0))
        sell = float(request.form.get('sell', 0))
        if item_name in ITEMS and buy >= 1 and sell >= 0:
            ITEMS[item_name]['buy'] = buy
            ITEMS[item_name]['sell'] = sell
            save_items()
    except:
        pass
    return redirect('/admin')

@app.route('/delete/<username>')
def delete_user(username):
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    if username in USERS and username != 'admin':
        del USERS[username]
        save_users()
    return redirect('/admin')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
