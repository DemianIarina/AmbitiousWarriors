from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from playwin import db, login_manager, app
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(22), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    children = db.relationship('Child', backref='parent', lazy=True)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"


class Child(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    picture = db.Column(db.String(50), nullable=False, default='default.jpg')
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    points = db.Column(db.Integer, default=0, nullable=False)
    tasks = db.relationship('Task', backref='child', lazy=True)
    rewards = db.relationship('Reward', backref='child', lazy=True)

    def __repr__(self):
        return f"Child('{self.name}', '{self.parent_id}', '{self.points}')"


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    points_awarded = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f"Task('{self.name}', '{self.child_id}', '{self.points_awarded}')"


class Reward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    points_required = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f"Reward('{self.name}', '{self.child_id}', '{self.points_required}')"
