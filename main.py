from flask import Flask, render_template, request, redirect, session
import json, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Tải dữ liệu người dùng
if os.path.exists('users.json'):
    with open('users.json', 'r') as f:
        USERS = json.load(f)
else:
    USERS = {}

# Tải dữ liệu vật phẩm
if os.path.exists('items.json'):
    with open('items.json', 'r') as f:
        ITEMS = json.load(f)
else:
    ITEMS = {}

# Hàm lưu dữ liệu
def save_users():
    with open('users.json', 'w') as f:
        json.dump(USERS, f, indent=4)

def save_items():
    with open('items.json', 'w') as f:
        json.dump(ITEMS, f, indent=4)

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
            error = 'Tên đăng nhập đã tồn tại.'
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
    user = USERS[username]
    today = datetime.now().date().isoformat()
    last_claimed = user.get('quests', {}).get('daily_login', {}).get('last_claimed', '')
    new_claim = last_claimed != today

    # Xác định rank cao nhất
    rank_order = ['rank_bronze', 'rank_silver', 'rank_gold', 'rank_platinum']
    highest_rank = None
    for rank in reversed(rank_order):
        if rank in user.get('inventory', []):
            highest_rank = rank
            break

    return render_template('dashboard.html',
                           username=username,
                           diamonds=user['diamonds'],
                           new_claim=new_claim,
                           custom_quests=user['quests'].get('custom', {}),
                           highest_rank=highest_rank)

@app.route('/claim/daily')
def claim_daily():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user = USERS[username]
    today = datetime.now().date().isoformat()
    if user['quests']['daily_login'].get('last_claimed') != today:
        user['diamonds'] += 10
        user['quests']['daily_login']['last_claimed'] = today
        save_users()
    return redirect('/dashboard')

@app.route('/submit_quest/<quest_id>', methods=['POST'])
def submit_quest(quest_id):
    username = session['username']
    if username in USERS:
        user_quests = USERS[username]['quests']['custom']
        if quest_id in user_quests and user_quests[quest_id]['status'] == 'assigned':
            user_quests[quest_id]['status'] = 'pending'
            save_users()
    return redirect('/dashboard')

@app.route('/claim_quest/<quest_id>', methods=['POST'])
def claim_quest(quest_id):
    username = session['username']
    user_quests = USERS[username]['quests']['custom']
    if quest_id in user_quests and user_quests[quest_id]['status'] == 'approved':
        USERS[username]['diamonds'] += user_quests[quest_id]['reward']
        user_quests[quest_id]['status'] = 'claimed'
        save_users()
    return redirect('/dashboard')

@app.route('/shop')
def shop():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user = USERS[username]
    return render_template('shop.html',
                           username=username,
                           diamonds=user['diamonds'],
                           inventory=user.get('inventory', []),
                           items=ITEMS)

@app.route('/buy/<item>', methods=['POST'])
def buy(item):
    if 'username' not in session:
        return redirect('/')
    user = USERS[session['username']]
    if item not in ITEMS or item in user['inventory']:
        return redirect('/shop')
    price = ITEMS[item]['buy']
    if user['diamonds'] >= price:
        user['diamonds'] -= price
        user['inventory'].append(item)
        save_users()
    return redirect('/shop')

@app.route('/sell/<item>', methods=['POST'])
def sell(item):
    if 'username' not in session:
        return redirect('/')
    user = USERS[session['username']]
    if item in user['inventory']:
        user['inventory'].remove(item)
        user['diamonds'] += ITEMS[item]['sell']
        save_users()
    return redirect('/shop')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ------------------- ADMIN -------------------

@app.route('/admin')
def admin():
    if session.get('username') != 'admin':
        return redirect('/')
    return render_template('admin.html', users=USERS, items=ITEMS)

@app.route('/assign_quest', methods=['POST'])
def assign_quest():
    if session.get('username') != 'admin':
        return redirect('/')
    username = request.form['username']
    title = request.form['title']
    reward = int(request.form['reward'])

    if username in USERS:
        quests = USERS[username]['quests']['custom']
        quest_id = f"quest{len(quests)+1}"
        quests[quest_id] = {
            "title": title,
            "reward": reward,
            "status": "assigned"
        }
        save_users()
    return redirect('/admin')

@app.route('/approve/<username>/<quest_id>', methods=['POST'])
def approve(username, quest_id):
    if session.get('username') != 'admin':
        return redirect('/')
    if username in USERS and quest_id in USERS[username]['quests']['custom']:
        USERS[username]['quests']['custom'][quest_id]['status'] = 'approved'
        save_users()
    return redirect('/admin')

@app.route('/give/<username>', methods=['POST'])
def give(username):
    if session.get('username') != 'admin':
        return redirect('/')
    amount = int(request.form['amount'])
    if username in USERS:
        USERS[username]['diamonds'] += amount
        save_users()
    return redirect('/admin')

@app.route('/delete/<username>')
def delete(username):
    if session.get('username') != 'admin':
        return redirect('/')
    if username in USERS:
        del USERS[username]
        save_users()
    return redirect('/admin')

@app.route('/update_prices', methods=['POST'])
def update_prices():
    if session.get('username') != 'admin':
        return redirect('/')
    for item in ITEMS:
        buy = request.form.get(f"{item}_buy")
        sell = request.form.get(f"{item}_sell")
        if buy and sell:
            ITEMS[item]['buy'] = int(buy)
            ITEMS[item]['sell'] = int(sell)
    save_items()
    return redirect('/admin')

# ---------------------------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
