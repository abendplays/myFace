import face_recognition

known_image = face_recognition.load_image_file("/home/deeplearning/Desktop/facialrec/static/profile/1.JPG")
unknown_image = face_recognition.load_image_file("/home/deeplearning/Desktop/facialrec/static/gallery/1.JPG")
known_encoding = face_recognition.face_encodings(known_image)[0]
print("knownFace Encoding:", known_encoding)

n = 0
check = 0


# while check == 0:
#     try:
#         unknown_encoding = face_recognition.face_encodings(unknown_image)[n]
#         print("durchlauf")
#         n = n + 1
#     except:
#         check = 1

unknown_encoding = face_recognition.face_encodings(unknown_image)


while check == 0:
    try:
        results = face_recognition.compare_faces([known_encoding], unknown_encoding[n], tolerance=0.6)
        if results[0] == True:
            print("Gotcha1")

        print("results:", results)
        n = n + 1
    except:
        check = 1
