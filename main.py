from flask import Flask, render_template, request, redirect, session, send_from_directory, url_for
import json, os, time
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# ========= Config upload =========
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTS

# ========= Load data =========
def load_json(path, default):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

USERS = load_json('users.json', {})
ITEMS = load_json('items.json', {})  # nếu bạn có shop

def save_users():
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(USERS, f, indent=4, ensure_ascii=False)

def save_items():
    with open('items.json', 'w', encoding='utf-8') as f:
        json.dump(ITEMS, f, indent=4, ensure_ascii=False)

# ========= Helpers =========
def ensure_user_scaffold(username):
    """Đảm bảo user có đủ các trường cần thiết."""
    USERS.setdefault(username, {})
    u = USERS[username]
    u.setdefault('password', '')
    u.setdefault('diamonds', 0)
    u.setdefault('inventory', [])
    u.setdefault('quests', {})
    u['quests'].setdefault('daily_login', {'last_claimed': ''})
    u['quests'].setdefault('custom', {})

def is_admin():
    return 'username' in session and session['username'] == 'admin'

# ========= Auth =========
@app.route('/', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        if username in USERS and USERS[username]['password'] == password:
            session['username'] = username
            return redirect('/admin' if username == 'admin' else '/dashboard')
        error = 'Sai tài khoản hoặc mật khẩu!'
    return render_template('index.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ''
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        if not username:
            error = 'Vui lòng nhập tên tài khoản.'
        elif username in USERS:
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ========= Dashboard (user) =========
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    ensure_user_scaffold(username)
    u = USERS[username]

    # Daily reward available?
    today = datetime.now().date().isoformat()
    last_claimed = u['quests']['daily_login'].get('last_claimed', '')
    new_claim = (last_claimed != today)

    # Highest rank (nếu shop bán rank)
    rank_order = ['rank_bronze', 'rank_silver', 'rank_gold', 'rank_platinum', 'rank_diamond']
    highest_rank = None
    for r in reversed(rank_order):
        if r in u.get('inventory', []):
            highest_rank = r
            break

    return render_template(
        'dashboard.html',
        username=username,
        diamonds=u.get('diamonds', 0),
        custom_quests=u['quests']['custom'],
        new_claim=new_claim,
        highest_rank=highest_rank
    )

@app.route('/claim/daily')
def claim_daily():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    ensure_user_scaffold(username)
    u = USERS[username]

    today = datetime.now().date().isoformat()
    last_claimed = u['quests']['daily_login'].get('last_claimed', '')
    if last_claimed != today:
        u['diamonds'] += 10
        u['quests']['daily_login']['last_claimed'] = today
        save_users()
    return redirect('/dashboard')

# ========= SHOP (tùy chọn nếu bạn dùng) =========
@app.route('/shop')
def shop():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    ensure_user_scaffold(username)
    u = USERS[username]
    return render_template('shop.html',
                           username=username,
                           diamonds=u.get('diamonds', 0),
                           inventory=u.get('inventory', []),
                           items=ITEMS)

@app.route('/buy/<item>', methods=['POST'])
def buy(item):
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    ensure_user_scaffold(username)
    u = USERS[username]
    if item in ITEMS and item not in u['inventory'] and u['diamonds'] >= ITEMS[item]['buy']:
        u['diamonds'] -= ITEMS[item]['buy']
        u['inventory'].append(item)
        save_users()
    return redirect('/shop')

@app.route('/sell/<item>', methods=['POST'])
def sell(item):
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    ensure_user_scaffold(username)
    u = USERS[username]
    if item in u['inventory'] and item in ITEMS:
        u['inventory'].remove(item)
        u['diamonds'] += ITEMS[item]['sell']
        save_users()
    return redirect('/shop')

# ========= QUIZ: User submit =========
@app.route('/submit_quiz/<quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    ensure_user_scaffold(username)
    u = USERS[username]

    quiz = u['quests']['custom'].get(quiz_id)
    if not quiz or quiz.get('status') not in ('available', 'rejected'):
        return redirect('/dashboard')

    chosen = request.form.get('answer')
    if chosen is None:
        return redirect('/dashboard')

    # lưu đáp án & chờ duyệt
    try:
        u['quests']['custom'][quiz_id]['user_answer'] = int(chosen)
    except:
        u['quests']['custom'][quiz_id]['user_answer'] = chosen  # fallback
    u['quests']['custom'][quiz_id]['status'] = 'waiting_approval'
    u['quests']['custom'][quiz_id]['submitted_at'] = datetime.now().isoformat()

    save_users()
    return redirect('/dashboard')

# ========= ADMIN =========
@app.route('/admin')
def admin():
    if not is_admin():
        return redirect('/')
    # tổng hợp pending
    pending = []  # list of dicts {username, qid, quiz}
    for name, data in USERS.items():
        if name == 'admin':  # bỏ qua chính admin
            continue
        ensure_user_scaffold(name)
        for qid, q in data['quests']['custom'].items():
            if q.get('status') == 'waiting_approval':
                pending.append({'username': name, 'qid': qid, 'quiz': q})
    return render_template('admin.html', users=USERS, pending=pending)

@app.route('/create_quiz', methods=['POST'])
def create_quiz():
    if not is_admin():
        return redirect('/')

    title = request.form.get('title','').strip()
    question = request.form.get('question','').strip()
    reward = int(request.form.get('reward', 0))
    # options
    options = [
        request.form.get('opt1','').strip(),
        request.form.get('opt2','').strip(),
        request.form.get('opt3','').strip(),
        request.form.get('opt4','').strip(),
    ]
    # đáp án đúng (index 0-3)
    correct_idx = int(request.form.get('correct', 0))
    target = request.form.get('target','ALL').strip()

    # ảnh (tùy chọn)
    image_path = ''
    file = request.files.get('image')
    if file and file.filename and allowed_file(file.filename):
        fname = secure_filename(f"{int(time.time())}_{file.filename}")
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        file.save(save_path)
        image_path = os.path.join('static', 'uploads', fname)

    # tạo id
    quiz_id = f"quiz_{int(time.time())}"

    def put_quiz(user):
        ensure_user_scaffold(user)
        USERS[user]['quests']['custom'][quiz_id] = {
            "title": title or "Quiz",
            "image": image_path,
            "question": question,
            "options": options,
            "answer": correct_idx,
            "reward": reward,
            "status": "available",
            "user_answer": None
        }

    if target == 'ALL':
        for name in USERS.keys():
            if name != 'admin':
                put_quiz(name)
    else:
        if target in USERS:
            put_quiz(target)

    save_users()
    return redirect('/admin')

@app.route('/approve_quiz/<username>/<quiz_id>', methods=['POST'])
def approve_quiz(username, quiz_id):
    if not is_admin():
        return redirect('/')
    ensure_user_scaffold(username)
    u = USERS[username]
    quiz = u['quests']['custom'].get(quiz_id)
    if not quiz or quiz.get('status') != 'waiting_approval':
        return redirect('/admin')

    # check đúng / sai
    correct = False
    if isinstance(quiz.get('answer'), int) and isinstance(quiz.get('user_answer'), int):
        correct = (quiz['answer'] == quiz['user_answer'])

    # cập nhật
    u['quests']['custom'][quiz_id]['status'] = 'approved'
    u['quests']['custom'][quiz_id]['approved_at'] = datetime.now().isoformat()
    u['quests']['custom'][quiz_id]['approved_result'] = 'correct' if correct else 'wrong'

    if correct:
        u['diamonds'] += int(quiz.get('reward', 0))

    save_users()
    return redirect('/admin')

@app.route('/reject_quiz/<username>/<quiz_id>', methods=['POST'])
def reject_quiz(username, quiz_id):
    if not is_admin():
        return redirect('/')
    ensure_user_scaffold(username)
    u = USERS[username]
    if quiz_id in u['quests']['custom']:
        u['quests']['custom'][quiz_id]['status'] = 'rejected'
        u['quests']['custom'][quiz_id]['rejected_at'] = datetime.now().isoformat()
        save_users()
    return redirect('/admin')

# ========= Run =========
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
