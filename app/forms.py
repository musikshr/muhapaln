from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
import re
import logging

logger = logging.getLogger(__name__)


def password_complexity(password):
    """Проверяет сложность пароля и возвращает (is_valid, message)"""
    errors = []

    if len(password) < 8:
        errors.append("минимум 8 символов")
    if not re.search(r'[A-Z]', password):
        errors.append("хотя бы одну заглавную букву")
    if not re.search(r'[a-z]', password):
        errors.append("хотя бы одну строчную букву")
    if not re.search(r'\d', password):
        errors.append("хотя бы одну цифру")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("хотя бы один специальный символ (!@#$%^&*() etc.)")
    if errors:
        return False, f"Пароль должен содержать: {', '.join(errors)}"
    return True, "Пароль надёжный"


class PasswordComplexity:
    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        is_valid, msg = password_complexity(field.data)
        if not is_valid:
            if self.message:
                raise ValidationError(self.message)
            raise ValidationError(msg)
        logger.info(f'Password complexity check passed for user registration')


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(), Length(min=3, max=64)
    ])
    email = StringField('Email', validators=[
        DataRequired(), Email()
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(),
        Length(min=8, message="Пароль должен быть не менее 8 символов"),
        PasswordComplexity()
    ])
    password2 = PasswordField('Повторите пароль', validators=[
        DataRequired(), EqualTo('password', message="Пароли не совпадают")
    ])
    submit = SubmitField('Зарегистрироваться')


class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class TaskForm(FlaskForm):
    title = StringField('Название', validators=[
                        DataRequired(), Length(max=100)])
    description = TextAreaField('Описание', validators=[Optional()])
    priority = SelectField('Приоритет', choices=[
        (1, 'Высокий'),
        (2, 'Средний'),
        (3, 'Низкий')
    ], coerce=int, default=2)
    due_date = DateField('Срок выполнения', validators=[
                         Optional()], format='%Y-%m-%d')
    submit = SubmitField('Сохранить')
