"""
Web UI לניהול חשבונות טלגרם
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for
import asyncio
import os
from accounts_manager import AccountManager

app = Flask(__name__)
manager = AccountManager()

# יצירת event loop לטיפול ב-async
def run_async(coro):
    """מריץ coroutine באופן סינכרוני"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@app.route('/')
def index():
    """דף הבית - רשימת חשבונות"""
    accounts = []
    for name in manager.list_accounts():
        account = manager.get_account(name)
        accounts.append({
            'name': name,
            'phone': account.get('phone', 'Bot'),
            'enabled': account.get('enabled', True),
            'has_client': name in manager.clients
        })
    return render_template('index.html', accounts=accounts)

@app.route('/account/add', methods=['GET', 'POST'])
def add_account():
    """הוספת חשבון חדש"""
    if request.method == 'POST':
        data = request.form
        name = data.get('name')
        api_id = int(data.get('api_id'))
        api_hash = data.get('api_hash')
        
        account_type = data.get('account_type')
        
        if account_type == 'bot':
            bot_token = data.get('bot_token')
            manager.add_account(name, api_id, api_hash, bot_token=bot_token)
        else:
            phone = data.get('phone')
            manager.add_account(name, api_id, api_hash, phone=phone)
        
        return redirect(url_for('index'))
    
    return render_template('add_account.html')

@app.route('/account/<name>/login', methods=['GET', 'POST'])
def login_account(name):
    """התחברות לחשבון"""
    if request.method == 'POST':
        code = request.form.get('code')
        result = run_async(manager.login_account(name, code))
        
        if result.get('success'):
            return redirect(url_for('index'))
        elif result.get('needs_code'):
            return render_template('login.html', name=name, needs_code=True)
        else:
            return render_template('login.html', name=name, error=result.get('error'))
    
    # GET - שליחת קוד
    result = run_async(manager.login_account(name))
    if result.get('needs_code'):
        return render_template('login.html', name=name, needs_code=True)
    
    return redirect(url_for('index'))

@app.route('/account/<name>/toggle', methods=['POST'])
def toggle_account(name):
    """הפעלה/כיבוי חשבון"""
    enabled = request.json.get('enabled', True)
    manager.toggle_account(name, enabled)
    return jsonify({'success': True})

@app.route('/account/<name>/delete', methods=['POST'])
def delete_account(name):
    """מחיקת חשבון"""
    manager.remove_account(name)
    return redirect(url_for('index'))

@app.route('/account/<name>/routes', methods=['GET', 'POST'])
def edit_routes(name):
    """עריכת routes לחשבון"""
    account = manager.get_account(name)
    if not account:
        return "Account not found", 404
    
    routes_file = account['routes_file']
    
    if request.method == 'POST':
        content = request.form.get('content')
        with open(routes_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return redirect(url_for('index'))
    
    # GET - הצגת קובץ
    if os.path.exists(routes_file):
        with open(routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = f"# Routes for {name}\nroutes: []"
    
    return render_template('edit_routes.html', name=name, content=content)

@app.route('/api/accounts')
def api_accounts():
    """API - רשימת חשבונות"""
    accounts = []
    for name in manager.list_accounts():
        account = manager.get_account(name)
        accounts.append({
            'name': name,
            'enabled': account.get('enabled'),
            'connected': name in manager.clients
        })
    return jsonify(accounts)

if __name__ == '__main__':
    # יצירת תיקיית templates אם לא קיימת
    os.makedirs('templates', exist_ok=True)
    
    print("🚀 Web UI running on http://localhost:5000")
    print("📱 Open browser to manage accounts")
    app.run(debug=True, host='0.0.0.0', port=5000)
