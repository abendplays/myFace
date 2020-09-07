import face_recognition
from flask import Flask, flash, jsonify, redirect, render_template, request, session, \
    url_for, jsonify, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os, re, argparse
from os.path import basename
from celery import Celery
from flask_session import Session
from zipfile import ZipFile
from flask_dropzone import Dropzone
from tempfile import mkdtemp
from datetime import datetime
from threading import Thread
import multiprocessing
import time
from helpers import apology, login_required
import sqlite3
from PIL import Image
from PIL import ImageFile

userName = ""

# Configure application
app = Flask(__name__)
dropzone = Dropzone(app)

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

basedir = os.path.abspath(os.path.dirname(__file__))

app.config.update(
    UPLOADED_PATH=os.path.join(basedir, 'static/gallery'),
    # Flask-Dropzone config:
    DROPZONE_ALLOWED_FILE_TYPE='image',
    DROPZONE_MAX_FILE_SIZE=3,
    DROPZONE_MAX_FILES=30,
)

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'img', 'jpeg'])

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



# known Face wird als Referenzbild geladen und encoded

unknown_image = []
unknown_encoding = []
results = []
picture_re = re.compile(r'.*\.jpg$', re.IGNORECASE)

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
            group.execute("SELECT profilePic FROM users WHERE userID = :userID", {'userID': session["user_id"]})
            id = group.fetchall()
            id = int(id[0][0])
            group.execute("SELECT ending FROM profiles WHERE userID = :userID AND imageID = :imageID", {'userID': session["user_id"], 'imageID': id})
            ending = group.fetchall()
            print("ending:", ending)
            profilePic = str(imageID[0][0]) + (ending[0][0])
            print("profilePid:", profilePic)
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
        inbox.execute("SELECT profilePic FROM users WHERE userID=:userID", {'userID': session["user_id"]})
        profile = inbox.fetchall()
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
            runner += 1
        print("profile:", profile)
        if profile[0][0] == None:
            userPic = 1
        else:
            userPic = 0
        print("groups:", userPic)
        return render_template('groups.html', groupNames=zip(groupNames, test), userPic=userPic)
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
        try:
            files = request.files.getlist('file')
        except:
            print("..")
        if files == []:
            print("not uploading any new files.")
        else:
            db = sqlite3.connect("facialrec.db")
            group = db.cursor()
            files = request.files.getlist('file')
            groupID = request.form.get("imageID")
            # print("groupID:", groupID)
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    extension = os.path.splitext(filename)[1]
                    group.execute("SELECT COUNT(*) FROM images")
                    lastID = group.fetchall()
                    print("last id: ", lastID[0][0])
                    newID = str(lastID[0][0] + 1)
                    path = os.path.join(app.config['UPLOADED_PATH'], filename)
                    file.save(os.path.join(app.config['UPLOADED_PATH'], filename))  # , filename))
                    image = Image.open(path)
                    try:
                        exif = image._getexif()
                    except AttributeError as e:
                        print
                        "Could not get exif - Bad image!"
                        exif = None
                    (width, height) = image.size
                    # print "\n===Width x Heigh: %s x %s" % (width, height)
                    if not exif:
                        if width > height:
                            image = image.rotate(90)
                            image.save(path, quality=100)
                            print("working on it")
                    else:
                        orientation_key = 274  # cf ExifTags
                        if orientation_key in exif:
                            orientation = exif[orientation_key]
                            rotate_values = {
                                3: 180,
                                6: 270,
                                8: 90
                            }
                            if orientation in rotate_values:
                                # Rotate and save the picture
                                image = image.rotate(rotate_values[orientation])
                                image.save(path, quality=100) #, exif=str(exif)
                                print("working on it")
                        else:
                            if width > height:
                                image = image.rotate(90)
                                image.save(path, quality=100) #, exif=str(exif)

                    os.rename(app.config['UPLOADED_PATH'] + '/' + filename,
                              app.config['UPLOADED_PATH'] + '/' + newID + extension)
                    intID = int(newID)
                    now = datetime.now()
                    date = now.strftime("%Y/%m/%d %H:%M:%S")
                    print("date:", date)
                    group.execute(
                        "INSERT INTO images (imageID, imageExt, groupID, userID, date) VALUES (:imageID, :ending, :groupID, :userID, :date)",
                        {'imageID': intID, 'ending': extension, 'groupID': groupID, 'userID': session["user_id"], 'date': date})
                    db.commit()
                    print("Name of the new Picture:", intID)
                    time.sleep(1)
            return redirect("groups")
        try:
            groupID = request.form.get("delete")
        except:
            print("not deleting today.")
        if groupID:
            db = sqlite3.connect("facialrec.db")
            group = db.cursor()
            group.execute("SELECT COUNT(*) FROM invites WHERE groupID = :groupID AND status=0", {'groupID': groupID})
            participants = group.fetchall()
            print("participants: ", participants[0][0])
            if participants[0][0] == 1:
                group.execute("DELETE FROM invites WHERE groupID = :groupID", {'groupID': groupID})
                db.commit()
                group.execute("UPDATE users SET groupCount = groupCount - 1 WHERE userID = :userID",
                              {'userID': session["user_id"]})
                db.commit()
                group.execute("DELETE FROM groups WHERE groupID = :groupID", {'groupID': groupID})
                db.commit()
                group.execute("DELETE FROM images WHERE groupID = :groupID", {'groupID': groupID})
                db.commit()
                return redirect("groups")
            else:
                group.execute("UPDATE invites SET status = 2 WHERE groupID = :groupID AND userID = :userID", {'groupID': groupID, 'userID': session["user_id"]})
                db.commit()
                group.execute("UPDATE users SET groupCount = groupCount - 1 WHERE userID = :userID",
                              {'userID': session["user_id"]})
                db.commit()
                return redirect("groups")
        else:
            try:
                groupID = request.form["downloadAll"]
            except:
                print("Doesn't want to add to group")
            if groupID:
                db = sqlite3.connect("facialrec.db")
                group = db.cursor()
                group.execute("SELECT imageID, imageExt FROM images WHERE groupID=:groupID", {'groupID': groupID})
                images = group.fetchall()
                name = "%s.zip" % (groupID)
                zipObj = ZipFile(name, 'w')
                for image in images:
                    filename = str(image[0]) + image[1]
                    print("filename:", filename)
                    filePath = os.path.join(app.config['UPLOADED_PATH'], filename)
                    zipObj.write(filePath, basename(filePath))
                zipObj.close()
                zipPath = "/home/deeplearning/Desktop/facialrec/%s.zip" % (groupID)
                zipName = "%s.zip" % (groupID)
                print("zipName:", zipName)
                cleanup.delay(zipPath)
                return send_file(zipPath, attachment_filename=zipName)
        try:
            groupID = request.form["downloadMy"]
        except:
            print("Doesn't want to add to group")
        if groupID:
            db = sqlite3.connect("facialrec.db")
            group = db.cursor()
            group.execute("SELECT imageID, imageExt FROM recognized WHERE groupID=:groupID AND userID=:userID", {'groupID': groupID, 'userID': session["user_id"]})
            images = group.fetchall()
            name = "%s.zip" % (groupID)
            zipObj = ZipFile(name, 'w')
            for image in images:
                filename = str(image[0]) + image[1]
                print("filename:", filename)
                filePath = os.path.join(app.config['UPLOADED_PATH'], filename)
                zipObj.write(filePath, basename(filePath))
            zipObj.close()
            zipPath = "/home/deeplearning/Desktop/facialrec/%s.zip" % (groupID)
            zipName = "%s.zip" % (groupID)
            print("zipName:", zipName)
            cleanup.delay(zipPath)
            return send_file(zipPath, attachment_filename=zipName)
        return("its a trap")


@celery.task
def cleanup(zipPath):
    time.sleep(4)
    os.remove(zipPath)
    print("removed")



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
        white = "white.jpg"
        group.execute("SELECT DISTINCT groupID FROM images WHERE userID=:userID ORDER BY date desc", {'userID': session['user_id']})
        groupID=group.fetchall()
        groupName=[]
        images=[]
        groupIDs=[]
        counter=[]
        runner = 0
        for groupss in groupID:
            counter.append(runner)
            groupIDs.append(groupss[0])
            group.execute("SELECT groupName FROM groups WHERE groupID=:groupID", {'groupID': groupss[0]})
            groupNames=group.fetchall()
            groupName.append(groupNames[0][0])
            group.execute("SELECT DISTINCT imageID, imageExt FROM images WHERE groupID=:groupID ORDER BY date desc limit 1", {'groupID': groupss[0]})
            image=group.fetchall()
            imagePath = "%s%s" % (image[0][0], image[0][1])
            images.append(imagePath)
            print("group:", groupss)
            runner +=1
        if len(images) == 0:
            images.append(white)
            counter.append(runner)
            groupName.append("No images")
            groupIDs.append("Test")
        print("groupName:", groupName)
        print("images:", images)
        test= zip(groupName, images, groupIDs)
        print("test:", test)
        return render_template("index.html", groupName = zip(groupName, images, groupIDs, counter), groups = zip(groupName, images, groupIDs, counter))
    else:
        groupID = request.form["groupID"]
        print("nö", groupID)
        return redirect(url_for('gallery', groupID=groupID))


@app.route("/gallery/<groupID>", methods=["GET", "POST"])
@login_required
def gallery(groupID):
    if request.method == 'GET':
        print("groupID:", groupID)
        groupID.replace("<", " ")
        groupID.replace(">", " ")
        print("groupID:", groupID)
        groupDB = sqlite3.connect("facialrec.db")
        group = groupDB.cursor()
        group.execute("SELECT imageID, imageExt FROM images WHERE groupID=:groupID", {'groupID': groupID})
        images=group.fetchall()
        print("imagesss:", images)
        toggle=1
        return render_template("gallery.html", images=images, toggle=toggle, groupID=groupID)
    else:
        toggle = request.form.get("toggle")
        print("toggle2222:", toggle)
        if toggle == '0':
            print("groupID:", groupID)
            group = groupID
            group = group[:-1]
            group = group[1:]
            groupIDs = int(group)
            print("groupID2:", groupIDs)
            groupDB = sqlite3.connect("facialrec.db")
            group = groupDB.cursor()
            group.execute("SELECT imageID, imageExt FROM images WHERE groupID=:groupID", {'groupID': groupIDs})
            images = group.fetchall()
            print("image:", images)
            toggle=1
            print("toggleee:", toggle)
            return render_template('gallery.html', images=images, toggle=toggle, groupID=groupIDs)
        else:
            print("groupID:", groupID)
            group=groupID
            group = group[:-1]
            group = group[1:]
            try:
                groupIDs = int(group)
            except:
                print("nothing")
            groupIDs = 55555
            groupDB = sqlite3.connect("facialrec.db")
            group = groupDB.cursor()
            group.execute("SELECT imageID, imageExt FROM recognized WHERE groupID=:groupID AND userID=:userID", {'groupID': groupIDs, 'userID': session["user_id"]})
            images = group.fetchall()
            print("imagesss:", images)
            toggle=0
        return render_template('gallery.html', images=images, toggle=toggle, groupID=groupIDs)


#unknown_image ist die Image Datei, in die Geladen wird.


@celery.task(bind=True)
def long_task(self, userID, bigID):
    groupDB = sqlite3.connect("facialrec.db")
    group = groupDB.cursor()
    group.execute("SELECT imageID, imageExt FROM images WHERE groupID = :groupID", {'groupID': bigID})
    images = group.fetchall()
    totalLen = len(images)
    runner = 0
    if totalLen == 0:
        print("An error has occured.") #added button to HTML
        return("sorry. There are no Images in this group yet.")
    else:
        group.execute("SELECT profilePic FROM users WHERE userID = :userID", {'userID': userID})
        profilePic = group.fetchall()
        group.execute("SELECT imageID, ending FROM profiles WHERE userID = :userID AND imageID = :imageID", {'userID': userID, 'imageID': profilePic[0][0]})
        known = group.fetchall()
        kImage = "/home/deeplearning/Desktop/facialrec/static/profile/%s%s" % (known[0][0], known[0][1])
        known_image = face_recognition.load_image_file(kImage)
        known_encoding = face_recognition.face_encodings(known_image)[0]
        group.execute("SELECT imageID, imageExt FROM images WHERE userID = :userID AND groupID = :groupID", {'userID': userID, 'groupID': bigID})
        images = group.fetchall()
        group.execute("SELECT tolerance FROM users WHERE userID = :userID", {'userID': userID})
        tolerance = group.fetchall()
        tolerance = tolerance[0][0]
        for image in images:  # es wird durch alle bilder geloopt
            n = 0
            check = 0
            found = False
            # umgebungsvariablen werden gesetzt
            filePath = "/home/deeplearning/Desktop/facialrec/static/gallery/%s%s" % (images[runner][0], images[runner][1])
            unknown_image = face_recognition.load_image_file(filePath)  # Image wird geladen # images[row] wird es mal werden
            unknown_encoding = face_recognition.face_encodings(unknown_image)
            print("image:", images[runner][0])
            while check == 0:
                try:
                    results = face_recognition.compare_faces([known_encoding], unknown_encoding[n], tolerance=tolerance)
                    if results[0] == True:
                        check = 1
                        found = True
                    else:
                        n = n + 1
                except:
                    check = 1
            # image wird durch eine try schleife durchgeschleift, bis es eine Fehlermeldung gibt. Dabei werden alle potenzielen Gesicher gecheckt
            if found == True:
                group.execute("SELECT imageID FROM recognized WHERE userID = :userID and imageID = :imageID", {'userID': userID, 'imageID': images[runner][0]})
                hasRun = group.fetchall()
                print("hasrun:", hasRun)
                if hasRun == []:
                    group.execute("INSERT INTO recognized (imageID, imageExt, groupID, userID) VALUES (:imageID, :imageExt, :groupID, :userID)", {'imageID': images[runner][0], 'imageExt': images[runner][1], 'groupID': bigID, 'userID': userID})
                    groupDB.commit()
                else:
                    print("already checked this image.")
                print("Detected the user in this image.")
            else:
                print("Didn't detect this user in this image.")
            currentImage = runner + 1
            self.update_state(state='PROGRESS',
                          meta={'current': currentImage, 'total': totalLen,
                                'status': 'successfully processed %s images' % images[runner][0]})
            runner = runner + 1
    return {'current': currentImage, 'total':totalLen, 'status': 'Task completed!',
            'result': 'success'}


@app.route('/longtask', methods=['POST'])
def longtask():
    bigID = request.form['bigID']
    print("bigID:", bigID)
    userID = session["user_id"]
    print("userID", userID)
    task = long_task.apply_async([userID, bigID]) # used to be: task = long_task.apply_async([bigID, userID])
    return jsonify({}), 202, {'Location': url_for('taskstatus',
                                                  task_id=task.id)}

@app.route('/status/<task_id>')
def taskstatus(task_id):
    task = long_task.AsyncResult(task_id)
    print("taskiddd:", task)
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



@app.route('/uploader', methods = ['GET', 'POST'])
@login_required
def uploader():
    return("gut so")


if __name__ == '__main__':
    app.run(debug=True)