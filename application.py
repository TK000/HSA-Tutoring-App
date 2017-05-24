import os
import re
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir
from flask_jsglue import JSGlue
from datetime import datetime

from helpers import *

# configure application
app = Flask(__name__)
JSGlue(app)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///tutoring.db")

timezone = 5

@app.route("/")
@login_required
def index():
    """index page"""
    
    # if user reached route via GET
    if request.method == "GET":
    
        # return the student index page
        return render_template("index.html")
    
    # if user reached route via POST
    else:
        return redirect(url_for("index"))
            

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # keep user logged in
        session["user_id"] = rows[0]["id"]
        
        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    
    # forget any user_id
    session.clear()
            
    # if user reached route via POST
    if request.method == "POST":
        # ensure username does not already exist
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        if len(rows) == 1:
            return apology("username already exists")
        else:
            # add username and password to database
            db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)", username = request.form.get("username"), hash = pwd_context.encrypt(request.form.get("password")))
            # select id of user 
            rows = db.execute("SELECT id FROM users WHERE username = :username", username=request.form.get("username"))
            # remember which user has logged in
            session["user_id"] = rows[0]["id"]
            # redirect user to home page
            return redirect(url_for("profile"))
			    
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
	    return render_template("register.html")


        
@app.route("/change", methods=["GET", "POST"])
def change():
    """Change password."""

# if user reached route via POST
    if request.method == "POST":

        # update password
        db.execute("UPDATE users SET hash = :hash WHERE id = :id", id = session["user_id"], hash = pwd_context.encrypt(request.form.get("password")))
        # redirect user to home page
        return redirect(url_for("index"))
			    
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
	    return render_template("change.html")
	    
@app.route("/profile", methods=["GET", "POST"])
def profile():
    """Update user profile."""
    
    # if user reached route via POST
    if request.method == "POST":

        # insert information from form into users
        db.execute("UPDATE users SET name=:name, email=:email, phone=:phone, role=:role WHERE id = :id", name = request.form.get("name"), email = request.form.get("email"), phone = request.form.get("phone"), id = session["user_id"], role = request.form.get("role"))
        return redirect(url_for("index"))
            
    # else if user reached route via GET
    else:
        return render_template("profile.html")
        
        
@app.route("/arrange", methods=["GET", "POST"])
def arrange():
    """Request an appointment"""
    
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # find tutor id
        tutor_id = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("tutor_username"))
        
        # check if tutor username exists
        if len(tutor_id) != 1:
            return apology("invalid tutor username")
        
        else:
            # insert information from form into requests
            db.execute("""INSERT INTO requests (student_id, year, month, day, start_hour, start_minute, duration, tutor_id, topic, status) 
                      VALUES (:student_id, :year, :month, :day, :start_hour, :start_minute, :duration, :tutor_id, :topic, :status)""",
                      student_id=session["user_id"], year=request.form.get("year"), month=request.form.get("month"), day=request.form.get("day"), start_hour=int(request.form.get("start_hour")) + int(request.form.get("am_pm")), start_minute=request.form.get("start_minute"), duration=request.form.get("duration"), tutor_id=tutor_id[0]["id"], topic=request.form.get("topic"), status='Pending')

            # redirect to page for logs
            return redirect(url_for("logs"))
       
    # else if user reached route via GET
    else:
        return render_template("arrange.html")
        
@app.route("/logs", methods=["GET", "POST"])
def logs():
    """display logs of requests"""
    
    userrows = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
    
    # if user is a student    
    if userrows[0]["role"] == "student":
        
        # if user reached route via GET
        if request.method == "GET":
            # query history for rows corresponding to current user
            rows = db.execute("SELECT * FROM requests WHERE student_id = :id ORDER BY year, month, day, start_hour, start_minute, duration LIMIT 30", id=session["user_id"])
        
            # for each row
            for row in rows:
                # find tutor name and username
                tutor = db.execute("SELECT name, username FROM users WHERE id = :id", id=int(row["tutor_id"]))
                if tutor != None:
                    row["tutor_name"] = tutor[0]["name"]
                    row["tutor_username"] = tutor[0]["username"]
                
            return render_template("logs_student.html", rows=rows)
            
         # else if user reached route via GET
        else:
            return redirect(url_for("logs_student"))
            
    # if user is a tutor
    if userrows[0]["role"] == "tutor":
            
        # if user reached route via GET
        if request.method == "GET":
            # query history for rows corresponding to current user
            rows = db.execute("SELECT * FROM requests WHERE tutor_id = :id ORDER BY year, month, day, start_hour, start_minute, duration LIMIT 30", id=session["user_id"])
            
            # for each row
            for row in rows:
                # find student name and username
                student = db.execute("SELECT name, username FROM users WHERE id = :id", id=int(row["student_id"]))
                if student != None:
                    row["student_name"] = student[0]["name"]
                    row["student_username"] = student[0]["username"]
            
            return render_template("logs_tutor.html", rows=rows)
            
         # else if user reached route via POST
        else:
            return redirect(url_for("logs_tutor"))

@app.route("/upcoming", methods=["GET", "POST"])
def upcoming(): 
    """display upcoming lessons"""
    
    userrows = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
        
    # if user is a student
    if userrows[0]["role"] == "student":
        # if user reached route via GET
        if request.method == "GET":
            
            # query requests for rows corresponding to user
            rows = db.execute("SELECT * FROM requests WHERE student_id = :id AND status = :status ORDER BY year, month, day, start_hour, start_minute, duration", id = session["user_id"], status = "Confirmed")
    
            # define the list items
            objects = []
    
            # for each row
            for row in rows:
                # find tutor name and username
                tutor = db.execute("SELECT name, username FROM users WHERE id = :id", id=int(row["tutor_id"]))
                if tutor != None:
                    row["tutor_name"] = tutor[0]["name"]
                    row["tutor_username"] = tutor[0]["username"]
                
                # if lesson is in the future, add to objects
                if row["year"] + 2000 > datetime.now().year: 
                    objects.append(row)
                elif row["year"] + 2000 == datetime.now().year and row["month"] > datetime.now().month:
                    objects.append(row)
                elif row["year"] + 2000 == datetime.now().year and row["month"] == datetime.now().month and row["day"] > datetime.now().day:
                    objects.append(row)
                elif row["year"] + 2000 == datetime.now().year and row["month"] == datetime.now().month and row["day"] == datetime.now().day and int(row["start_hour"]) + timezone > datetime.now().hour:
                    objects.append(row)
                elif row["year"] + 2000 == datetime.now().year and row["month"] == datetime.now().month and row["day"] == datetime.now().day and int(row["start_hour"]) + timezone == datetime.now().hour and int(row["start_minute"]) > datetime.now().minute:
                    objects.append(row)
            
            return render_template("upcoming_student.html", objects = objects)
            
        # else if user reached route via POST
        else:
            return redirect(url_for("upcoming"))
    
    # if user is a tutor
    if userrows[0]["role"] == "tutor":
        # if user reached route via GET
        if request.method == "GET":
            # query requests for rows involving user
            rows = db.execute("SELECT * FROM requests WHERE tutor_id = :id AND status = :status ORDER BY year, month, day, start_hour, start_minute, duration", id = session["user_id"], status = "Confirmed")
    
            # define list items
            items = []
    
            # for each row
            for row in rows:
                # find student name and username
                student = db.execute("SELECT name, username FROM users WHERE id = :id", id=int(row["student_id"]))
                if student != None:
                    row["student_name"] = student[0]["name"]
                    row["student_username"] = student[0]["username"]
                    
                # if lesson is in the future, add to items
                if row["year"] + 2000 > datetime.now().year: 
                    items.append(row)
                elif row["year"] + 2000 == datetime.now().year and row["month"] > datetime.now().month:
                    items.append(row)
                elif row["year"] + 2000 == datetime.now().year and row["month"] == datetime.now().month and row["day"] > datetime.now().day:
                    items.append(row)
                elif row["year"] + 2000 == datetime.now().year and row["month"] == datetime.now().month and row["day"] == datetime.now().day and int(row["start_hour"]) + timezone > datetime.now().hour:
                    items.append(row)
                elif row["year"] + 2000 == datetime.now().year and row["month"] == datetime.now().month and row["day"] == datetime.now().day and int(row["start_hour"]) + timezone == datetime.now().hour and int(row["start_minute"]) > datetime.now().minute:
                    items.append(row)
            
            return render_template("upcoming_tutor.html", items = items)
        
        # else if user reached route via POST
        else:
            return redirect(url_for("upcoming"))
            

@app.route("/respond", methods=["GET", "POST"])
def respond():
    """respond to lesson requests"""
    
    # if user reached route via GET
    if request.method == "GET":
        # query requests for rows involving user
        rows = db.execute("SELECT * FROM requests WHERE tutor_id = :id AND status = :status ORDER BY year, month, day, start_hour, start_minute, duration", id = session["user_id"], status = "Pending")
        
        # for each row
        for row in rows:
            # find student name and username
            student = db.execute("SELECT name, username FROM users WHERE id = :id", id=int(row["student_id"]))
            if student != None:
                row["student_name"] = student[0]["name"]
                row["student_username"] = student[0]["username"]
                
        return render_template("respond.html", rows=rows)
    
    # else if user reached route via POST
    else:
       return redirect(url_for("respond")) 
       

@app.route("/confirm", methods=["GET", "POST"])
def confirm(): 
    """confirm and decline lesson requests"""
    
    # list of rows to be confirmed and declined
    confirmed = request.form.getlist("confirm")
    declined = request.form.getlist("decline")
    
    # if confirmed is not empty
    if confirmed:
        # change status of each row to 'confirmed'
        for i in range(len(confirmed)):
            db.execute("UPDATE requests SET status=:status WHERE id=:id", status="Confirmed", id=confirmed[i])
            
    # if declined is not empty
    if declined:
        # change status of each row to 'declined'
        for i in range(len(declined)):
            db.execute("UPDATE requests SET status=:status WHERE id=:id", status="Declined", id=declined[i])

    return redirect(url_for("respond")) 
    

@app.route("/cancel", methods=["GET", "POST"])
def cancel():
    """cancel a lesson"""
    
    # list of rows to be cancelled
    cancelled = request.form.getlist("cancel")
    
    # if cancelled is not empty
    if cancelled:
        # change status of each row to 'cancelled'
        for i in range(len(cancelled)):
            db.execute("UPDATE requests SET status=:status WHERE id=:id", status="Cancelled", id=cancelled[i])
            
    return redirect(url_for("upcoming")) 
    
@app.route("/people", methods=["GET", "POST"])
def people():
    """view your contacts"""
    
    userrows = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
   
    # if user is a student
    if userrows[0]["role"] == "student":
        # if user reached route via GET
        if request.method == "GET":
            
            # query requests for rows corresponding to user
            rows = db.execute("SELECT * FROM requests WHERE student_id = :id", id = session["user_id"])
            
            # define a list
            people = []
            
            # for each row
            for row in rows:
                # query users for tutors user has contacted
                tutors = db.execute("SELECT * FROM users WHERE id = :id", id = row["tutor_id"])
                # add tutors to the list
                for i in range(len(people)):
                    if tutors[0] == people[i]:
                        people.remove(people[i])
                people.append(tutors[0])
                
            return render_template("people.html", people=people)
            
        # else if user reached route via POST
        else:
            return redirect(url_for("people"))
            
    # if user is a tutor
    if userrows[0]["role"] == "tutor":
        # if user reached route via GET
        if request.method == "GET":
            
            # query requests for rows corresponding to user
            rows = db.execute("SELECT * FROM requests WHERE tutor_id = :id", id = session["user_id"])
            
            # define a list
            people = []
            
            # for each row
            for row in rows:
                # query users for students user has been contacted by
                students = db.execute("SELECT * FROM users WHERE id = :id", id = row["student_id"])
                # add tutors to the list
                for i in range(len(people)):
                    if students[0] == people[i]:
                        people.remove(people[i])
                people.append(students[0])
                
            return render_template("people.html", people=people)
                    
        # else if user reached route via POST
        else:
            return redirect(url_for("people"))
            
        
    

        
