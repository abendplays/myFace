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
app.config['UPLOAD_FOLDER'] = '/home/deeplearning/Desktop/facialrec/static/profile'
app.config['UPLOAD_FOLDER_IMG'] = '/home/deeplearning/Desktop/facialrec/static/gallery'

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

#groupDB = sqlite3.connect("facialrec.db")
#group = groupDB.cursor()
# initializing Databasconnector




known_image = face_recognition.load_image_file("/home/deeplearning/Desktop/facialrec/known face/Nik.jpg")
known_encoding = face_recognition.face_encodings(known_image)[0]
# known Face wird als Referenzbild geladen und encoded

unknown_image = []
unknown_encoding = []
results = []

inTolerance = 0.6
# arrays für alle mit den unknown images verwandten Teilen werden aufgesetzt


@app.route('/profile', methods = ['GET', 'POST']) # TODO check for exsisting profile picture and delete if applicable
@login_required
def profile():
    if request.method == 'GET':
        groupDB = sqlite3.connect("facialrec.db")
        group = groupDB.cursor()
        group.execute("SELECT profilePic FROM users WHERE userID = :userID", {'userID': session["user_id"]})
        imageID = group.fetchall()
        group.execute("SELECT userName FROM users WHERE userID = :userID", {'userID': session["user_id"]})
        userName = group.fetchall()
        userName = userName[0][0]
        print("imageID:", imageID[0][0])
        if imageID[0][0] == None:
            profilePic = 'noPBset.jpg'
        else:
            group.execute("SELECT ending FROM profiles WHERE userID = :userID", {'userID': session["user_id"]})
            ending = group.fetchall()
            profilePic = str(imageID[0][0]) + (ending[0][0])
        group.execute("SELECT COUNT (*) FROM invites WHERE userID = :userID AND status=0", {'userID': session["user_id"]})
        active = group.fetchall()
        group.execute("SELECT COUNT (*) FROM invites WHERE userID = :userID AND status=1", {'userID': session["user_id"]})
        pending = group.fetchall()
        return render_template('profile.html',  userName=userName, profilePic=profilePic, active=active, pending=pending) #profilePic=profilePic,
    else:
        print("start")
        file = request.files['file']
        print("start")
        filename = secure_filename(file.filename)
        groupDB = sqlite3.connect("facialrec.db")
        extension = os.path.splitext(filename)[1]
        group = groupDB.cursor()
        group.execute("SELECT COUNT(*) FROM profiles")
        lastID = group.fetchall()
        print("last id: ", lastID[0][0])
        newID = str(lastID[0][0] + 1)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)) #, filename))
        os.rename(app.config['UPLOAD_FOLDER'] + '/' + filename, app.config['UPLOAD_FOLDER'] + '/' + newID + extension)
        group.execute("UPDATE users SET profilePic = :profilePic WHERE userID = :userID", {'profilePic': newID, 'userID': session["user_id"]})
        groupDB.commit()
        intID = str(newID)
        group.execute("INSERT INTO profiles (imageID, userID, ending) VALUES (:imageID, :userID, :ending)", {'imageID': intID, 'userID': session["user_id"], 'ending': extension})
        groupDB.commit()
        print("Name of the new profile Picture:", newID)
        profilePic = str(newID[0][0]) + extension
        group.execute("SELECT userName FROM users WHERE userID = :userID", {'userID': session["user_id"]})
        userName = group.fetchall()
        return redirect("profile")


@app.route('/groups', methods = ['GET', 'POST'])
@login_required
def groups():
    if request.method == 'GET':
        db = sqlite3.connect("facialrec.db")
        inbox = db.cursor()
        inbox.execute("SELECT groupName, createdBy, groupID FROM invites WHERE userID = :userID AND status = 0",
                      {'userID': session["user_id"]})
        groupNames = inbox.fetchall()
        runner = 0
        test = []
        for groupName in groupNames:
            inbox.execute("SELECT userName FROM invites WHERE groupID = :groupID AND status = 0",
                          {'groupID': groupNames[runner][2]})
            users = inbox.fetchall()
            # print("", users)
            # print("grouping:", groupNames[runner][2])
            laeufer = 0
            participants = ""
            for users in users:
                if laeufer == 0:
                    participants = participants + users[0]
                    laeufer += 1
                else:
                    participants = participants + ", " + users[0]
                    laeufer += 1
            test.append(participants)
            # test.append(participants)
            runner += 1
            # print("groupNames:", groupNames)
        return render_template('groups.html', groupNames=zip(groupNames, test))
    else:
        try:
            submitOrig = request.form["userNames"]
            print("submitOrig 1: ", submitOrig)
        except:
            submitOrig = None
            print("It's not a new group")
        if submitOrig is not None:
            groupName = request.form.get("groupName")
            userNames = request.form.get("userNames")
            db = sqlite3.connect("facialrec.db")
            group = db.cursor()
            # error checking the groupName:
            if groupName == (''):
                return("Please enter a Groupname!")
            if userNames == (''):
                return("Please enter at least one other Username!")
            users = userNames.split(",")
            runner = 0
            for user in users:
                group.execute("SELECT * FROM users WHERE userName = :userName", {'userName': users[runner]})
                checkName = group.fetchall()
                print("Checkname:", checkName)
                print("first try:", users[runner])
                if checkName == []: # erster versuch war nicht erfolgreich: nutzer nicht gefunden
                    checker = users[runner].translate({ord(' '): None}) # zweiter versuch entfernt leerzeichen davor.
                    group.execute("SELECT * FROM users WHERE userName = :userName", {'userName': checker})
                    checkName = group.fetchall()
                    print("checkname2:", checker)
                    if checkName == []: # auch zweiter versuch war nicht erfolgreich.
                        return("dat is kein name du depp, egal wie man es dreht und wendet: dat funzt nicht. Der Nutzername existiert nicht: " + users[runner])
                    else:
                        users[runner] = checker
                        print("second try:", users[runner])
                runner += 1
            # es ist sichergestellt, dass alle nutzer existieren!
            group.execute("INSERT INTO groups (groupName) VALUES (:groupName)", {'groupName': groupName}) # grupper wird erstellt
            db.commit() # gruppe wird erstellt.
            groupID = int(group.lastrowid)  # groupID gepseichert
            group.execute("UPDATE users SET groupCount = groupCount + 1 WHERE userID = :userID", {'userID': session["user_id"]})
            db.commit() # nutzers group count wird inkrementiert aber nur für den erstelleter # TODO auch für die anderen machen
            group.execute("SELECT userName FROM users WHERE userID = :userID", {'userID': session["user_id"]})
            groupCreator = group.fetchall()
            group.execute("INSERT INTO invites (groupID, groupName, userID, userName, status, createdBy) VALUES (:groupID, :groupName, :userID, :userName, 0, :createdBy)", {'groupID': groupID, 'groupName': groupName, 'userID': session["user_id"], 'userName': groupCreator[0][0], 'createdBy': groupCreator[0][0]})
            db.commit() # der ersteller der gruppe wird in die invites als bestätigt eingefügt.
            print("Die groupID lautet:", groupID)
            runner = 0
            for user in users:
                group.execute("SELECT userID FROM users WHERE userName = :userName", {'userName': users[runner]})
                userID = group.fetchall() # holt sich die userID als unique identifier.
                print("userID:", userID[0][0])
                group.execute("INSERT INTO invites (groupID, groupName, userID, userName, createdBy) VALUES (:groupID, :groupName, :userID, :userName, :createdBy)", {'groupID': groupID, 'groupName': groupName, 'userID': userID[0][0], 'userName': users[runner], 'createdBy': groupCreator[0][0]})
                db.commit()
                runner += 1
            out = ("The group " + groupName + " has been succesfully created!")
            return(out)


        else:
            try:
                submitOrig = request.form["groupID"]
                print("submitOrig 1: ", submitOrig)
            except:
                print("Doesn't want to add to group")
        if submitOrig is not None:
            groupID = request.form.get("groupID")
            print("groupID:", groupID)
            userAdd = request.form.get("userAdd")
            print("userAdd:", userAdd)
            db = sqlite3.connect("facialrec.db")
            group = db.cursor()
            # error checking the groupName:
            if userAdd == (''):
                return ("Please enter at least one other Username!")
            users = userAdd.split(",")
            runner = 0
            for user in users:
                group.execute("SELECT * FROM users WHERE userName = :userName", {'userName': users[runner]})
                checkName = group.fetchall()
                print("Checkname:", checkName)
                print("first try:", users[runner])
                if checkName == []: # erster versuch war nicht erfolgreich: nutzer nicht gefunden
                    checker = users[runner].translate({ord(' '): None}) # zweiter versuch entfernt leerzeichen davor.
                    group.execute("SELECT * FROM users WHERE userName = :userName", {'userName': checker})
                    checkName = group.fetchall()
                    print("checkname2:", checker)
                    if checkName == []: # auch zweiter versuch war nicht erfolgreich.
                        return("dat is kein name du depp, egal wie man es dreht und wendet: dat funzt nicht. Der Nutzername existiert nicht: " + users[runner])
                    else:
                        users[runner] = checker
                        print("second try:", users[runner])
                runner += 1
            # es ist sichergestellt, dass alle nutzer existieren!
            runner = 0
            for user in users:
                group.execute("SELECT * FROM invites WHERE userName = :userName AND status = 0 AND groupID = :groupID", {'userName': users[runner], 'groupID': groupID})
                checkGroup = group.fetchall()
                print("CheckGroup:", checkGroup)
                print("first try:", users[runner])
                if checkGroup == []: # erster versuch war nicht erfolgreich: nutzer nicht gefunden
                    checker = users[runner].translate({ord(' '): None}) # zweiter versuch entfernt leerzeichen davor.
                    group.execute("SELECT * FROM invites WHERE userName = :userName AND status = 0 AND groupID = :groupID", {'userName': checker, 'groupID': groupID})
                    checkGroup = group.fetchall()
                    print("checkname2:", checker)
                    if checkGroup == []: # auch zweiter versuch war nicht erfolgreich.
                        users[runner] = checker
                    else:
                        return ("This user is already a participant in this group.")
                else:
                    return("This user is already a participant in this group.")
                runner += 1
            group.execute("SELECT createdBy FROM invites WHERE userID = :userID AND groupID = :groupID", {'userID': session["user_id"], 'groupID': groupID})
            groupCreator = group.fetchall()
            runner = 0
            for user in users:
                group.execute("SELECT userID FROM users WHERE userName = :userName", {'userName': users[runner]})
                userID = group.fetchall() # holt sich die userID als unique identifier.
                print("userID:", userID[0][0])
                group.execute("SELECT groupName FROM invites WHERE userID = :userID AND groupID = :groupID", {'userID': session["user_id"], 'groupID': groupID})
                groupName = group.fetchall()  # holt sich die userID als unique identifier.
                group.execute("INSERT INTO invites (groupID, groupName, userID, userName, createdBy) VALUES (:groupID, :groupName, :userID, :userName, :createdBy)", {'groupID': groupID, 'groupName': groupName[0][0], 'userID': userID[0][0], 'userName': users[runner], 'createdBy': groupCreator[0][0]})
                db.commit()
                runner += 1
            out = ("The user(s) have been succesfully added to the group.")
            return(out)



        # print("groupName, userNames, userAdd:", groupName, userNames, userAdd)

        return("its a trap")

#todo: groupcount inbox


@app.route('/inbox', methods = ['GET', 'POST'])
@login_required
def inbox():
    if request.method == "GET":
        db = sqlite3.connect("facialrec.db")
        inbox = db.cursor()
        inbox.execute("SELECT groupName, createdBy, groupID FROM invites WHERE userID = :userID AND status = 1", {'userID': session["user_id"]})
        groupNames = inbox.fetchall()
        runner = 0
        test = []
        for groupName in groupNames:
            inbox.execute("SELECT userName FROM invites WHERE groupID = :groupID AND status = 0",
                          {'groupID': groupNames[runner][2]})
            users = inbox.fetchall()
            #print("", users)
            #print("grouping:", groupNames[runner][2])
            laeufer = 0
            participants = ""
            for users in users:
                if laeufer == 0:
                    participants = participants + users[0]
                    laeufer += 1
                else:
                    participants = participants + ", " + users[0]
                    laeufer += 1
            test.append(participants)
            #test.append(participants)
            runner += 1
        return render_template('inbox.html', groupNames=zip(groupNames, test))
    elif request.method == "POST":
        returnvalue = request.form.get("groupID")
        length = len(returnvalue)
        length -=1
        groupID = returnvalue
        db = sqlite3.connect("facialrec.db")
        inbox = db.cursor()
        print("groupID", returnvalue)
        if returnvalue[length] == 'a':
            print("accepted")
            groupID = groupID.replace("a", "")
            print("userID", groupID)
            inbox.execute("UPDATE invites SET status = 0 WHERE userID = :userID AND groupID = :groupID",
                          {'userID': session["user_id"], 'groupID': groupID})
            db.commit()
            inbox.execute("UPDATE users SET groupCount = groupCount + 1 WHERE userID = :userID", {'userID': session["user_id"]})
            db.commit()
        elif returnvalue[length] == 'd':
            print("declined")
            groupID = groupID.replace("d", "")
            print("userID", groupID)
            inbox.execute("UPDATE invites SET status = 2 WHERE userID = :userID AND groupID = :groupID",
                          {'userID': session["user_id"], 'groupID': groupID})
            db.commit()
            print("success")
        return redirect("inbox")


@app.route('/uploader', methods = ['GET', 'POST'])
@login_required
def uploader():
    return("gut so")
   # if request.method == 'POST':
   #     file = request.files.getlist("file")
   #     filename = secure_filename(file.filename)
   #     groupDB = sqlite3.connect("facialrec.db")
   #     group = groupDB.cursor()
   #     group.execute("SELECT COUNT(*) FROM profiles")
   #     lastID = group.fetchall()
   #     newID = lastID + 1
   #     file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename), newID)
   #     group.execute("UPDATE users SET profilePic = :profilePic WHERE userID = :userID", {'profilePic': newID, 'userID': session["user_id"]})
   #     print("Name of the new profile Picture:", newID)
   #     return 'files uploaded successfully'

   # if request.method == 'POST':
   #     upload = request.files.getlist("file")
   #     for file in upload:
   #         print(upload)
   #         filename = secure_filename(file.filename)
   #         groupDB = sqlite3.connect("facialrec.db")
   #         group = groupDB.cursor()
   #         group.execute("SELECT * FROM users WHERE profilePic = :profilePic",
   #                   {'profilePic': filename})
   #         checkImage = group.fetchall()
   #         print("found image:", checkImage)
   #         if checkImage == []:
   #             group.execute("UPDATE users SET profilePic = :profilePic WHERE userID = :userID", {'profilePic': filename, 'userID': session["user_id"]})
   #             groupDB.commit()  #fixen bugfix needed
   #             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
   #             print("file.filename: ", file.filename)
   #         else:
   #             print("please rename this image")
   #     return 'files uploaded successfully'
   # else:
   #     return render_template("profile.html")



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
        groupDB = sqlite3.connect("facialrec.db")
        group = groupDB.cursor()
        group.execute("SELECT groupID, groupName FROM invites WHERE userID=:userID AND status=0", {'userID': session['user_id']})
        groups = group.fetchall()
        print("groups:", groups)
        progress = 0
        return render_template("index.html", progress=progress, groups=groups)
    else:
        print("length:", len(imagesDB))
        progress = 0
        for image in imagesDB:
            print("", progress)
            progress += 1
        #algorithm()
        progress = progress
        print("progresss", progress)
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