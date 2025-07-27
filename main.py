from flask import Flask, render_template, request, redirect, session
import os, json

app = Flask(__name__)
app.secret_key = 'bi_mat'

# Load users
if os.path.exists('users.json'):
    with open('users.json', 'r') as f:
        USERS = json.load(f)
else:
    USERS = {
        "admin": {
            "password": "1234",
            "diamonds": 0,
            "inventory": [],
            "missions": []
        }
    }

# Load items
if os.path.exists('items.json'):
    with open('items.json', 'r') as f:
        ITEMS = json.load(f)
else:
    ITEMS = {
        "kiếm rồng": {"buy": 20, "sell": 10, "image": "kiem.png"},
        "giáp vàng": {"buy": 35, "sell": 17, "image": "giap.jpg"},
        "khiên băng": {"buy": 40, "sell": 20, "image": "khien.jpg"}
    }

@app.route('/', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS and USERS[username]['password'] == password:
            session['username'] = username
            if username == 'admin':
                return redirect('/admin')
            return redirect('/dashboard')
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
            USERS[username] = {
                "password": password,
                "diamonds": 0,
                "inventory": [],
                "missions": []
            }
            with open('users.json', 'w') as f:
                json.dump(USERS, f, indent=4)
            return redirect('/')
    return render_template('register.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    user = USERS[session['username']]
    return render_template(
        'dashboard.html',
        username=session['username'],
        diamonds=user['diamonds'],
        missions=user.get('missions', [])
    )

@app.route('/shop')
def shop():
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    user_data = USERS[session['username']]
    return render_template('shop.html',
        username=session['username'],
        diamonds=user_data['diamonds'],
        items=ITEMS,
        inventory=user_data['inventory']
    )

@app.route('/buy/<item>', methods=['POST'])
def buy(item):
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    user = USERS[session['username']]
    if item in ITEMS and item not in user['inventory']:
        if user['diamonds'] >= ITEMS[item]['buy']:
            user['diamonds'] -= ITEMS[item]['buy']
            user['inventory'].append(item)
            with open('users.json', 'w') as f:
                json.dump(USERS, f, indent=4)
    return redirect('/shop')

@app.route('/sell/<item>', methods=['POST'])
def sell(item):
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    user = USERS[session['username']]
    if item in user['inventory'] and item in ITEMS:
        user['inventory'].remove(item)
        user['diamonds'] += ITEMS[item]['sell']
        with open('users.json', 'w') as f:
            json.dump(USERS, f, indent=4)
    return redirect('/shop')

@app.route('/admin', methods=['GET'])
def admin():
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    return render_template('admin.html', users=USERS, items=ITEMS)

@app.route('/delete/<username>')
def delete_user(username):
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    if username in USERS and username != 'admin':
        del USERS[username]
        with open('users.json', 'w') as f:
            json.dump(USERS, f, indent=4)
    return redirect('/admin')

@app.route('/give/<username>', methods=['POST'])
def give(username):
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    amount = int(request.form['amount'])
    if username in USERS:
        USERS[username]['diamonds'] += amount
        with open('users.json', 'w') as f:
            json.dump(USERS, f, indent=4)
    return redirect('/admin')

@app.route('/update_price', methods=['POST'])
def update_price():
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    for item in ITEMS:
        buy = request.form.get(f'buy_{item}')
        sell = request.form.get(f'sell_{item}')
        if buy and sell:
            ITEMS[item]['buy'] = float(buy)
            ITEMS[item]['sell'] = float(sell)
    with open('items.json', 'w') as f:
        json.dump(ITEMS, f, indent=4)
    return redirect('/admin')

@app.route('/create_mission', methods=['POST'])
def create_mission():
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    title = request.form.get('title')
    reward = int(request.form.get('reward'))
    for user in USERS:
        if user != 'admin':
            USERS[user].setdefault('missions', [])
            USERS[user]['missions'].append({
                "title": title,
                "reward": reward,
                "completed": False
            })
    with open('users.json', 'w') as f:
        json.dump(USERS, f, indent=4)
    return redirect('/admin')

@app.route('/complete_mission/<int:mission_id>', methods=['POST'])
def complete_mission(mission_id):
    if 'username' not in session:
        return redirect('/')
    user = USERS[session['username']]
    if 0 <= mission_id < len(user['missions']):
        mission = user['missions'][mission_id]
        if not mission['completed']:
            mission['completed'] = True
            user['diamonds'] += mission['reward']
            with open('users.json', 'w') as f:
                json.dump(USERS, f, indent=4)
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
