from flask import Flask
from flask import render_template, request
import os
import json
import database_helper


app = Flask(__name__, template_folder='templates', static_folder='static')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/projects')
def projects():
    return render_template('projects.html')


@app.route('/services')
def about():
    return render_template('services.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/projects/<filename>')
def project(filename):
    if filename in project_files:
        return render_template(f'projects/{filename}')
    else:
        return render_template("404.html"), 404


@app.route('/submit_contact_form', methods=['POST'])
def submit_contact_form():
    data = request.form
    print(data)
    database_helper.create_database()
    database_helper.insert_contact_request(data['firstname'],
                                           data['lastname'],
                                           data['country'],
                                           data['email'],
                                           data['message'])
    return render_template('form_submitted.html')


@app.route('/admin', methods=['POST'])
def admin():
    def read_credentials_from_file(file_path='credentials.json'):
        with open(file_path, 'r') as file:
            credentials_json = json.load(file)
        return credentials_json

    credentials = read_credentials_from_file()
    username = credentials.get('username', '')
    password = credentials.get('password', '')

    if request.method == 'POST':
        if request.form['username'] == username and request.form['password'] == password:
            return database_helper.get_database()
        else:
            return {"message": 'Incorrect username or password'}


if __name__ == '__main__':
    project_files = [f for f in os.listdir('../ClasenDataScience/templates/projects') if f.endswith('.html')]
    base_dir_files = [f for f in os.listdir('templates/') if f.endswith('.html')]

    app.run(debug=True)
