from flask import Flask, redirect, url_for, request, session, render_template, send_file
from dotenv import load_dotenv
from flask_mysqldb import MySQL # type: ignore
from datetime import datetime
import xlsxwriter, io, os
import pandas as pd

from middleware.users import login_required, add_no_cache_headers, is_logged_in
from model.models import callMymodel

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

# Setiap permintaan untuk menambahkan header no-cache
@app.after_request
def after_request(response):
    return add_no_cache_headers(response)

@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html'), 404

@app.route('/')
def home():
    error_message = session.pop('error_message', None)
    return render_template('index.html', error=error_message)

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
    cur.execute("SELECT * FROM data ORDER BY id DESC")
    data = cur.fetchall()
    cur.close()
    
    success_message_login = session.pop('success_message_login', None)
    return render_template('dashboard.html', data=data, success=success_message_login)

@app.route('/dashboard/dev')
@login_required
def dev_dashboard():    
    cur = mysql.connection.cursor()
    cur.execute("""
                SELECT  d.timestamp, d.fileName, d.status, d.result, 
                        ac.label AS actual_label
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                ORDER BY d.id DESC;""")
    data = cur.fetchall()
    
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data 
                WHERE status = 'SUCCESS' AND id_actualLabel != 3241""")
    total_rows = cur.fetchone()['total_rows']
    
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                WHERE d.result = 'normal' AND ac.label = 'normal' AND d.status = 'SUCCESS';""")
    tp = cur.fetchone()['total_rows']
    
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                WHERE d.result = 'abnormal' AND ac.label = 'abnormal' AND d.status = 'SUCCESS';""")
    tn = cur.fetchone()['total_rows']
    
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                WHERE d.result = 'normal' AND ac.label = 'abnormal' AND d.status = 'SUCCESS';""")
    fp = cur.fetchone()['total_rows']
    
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                WHERE d.result = 'abnormal' AND ac.label = 'normal' AND d.status = 'SUCCESS';""")
    fn = cur.fetchone()['total_rows']
    
    cur.close()
    
    accuracy = round((tp + tn) / (tp + fp + fn + tn) * 100, 2)
    precision = round(tp / (tp + fp) * 100, 2)
    recall = round(tp / (tp + fn) * 100, 2)
    fscore = round(2 * (recall * precision) / (recall + precision), 2)
    
    success_message_login = session.pop('success_message_login', None)
    return render_template('developer.html', data=data, total_rows=total_rows, tp=tp, tn=tn, fp=fp, fn=fn, 
                        accuracy=accuracy, precision=precision, recall=recall, fscore=fscore,
                        success=success_message_login)


@app.route('/exportData', methods=['GET'])
@login_required
def export_data():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if not start_date or not end_date:
        return "Start date and end date are required", 400
    
    # Query to fetch data within the date range
    query = """ SELECT * FROM data WHERE timestamp BETWEEN %s AND %s """
    
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
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                    as_attachment=True, download_name='filtered_data.xlsx')


@app.route('/uploadData', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        session['error_message'] = 'No file part'
        return redirect(url_for('home'))
    
    file = request.files['file']
    filename = file.filename
    file_name_without_ext = os.path.splitext(filename)[0]
    
    if file.filename == '':
        session['error_message'] = 'No selected file'
        return redirect(url_for('home'))
    
    if file and file.filename.endswith('.wav'):
        file_path = os.path.join('./data', filename)
        file.save(file_path)
        
        try:
            preds = callMymodel(file_path)
            
            if preds is not None:
                session['prediction'] = preds
                
                # Insert into the data table
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                status = 'SUCCESS'
                actuallabel_id = None
                
                # Get the actuallabel_id from the actuallabel table
                cur = mysql.connection.cursor()
                query = "SELECT id FROM actuallabel WHERE fileName = %s"
                cur.execute(query, (file_name_without_ext,))
                result = cur.fetchone()
                
                if result:
                    actuallabel_id = result['id']
                    query = """
                        INSERT INTO data (timestamp, fileName, status, result, id_actualLabel)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    cur.execute(query, (timestamp, file_name_without_ext, status, preds, actuallabel_id))
                else:
                    query = """
                        INSERT INTO data (timestamp, fileName, status, result)
                        VALUES (%s, %s, %s, %s)
                    """
                    cur.execute(query, (timestamp, file_name_without_ext, status, preds))
                
                mysql.connection.commit()
                cur.close()
                
                return redirect(url_for('results'))
            else:
                session['error_message'] = "Error in Preprocessing Data"
                session['prediction'] = None
                return redirect(url_for('home'))
        finally:
            # Ensure the temporary file is removed
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
        session['error_message'] = "Invalid file type, only .wav files are supported."
        session['prediction'] = None
        
        # Insert into the database
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = 'ERROR'
        
        cur = mysql.connection.cursor()
        query = """ INSERT INTO data (timestamp, fileName, status) VALUES (%s, %s, %s) """
        cur.execute(query, (timestamp, filename, status))
        mysql.connection.commit()
        cur.close()
        
        return redirect(url_for('home'))


@app.route('/results')
def results():
    prediction = session.pop('prediction', None)
    if prediction is None:
        return redirect(url_for('home'))
    
    prediction_upper = prediction.upper()
    return render_template('results.html', prediction=prediction_upper)


if __name__ == '__main__':
    app.run(debug=True)