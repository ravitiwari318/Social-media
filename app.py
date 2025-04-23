from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretmre'


@app.route('/')
def index():
    flash('Welcome to the Flask App', 'info')
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/loginpage')
def login():
    return render_template('loginpage.html')
  
@app.route('/registration')
def registration():
    return render_template("registration.html")  

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)