from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateField, SelectField
from wtforms.validators import DataRequired, Length, Email
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=150)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    phone = StringField('Phone', validators=[DataRequired(), Length(min=8, max=8)])  # Adjust as per your requirements
    email = StringField('Email', validators=[DataRequired(), Email()])  # Use Email validator here
    is_admin = BooleanField('Admin')
    submit = SubmitField('Submit')

class ShiftForm(FlaskForm):
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    shift_type = SelectField('Shift Type', choices=[('Morning', 'Morning'), ('Afternoon', 'Afternoon'), ('Night', 'Night'), ('10-6 Shift', '10-6 Shift'), ('Monitoring', 'Monitoring')], validators=[DataRequired()])
    submit = SubmitField('Add Shift')

class ShiftChangeRequestForm(FlaskForm):
    shift_id = SelectField('Shift', choices=[], coerce=int)
    target_user_id = SelectField('Target User', choices=[], coerce=int)
    submit = SubmitField('Request Shift Change')

class HolidayForm(FlaskForm):
    name = StringField('Holiday Name', validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    submit = SubmitField('Add Holiday')
