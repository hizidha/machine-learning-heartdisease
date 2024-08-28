from flask import Flask, redirect, url_for, request, session, render_template, send_file
from flask_mysqldb import MySQL # type: ignore
from dotenv import load_dotenv
from datetime import datetime
import io, os
import pandas as pd

from middleware import login_required, add_no_cache_headers, is_logged_in
from model import call_model

app = Flask(__name__)

load_dotenv()
os.getenv('TF_ENABLE_ONEDNN_OPTS')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

app.secret_key = os.getenv('SECRET_KEY')
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)


# remove cache header
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
                SELECT  d.timestamp, d.file_name, d.status, d.result_base, d.result_ensemble,
                        ac.label AS actual_label
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                ORDER BY d.id DESC;""")
    data = cur.fetchall()
    
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data 
                WHERE status = 'SUCCESS' AND id_actualLabel != 3241""")
    total_rows = cur.fetchone()['total_rows']
    
    # Base Learner
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                WHERE d.result_base = 'normal' AND ac.label = 'normal' AND d.status = 'SUCCESS';""")
    tp_base = cur.fetchone()['total_rows']
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                WHERE d.result_base = 'abnormal' AND ac.label = 'abnormal' AND d.status = 'SUCCESS';""")
    tn_base = cur.fetchone()['total_rows']
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                WHERE d.result_base = 'normal' AND ac.label = 'abnormal' AND d.status = 'SUCCESS';""")
    fp_base = cur.fetchone()['total_rows']
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                WHERE d.result_base = 'abnormal' AND ac.label = 'normal' AND d.status = 'SUCCESS';""")
    fn_base = cur.fetchone()['total_rows']

    # Base Learner
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                WHERE d.result_ensemble = 'normal' AND ac.label = 'normal' AND d.status = 'SUCCESS';""")
    tp_ensemble = cur.fetchone()['total_rows']
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                WHERE d.result_ensemble = 'abnormal' AND ac.label = 'abnormal' AND d.status = 'SUCCESS';""")
    tn_ensemble = cur.fetchone()['total_rows']
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                WHERE d.result_ensemble = 'normal' AND ac.label = 'abnormal' AND d.status = 'SUCCESS';""")
    fp_ensemble = cur.fetchone()['total_rows']
    cur.execute("""
                SELECT COUNT(*) AS total_rows 
                FROM data d LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                WHERE d.result_ensemble = 'abnormal' AND ac.label = 'normal' AND d.status = 'SUCCESS';""")
    fn_ensemble = cur.fetchone()['total_rows']
    
    cur.close()
    
    # Hitung metrik evaluasi model untuk model base
    if (tp_base + fp_base + fn_base + tn_base) != 0:
        accuracy_1 = round((tp_base + tn_base) / (tp_base + fp_base + fn_base + tn_base) * 100, 2)
    else:
        accuracy_1 = 0.0  # Atau nilai default lainnya jika dianggap sesuai

    if (tp_base + fp_base) != 0:
        precision_1 = round(tp_base / (tp_base + fp_base) * 100, 2)
    else:
        precision_1 = 0.0  # Atau nilai default lainnya jika dianggap sesuai

    if (tp_base + fn_base) != 0:
        recall_1 = round(tp_base / (tp_base + fn_base) * 100, 2)
    else:
        recall_1 = 0.0  # Atau nilai default lainnya jika dianggap sesuai

    if (recall_1 + precision_1) != 0:
        fscore_1 = round(2 * (recall_1 * precision_1) / (recall_1 + precision_1), 2)
    else:
        fscore_1 = 0.0  # Atau nilai default lainnya jika dianggap sesuai

    # Hitung metrik evaluasi model untuk ensemble model
    if (tp_ensemble + fp_ensemble + fn_ensemble + tn_ensemble) != 0:
        accuracy_2 = round((tp_ensemble + tn_ensemble) / (tp_ensemble + fp_ensemble + fn_ensemble + tn_ensemble) * 100, 2)
    else:
        accuracy_2 = 0.0  # Atau nilai default lainnya jika dianggap sesuai

    if (tp_ensemble + fp_ensemble) != 0:
        precision_2 = round(tp_ensemble / (tp_ensemble + fp_ensemble) * 100, 2)
    else:
        precision_2 = 0.0  # Atau nilai default lainnya jika dianggap sesuai

    if (tp_ensemble + fn_ensemble) != 0:
        recall_2 = round(tp_ensemble / (tp_ensemble + fn_ensemble) * 100, 2)
    else:
        recall_2 = 0.0  # Atau nilai default lainnya jika dianggap sesuai

    if (recall_2 + precision_2) != 0:
        fscore_2 = round(2 * (recall_2 * precision_2) / (recall_2 + precision_2), 2)
    else:
        fscore_2 = 0.0  # Atau nilai default lainnya jika dianggap sesuai
    
    success_message_login = session.pop('success_message_login', None)
    return render_template('developer.html', data=data, total_rows=total_rows, 
                        tp_1=tp_base, tn_1=tn_base, fp_1=fp_base, fn_1=fn_base, 
                        accuracy_base=accuracy_1, precision_base=precision_1, recall_base=recall_1, fscore_base=fscore_1,
                        tp_2=tp_ensemble, tn_2=tn_ensemble, fp_2=fp_ensemble, fn_2=fn_ensemble, 
                        accuracy_ensemble=accuracy_2, precision_ensemble=precision_2, recall_ensemble=recall_2, fscore_ensemble=fscore_2,
                        success=success_message_login)


@app.route('/exportData', methods=['GET'])
@login_required
def export_data():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if not start_date or not end_date:
        return "Start date and end date are required", 400
    
    # Query to fetch data within the date range
    query = """ SELECT d.timestamp, d.file_name, d.status, d.result_base, d.result_ensemble, ac.label AS actual_label
                FROM data d
                LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
                WHERE d.timestamp BETWEEN %s AND %s; """
    
    cur = mysql.connection.cursor()
    cur.execute(query, (start_date + ' 00:00:00', end_date + ' 23:59:59'))
    result = cur.fetchall()
    cur.close()
    
    # Create a DataFrame from the result
    df = pd.DataFrame(result, columns=['timestamp', 'file_name', 'status', 'result_base', 'result_ensemble', 'actual_label'])
    
    # Add a sequential number column
    df.insert(0, 'No', range(1, len(df) + 1))
    
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
            preds_base, preds_ensemble = call_model(file_path)
            
            if preds_base is not None:
                session['prediction_base'] = preds_base
                session['prediction_ensemble'] = preds_ensemble
                
                # Insert into the data table
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                status = 'SUCCESS'
                actuallabel_id = None
                
                # Get the actuallabel_id from the actuallabel table
                cur = mysql.connection.cursor()
                query = "SELECT id FROM actuallabel WHERE file_name = %s"
                cur.execute(query, (file_name_without_ext,))
                result = cur.fetchone()
                
                if result:
                    actuallabel_id = result['id']
                    query = """
                        INSERT INTO data (timestamp, file_name, status, result_base, result_ensemble, id_actualLabel)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cur.execute(query, (timestamp, file_name_without_ext, status, preds_base, preds_ensemble, actuallabel_id))
                else:
                    query = """
                        INSERT INTO data (timestamp, file_name, status, result_base, result_ensemble)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    cur.execute(query, (timestamp, file_name_without_ext, status, preds_base, preds_ensemble))
                
                mysql.connection.commit()
                cur.close()
                
                return redirect(url_for('results'))
            else:
                session['error_message'] = "Error in Preprocessing Data"
                session['prediction_base'] = None
                session['prediction_ensemble'] = None
                return redirect(url_for('home'))
        finally:
            # Ensure the temporary file is removed
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
        session['error_message'] = "Invalid file type, only .wav files are supported."
        session['prediction_base'] = None
        session['prediction_ensemble'] = None
        
        # Insert into the database
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = 'ERROR'
        
        cur = mysql.connection.cursor()
        query = """ INSERT INTO data (timestamp, file_name, status) VALUES (%s, %s, %s) """
        cur.execute(query, (timestamp, filename, status))
        mysql.connection.commit()
        cur.close()
        
        return redirect(url_for('home'))


@app.route('/results')
def results():
    prediction_1 = session.pop('prediction_base', None)
    prediction_2 = session.pop('prediction_ensemble', None)
    if prediction_1 is None:
        return redirect(url_for('home'))
    
    prediction_upper_1 = prediction_1.upper()
    prediction_upper_2 = prediction_2.upper()
    return render_template('results.html', prediction_base=prediction_upper_1, prediction_ensemble=prediction_upper_2)


if __name__ == '__main__':
    app.run(debug=True)