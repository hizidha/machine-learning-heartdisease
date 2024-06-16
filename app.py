from flask import Flask, redirect, url_for, request, session, render_template, send_file
from middleware.users import login_required, add_no_cache_headers, is_logged_in
from flask_mysqldb import MySQL
from dotenv import load_dotenv
import pandas as pd
import io
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# MySQL configurations
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.after_request
def after_request(response):
    return add_no_cache_headers(response)

@app.route('/')
def home():
    return redirect(url_for('login_page'))

@app.route('/dashboard', methods=['GET', 'POST'])
def login_page():
    errors = ''
    success_message = session.pop('success_message', None)
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == 'superadmin' and password == 'admin123':
            session['logged_in'] = True
            session['success_message_login'] = 'You have been successfully logged in.'
            return redirect(url_for('admin_dashboard'))
        else:
            errors = 'Invalid credentials. Please try again.'
            return render_template('login.html', error=errors)
        
    elif request.method == 'GET':
        if is_logged_in():
            return redirect(url_for('admin_dashboard'))
        else:
            session.pop('success_message', None)
            return render_template('login.html', success=success_message)

@app.route('/logout')
def logout():
    if is_logged_in():
        session.pop('logged_in', None)
        session['success_message'] = 'You have been successfully logged out.'
    return redirect(url_for('login_page'))

@app.route('/dashboard/admin')
@login_required
def admin_dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM data")
    data = cur.fetchall()
    cur.close()
    
    success_message_login = session.pop('success_message_login', None)
    return render_template('dashboard.html', data=data, success=success_message_login)

@app.route('/exportData', methods=['GET'])
@login_required
def export_data():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if not start_date or not end_date:
        return "Start date and end date are required", 400
    
    # Query to fetch data within the date range
    query = """
    SELECT * FROM data
    WHERE timestamp BETWEEN %s AND %s
    """
    
    cur = mysql.connection.cursor()
    cur.execute(query, (start_date + ' 00:00:00', end_date + ' 23:59:59'))
    result = cur.fetchall()
    cur.close()
    
    # Create a DataFrame from the result
    df = pd.DataFrame(result)
    
    # Create an Excel file from the DataFrame
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)
    
    output.seek(0)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='data.xlsx')


if __name__ == '__main__':
    app.run(debug=True)