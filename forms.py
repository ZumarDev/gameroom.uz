from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, FloatField, TextAreaField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, EqualTo

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
    gaming_center_name = StringField("O'yinxona nomi", validators=[DataRequired(), Length(min=2, max=100)])
    password = PasswordField('Parol', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Parolni tasdiqlash', validators=[DataRequired(), EqualTo('password', message='Parollar mos emas')])
    secret_key = PasswordField('Maxfiy kalit', validators=[DataRequired()])

class ProductCategoryForm(FlaskForm):
    name = StringField('Kategoriya nomi', validators=[DataRequired(), Length(min=1, max=100)])
    description = TextAreaField('Tavsif')

class ProductForm(FlaskForm):
    name = StringField('Mahsulot nomi', validators=[DataRequired(), Length(min=1, max=100)])
    category_id = SelectField('Kategoriya', coerce=int, validators=[DataRequired()])
    price = FloatField('Narx', validators=[DataRequired(), NumberRange(min=0)])
    unit = StringField('O\'lchov birligi', validators=[Length(max=20)], default='dona')
    stock_quantity = IntegerField('Zaxira miqdori', validators=[DataRequired(), NumberRange(min=0)], default=0)
    min_stock_alert = IntegerField('Minimal zaxira ogohlantiruvi', validators=[DataRequired(), NumberRange(min=0)], default=5)

class StockUpdateForm(FlaskForm):
    quantity = IntegerField('Miqdor', validators=[DataRequired(), NumberRange(min=1)])
    action = SelectField('Amal', choices=[
        ('add', 'Qo\'shish'),
        ('remove', 'Chiqarish')
    ], validators=[DataRequired()])
    note = TextAreaField('Izoh')

class InventoryForm(FlaskForm):
    product_id = SelectField('Mahsulot', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Miqdor', validators=[DataRequired(), NumberRange(min=1)])
    action = SelectField('Amal', choices=[
        ('add', 'Qo\'shish'),
        ('set', 'Belgilash')
    ], validators=[DataRequired()])
    note = TextAreaField('Izoh')

class SessionForm(FlaskForm):
    room_id = SelectField('Xona', coerce=int, validators=[DataRequired()])
    session_type = SelectField('Seans turi', choices=[
        ('fixed', 'Belgilangan vaqt'),
        ('vip', 'VIP')
    ], validators=[DataRequired()])
    input_type = SelectField('Qanday kiritasiz?', choices=[
        ('time', 'Vaqt davomiyligi'),
        ('amount', 'Summa (avtomatik vaqt hisoblanadi)')
    ], validators=[DataRequired()], default='time')
    duration_hours = IntegerField('Soat', validators=[Optional(), NumberRange(min=0, max=24)], default=0)
    duration_minutes = IntegerField('Daqiqa', validators=[Optional(), NumberRange(min=0, max=59)], default=30)
    amount_input = FloatField('Summa', validators=[Optional(), NumberRange(min=0)])

class AddProductToSessionForm(FlaskForm):
    product_id = SelectField('Mahsulot', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Miqdori', validators=[DataRequired(), NumberRange(min=1)], default=1)
    session_id = HiddenField()

class PasswordResetForm(FlaskForm):
    username = StringField('Foydalanuvchi nomi', validators=[DataRequired(), Length(min=4, max=20)])
    secret_key = PasswordField('Maxfiy kalit', validators=[DataRequired()])
    new_password = PasswordField('Yangi parol', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Parolni tasdiqlash', validators=[DataRequired(), EqualTo('new_password', message='Parollar mos emas')])

class LanguageSwitchForm(FlaskForm):
    language = SelectField('Til', choices=[
        ('uz', "O'zbek"),
        ('ru', 'Русский'),
        ('en', 'English')
    ], validators=[DataRequired()])

class ReportForm(FlaskForm):
    report_type = SelectField('Hisobot turi', choices=[
        ('daily', 'Kunlik hisobot'),
        ('weekly', 'Haftalik hisobot'),
        ('monthly', 'Oylik hisobot')
    ], validators=[DataRequired()], default='daily')
    date = StringField('Sana', validators=[DataRequired()])

class PasswordResetForm(FlaskForm):
    username = StringField('Foydalanuvchi nomi', validators=[DataRequired(), Length(min=4, max=20)])
    secret_key = PasswordField('Maxfiy kalit', validators=[DataRequired()])
    new_password = PasswordField('Yangi parol', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Parolni tasdiqlash', validators=[DataRequired(), EqualTo('new_password', message='Parollar mos emas')])

class LanguageSwitchForm(FlaskForm):
    language = SelectField('Til', choices=[
        ('uz', 'O\'zbekcha'),
        ('ru', 'Русский'),
        ('en', 'English')
    ], validators=[DataRequired()])

class ReportForm(FlaskForm):
    report_type = SelectField('Hisobot turi', choices=[
        ('daily', 'Kunlik'),
        ('weekly', 'Haftalik'),
        ('monthly', 'Oylik')
    ], validators=[DataRequired()], default='daily')
    date = StringField('Sana (YYYY-MM-DD)')
    export_format = SelectField('Eksport formati', choices=[
        ('pdf', 'PDF'),
        ('excel', 'Excel')
    ], validators=[DataRequired()], default='pdf')
