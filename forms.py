from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, FloatField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Email, Length, NumberRange

class LoginForm(FlaskForm):
    username = StringField('Foydalanuvchi nomi', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Parol', validators=[DataRequired()])

class RoomForm(FlaskForm):
    name = StringField('Xona nomi', validators=[DataRequired(), Length(min=1, max=100)])
    description = TextAreaField('Tavsif')

class ProductForm(FlaskForm):
    name = StringField('Mahsulot nomi', validators=[DataRequired(), Length(min=1, max=100)])
    category = SelectField('Kategoriya', choices=[
        ('drinks', 'Ichimliklar'),
        ('snacks', 'Gazaklar'),
        ('food', 'Ovqatlar'),
        ('other', 'Boshqa')
    ], validators=[DataRequired()])
    price = FloatField('Narx', validators=[DataRequired(), NumberRange(min=0)])

class SessionForm(FlaskForm):
    room_id = SelectField('Xona', coerce=int, validators=[DataRequired()])
    session_type = SelectField('Seans turi', choices=[
        ('fixed', 'Belgilangan vaqt'),
        ('vip', 'VIP')
    ], validators=[DataRequired()])
    duration_minutes = SelectField('Davomiyligi', choices=[
        (30, '30 daqiqa - 15,000 som'),
        (60, '60 daqiqa - 25,000 som'),
        (90, '90 daqiqa - 35,000 som'),
        (120, '120 daqiqa - 45,000 som')
    ], coerce=int)

class AddProductToSessionForm(FlaskForm):
    product_id = SelectField('Mahsulot', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Miqdori', validators=[DataRequired(), NumberRange(min=1)], default=1)
    session_id = HiddenField()
