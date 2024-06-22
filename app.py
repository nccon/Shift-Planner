from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, Shift, ShiftChangeRequest, LogEntry, Holiday
from forms import LoginForm, UserForm, ShiftForm, ShiftChangeRequestForm, HolidayForm
from datetime import datetime, timedelta
import serial
import time
import csv
from io import StringIO
import threading

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize GSM serial communication
gsm_serial = serial.Serial("/dev/ttyAMA0", baudrate=115200, timeout=1)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_shift_change_request():
    return dict(ShiftChangeRequest=ShiftChangeRequest)

@app.before_request
def before_request():
    request.start_time = datetime.utcnow()

@app.after_request
def after_request(response):
    if current_user.is_authenticated:
        duration = (datetime.utcnow() - request.start_time).total_seconds()
        log_entry = LogEntry(
            user_id=current_user.id,
            method=request.method,
            endpoint=request.path,
            status_code=response.status_code,
            duration=duration
        )
        db.session.add(log_entry)
        db.session.commit()
    return response

@app.route('/delete_holiday/<int:holiday_id>', methods=['POST'])
@login_required
def delete_holiday(holiday_id):
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    holiday = Holiday.query.get(holiday_id)
    if holiday:
        db.session.delete(holiday)
        db.session.commit()
        flash('Holiday deleted successfully!', 'success')
    else:
        flash('Holiday not found.', 'danger')
    return redirect(url_for('manage'))


@app.route('/')
def index():
    shifts = Shift.query.all()
    holidays = Holiday.query.all()
    shifts_dict = [
        {
            'title': f"{shift.user.username}: {shift.shift_type}",
            'start': shift.start_date.strftime('%Y-%m-%d'),
            'end': (shift.end_date + timedelta(days=1)).strftime('%Y-%m-%d'),  # FullCalendar's end date is exclusive
            'color': 'purple' if shift.shift_type == '10-6 Shift' else 'green' if shift.shift_type == 'Monitoring' else ''
        } for shift in shifts
    ]
    
    holidays_dict = [
        {
            'title': holiday.name,
            'start': holiday.date.strftime('%Y-%m-%d'),
            'end': holiday.date.strftime('%Y-%m-%d'),
            'color': 'light pink',
            'display': 'background'
        } for holiday in holidays
    ]
    
    events = shifts_dict + holidays_dict
    change_form = ShiftChangeRequestForm()
    change_form.shift_id.choices = [(shift.id, f"{shift.user.username}: {shift.shift_type} from {shift.start_date} to {shift.end_date}") for shift in shifts]
    change_form.target_user_id.choices = [(user.id, user.username) for user in User.query.all()]
    return render_template('index.html', events=events, change_form=change_form)

@app.route('/export_shifts', methods=['POST'])
@login_required
def export_shifts():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    user_id = request.form.get('user_id')
    export_type = request.form.get('export_type')

    query = Shift.query.filter(Shift.start_date >= start_date, Shift.end_date <= end_date)

    if user_id != 'all':
        query = query.filter_by(user_id=user_id)

    if export_type == 'weekends':
        query = query.filter(Shift.start_date.op('strftime')('%w').in_(['0', '6']))
    elif export_type == 'bank_holidays':
        holidays = [holiday.date for holiday in Holiday.query.all()]
        query = query.filter(Shift.start_date.in_(holidays))

    shifts = query.all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Username', 'Shift Type', 'Start Date', 'End Date'])

    for shift in shifts:
        writer.writerow([shift.user.username, shift.shift_type, shift.start_date, shift.end_date])

    output.seek(0)

    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=shifts.csv'}
    )

@app.route('/export_logs')
@login_required
def export_logs():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    log_entries = LogEntry.query.all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['User ID', 'Username', 'Method', 'Endpoint', 'Status Code', 'Duration', 'Timestamp'])

    for entry in log_entries:
        user = User.query.get(entry.user_id)
        writer.writerow([entry.user_id, user.username, entry.method, entry.endpoint, entry.status_code, entry.duration, entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')])

    output.seek(0)

    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=logs.csv'}
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:
            login_user(user, remember=form.remember.data)
            return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/manage', methods=['GET', 'POST'])
@login_required
def manage():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    shift_form = ShiftForm()
    shift_form.user_id.choices = [(user.id, user.username) for user in User.query.all()]
    
    holiday_form = HolidayForm()

    if request.method == 'POST':
        if shift_form.submit.data and shift_form.validate_on_submit():
            # Handle adding a new shift
            new_shift = Shift(
                user_id=shift_form.user_id.data,
                start_date=shift_form.start_date.data,
                end_date=shift_form.end_date.data,
                shift_type=shift_form.shift_type.data
            )
            db.session.add(new_shift)
            db.session.commit()
            flash('Shift added successfully!', 'success')

            # Send SMS notification
            user = User.query.get(shift_form.user_id.data)
            phone_number = user.phone
            message = f"Hi! Just a reminder. You have been added on the schedule for shift: {shift_form.shift_type.data} on {shift_form.start_date.data} until {shift_form.end_date.data}"
            send_sms(phone_number, message)

            return redirect(url_for('manage'))
        
        elif 'delete_shift' in request.form:
            shift_id = request.form.get('shift_id')
            shift_to_delete = Shift.query.get(shift_id)
            if shift_to_delete:
                # Delete related shift change requests first
                ShiftChangeRequest.query.filter_by(shift_id=shift_id).delete()
                db.session.delete(shift_to_delete)
                db.session.commit()
                flash('Shift deleted successfully!', 'success')
            return redirect(url_for('manage'))
            
        elif holiday_form.submit.data and holiday_form.validate_on_submit():
            # Handle adding a new holiday
            new_holiday = Holiday(
                name=holiday_form.name.data,
                date=holiday_form.date.data
            )
            db.session.add(new_holiday)
            db.session.commit()
            flash('Holiday added successfully!', 'success')
            return redirect(url_for('manage'))    

    shifts = Shift.query.all()
    holidays = Holiday.query.all()
    return render_template('manage.html', shift_form=shift_form, holidays=holidays, holiday_form=holiday_form, shifts=shifts)

@app.route('/update_shift', methods=['POST'])
@login_required
def update_shift():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    shift_id = data.get('shift_id')
    user_id = data.get('user_id')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    shift_type = data.get('shift_type')

    shift = Shift.query.get(shift_id)
    if shift:
        shift.user_id = user_id
        shift.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        shift.end_date = datetime.strptime(end_date, '%Y-%m-%d')
        shift.shift_type = shift_type
        db.session.commit()
        return jsonify({'success': 'Shift updated successfully!'})
    return jsonify({'error': 'Shift not found'}), 404

@app.route('/request_shift_change', methods=['POST'])
@login_required
def request_shift_change():
    form = ShiftChangeRequestForm()
    form.shift_id.choices = [(shift.id, f"{shift.shift_type} from {shift.start_date} to {shift.end_date}") for shift in Shift.query.filter_by(user_id=current_user.id).all()]
    form.target_user_id.choices = [(user.id, user.username) for user in User.query.filter(User.id != current_user.id).all()]
    if form.validate_on_submit():
        shift_id = form.shift_id.data
        shift = Shift.query.get(shift_id)
        new_request = ShiftChangeRequest(
            shift_id=shift_id,
            requester_id=current_user.id,
            target_user_id=form.target_user_id.data,
            status='Pending'
        )
        db.session.add(new_request)
        db.session.commit()
        flash('Shift change request sent successfully!', 'success')
        return redirect(url_for('my_shifts'))
    flash('Failed to send shift change request.', 'danger')
    return redirect(url_for('my_shifts'))

@app.route('/calendar')
@login_required
def calendar():
    shifts = Shift.query.all()
    holidays = Holiday.query.all()
    
    shifts_dict = [
        {
            'title': f"{shift.user.username}: {shift.shift_type}",
            'start': shift.start_date.strftime('%Y-%m-%d'),
            'end': (shift.end_date + timedelta(days=1)).strftime('%Y-%m-%d'),  # FullCalendar's end date is exclusive
            'color': 'purple' if shift.shift_type == '10-6 Shift' else 'green' if shift.shift_type == 'Monitoring' else 'blue'
        } for shift in shifts
    ]
    
    holidays_dict = [
        {
            'title': holiday.name,
            'start': holiday.date.strftime('%Y-%m-%d'),
            'end': holiday.date.strftime('%Y-%m-%d'),
            'textColor':'black',
            'color': 'light pink',
            'display': 'background'
        } for holiday in holidays
    ]
    
    events = shifts_dict + holidays_dict
    
    return render_template('calendar.html', events=events)



@app.route('/my_shifts', methods=['GET', 'POST'])
@login_required
def my_shifts():
    shifts = Shift.query.filter_by(user_id=current_user.id).all()
    requests = ShiftChangeRequest.query.filter_by(requester_id=current_user.id).all()

    # Check for any approved or denied requests
    approved_requests = ShiftChangeRequest.query.filter_by(requester_id=current_user.id, status='Approved').all()
    denied_requests = ShiftChangeRequest.query.filter_by(requester_id=current_user.id, status='Denied').all()

    # Shift change request form
    change_form = ShiftChangeRequestForm()
    user_shifts = Shift.query.filter_by(user_id=current_user.id).all()
    other_users = User.query.filter(User.id != current_user.id).all()
    change_form.shift_id.choices = [(shift.id, f"{shift.shift_type} from {shift.start_date} to {shift.end_date}") for shift in user_shifts]
    change_form.target_user_id.choices = [(user.id, user.username) for user in other_users]

    if change_form.validate_on_submit():
        shift_id = change_form.shift_id.data
        shift = Shift.query.get(shift_id)
        new_request = ShiftChangeRequest(
            shift_id=shift_id,
            requester_id=current_user.id,
            target_user_id=change_form.target_user_id.data,
            status='Pending'
        )
        db.session.add(new_request)
        db.session.commit()
        flash('Shift change request sent successfully!', 'success')
        return redirect(url_for('my_shifts'))

    return render_template('my_shifts.html', shifts=shifts, requests=requests, approved_requests=approved_requests, denied_requests=denied_requests, change_form=change_form)

@app.route('/manage_requests', methods=['GET', 'POST'])
@login_required
def manage_requests():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    requests = ShiftChangeRequest.query.all()

    if request.method == 'POST':
        request_id = request.form.get('request_id')
        action = request.form.get('action')
        shift_request = ShiftChangeRequest.query.get(request_id)

        if action == 'approve' and shift_request.status == 'Pending':
            shift = Shift.query.get(shift_request.shift_id)
            shift.user_id = shift_request.target_user_id
            shift_request.status = 'Approved'
            db.session.commit()
            flash('Shift change approved!', 'success')
        elif action == 'deny' and shift_request.status == 'Pending':
            shift_request.status = 'Denied'
            db.session.commit()
            flash('Shift change denied.', 'danger')

    return render_template('manage_requests.html', requests=requests)

@app.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    user_form = UserForm()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')
        user = User.query.get(user_id)

        if user_form.submit.data and user_form.validate_on_submit():
            # Handle adding a new user
            new_user = User(
                username=user_form.username.data,
                password=user_form.password.data,
                phone=user_form.phone.data,
                email=user_form.email.data,
                is_admin=user_form.is_admin.data
            )
            db.session.add(new_user)
            db.session.commit()
            flash('User added successfully!', 'success')
            return redirect(url_for('manage_users'))
        
        if action == 'delete':
            if user:
                db.session.delete(user)
                db.session.commit()
                flash('User deleted successfully!', 'success')

        elif action == 'toggle_admin':
            if user:
                user.is_admin = not user.is_admin
                db.session.commit()
                flash('User admin status updated!', 'success')

        elif action == 'update_phone':
            new_phone = request.form.get('new_phone')
            if user and new_phone:
                user.phone = new_phone
                db.session.commit()
                flash('User phone number updated!', 'success')

        elif action == 'reset_password':
            new_password = request.form.get('new_password')
            repeat_password = request.form.get('repeat_password')
            if user and new_password == repeat_password:
                user.password = new_password
                db.session.commit()
                flash('User password reset successfully!', 'success')
            else:
                flash('Passwords do not match.', 'danger')

    users = User.query.all()
    return render_template('manage_users.html', users=users, user_form=user_form)

@app.route('/logs')
@login_required
def logs():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    log_entries = LogEntry.query.all()
    
    # Aggregate status codes
    status_code_counts = db.session.query(LogEntry.status_code, db.func.count(LogEntry.status_code)).group_by(LogEntry.status_code).all()
    status_code_counts_dict = {entry[0]: entry[1] for entry in status_code_counts}

    log_entries_dict = [log_entry.to_dict() for log_entry in log_entries]
    return render_template('logs.html', log_entries=log_entries_dict, status_code_counts=status_code_counts_dict)

def send_sms(phone_number, message):
    try:
        gsm_serial.write(b'AT\r')
        time.sleep(1)
        gsm_serial.write(b'AT+CMGF=1\r')
        time.sleep(1)
        gsm_serial.write(f'AT+CMGS="{phone_number}"\r'.encode())
        time.sleep(1)
        gsm_serial.write(message.encode() + b"\x1A\r")
        time.sleep(1)
        print("SMS sent successfully!")
    except Exception as e:
        print(f"Failed to send SMS: {str(e)}")

@app.route('/create_admin')
def create_admin():
    existing_admin = User.query.filter_by(username="admin").first()
    if not existing_admin:
        admin_user = User(
            username="admin",
            password="adminpassword",
            phone="12345678",
            email="admin@example.com",
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
        return "Admin user created successfully!"
    else:
        return "Admin user already exists."

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='192.168.10.43', port=5000)
