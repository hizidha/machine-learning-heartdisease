import os
import io
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

load_dotenv()

from flask import Flask, jsonify, redirect, url_for, request, session, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from middleware import login_required, add_no_cache_headers, is_logged_in
from model import call_model

app = Flask(__name__)

# Configure DB
app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@"
    f"{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)


# Middleware to add no-cache headers
@app.after_request
def after_request(response):
    return add_no_cache_headers(response)

# Error handler for 404
@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html'), 404

# Home route
@app.route('/')
def home():
    error_message = session.pop('error_message', None)
    return render_template('index.html', error=error_message)

# Login route
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

# Logout route
@app.route('/logout')
def logout():
    if is_logged_in():
        session.pop('logged_in', None)
        session['success_message'] = 'You have been successfully logged out.'
    return redirect(url_for('login_page'))

# Admin dashboard route
@app.route('/dashboard/admin')
@login_required
def admin_dashboard():
    data = db.session.execute(text("SELECT * FROM data ORDER BY id DESC")).fetchall()
    success_message_login = session.pop('success_message_login', None)
    return render_template('dashboard.html', data=data, success=success_message_login)

# Developer dashboard route
@app.route('/dashboard/dev')
@login_required
def dev_dashboard():
    data = db.session.execute(text("""
        SELECT d.timestamp, d.file_name, d.status, d.result_base, d.result_ensemble, ac.label AS actual_label
        FROM data d
        LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
        ORDER BY d.id DESC;
    """)).fetchall()

    total_rows = db.session.execute(text("""
        SELECT COUNT(*) AS total_rows 
        FROM data 
        WHERE status = 'SUCCESS' AND id_actualLabel != 3241;
    """)).scalar()

    # Queries for Base Learner metrics
    tp_base = db.session.execute(text("""
        SELECT COUNT(*) AS total_rows 
        FROM data d 
        LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
        WHERE d.result_base = 'normal' AND ac.label = 'normal' AND d.status = 'SUCCESS';
    """)).scalar()
    tn_base = db.session.execute(text("""
        SELECT COUNT(*) AS total_rows 
        FROM data d 
        LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
        WHERE d.result_base = 'abnormal' AND ac.label = 'abnormal' AND d.status = 'SUCCESS';
    """)).scalar()
    fp_base = db.session.execute(text("""
        SELECT COUNT(*) AS total_rows 
        FROM data d 
        LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
        WHERE d.result_base = 'normal' AND ac.label = 'abnormal' AND d.status = 'SUCCESS';
    """)).scalar()
    fn_base = db.session.execute(text("""
        SELECT COUNT(*) AS total_rows 
        FROM data d 
        LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
        WHERE d.result_base = 'abnormal' AND ac.label = 'normal' AND d.status = 'SUCCESS';
    """)).scalar()

    # Queries for Ensemble Learner metrics
    tp_ensemble = db.session.execute(text("""
        SELECT COUNT(*) AS total_rows 
        FROM data d 
        LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
        WHERE d.result_ensemble = 'normal' AND ac.label = 'normal' AND d.status = 'SUCCESS';
    """)).scalar()
    tn_ensemble = db.session.execute(text("""
        SELECT COUNT(*) AS total_rows 
        FROM data d 
        LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
        WHERE d.result_ensemble = 'abnormal' AND ac.label = 'abnormal' AND d.status = 'SUCCESS';
    """)).scalar()
    fp_ensemble = db.session.execute(text("""
        SELECT COUNT(*) AS total_rows 
        FROM data d 
        LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
        WHERE d.result_ensemble = 'normal' AND ac.label = 'abnormal' AND d.status = 'SUCCESS';
    """)).scalar()
    fn_ensemble = db.session.execute(text("""
        SELECT COUNT(*) AS total_rows 
        FROM data d 
        LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
        WHERE d.result_ensemble = 'abnormal' AND ac.label = 'normal' AND d.status = 'SUCCESS';
    """)).scalar()
    
    # Calculate evaluation metrics for base model
    accuracy_1 = round((tp_base + tn_base) / (tp_base + fp_base + fn_base + tn_base) * 100, 2) if (tp_base + fp_base + fn_base + tn_base) != 0 else 0.0
    precision_1 = round(tp_base / (tp_base + fp_base) * 100, 2) if (tp_base + fp_base) != 0 else 0.0
    recall_1 = round(tp_base / (tp_base + fn_base) * 100, 2) if (tp_base + fn_base) != 0 else 0.0
    fscore_1 = round(2 * (recall_1 * precision_1) / (recall_1 + precision_1), 2) if (recall_1 + precision_1) != 0 else 0.0

    # Calculate evaluation metrics for ensemble model
    accuracy_2 = round((tp_ensemble + tn_ensemble) / (tp_ensemble + fp_ensemble + fn_ensemble + tn_ensemble) * 100, 2) if (tp_ensemble + fp_ensemble + fn_ensemble + tn_ensemble) != 0 else 0.0
    precision_2 = round(tp_ensemble / (tp_ensemble + fp_ensemble) * 100, 2) if (tp_ensemble + fp_ensemble) != 0 else 0.0
    recall_2 = round(tp_ensemble / (tp_ensemble + fn_ensemble) * 100, 2) if (tp_ensemble + fn_ensemble) != 0 else 0.0
    fscore_2 = round(2 * (recall_2 * precision_2) / (recall_2 + precision_2), 2) if (recall_2 + precision_2) != 0 else 0.0
    
    success_message_login = session.pop('success_message_login', None)
    return render_template('developer.html', data=data, total_rows=total_rows, 
                        tp_1=tp_base, tn_1=tn_base, fp_1=fp_base, fn_1=fn_base, 
                        accuracy_base=accuracy_1, precision_base=precision_1, recall_base=recall_1, fscore_base=fscore_1,
                        tp_2=tp_ensemble, tn_2=tn_ensemble, fp_2=fp_ensemble, fn_2=fn_ensemble, 
                        accuracy_ensemble=accuracy_2, precision_ensemble=precision_2, recall_ensemble=recall_2, fscore_ensemble=fscore_2,
                        success=success_message_login)

# Export data route
@app.route('/exportData', methods=['GET'])
@login_required
def export_data():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if not start_date or not end_date:
        return jsonify({"error": "Start date and end date are required"}), 400
    
    # Parse dates and add time if needed
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    # Query to fetch data within the date range
    query = text("""
        SELECT d.timestamp, d.file_name, d.status, d.result_base, d.result_ensemble, ac.label AS actual_label
        FROM data d
        LEFT JOIN actuallabel ac ON d.id_actualLabel = ac.id
        WHERE d.timestamp >= :start_date AND d.timestamp <= :end_date
        ORDER BY d.id DESC;
    """)
    
    result = db.session.execute(query, {"start_date": start_date, "end_date": end_date})
    data = result.fetchall()

    # Convert data to DataFrame for exporting to Excel
    df = pd.DataFrame(data, columns=['Timestamp', 'File Name', 'Status', 'Result Base', 'Result Ensemble', 'Actual Label'])
    
    # Convert datetime columns to timezone-naive
    if 'Timestamp' in df.columns:
        df['Timestamp'] = df['Timestamp'].apply(lambda x: x.replace(tzinfo=None) if pd.notnull(x) else x)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')

    output.seek(0)

    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                    download_name=f'Data_{start_date.strftime("%Y-%m-%d")}_to_{end_date.strftime("%Y-%m-%d")}.xlsx', as_attachment=True)

# Upload data route
@app.route('/predict', methods=['POST'])
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
                
                # Fetch actuallabel_id from actuallabel table
                result = db.session.execute(text("SELECT id FROM actuallabel WHERE file_name = :file_name"), 
                            {"file_name": file_name_without_ext}).fetchone()
                
                if result:
                    actuallabel_id = result[0]
                    db.session.execute(text("""
                        INSERT INTO data (timestamp, file_name, status, result_base, result_ensemble, id_actualLabel)
                        VALUES (:timestamp, :file_name, :status, :result_base, :result_ensemble, :id_actualLabel)
                    """), {
                        "timestamp": timestamp, 
                        "file_name": file_name_without_ext, 
                        "status": status, 
                        "result_base": preds_base, 
                        "result_ensemble": preds_ensemble, 
                        "id_actualLabel": actuallabel_id
                    })
                else:
                    db.session.execute(text("""
                        INSERT INTO data (timestamp, file_name, status, result_base, result_ensemble)
                        VALUES (:timestamp, :file_name, :status, :result_base, :result_ensemble)
                    """), {
                        "timestamp": timestamp, 
                        "file_name": file_name_without_ext, 
                        "status": status, 
                        "result_base": preds_base, 
                        "result_ensemble": preds_ensemble
                    })
                db.session.commit()
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
        
        # Insert error status into the database
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = 'ERROR'
        
        db.session.execute(text("""
            INSERT INTO data (timestamp, file_name, status) 
            VALUES (:timestamp, :file_name, :status)
        """), {
            "timestamp": timestamp, 
            "file_name": filename, 
            "status": status
        })
        db.session.commit()
        return redirect(url_for('home'))

# Results route
@app.route('/results')
def results():
    prediction_1 = session.pop('prediction_base', None)
    prediction_2 = session.pop('prediction_ensemble', None)
    
    if prediction_1 is None:
        return redirect(url_for('home'))
    
    prediction_upper_1 = prediction_1.upper()
    prediction_upper_2 = prediction_2.upper()
    
    return render_template('results.html', prediction_base=prediction_upper_1, prediction_ensemble=prediction_upper_2)


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)