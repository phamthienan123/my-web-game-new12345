from flask import Flask, render_template, request, redirect, session
import json, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Load dữ liệu người dùng
if os.path.exists('users.json'):
    with open('users.json', 'r') as f:
        USERS = json.load(f)
else:
    USERS = {}

# Load dữ liệu vật phẩm
if os.path.exists('items.json'):
    with open('items.json', 'r') as f:
        ITEMS = json.load(f)
else:
    ITEMS = {}

# Lưu user
def save_users():
    with open('users.json', 'w') as f:
        json.dump(USERS, f, indent=4)

# Lưu items
def save_items():
    with open('items.json', 'w') as f:
        json.dump(ITEMS, f, indent=4)

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
            return redirect('/dashboard')
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
                'diamonds': 0,
                'inventory': [],
                'quests': {
                    'daily_login': {'last_claimed': ''},
                    'custom': {}
                }
            }
            save_users()
            return redirect('/')
    return render_template('register.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user_data = USERS.get(username, {})
    today = datetime.now().date().isoformat()
    last_claimed = user_data.get('quests', {}).get('daily_login', {}).get('last_claimed', '')
    new_claim = last_claimed != today

    # Xác định rank cao nhất từ inventory
    rank_order = ['rank_bronze', 'rank_silver', 'rank_gold', 'rank_platinum']
    highest_rank = None
    for rank in reversed(rank_order):
        if rank in user_data.get('inventory', []):
            highest_rank = rank
            break

    return render_template('dashboard.html',
                           username=username,
                           diamonds=user_data.get('diamonds', 0),
                           quests=user_data.get('quests', {}),
                           new_claim=new_claim,
                           now=datetime.now,
                           highest_rank=highest_rank)

@app.route('/claim/daily')
def claim_daily():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user_data = USERS.get(username)
    today = datetime.now().strftime('%Y-%m-%d')
    last_claimed = user_data.get('quests', {}).get('daily_login', {}).get('last_claimed', '')
    if last_claimed != today:
        user_data['diamonds'] += 10
        user_data['quests']['daily_login']['last_claimed'] = today
        save_users()
    return redirect('/dashboard')

@app.route('/shop')
def shop():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user_data = USERS.get(username, {})
    return render_template('shop.html',
                           username=username,
                           diamonds=user_data.get('diamonds', 0),
                           inventory=user_data.get('inventory', []),
                           items=ITEMS)

@app.route('/buy/<item>', methods=['POST'])
def buy(item):
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user = USERS.get(username)
    if item not in ITEMS:
        return redirect('/shop')
    if item in user['inventory']:
        return redirect('/shop')
    if user['diamonds'] >= ITEMS[item]['buy']:
        user['diamonds'] -= ITEMS[item]['buy']
        user['inventory'].append(item)
        save_users()
    return redirect('/shop')

@app.route('/sell/<item>', methods=['POST'])
def sell(item):
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user = USERS.get(username)
    if item in user['inventory']:
        user['inventory'].remove(item)
        user['diamonds'] += ITEMS[item]['sell']
        save_users()
    return redirect('/shop')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/admin')
def admin():
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    return render_template('admin.html', users=USERS, items=ITEMS)

@app.route('/give/<username>', methods=['POST'])
def give(username):
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    amount = int(request.form.get('amount', 0))
    if username in USERS:
        USERS[username]['diamonds'] += amount
        save_users()
    return redirect('/admin')

@app.route('/delete/<username>')
def delete(username):
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    if username in USERS:
        del USERS[username]
        save_users()
    return redirect('/admin')

@app.route('/update_prices', methods=['POST'])
def update_prices():
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    for item in ITEMS:
        buy_key = f"{item}_buy"
        sell_key = f"{item}_sell"
        if buy_key in request.form and sell_key in request.form:
            try:
                ITEMS[item]['buy'] = int(request.form[buy_key])
                ITEMS[item]['sell'] = int(request.form[sell_key])
            except:
                pass
    save_items()
    return redirect('/admin')

@app.route('/assign_quest', methods=['POST'])
def assign_quest():
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/')
    username = request.form.get('username')
    title = request.form.get('title')
    reward = int(request.form.get('reward'))
    if username in USERS:
        if 'quests' not in USERS[username]:
            USERS[username]['quests'] = {}
        if 'custom' not in USERS[username]['quests']:
            USERS[username]['quests']['custom'] = {}
        quest_id = f"quest{len(USERS[username]['quests']['custom']) + 1}"
        USERS[username]['quests']['custom'][quest_id] = {
            "title": title,
            "reward": reward,
            "status": "pending"
        }
        save_users()
    return redirect('/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

