import os

import pandas as pd
import requests
from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from dkan import DataCatalogFetchAPI
from synthData import generate_synthetic_data

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = os.path.join('static', 'downloads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
app.secret_key = 'supersecretkey'

ALLOWED_EXTENSIONS = {'csv'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB in bytes

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_valid_csv_url(url):
    try:
        response = requests.get(url, allow_redirects=True, timeout=10, stream=True)
        content_type = response.headers.get('Content-Type', '')
        content_length = response.headers.get('Content-Length')

        # Check content length if available
        if content_length and int(content_length) > MAX_FILE_SIZE:
            return None  # File is too large

        if response.status_code == 200 and ('text/csv' in content_type or url.endswith('.csv')):
            temp_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'temp.csv')

            # Save the file in chunks and check size while writing
            total_size = 0
            with open(temp_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                    total_size += len(chunk)
                    if total_size > MAX_FILE_SIZE:
                        f.close()
                        os.remove(temp_filename)  # Delete oversized file
                        return None  # File is too large
                    f.write(chunk)

            return 'temp.csv'
        return None
    except requests.RequestException:
        return None

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404  # Render a custom 404 page

@app.route('/')
def index():  # put application's code here
    return render_template('index.html')

@app.route('/fetch_dkan',methods=['POST'])
def fetch_datasets():
    print('fetching datasets')
    dkan_api = DataCatalogFetchAPI("https://dassa.aphrc.org/data-catalog/")

    saved_urls= dkan_api.get_dataset_resources()
    return {"urls":saved_urls}

@app.route('/upload',methods=['POST','GET'])
def upload():  # put application's code here
    if request.method == 'POST':
        file = request.files.get('dataset')
        url = request.form.get('dataset_url')

        if file and file.filename:
            if allowed_file(file.filename):
                file.seek(0, os.SEEK_END)  # Move to end of file to get its size
                file_size = file.tell()  # Get the size in bytes
                file.seek(0)  # Reset file pointer to the beginning

                if file_size > MAX_FILE_SIZE:
                    flash('File is too large. Maximum allowed size is 500MB.', 'error')
                    return redirect(url_for('upload'))

                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                flash('File uploaded successfully!', 'success')
                return redirect(url_for('view_data', filename=filename))
            else:
                flash('Invalid file format. Only CSV files are allowed.', 'error')
                return redirect(url_for('upload'))

        elif url:
            tempfilename = is_valid_csv_url(url)
            if tempfilename:
                flash('Valid CSV URL provided!', 'success')
                return redirect(url_for('view_data', filename=tempfilename))
            else:
                flash('Invalid URL or not a CSV file.', 'error')
                return redirect(url_for('upload'))

        flash('Please upload a CSV file or provide a valid CSV URL.', 'error')
        return redirect(url_for('upload'))

    return render_template('upload/index.html')


@app.route('/view-data/<filename>')
def view_data(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    print(filepath)
    if not os.path.exists(filepath):
        flash('File not found!', 'error')
        return redirect(url_for('upload'))

    df = pd.read_csv(filepath)
    top_rows = df.head(10).to_dict(orient='records')
    columns = df.columns.tolist()

    return render_template('Process/view_data.html', columns=columns, rows=top_rows, filename=filename)

@app.route('/process-data/<filename>', methods=['POST'])
def process_columns(filename):
    selected_columns = request.form.getlist('selected_columns')

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(filepath):
        flash('File not found!', 'error')
        return redirect(url_for('upload'))
    try:
        gen_data = generate_synthetic_data(pd.read_csv(filepath), selected_columns)
    except Exception as e:
        print(e)
        flash('An error occurred. Try again.', 'error')
        return redirect(url_for('view_data', filename=filename))


    if gen_data is None:
        flash('Please select at least one column.', 'error')
        return redirect(url_for('view_data', filename=filename))

    gen_df = gen_data  # Keep only selected columns

    # Ensure download folder exists
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

    # Save processed CSV
    processed_filename = f"processed_{filename}"
    processed_filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], processed_filename)
    gen_df.to_csv(processed_filepath, index=False)

    flash('Synthic Data Generated successfully!', 'success')

    return redirect(url_for('download_data', filename=processed_filename))


@app.route('/download-data/<filename>')
def download_data(filename):
    processed_filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)

    if not os.path.exists(processed_filepath):
        flash('Processed file not found!', 'error')
        return redirect(url_for('upload'))

    # Read processed data
    df = pd.read_csv(processed_filepath)
    data = df.head(10).to_dict(orient='records')
    columns = df.columns.tolist()

    # Generate file download URL
    file_url = url_for('static', filename=f'downloads/{filename}', _external=True)

    return render_template('Process/download_data.html', columns=columns, rows=data, file_url=file_url, filename=filename)


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run()
