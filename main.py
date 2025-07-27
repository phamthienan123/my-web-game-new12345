from flask import Flask, render_template, request, redirect, session
import os, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# Khởi tạo dữ liệu USERS
if os.path.exists('users.json'):
    try:
        with open('users.json', 'r') as f:
            USERS = json.load(f)
    except json.JSONDecodeError:
        USERS = {}
else:
    USERS = {}

# Khởi tạo dữ liệu ITEMS
if os.path.exists('items.json'):
    with open('items.json', 'r') as f:
        ITEMS = json.load(f)
else:
    ITEMS = {
        "kiếm rồng": {"buy": 20, "sell": 10, "image": "kiem.png"},
        "giáp vàng": {"buy": 35, "sell": 17, "image": "giap.jpg"},
        "khiên băng": {"buy": 40, "sell": 20, "image": "khien.jpg"}
    }
    with open('items.json', 'w') as f:
        json.dump(ITEMS, f, indent=2)

# Trang đăng nhập
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
            error = 'Sai tài khoản hoặc mật khẩu.'
    return render_template('index.html', error=error)

# Trang đăng ký
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS:
            error = 'Tên tài khoản đã tồn tại.'
        else:
            USERS[username] = {
                "password": password,
                "diamonds": 0,
                "inventory": [],
                "quests": {}
            }
            with open('users.json', 'w') as f:
                json.dump(USERS, f, indent=2)
            return redirect('/')
    return render_template('register.html', error=error)

# Trang người dùng chính
@app.route('/dashboard')
def dashboard():
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    username = session['username']
    user_data = USERS[username]

    # Nhiệm vụ đăng nhập mỗi ngày
    today = datetime.now().strftime('%Y-%m-%d')
    quests = user_data.get("quests", {})
    daily = quests.get("daily_login", {})
    last_claimed = daily.get("last_claimed")

    new_claim = False
    if last_claimed != today:
        quests["daily_login"] = {"last_claimed": today}
        user_data['diamonds'] += 5
        new_claim = True

    user_data["quests"] = quests
    USERS[username] = user_data
    with open('users.json', 'w') as f:
        json.dump(USERS, f, indent=2)

    return render_template("dashboard.html", username=username, diamonds=user_data['diamonds'], new_claim=new_claim)

# Trang cửa hàng
@app.route('/shop')
def shop():
    if 'username' not in session or session['username'] == 'admin':
        return redirect('/')
    username = session['username']
    user_data = USERS[username]
    return render_template("shop.html", username=username, diamonds=user_data['diamonds'], items=ITEMS, inventory=user_data['inventory'])

# Mua vật phẩm
@app.route('/buy/<item>', methods=['POST'])
def buy_item(item):
    username = session.get('username')
    if not username or username == 'admin':
        return redirect('/')
    if item not in ITEMS:
        return redirect('/shop')

    user = USERS[username]
    if item in user['inventory']:
        return redirect('/shop')
    if user['diamonds'] >= ITEMS[item]['buy']:
        user['diamonds'] -= ITEMS[item]['buy']
        user['inventory'].append(item)
        USERS[username] = user
        with open('users.json', 'w') as f:
            json.dump(USERS, f, indent=2)
    return redirect('/shop')

# Bán vật phẩm
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
            json.dump(USERS, f, indent=2)
    return redirect('/shop')

# Trang quản lý admin
@app.route('/admin')
def admin():
    if session.get('username') != 'admin':
        return redirect('/')
    users = {u: info for u, info in USERS.items() if u != 'admin'}
    return render_template("admin.html", users=users)

# Admin tặng kim cương
@app.route('/give/<username>', methods=['POST'])
def give_diamonds(username):
    if session.get('username') != 'admin':
        return redirect('/')
    amount = int(request.form.get('amount', 0))
    if username in USERS:
        USERS[username]['diamonds'] += amount
        with open('users.json', 'w') as f:
            json.dump(USERS, f, indent=2)
    return redirect('/admin')

# Admin tạo nhiệm vụ
@app.route('/add_quest', methods=['POST'])
def add_quest():
    if session.get('username') != 'admin':
        return redirect('/')
    title = request.form.get('title')
    reward = int(request.form.get('reward', 0))
    for user in USERS:
        if user != 'admin':
            USERS[user]['quests'].setdefault('custom', {})
            USERS[user]['quests']['custom'][title] = {
                "title": title,
                "reward": reward,
                "status": "pending"
            }
    with open('users.json', 'w') as f:
        json.dump(USERS, f, indent=2)
    return redirect('/admin')

# User gửi yêu cầu hoàn thành nhiệm vụ
@app.route('/submit_quest/<quest>', methods=['POST'])
def submit_quest(quest):
    username = session.get('username')
    if not username or username == 'admin':
        return redirect('/')
    user = USERS[username]
    user['quests']['custom'][quest]['status'] = "submitted"
    with open('users.json', 'w') as f:
        json.dump(USERS, f, indent=2)
    return redirect('/dashboard')

# Admin duyệt nhiệm vụ
@app.route('/approve/<username>/<quest>', methods=['POST'])
def approve_quest(username, quest):
    if session.get('username') != 'admin':
        return redirect('/')
    if username in USERS:
        USERS[username]['quests']['custom'][quest]['status'] = 'approved'
        reward = USERS[username]['quests']['custom'][quest]['reward']
        USERS[username]['diamonds'] += reward
        with open('users.json', 'w') as f:
            json.dump(USERS, f, indent=2)
    return redirect('/admin')

# Đăng xuất
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
