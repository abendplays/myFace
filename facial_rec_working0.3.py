import face_recognition
from flask import Flask, flash, jsonify, redirect, render_template, request, session, \
    url_for, jsonify
import os
from celery import Celery
import random
import time

import sqlite3
#import cs50

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SECRET_KEY'] = 'top-secret!'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

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

group.execute("SELECT fileName FROM group1")
imagesDB = group.fetchall()

# get all imagepaths for check purposes
images = ['contrast.jpg']  #, 'test.jpg', 'one_person.jpg', 'test2.jpg'

known_image = face_recognition.load_image_file("/home/deeplearning/Desktop/facialrec/known face/Nik.jpg")
known_encoding = face_recognition.face_encodings(known_image)[0]
# known Face wird als Referenzbild geladen und encoded

unknown_image = []
unknown_encoding = []
results = []

inTolerance = 0.6
# arrays für alle mit den unknown images verwandten Teilen werden aufgesetzt

@app.route("/", methods=["GET", "POST"])
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


#diese wird hier encoded
#def algorithm():
    # progress = 0
    # print("gotcha")
    # runner = 0
    # for image in imagesDB:  # es wird durch alle bilder geloopt
    #     n = 0
    #     check = 0
    #     # umgebungsvariablen werden gesetzt
    #     print("unknown Image from DB: ", imagesDB[runner][0])
    #     filePath = "/home/deeplearning/Desktop/facialrec/unknown face/%s" % (imagesDB[runner][0])
    #     unknown_image = face_recognition.load_image_file(
    #         filePath)  # Image wird geladen # images[row] wird es mal werden
    #     while check == 0:
    #         try:
    #             unknown_encoding = face_recognition.face_encodings(unknown_image)[n]
    #             n = n + 1
    #         except:
    #             check = 1
    #     # image wird durch eine try schleife durchgeschleift, bis es eine Fehlermeldung gibt. Dabei werden alle potenzielen Gesicher gecheckt
    #     results = face_recognition.compare_faces([known_encoding], unknown_encoding, inTolerance)
    #     print("results:", results)
    #     progress += 1
    #     runner = runner + 1
    # return ("finished")


@celery.task(bind=True)
def long_task(self):
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

if __name__ == '__main__':
    app.run(debug=True)











