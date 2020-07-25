import face_recognition
import os

import sqlite3
#import cs50

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
    results = face_recognition.compare_faces([known_encoding], unknown_encoding, inTolerance)
    print("results:", results)
    runner = runner + 1


#unknown_image ist die Image Datei, in die Geladen wird.


#diese wird hier encoded






