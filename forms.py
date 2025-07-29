from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, FloatField, TextAreaField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange

class LoginForm(FlaskForm):
    username = StringField('Foydalanuvchi nomi', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Parol', validators=[DataRequired()])

class RoomCategoryForm(FlaskForm):
    name = StringField('Kategoriya nomi', validators=[DataRequired(), Length(min=1, max=100)])
    description = TextAreaField('Tavsif')
    price_per_30min = FloatField('30 daqiqa uchun narx (som)', validators=[DataRequired(), NumberRange(min=0)], default=15000)

class RoomForm(FlaskForm):
    name = StringField('Xona nomi', validators=[DataRequired(), Length(min=1, max=100)])
    description = TextAreaField('Tavsif')
    category_id = SelectField('Kategoriya', coerce=int, validators=[DataRequired()])
    custom_price_per_30min = FloatField('Maxsus narx (30 daqiqa)', validators=[NumberRange(min=0)])

class RegisterForm(FlaskForm):
    username = StringField('Foydalanuvchi nomi', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Parol', validators=[DataRequired(), Length(min=6)])
    secret_key = StringField('Maxfiy kalit', validators=[DataRequired()])

class ProductForm(FlaskForm):
    name = StringField('Mahsulot nomi', validators=[DataRequired(), Length(min=1, max=100)])
    category = SelectField('Kategoriya', choices=[
        ('drinks', 'Ichimliklar'),
        ('snacks', 'Gazaklar'),
        ('food', 'Ovqatlar'),
        ('other', 'Boshqa')
    ], validators=[DataRequired()])
    price = FloatField('Narx', validators=[DataRequired(), NumberRange(min=0)])
    stock_quantity = IntegerField('Zaxira miqdori', validators=[DataRequired(), NumberRange(min=0)], default=0)
    min_stock_level = IntegerField('Minimal zaxira darajasi', validators=[DataRequired(), NumberRange(min=0)], default=5)
    unit = StringField('O\'lchov birligi', validators=[Length(max=20)], default='dona')

class StockAdjustmentForm(FlaskForm):
    product_id = SelectField('Mahsulot', coerce=int, validators=[DataRequired()])
    movement_type = SelectField('Harakat turi', choices=[
        ('purchase', 'Xarid (Qo\'shish)'),
        ('adjustment', 'Tuzatma'),
        ('loss', 'Yo\'qotish')
    ], validators=[DataRequired()])
    quantity = IntegerField('Miqdor', validators=[DataRequired(), NumberRange(min=1)])
    reason = StringField('Sabab', validators=[Length(max=200)])
    notes = TextAreaField('Izohlar')
    submit = SubmitField('Qo\'llash')

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
