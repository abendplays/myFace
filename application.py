import face_recognition
from flask import Flask, flash, jsonify, redirect, render_template, request, session, \
    url_for, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os
from celery import Celery
from flask_session import Session
import random
from tempfile import mkdtemp
import time
from helpers import apology, login_required

import sqlite3
#import cs50

userName = ""

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SECRET_KEY'] = 'top-secret!'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
app.config['UPLOAD_FOLDER'] = '/home/deeplearning/Desktop/facialrec/profile'

# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

groupDB = sqlite3.connect("facialrec.db")
group = groupDB.cursor()
# initializing Databasconnector




known_image = face_recognition.load_image_file("/home/deeplearning/Desktop/facialrec/known face/Nik.jpg")
known_encoding = face_recognition.face_encodings(known_image)[0]
# known Face wird als Referenzbild geladen und encoded

unknown_image = []
unknown_encoding = []
results = []

inTolerance = 0.6
# arrays für alle mit den unknown images verwandten Teilen werden aufgesetzt


@app.route('/profile')
@login_required
def upload_file():
   return render_template('profile.html')


@app.route('/groups', methods = ['GET', 'POST'])
@login_required
def groups():
    if request.method == 'GET':
        return render_template('groups.html')
    else:
        print("false")


@app.route('/uploader', methods = ['GET', 'POST'])
@login_required
def upload_files():
   if request.method == 'POST':
      f = request.files['file']
      filename = secure_filename(f.filename)

      groupDB = sqlite3.connect("facialrec.db")
      group = groupDB.cursor()
      group.execute("SELECT * FROM users WHERE profilePic = :profilePic",
                    {'profilePic': filename})
      checkImage = group.fetchall()
      print(":", checkImage)
      if checkImage != []:
          return ('please rename this image') # todo: automatic rename
      group.execute("INSERT INTO users (profilePic) VALUES (:profilePic) WHERE userID = :userID", {'profilePic': filename, 'userID': session["user_id"]})
      groupDB.commit()  #fixen bugfix needed
      f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
      print("f.filename: ", f.filename)
      return 'file uploaded successfully'


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        groupDB = sqlite3.connect("facialrec.db")
        group = groupDB.cursor()
        username = request.form.get("username")
        password = request.form.get("password")
        conPassword = request.form.get("conPassword")
        if username == (''):
            return ("Please enter a valid username.")
        if password != conPassword:
            return ("The passwords don't match")  # todo, passwörter stimmen nicht überein
        if password == (''):
            return ("Password to short")
        if ',' in username:
            return("Sorry, the username can't contain the character ','.")
        group.execute("SELECT * FROM users WHERE userName = :checkUser", {'checkUser': username})
        checkUser = group.fetchall()
        if len(checkUser) != 0:
            return ("Nutername bereits vergeben.")  # todo, nutername bereits vergeben
        else:
            pwHashed = generate_password_hash(password)
            print("pwHashed:", pwHashed)
            group.execute("INSERT INTO users (userName, passwordHash) VALUES (:username, :pwHashed)", {'username': username, 'pwHashed': pwHashed})
            groupDB.commit()
            print("alles gut")
            return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        groupDB = sqlite3.connect("facialrec.db")
        group = groupDB.cursor()

        # Query database for username
        group.execute("SELECT * FROM users WHERE username = :username",
                      {'username': request.form.get("username")})
        rows = group.fetchall()
        userName = request.form.get("username")
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == 'GET':
        progress = 0
        return render_template("index.html", progress=progress)
    else:
        print("length:", len(imagesDB))
        progress = 0
        for image in imagesDB:
            print("", progress)
            progress += 1
        #algorithm()
        progress = progress
        print("progress", progress)
        return render_template("index.html", progress=progress)

#unknown_image ist die Image Datei, in die Geladen wird.


@celery.task(bind=True)
def long_task(self):
    group.execute("SELECT fileName FROM group1")
    imagesDB = group.fetchall()
    totalLen = len(imagesDB)
    runner = 0
    for image in imagesDB:  # es wird durch alle bilder geloopt
        n = 0
        check = 0
        # umgebungsvariablen werden gesetzt
        print("unknown Image from DB: ", imagesDB[runner][0])
        filePath = "/home/deeplearning/Desktop/facialrec/unknown face/%s" % (imagesDB[runner][0])
        unknown_image = face_recognition.load_image_file(filePath)  # Image wird geladen # images[row] wird es mal werden
        while check == 0:
            try:
                unknown_encoding = face_recognition.face_encodings(unknown_image)[n]
                n = n + 1
            except:
                check = 1
        # image wird durch eine try schleife durchgeschleift, bis es eine Fehlermeldung gibt. Dabei werden alle potenzielen Gesicher gecheckt
        # results = face_recognition.compare_faces([known_encoding], unknown_encoding, inTolerance)
        print("results:", results)
        currentImage = runner + 1
        self.update_state(state='PROGRESS',
                          meta={'current': currentImage, 'total': totalLen,
                                'status': 'successfully processed %s' % imagesDB[runner][0]})
        runner = runner + 1
        time.sleep(1)
    return {'current': currentImage, 'total': totalLen, 'status': 'Task completed!',
            'result': 'success'}


@app.route('/longtask', methods=['POST'])
def longtask():
    task = long_task.apply_async()
    return jsonify({}), 202, {'Location': url_for('taskstatus',
                                                  task_id=task.id)}

@app.route('/status/<task_id>')
def taskstatus(task_id):
    task = long_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


if __name__ == '__main__':
    app.run(debug=True)











