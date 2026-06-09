from flask import render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime, timedelta
from calendar import monthcalendar
from app import db
from app.models import User, Task
from app.forms import LoginForm, RegistrationForm, TaskForm
import logging

logger = logging.getLogger(__name__)


def init_routes(app):

    @app.route('/')
    @app.route('/index')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('tasks'))
        return render_template('index.html')

    @app.route('/tasks')
    @login_required
    def tasks():
        status_filter = request.args.get('status', 'all')
        priority_filter = request.args.get('priority', 'all')

        query = Task.query.filter_by(user_id=current_user.id)

        if status_filter == 'active':
            query = query.filter_by(is_done=False)
        elif status_filter == 'completed':
            query = query.filter_by(is_done=True)

        if priority_filter != 'all':
            query = query.filter_by(priority=int(priority_filter))

        tasks_list = query.order_by(
            Task.is_done.asc(),
            Task.priority.asc(),
            Task.due_date.asc(),
            Task.created_at.desc()
        ).all()

        total_tasks = Task.query.filter_by(user_id=current_user.id).count()
        completed_tasks = Task.query.filter_by(
            user_id=current_user.id, is_done=True).count()
        completion_percent = (
            completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        logger.info(
            f'User {current_user.username} viewed tasks list (status={status_filter}, priority={priority_filter})')

        return render_template('tasks.html',
                               tasks=tasks_list,
                               status_filter=status_filter,
                               priority_filter=priority_filter,
                               total_tasks=total_tasks,
                               completed_tasks=completed_tasks,
                               completion_percent=int(completion_percent))

    @app.route('/task/new', methods=['GET', 'POST'])
    @login_required
    def new_task():
        form = TaskForm()

        if form.validate_on_submit():
            task = Task(
                title=form.title.data,
                description=form.description.data or '',
                priority=form.priority.data,
                due_date=form.due_date.data,
                user_id=current_user.id
            )
            db.session.add(task)
            db.session.commit()

            logger.info(
                f'User {current_user.username} created task ID {task.id}: "{task.title}"')
            flash('Задача успешно создана!', 'success')
            return redirect(url_for('tasks'))

        return render_template('task_form.html', form=form, title='Создать задачу')

    @app.route('/task/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_task(id):
        task = Task.query.get_or_404(id)

        if task.user_id != current_user.id:
            logger.warning(
                f'User {current_user.username} tried to edit task {id} belonging to user {task.user_id}')
            abort(403)

        form = TaskForm(obj=task)

        if form.validate_on_submit():
            task.title = form.title.data
            task.description = form.description.data or ''
            task.priority = form.priority.data
            task.due_date = form.due_date.data
            task.updated_at = datetime.utcnow()
            db.session.commit()

            logger.info(f'User {current_user.username} edited task ID {id}')
            flash('Задача обновлена!', 'success')
            return redirect(url_for('tasks'))

        return render_template('task_form.html', form=form, title='Редактировать задачу', task=task)

    @app.route('/task/<int:id>/delete', methods=['POST'])
    @login_required
    def delete_task(id):
        task = Task.query.get_or_404(id)

        if task.user_id != current_user.id:
            logger.warning(
                f'User {current_user.username} tried to delete task {id} belonging to user {task.user_id}')
            abort(403)

        db.session.delete(task)
        db.session.commit()

        logger.info(
            f'User {current_user.username} deleted task ID {id}: "{task.title}"')
        flash('Задача удалена!', 'success')
        return redirect(url_for('tasks'))

    @app.route('/task/<int:id>/toggle', methods=['POST'])
    @login_required
    def toggle_task(id):
        task = Task.query.get_or_404(id)

        if task.user_id != current_user.id:
            abort(403)

        task.is_done = not task.is_done
        task.updated_at = datetime.utcnow()
        db.session.commit()

        status = 'completed' if task.is_done else 'active'
        logger.info(
            f'User {current_user.username} marked task {id} as {status}')
        flash(
            f'Задача {"выполнена" if task.is_done else "возвращена в работу"}!', 'success')
        return redirect(url_for('tasks'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('tasks'))
        form = RegistrationForm()
        if form.validate_on_submit():
            if User.query.filter_by(username=form.username.data).first():
                logger.warning(
                    f'Registration failed: username {form.username.data} already taken')
                flash('Имя пользователя уже занято', 'danger')
                return render_template('register.html', form=form)
            if User.query.filter_by(email=form.email.data).first():
                logger.warning(
                    f'Registration failed: email {form.email.data} already registered')
                flash('Email уже используется', 'danger')
                return render_template('register.html', form=form)
            from app.forms import password_complexity
            is_valid, msg = password_complexity(form.password.data)
            if not is_valid:
                logger.warning(
                    f'Registration failed: weak password attempt for user {form.username.data} - {msg}')
                flash(f'Пароль слишком слабый. {msg}', 'danger')
                return render_template('register.html', form=form)

            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            logger.info(
                f'New user registered: {form.username.data} (email: {form.email.data}) with strong password')
            flash('Регистрация успешна! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        if form.errors:
            logger.warning(f'Registration validation errors: {form.errors}')

        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('tasks'))

        form = LoginForm()

        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()

            if user and user.check_password(form.password.data):
                login_user(user)
                logger.info(f'User {user.username} logged in successfully')
                flash(f'Добро пожаловать, {user.username}!', 'success')
                return redirect(url_for('tasks'))
            else:
                logger.warning(
                    f'Failed login attempt for username: {form.username.data}')
                flash('Неверное имя пользователя или пароль', 'danger')

        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logger.info(f'User {current_user.username} logged out')
        logout_user()
        flash('Вы вышли из системы', 'info')
        return redirect(url_for('index'))

    @app.route('/api/task/<int:id>')
    @login_required
    def api_task(id):
        task = Task.query.get_or_404(id)

        if task.user_id != current_user.id:
            abort(403)

        priority_colors = {1: '#e53e3e', 2: '#ed8936', 3: '#48bb78'}
        priority_texts = {1: '🔥 Высокий', 2: '📌 Средний', 3: '🌿 Низкий'}

        return jsonify({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'priority': task.priority,
            'priority_text': priority_texts.get(task.priority, 'Не указан'),
            'priority_color': priority_colors.get(task.priority, '#718096'),
            'is_done': task.is_done,
            'due_date': task.due_date.strftime('%d.%m.%Y') if task.due_date else None
        })

    @app.route('/calendar')
    @app.route('/calendar/<int:year>/<int:month>')
    @login_required
    def calendar(year=None, month=None):
        today = datetime.now().date()

        if year is None or month is None:
            year = today.year
            month = today.month

        month_names = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]

        cal = monthcalendar(year, month)

        start_date = datetime(year, month, 1).date()

        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()

        tasks = Task.query.filter(
            Task.user_id == current_user.id,
            Task.due_date >= start_date,
            Task.due_date < end_date
        ).all()

        tasks_by_date = {}
        for task in tasks:
            if task.due_date:
                day = task.due_date.day
                if day not in tasks_by_date:
                    tasks_by_date[day] = []
                tasks_by_date[day].append(task)

        logger.info(
            f'User {current_user.username} viewed calendar for {year}-{month} with {len(tasks)} tasks')

        current_date = datetime(year, month, 1)
        prev_date = current_date - timedelta(days=1)
        next_date = current_date + timedelta(days=32)

        prev_year, prev_month = prev_date.year, prev_date.month
        next_year, next_month = next_date.year, next_date.month

        prev_month_name = month_names[prev_month - 1]
        next_month_name = month_names[next_month - 1]
        month_name = month_names[month - 1]

        return render_template('calendar.html',
                               calendar_data=cal,
                               tasks_by_date=tasks_by_date,
                               year=year,
                               month=month,
                               prev_year=prev_year,
                               prev_month=prev_month,
                               next_year=next_year,
                               next_month=next_month,
                               month_name=month_name,
                               prev_month_name=prev_month_name,
                               next_month_name=next_month_name,
                               today_day=today.day,
                               today_year=today.year,
                               today_month=today.month)

    @app.errorhandler(404)
    def not_found_error(error):
        logger.error(f'404 error: {request.path}')
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f'500 error: {str(error)}')
        return render_template('500.html'), 500
