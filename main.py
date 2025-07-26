from flask import Flask, render_template, request, redirect, session
import json, os

app = Flask(__name__)
app.secret_key = 'matkhau_bimat'

# Load dữ liệu tài khoản
if os.path.exists('users.json'):
    with open('users.json', 'r') as f:
        USERS = json.load(f)
else:
    USERS = {
        "admin": {"password": "1234", "diamonds": 0, "inventory": []}
    }
    with open('users.json', 'w') as f:
        json.dump(USERS, f)

# Load dữ liệu vật phẩm
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
        json.dump(ITEMS, f)

@app.route('/', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS and USERS[username]['password'] == password:
            session['username'] = username
            return redirect('/admin' if username == 'admin' else '/dashboard')
        else:
            error = 'Sai tài khoản hoặc mật khẩu!'
    return render_template('index.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS:
            error = 'Tài khoản đã tồn tại!'
        else:
            USERS[username] = {"password": password, "diamonds": 0, "inventory": []}
            with open('users.json', 'w') as f:
                json.dump(USERS, f)
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
    return render_template('shop.html',
                           username=session['username'],
                           diamonds=user['diamonds'],
                           items=ITEMS,
                           inventory=user['inventory'])

@app.route('/buy/<item>', methods=['POST'])
def buy_item(item):
    username = session.get('username')
    if not username or username == 'admin':
        return redirect('/')
    user = USERS[username]
    if item in ITEMS and item not in user['inventory']:
        if user['diamonds'] >= ITEMS[item]['buy']:
            user['diamonds'] -= ITEMS[item]['buy']
            user['inventory'].append(item)
            with open('users.json', 'w') as f:
                json.dump(USERS, f)
    return redirect('/shop')

@app.route('/sell/<item>', methods=['POST'])
def sell_item(item):
    username = session.get('username')
    if not username or username == 'admin':
        return redirect('/')
    user = USERS[username]
    if item in user['inventory']:
        user['inventory'].remove(item)
        user['diamonds'] += ITEMS[item]['sell']
        with open('users.json', 'w') as f:
            json.dump(USERS, f)
    return redirect('/shop')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    if request.method == 'POST':
        # Cập nhật giá mua/bán
        for item in ITEMS:
            buy = request.form.get(f"{item}_buy")
            sell = request.form.get(f"{item}_sell")
            if buy and sell:
                try:
                    ITEMS[item]['buy'] = int(buy)
                    ITEMS[item]['sell'] = int(sell)
                except:
                    pass
        with open('items.json', 'w') as f:
            json.dump(ITEMS, f)
    users_to_show = {u: info for u, info in USERS.items() if u != 'admin'}
    return render_template('admin.html', users=users_to_show, items=ITEMS)

@app.route('/give/<username>', methods=['POST'])
def give_diamonds(username):
    if 'username' in session and session['username'] == 'admin':
        amount = int(request.form.get('amount', 0))
        if username in USERS and username != 'admin':
            USERS[username]['diamonds'] += amount
            with open('users.json', 'w') as f:
                json.dump(USERS, f)
    return redirect('/admin')

@app.route('/delete/<username>')
def delete_user(username):
    if 'username' in session and session['username'] == 'admin':
        if username in USERS and username != 'admin':
            del USERS[username]
            with open('users.json', 'w') as f:
                json.dump(USERS, f)
    return redirect('/admin')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
