from flask import Flask, render_template, request
import sqlite3

DB_PATH = 'db/srms_db.db'

app = Flask(__name__)
 
# @app.route("/")
# def home():
#     return "Ahmad Idris Musa"
@app.route('/')
def base():
     return render_template('base.html')

@app.route('/home')
def home():
     return render_template('home.html')

@app.route('/about')
def about():
     return render_template('about.html')

@app.route('/students')
def students():
     return render_template('students.html')

@app.route('/teachers')
def teachers():
     return render_template('teachers.html')

@app.route('/subjects')
def subjects():
     return render_template('subjects.html')

@app.route('/login', methods=['GET', 'POST', 'PATCH', 'DELETE'])
def login():
     query_result = None
     if request.method == 'POST':
          #RUN  a sqlite3 query when the button is click3d
          conn = sqlite3.connect(DB_PATH)
          cursor = conn.cursor()
          cursor.execute('SELECT COUNT(*) FROM tbl_students')
          ##[{id:001, reNo: 'is'}]
          query_result == cursor.fetchone();
          for row in query_result:
               print(row);
          
          conn.close()

     return render_template('login.html', query_result=query_result)