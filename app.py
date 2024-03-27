# import the required libraries
from flask import Flask, render_template, send_file, request, redirect, flash, session, url_for
import sqlite3
import hashlib
from PIL import Image
import datetime
import jwt
from io import BytesIO
import base64
import random
import string
import os
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
import shutil
import os
import psycopg2

app = Flask(__name__)

# constants to use in the application
app.config['SECRET_KEY'] = 'FHDJAKLFJIEWAFNA'
app.config['SESSION_COOKIE_PERMANENT'] = True
app.config['TRANSITION'] = 'NONE'
app.config['AUDIO'] = 'NONE'
salt = "krish" # salt to hash the password

# make the folder that stores the timeline images
UPLOAD_FOLDER = 'timeline'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# function to generate jwt token
def generate_jwt_token(username):
    payload = {
        'username': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)  # Token expires in 30 minutes
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')  # Use encode function from jwt module
    return token

# function to verify jwt token
def verify_jwt_token(token):
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])  # Use decode function from jwt module
        return payload['username']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# function to create the video
# use all the images stored in the timeline folder in alphabetical order and makes the video with the given transitions and audio
def create_video():
    # Get all the images from the timeline folder
    clips = []
    image_folder = 'timeline'
    for f in os.listdir(image_folder):
        if os.path.isfile(os.path.join(image_folder, f)):
            clips.append(ImageClip(os.path.join(image_folder, f)).set_duration(2))

    # apply the transitions
    if app.config['TRANSITION'] == "fade-out":
        for i in range(len(clips) - 1):
            clips[i] = clips[i].crossfadeout(2)
    elif app.config['TRANSITION'] == "fade-in":
        for i in range(len(clips) - 1):
            clips[i] = clips[i].crossfadein(2)

    # apply the audio
    if app.config['AUDIO'] == "audio-1":
        audio = AudioFileClip("static/audio/audio-1.mp3")
        audio = audio.subclip(0, 2 * (len(clips)))
        clips[0] = clips[0].set_audio(audio)

    elif app.config['AUDIO'] == "audio-2":
        audio = AudioFileClip("static/audio/audio-2.mp3")
        audio = audio.subclip(0, 2 * (len(clips)))
        clips[0] = clips[0].set_audio(audio)
    
    elif app.config['AUDIO'] == "audio-3":
        audio = AudioFileClip("static/audio/audio-3.mp3")
        audio = audio.subclip(0, 2 * (len(clips)))
        clips[0] = clips[0].set_audio(audio)

    # Concatenate clips with transitions
    video_clip = concatenate_videoclips(clips, method="compose")
    # save the video file
    video_clip.write_videofile("static/finalVideo/output_video.mp4", codec="libx264", fps=24, remove_temp=True)
    # remove all the images from the timeline folder and remake the folder
    shutil.rmtree('timeline')
    os.makedirs('timeline')


###################################################################### landing page ######################################################################################
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

###################################################################### login page #########################################################################################
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # connect to the database
        connection = psycopg2.connect("postgresql://raunak:p3w3jJ5ID9ep5rMve2UhKg@iss-project-8924.8nk.gcp-asia-southeast1.cockroachlabs.cloud:26257/user_data?sslmode=verify-full&sslrootcert=/root.crt")
        cursor = connection.cursor()
        
        # retrieve data from the form
        name = request.form['name']
        password = request.form['password']
        # print it on the terminal(for debugging)
        print(name, password)

        # check if the user is admin or not
        if name == "mukta" and password == "ihateiss":
            return redirect("/admin")
        
        # hash the password
        hashed_password = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        
        # check if the user is correct by running the query, if the user is valid then go to the user index page else show an alert
        query = "SELECT username, password FROM users where username= '"+name+"' and password='"+hashed_password+"' "
        cursor.execute(query)
        results = cursor.fetchall()
        
        if len(results) == 0: # if the user is not found
            return render_template('login.html', error = True)
        else: # if found go to the home page and store the token in the session
            session['token'] = generate_jwt_token(name)
            return redirect("/home ")
        
    return render_template('login.html') # if method is not post then show the login page

###################################################################### signup page ########################################################################################
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # connect to the server
        connection = psycopg2.connect("postgresql://raunak:p3w3jJ5ID9ep5rMve2UhKg@iss-project-8924.8nk.gcp-asia-southeast1.cockroachlabs.cloud:26257/user_data?sslmode=verify-full&sslrootcert=/root.crt")
        cursor = connection.cursor()
        
        # get data from the html form
        firstname = request.form['firstn']
        lastname = request.form['lastn']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        #hash the password before storing 
        password_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        
        #print the data in terminal for debugging
        print(firstname, lastname, username, email, password_hash)
        
        # insert the data into the database
        query = " INSERT INTO users VALUES ('"+firstname+"' , '"+lastname+"' , '"+username+"', '"+email+"', '"+password_hash+"') "
        cursor.execute(query)
        connection.commit()
        
        return redirect("/home") # go to the home page after signup
        
    return render_template('signup.html') # if method is not post then show the signup page

###################################################################### upload page ########################################################################################
@app.route("/upload",methods=["POST","GET"])
def upload():
    # check if the user is logged in or not
    token = session.get('token')
    if not token: # if not logged in then go to the login page
        return redirect('/login')
    username = verify_jwt_token(token)
    if not username: # if not logged in then go to the login page
        return redirect('/login')
    
    if request.method == 'POST':
        
        # connect to the database
        connection = psycopg2.connect("postgresql://raunak:p3w3jJ5ID9ep5rMve2UhKg@iss-project-8924.8nk.gcp-asia-southeast1.cockroachlabs.cloud:26257/user_data?sslmode=verify-full&sslrootcert=/root.crt")
        cursor = connection.cursor()
        
        # get the images from the form
        files = request.files.getlist('images[]')

        # store the images into sql database
        for file in files:
            imageFile = file.read()
            filename = file.filename
            
            myname = username
            query = "INSERT INTO images (username, image, imagename) VALUES (%s, %s, %s)"
            cursor.execute(query, (myname, psycopg2.Binary(imageFile), filename))
            
        connection.commit() # commit the changes and redirect to the home page
        return redirect("/home")
        
    return render_template('/upload.html')

###################################################################### home page ########################################################################################
@app.route("/home", methods=["POST", "GET"])
def home():
    # check if the user is logged in or not
    token = session.get('token')
    if not token: # if not logged in then go to the login page
        return redirect('/login')
    username = verify_jwt_token(token)
    if not username: # if not logged in then go to the login page
        return redirect('/login')
    
    # connect to the database
    connection = psycopg2.connect("postgresql://raunak:p3w3jJ5ID9ep5rMve2UhKg@iss-project-8924.8nk.gcp-asia-southeast1.cockroachlabs.cloud:26257/user_data?sslmode=verify-full&sslrootcert=/root.crt")
    cursor = connection.cursor()
    
    # get the username, images and other data from the database
    query_1 = "SELECT * FROM users WHERE username = '"+username+"'" # for user data
    query_2 = "SELECT imagename FROM images WHERE username = '"+username+"'" # for getting all the images uploaded by the user 
    query_3 = "SELECT image FROM images WHERE username = '"+username+"'" # for getting all the images uploaded by the user 

    # get the username
    cursor.execute(query_1)
    user_data = cursor.fetchall()
    # get the imagenames
    cursor.execute(query_2)
    imagenames = cursor.fetchall()
    # get the images
    cursor.execute(query_3)
    images = cursor.fetchall()

    connection.close() 
     
    print(user_data) # print the data for debugging
    
    # get the name and other data from the list
    name = user_data[0][0]
    lastname = user_data[0][1]
    email = user_data[0][3]
    
    # convert the images to base64 format to display on the html page
    images_base64 = []
    for image in images:
        image = image[0]
        image_base64 = base64.b64encode(image).decode('utf-8')
        images_base64.append((image_base64))

    # get the image names
    image_names = []
    for image_name in imagenames:
        image_names.append(image_name[0])
        
    # render the home page with the data
    return render_template("home.html", username = name, lastname = lastname, email = email, images_data = images_base64, image_names = image_names, total_images = len(images_base64))

###################################################################### audio and transitions ########################################################################################
@app.route('/audio', methods=["POST", "GET"])
def audio():
    if request.method == "POST": # store the audio and transitioin selected by the user
        app.config['TRANSITION'] = request.form['transition']
        app.config['AUDIO'] = request.form['audio']
        
    # render the audio page
    return render_template("trans_aud.html")


###################################################################### admin page ########################################################################################
@app.route('/admin')
def admin():
    # connect to the database
    connection = psycopg2.connect("postgresql://raunak:p3w3jJ5ID9ep5rMve2UhKg@iss-project-8924.8nk.gcp-asia-southeast1.cockroachlabs.cloud:26257/user_data?sslmode=verify-full&sslrootcert=/root.crt")
    cursor = connection.cursor()
    
    # get the userdata from the database
    query = "SELECT * FROM users"   
    cursor.execute(query)
    users = cursor.fetchall()
    connection.close()

    print(users[0][0]) # print the data for debugging
    
    # render the admin page with the data
    return render_template('admin.html', user_data = users)

###################################################################### video preview ########################################################################################
@app.route('/video', methods=["POST","GET"])
def video():
    return render_template('video.html')


###################################################################### editor page ########################################################################################
@app.route('/edit',methods=["POST","GET"])
def edit():
    # check if the user is logged in or not
    token = session.get('token')
    if not token: # if not logged in then go to the login page
        return redirect('/login')
    username = verify_jwt_token(token)
    if not username: # if not logged in then go to the login page
        return redirect('/login')   
    
    # connect to the database
    conn = psycopg2.connect("postgresql://raunak:p3w3jJ5ID9ep5rMve2UhKg@iss-project-8924.8nk.gcp-asia-southeast1.cockroachlabs.cloud:26257/user_data?sslmode=verify-full&sslrootcert=/root.crt")
    cursor = conn.cursor()

    # get the images from the database
    cursor.execute("SELECT image FROM images WHERE username='"+username+"'")
    image_data = cursor.fetchall()
    conn.close()

    # convert the images to base64 format to display on the html page
    images_base64 = []
    for image in image_data:
        image = image[0]
        image_base64 = base64.b64encode(image).decode('utf-8')
        images_base64.append((image_base64))

    if request.method == 'POST':
        # get the timeline images from the html page
        if 'files[]' not in request.files:
            return 'No file part'
        files = request.files.getlist('files[]')

        # list of names to store the images in the timeline folder in alphabetical order
        namesList = ['aa', 'ab', 'ac', 'ad', 'ae', 'af', 'ag', 'ah', 'ai', 'aj', 'ak', 'al', 'am', 'an', 'ao', 'ap', 'aq', 'ar', 'as', 'at', 'au', 'av', 'aw', 'ax', 'ay', 'az',
                     'ba', 'bb', 'bc', 'bd', 'be', 'bf', 'bg', 'bh', 'bi', 'bj', 'bk', 'bl', 'bm', 'bn', 'bo', 'bp', 'bq', 'br', 'bs', 'bt', 'bu', 'bv', 'bw', 'bx', 'by', 'bz']
        index = 0
        for file in files:
            # give the image name from the list
            res = ''.join(str(namesList[index]))
            index += 1

            if file.filename == '':
                return 'No selected file'

            # save the image in the timeline folder
            if file:
                filename = str(res) + ".png"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # create the video and show the preview
        create_video()
        print("video is succesfully made")
        return redirect('/video')

    # if not post return the editor page with the user data
    return render_template('editor.html', images = images_base64)

###################################################################### logout ########################################################################################
@app.route('/logout')
def logout():
    session.pop('token', None) # pop the user token on logout
    shutil.rmtree('static/finalVideo') # remove the video from the finalVideo folder
    os.makedirs('static/finalVideo') 
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)