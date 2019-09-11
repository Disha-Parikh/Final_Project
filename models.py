from datetime import datetime
from IntellFRS import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.BigInteger, nullable= False)
    cal_id = db.Column(db.String(), unique=True, nullable=False)
    address = db.Column(db.String(200), unique=True)
    image_file = db.Column(db.String(200), nullable=False, default='default.jpg')
    # Referer
    attendance = db.relationship('Attendance', backref='user', lazy=True)

    def __repr__(self):
        return f"User('{self.id}','{self.name}', '{self.email}', '{self.mobile}','{self.cal_id}', '{self.address}')"

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    presence = db.Column(db.String(8), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    reg_no= db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)

    def __repr__(self):
        return f"Attendance('{self.id}', '{self.presence}','{self.date}','{self.reg_no}')"
