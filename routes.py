from sqlalchemy.ext.declarative import DeclarativeMeta
from importlib import import_module
import os
import secrets
from PIL import Image
from flask import render_template, Response, url_for, flash, redirect, request, abort, jsonify
from IntellFRS import app, db, bcrypt
from IntellFRS.forms import RegistrationForm, LoginForm, UpdateAccountForm
from IntellFRS.models import User, Attendance
from flask_login import login_user, current_user, logout_user, login_required
from email.mime.text import MIMEText
import smtplib
import pycronofy
import datetime
import json
import pandas as pd


if os.environ.get('CAMERA'):
    Camera = import_module('camera_' + os.environ['CAMERA']).Camera
else:
    from IntellFRS.camera_opencv import Camera


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)


name = ""
id_name = 0
data = ()
@app.route('/')
@app.route('/index')
def index():
    logout_user()
    return render_template('index1.html')


def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    else:
        return render_template('login.html')


@app.route('/fetchdata/', methods=['POST','GET'])
def fetchdata():
    global data
    global name
    global id_name
    id_name, name = Camera.ret_names()
    if(name =="Unknown"):
        return jsonify({'data':"Unknown"})
    else:
        data = User.query.filter_by(id = id_name).first()
        temp_dict = {'name':data.name, 'email': data.email, 'mobile': data.mobile, 'address': data.address}
        d = datetime.date.today()
        reg = db.session.query(User.id).filter_by(id = id_name).first()
        att = Attendance(presence = 'P', date = d, reg_no = reg[0])
        date_exists = db.session.query(Attendance.date).filter(Attendance.reg_no==reg[0],Attendance.date==d).first()
        if date_exists:
            temp = {'name':data.name, 'email': data.email, 'mobile': data.mobile, 'address': data.address, 'msg':"Attendance already done for today"}
            return jsonify({'data':temp})
        else:
            db.session.add(att)
            db.session.commit()
            return jsonify({'data':temp_dict})


@app.route("/logint", methods=['GET', 'POST'])
def logint():
    global name
    global id_name
    # id_name,name = Camera.ret_names()
    user = User.query.filter_by(id = id_name).first()
    form = LoginForm(obj=user)
    rform = RegistrationForm()
    if user:
        login_user(user, remember=form.remember.data)
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('events'))
    else:
       flash('Login Unsuccessful. Please look into the camera', 'danger')
       return redirect(url_for('login'))


@app.route('/home')
def home():
    return render_template('index1.html', title='Home')

@app.route('/events')
@login_required
def events():
    return render_template('show_events.html')

@app.route('/event')
@login_required
def event():
    global data
    global id_name
    global name
    data = User.query.filter_by(id = id_name).first()
    cal_id = data.cal_id
    cronofy = pycronofy.Client(access_token="Ru-JiYhxeyAaCRyCevGnLzv3BrUvZwWU")
    timezone_id = 'Asia/Calcutta'
    from_date = datetime.date.today()
    to_date = (datetime.date.today() + datetime.timedelta(days=1))
    YOUR_CAL_ID = cal_id
    all_events = cronofy.read_events(calendar_ids=(YOUR_CAL_ID,),
        from_date=from_date,
        to_date=to_date,
        tzid=timezone_id
    ).all()

    conv = json.dumps(all_events)
    return conv



@app.route("/attendance", methods=['GET', 'POST'])
@login_required
def attendance():
    return render_template('graph2.html')


@app.route("/att", methods=['GET', 'POST'])
@login_required
def att():
    global data
    global id_name
    global name
    reg = db.session.query(User.id).filter_by(id = id_name).first()
    reg_n = reg[0]
    df= pd.read_sql(sql=db.session.query(Attendance).filter(Attendance.reg_no==reg_n, Attendance.presence=='P').
                                                with_entities(Attendance.date).statement, con=db.session.bind)

    df["date"] = pd.to_datetime(df["date"])

    counts= df.groupby([df['date'].dt.month.rename('month')]).agg({'count'})

    c=counts.to_json(orient='columns')
    x=str(c)
    y=x[20:-1]
    return y


@app.route("/logout")
def logout():
    logout_user()
    # global data
    global id_name
    # global name
    id_name = 0
    return redirect(url_for('index'))


@app.route("/about")
def about():
    return render_template('about.html', title='About')


def save_picture(form_picture):
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = str(current_user.id) + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    form_picture.save(picture_path)
    return picture_fn, picture_path


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file, picture_path = save_picture(form.picture.data)
            current_user.image_file = picture_path
        current_user.name = form.name.data
        current_user.email = form.email.data
        current_user.cal_id = form.cal_id.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.name.data = current_user.name
        form.email.data = current_user.email
        form.cal_id.data = current_user.cal_id
        im = str(id_name)+'.jpg'

    image_file = url_for('static', filename='profile_pics/' + im)

    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)

def send_email(user, email):
    from_e= "intellfrs@gmail.com"
    from_p= "bcrypt@123"
    to_email=email
    subject="Registration"
    message="Hi <br> <strong>%r</strong>,  You have been registered successfully. <br> Thanks!" % (user)
    msg=MIMEText(message, 'html')
    msg['Subject']=subject
    msg['To']=to_email
    msg['From']=from_e
    gmail=smtplib.SMTP('smtp.gmail.com',587)
    gmail.ehlo()
    gmail.starttls()
    gmail.login(from_e, from_p)
    gmail.send_message(msg)


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
    	im = Camera.ret_path()
    	user = User(name=form.name.data, email=form.email.data, mobile=form.mobile.data, cal_id=form.cal_id.data, address = form.address.data, image_file=im)
    	db.session.add(user)
    	db.session.commit()
    	flash('Your account has been created! You are now able to log in', 'success')
    	send_email(form.name.data, form.email.data)
    	return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)
