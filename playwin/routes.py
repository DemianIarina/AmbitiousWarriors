import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from playwin import app, db, bcrypt, mail
from playwin.forms import (RegistrationForm, LoginForm, UpdateAccountForm, PostForm, RequestResetForm,
                           ResetPasswordForm, ChildForm, TaskForm, RewardForm)
from playwin.models import User, Post, Child, Task, Reward
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message


@app.route("/")
@app.route("/home")
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('home.html', posts=posts)


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post', form=form, legend='New Post')


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post', form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(
        author=user
    ).order_by(
        Post.date_posted.desc()
    ).paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in!', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


@app.route("/child/new", methods=['GET', 'POST'])
@login_required
def add_child():
    form = ChildForm()
    if form.validate_on_submit():
        child = Child(name=form.name.data, parent_id=current_user.id)
        db.session.add(child)
        db.session.commit()
        flash('Your child has been added!', 'success')
        return redirect(url_for('children'))
    return render_template('add_child.html', title='Add Child', form=form, legend='Add Child')


@app.route("/child/<int:child_id>")
def child(child_id):
    page = request.args.get('page', 1, type=int)
    child = Child.query.get_or_404(child_id)
    if child.parent != current_user:
        abort(403)
    tasks = Task.query.filter_by(child_id=child.id).paginate(page=page, per_page=100)
    rewards = Reward.query.filter_by(child_id=child.id).paginate(page=page, per_page=100)
    return render_template('child.html', title=child.name, child=child, tasks=tasks, rewards=rewards)


@app.route("/child/<int:child_id>/update", methods=['GET', 'POST'])
@login_required
def update_child(child_id):
    child = Child.query.get_or_404(child_id)
    if child.parent != current_user:
        abort(403)
    form = ChildForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            child.picture = picture_file
        child.name = form.name.data
        db.session.commit()
        flash("Your child's information has been updated!", 'success')
        return redirect(url_for('child', child_id=child.id))
    elif request.method == 'GET':
        form.name.data = child.name
    picture = url_for('static', filename='profile_pics/' + child.picture)
    return render_template('update_child.html', title='Update',
                           picture=picture, form=form, legend='Update', child=child)


@app.route("/child/<int:child_id>/delete", methods=['POST'])
@login_required
def remove_child(child_id):
    child = Child.query.get_or_404(child_id)
    if child.parent != current_user:
        abort(403)
    db.session.delete(child)
    db.session.commit()
    flash('Your child has been removed!', 'success')
    return redirect(url_for('children'))


@app.route("/children")
def children():
    page = request.args.get('page', 1, type=int)
    if current_user.is_authenticated:
        user = User.query.filter_by(username=current_user.username).first_or_404()
        children = Child.query.filter_by(parent=user).order_by(Child.name.asc()).paginate(page=page, per_page=10)
    else:
        children = 1
        user = 1
    return render_template('children.html', title='About', children=children, user=user)


@app.route("/child/<int:child_id>/task/new", methods=['GET', 'POST'])
@login_required
def add_task(child_id):
    child = Child.query.get_or_404(child_id)
    if child.parent != current_user:
        abort(403)
    form = TaskForm()
    if form.validate_on_submit():
        task = Task(name=form.name.data, description=form.description.data,
                    points_awarded=form.points_awarded.data, child_id=child.id)
        db.session.add(task)
        db.session.commit()
        flash('Your task has been added!', 'success')
        return redirect(url_for('child', child_id=child.id))
    return render_template('add_task.html', title='Add Task', form=form, legend='Add Task')


@app.route("/child/<int:child_id>/task/<int:task_id>/delete", methods=['POST'])
@login_required
def remove_task(child_id, task_id):
    task = Task.query.get_or_404(task_id)
    child = Child.query.get_or_404(child_id)
    if child.parent != current_user:
        abort(403)
    db.session.delete(task)
    db.session.commit()
    flash('The task has been removed!', 'success')
    return redirect(url_for('children'))


@app.route("/child/<int:child_id>/task/<int:task_id>/complete", methods=['POST'])
@login_required
def check_task(child_id, task_id):
    task = Task.query.get_or_404(task_id)
    child = Child.query.get_or_404(child_id)
    if child.parent != current_user:
        abort(403)
    child.points = child.points + task.points_awarded
    db.session.delete(task)
    db.session.commit()
    flash('The task has been completed!', 'success')
    return redirect(url_for('children'))


@app.route("/child/<int:child_id>/reward/new", methods=['GET', 'POST'])
@login_required
def add_reward(child_id):
    child = Child.query.get_or_404(child_id)
    if child.parent != current_user:
        abort(403)
    form = RewardForm()
    if form.validate_on_submit():
        reward = Reward(name=form.name.data, description=form.description.data,
                        points_required=form.points_required.data, child_id=child.id)
        db.session.add(reward)
        db.session.commit()
        flash('Your reward has been added!', 'success')
        return redirect(url_for('child', child_id=child.id))
    return render_template('add_reward.html', title='Add Reward', form=form, legend='Add Reward')


@app.route("/child/<int:child_id>/reward/<int:reward_id>/delete", methods=['POST'])
@login_required
def remove_reward(child_id, reward_id):
    reward = Reward.query.get_or_404(reward_id)
    child = Child.query.get_or_404(child_id)
    if child.parent != current_user:
        abort(403)
    db.session.delete(reward)
    db.session.commit()
    flash('The reward has been removed!', 'success')
    return redirect(url_for('children'))


@app.route("/child/<int:child_id>/reward/<int:reward_id>/buy", methods=['POST'])
@login_required
def buy_reward(child_id, reward_id):
    reward = Reward.query.get_or_404(reward_id)
    child = Child.query.get_or_404(child_id)
    if child.parent != current_user:
        abort(403)
    child.points = child.points - reward.points_required
    db.session.delete(reward)
    db.session.commit()
    flash('The reward has been purchased!', 'success')
    return redirect(url_for('children'))