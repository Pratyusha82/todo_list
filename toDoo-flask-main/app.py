from flask import Flask, render_template, session, request, url_for, redirect,flash
from flask.helpers import make_response
from flask.json import jsonify
import pymongo
import json
from bson import ObjectId
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from asyncio import tasks


app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost/todo_list"
app.config['SECRET_KEY'] = 'pushpapratyusha'
mongo = PyMongo(app)
users = mongo.db.users
tasks = mongo.db.tasks
bcrypt = Bcrypt(app)
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


@app. route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        user_email = request.form["email"]
        user_name = request.form["usrname"]
        user_password = request.form["passwd"]
        print(user_email)
        print(user_password)
        hashed_password = bcrypt.generate_password_hash(user_password).decode('utf-8')

        if users.count_documents({'email': user_email}) == 0:
            new_user = {
                'email': user_email,
                'username': user_name,
                'password': hashed_password
            }
            users.insert_one(new_user)
            session["email"] = user_email
            return redirect(url_for("home"))
        else:
            render_template(
                "login.html", message="User account already exists")
    else:
        return render_template("signup.html")


@app. route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        user_email = request.form["email"]
        user_password = request.form["passwd"]
        # check credentials
        x = users.find_one({'email': user_email})
        if x is not None:
            if bcrypt.check_password_hash(x['password'],user_password):
            # if x['password'] == user_password:
                session["email"] = user_email
                return redirect(url_for("home"))
            else:
                return render_template("login.html", message="Wrong password")
        else:
            return render_template("login.html", message="Invalid email id")

    else:
        return render_template("login.html", message="")


@app. route("/logout", methods=["GET"])
def logout():
    session.pop('email', None)
    return redirect(url_for("home"))


def getUserStats():
    active_tasks = tasks.count_documents(
        {'user': session['email'], 'status': 1})
    completed_tasks = tasks.count_documents(
        {'user': session['email'], 'status': 0})
    try:
        percent = int((completed_tasks/(active_tasks + completed_tasks))*100)
    except ZeroDivisionError:
        percent = 0

    user_stats = {
        'email': session['email'],
        'name': users.find_one({'email': session['email']})['username'],
        'completed': completed_tasks,
        'rem_tasks': active_tasks,
        'percent': percent
    }
    return user_stats


@app.route("/updatePassword", methods=["POST"])
def updatePassword():
    msg = ""
    x = users.find_one({'email': session['email']})
    user_password = request.form["oldpasswd"]
    if bcrypt.check_password_hash(x['password'],user_password):
    # if x['password'] == user_password:
        new_password = request.form["newpasswd"]
        users.update_one({'email': session['email']}, {
                         '$set': {'password': new_password}})
        msg = "updated Password successfully"
    else:
        msg = "Wrong password"

    return render_template("profile.html", title="User profile", message=msg, user=getUserStats())


@app.route("/deleteAccount", methods=["POST"])
def deleteUser():
    user_password = request.form["passwd"]
    print(user_password)
    x = users.find_one({'email': session['email']})
    print(x['password'])
    # if bcrypt.check_password_hash(x['password'],user_password):
    if x['password'] == user_password:
        users.delete_one({'email': session['email']})
        tasks.delete_many({'email': session['email']})
        return redirect(url_for("logout"))
    else:
        msg = "Wrong password. Account deletion failed."
    
    return render_template("profile.html", title="User profile", message=msg, user=getUserStats())




@app.route("/markCompleted", methods=['POST'])
def markCompleted():
    t = request.get_json()
    print(t)
    tasks.update_one({'_id': ObjectId(t['id'])}, {'$set': {'status': 0}})
    return '200'


@app.route("/markAllCompleted", methods=['POST'])
def markAllCompleted():
    tasks.update_many({'user': session['email']}, {'$set': {'status': 0}})
    return '200'


@app.route("/markIncomplete")
def markAllIncomplete():
    tasks.update_many({'user': session['email']}, {'$set': {'status': 1}})
    return '200'


@app.route("/addTask", methods=['POST'])
def addTask():
    t = request.get_json()
    new_task = {
        'content': t['task'],
        'status': 1,
        'user': session['email']
    }
    x = tasks.insert_one(new_task)
    res = make_response(jsonify({'id': str(x.inserted_id)}), 200)
    return res

@app.route("/UpdateTasks/<id>",methods=['GET','POST'])
def updateTasks(id):
        # if request.method=='GET':
        #     # update = tasks.find({'_id':ObjectId(id)})
        #     updateu = tasks.find({'_id':ObjectId(id)})
        #     oldvalues = []
        #     for i in updateu:
        #         print(i)
        #         oldvalues.append(i)
        # if request.method=='POST':
        #     tasks= request.form['tasks']
        #     # db.note.update_one({'_id':ObjectId(id)},{'$set':{'title':title,'note':note}})
        #         # user = db.find_one({'email':uemail},{'_id':0,'name':1})
        #     tasks.delete_many({'_id':ObjectId(id)})
        #     insertnewta = tasks.insert_one({
        #     'tasks':tasks
        #     })
        #     tasksd=tasks.find({})
        #     tasksl=[]
        #     for i in tasksd:
        #         tasksl.append(i)
        #     flash(f'Post updated succesfully','success')
        #     return render_template('index.html',tasks=tasksl)
        # return render_template("update.html",posts=oldvalues)

    if session["email"]:
        if request.method == "GET":
            updateu = tasks.find({'_id':ObjectId(id)})
            oldvalues = []
            for i in updateu:
                print(i)
                oldvalues.append(i)

        if request.method == "POST":
            ta= request.form['tasks']
            tasks.update_one({"_id" : ObjectId(id)}, {'$set' : {"content": ta}})
            flash(f'Post updated succesfully','success')
            return redirect("/homepage")
        return render_template("update.html",oldvalues=oldvalues)
    else:
        return redirect("/login")

@app.route("/completed")
def getCompletedTasks():
    usr_inactive_tasks = tasks.find({'user': session['email'], 'status': 0})
    return render_template("finished.html", title="Finished tasks", tasks=usr_inactive_tasks)


@app.route("/deleteCompleted")
def deleteCompletedTasks():
    tasks.delete_many({'user': session['email'], 'status': 0})
    return '200'


@app.route("/about")
def about():
    return render_template("about.html", title="About")


@app.route("/profile")
def displayProfile():
    return render_template("profile.html", title="User profile", message="", user=getUserStats())

@app.route('/')
@app.route('/homepage',methods=['GET','POST'])
def home():
    if "email" in session:
        usrname = users.find_one({'email': session['email']})['username']
        usr_tasks = tasks.find({'user': session['email']})
        usr_active_tasks = []
        for x in usr_tasks:
            if x['status'] == 1:
                usr_active_tasks.append(x)
        return render_template("index.html", title="My home", user=usrname, tasks=usr_active_tasks)
    else:
        return redirect(url_for("login"))




if __name__ == '__main__':
    app.run(debug=True)
