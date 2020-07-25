import face_recognition
import os
import sqlite3

groupDB = sqlite3.connect("facialrec.db")
cursor = groupDB.cursor()

cursor.execute("SELECT fileName FROM group1")
images = cursor.fetchall()
print ("imagespaths: ", images)

known_image = face_recognition.load_image_file("/home/deeplearning/Desktop/facialrec/known face/Nik.jpg")
# known Face wird als Referenzbild verwendet



#for row in images:
unknown_image = face_recognition.load_image_file(os.path.join("/home/deeplearning/Desktop/facialrec/unknown face/contrast.jpg"))
#unknown_image ist die Image Datei, in die Geladen wird.

biden_encoding = face_recognition.face_encodings(known_image)[0]
#diese wird hier encoded

n = 0
check = 0

while check == 0:
    try:
        unknown_encoding = face_recognition.face_encodings(unknown_image)[n]
        n = n + 1
    except:
        check = 1

results = face_recognition.compare_faces([biden_encoding], unknown_encoding)

print("results:", results)
