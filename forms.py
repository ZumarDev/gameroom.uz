from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, FloatField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Email, Length, NumberRange

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])

class RoomForm(FlaskForm):
    name = StringField('Room Name', validators=[DataRequired(), Length(min=1, max=100)])
    description = TextAreaField('Description')

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(min=1, max=100)])
    category = SelectField('Category', choices=[
        ('drinks', 'Drinks'),
        ('snacks', 'Snacks'),
        ('food', 'Food'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])

class SessionForm(FlaskForm):
    room_id = SelectField('Room', coerce=int, validators=[DataRequired()])
    session_type = SelectField('Session Type', choices=[
        ('fixed', 'Fixed Time'),
        ('vip', 'VIP')
    ], validators=[DataRequired()])
    duration_minutes = SelectField('Duration', choices=[
        (30, '30 minutes - 15,000 som'),
        (60, '60 minutes - 25,000 som'),
        (90, '90 minutes - 35,000 som'),
        (120, '120 minutes - 45,000 som')
    ], coerce=int)

class AddProductToSessionForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)], default=1)
    session_id = HiddenField()
