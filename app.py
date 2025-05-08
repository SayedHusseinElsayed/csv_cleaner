from flask import Flask, render_template, request, send_file, redirect, url_for
import os
import csv
import re
import tempfile
from werkzeug.utils import secure_filename
from zipfile import ZipFile

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
app.config['CLEANED_FOLDER'] = tempfile.mkdtemp()

SPECIAL_CHARACTERS_PATTERN = r"[<>`]"
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

def is_valid_email(text):
    return EMAIL_REGEX.match(text) is not None

def clean_text(text):
    if text is None:
        return ''
    text = text.strip()
    if not text:
        return ''
    if is_valid_email(text):
        return text

    if text.count('"') % 2 != 0:
        text = text.replace('"', '')

    preserved_parts = re.findall(r'\b(?:\d{1,2}[:/]){1,2}\d{1,4}(?:\s?[APap][Mm])?\b', text)
    for i, part in enumerate(preserved_parts):
        text = text.replace(part, f"__KEEP{i}__")

    text = re.sub(SPECIAL_CHARACTERS_PATTERN, ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    for i, part in enumerate(preserved_parts):
        text = text.replace(f"__KEEP{i}__", part)

    return text.strip()

def clean_csv_no_headers(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as infile:
        sample = infile.readline()
        infile.seek(0)
        delimiter = ';' if sample.count(';') > sample.count(',') else ','
        reader = csv.reader(infile, delimiter=delimiter)

        with open(output_path, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            for row in reader:
                cleaned_row = [clean_text(cell) for cell in row]
                if any(cell.strip() for cell in cleaned_row):
                    writer.writerow(cleaned_row)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        uploaded_files = request.files.getlist("files")
        cleaned_paths = []

        for file in uploaded_files:
            if file.filename == '':
                continue
            filename = secure_filename(file.filename)
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(input_path)

            output_name = filename.replace(".csv", "_cleaned.csv")
            output_path = os.path.join(app.config['CLEANED_FOLDER'], output_name)
            clean_csv_no_headers(input_path, output_path)
            cleaned_paths.append(output_path)

        # Zip the cleaned files
        zip_path = os.path.join(app.config['CLEANED_FOLDER'], 'cleaned_files.zip')
        with ZipFile(zip_path, 'w') as zipf:
            for file_path in cleaned_paths:
                zipf.write(file_path, os.path.basename(file_path))

        return redirect(url_for('download_file', filename='cleaned_files.zip'))

    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['CLEANED_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
