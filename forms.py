# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, validators, IntegerField
# from wtforms.validators import DataRequired, EqualTo

class RegisterForm(FlaskForm):
    userid = StringField('User ID', [validators.DataRequired()])
    username = StringField('Username', [validators.DataRequired()])
    password = PasswordField('Password', [validators.DataRequired(), validators.EqualTo('re_password', message='Passwords must match')])
    re_password = PasswordField('re_Password', [validators.DataRequired()])

class LoginForm(FlaskForm):     
    userid = StringField('User ID', [validators.DataRequired()])
    password = PasswordField('Password', [validators.DataRequired()])

class PasswordForm(FlaskForm):
    password = PasswordField('Password', [validators.DataRequired(), validators.EqualTo('re_password', message='Passwords must match')])
    re_password = PasswordField('re_Password', [validators.DataRequired()])

class EnergyForm(FlaskForm):
    serialnumber = StringField('Serial Number', [validators.DataRequired()])
    maxcurrent = IntegerField('Max. Current', [validators.DataRequired()])

class CardForm(FlaskForm):
    cardname = StringField('Card Name', [validators.DataRequired()])
    cardnumber = StringField('Card Number', [validators.DataRequired()])