from flask import Flask, flash, redirect, render_template, request, session, url_for
import re
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = 'srms_database.db'
EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

app = Flask(__name__)
app.secret_key = 'srms-development-key'

# SMTP EMAIL CONFIGURATION

SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', 'idrisahmadd15@gmail.com')      # e.g., 'your.email@gmail.com'
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'pvxp jtpc dznz jlcx')  # e.g., 'abcd efgh ijkl mnop'

def send_notification_email(recipient_email, subject, body_text):
    """
    Sends an email notification if SMTP credentials are provided.
    If no credentials are set, prints the email content to terminal/log.
    """
    print(f"\n==================== MENTORSHIP PAIRING UPDATES ====================")
    print(f"TO: {recipient_email}")
    print(f"SUBJECT: {subject}")
    print(f"BODY:\n{body_text}")
    print(f"============================================================")

    if not recipient_email:
        print("[Email Warning] No recipient email address provided.")
        return False

    if not SMTP_USER or not SMTP_PASSWORD:
        print("[Email Warning] SMTP_USER or SMTP_PASSWORD is not set. Email printed to console instead of sending over network.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = f"Mentorship Hub <{SMTP_USER}>"
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_text, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"[Email Success] Email delivered successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"[Email Error] Failed to send email to {recipient_email}: {e}")
        return False


def init_admin_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ActivityLog
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ActivityLog (
            ActivityID INTEGER PRIMARY KEY AUTOINCREMENT,
            Activity TEXT NOT NULL,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Login
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Login (
            LoginID INTEGER PRIMARY KEY AUTOINCREMENT,
            Username TEXT UNIQUE,
            Password TEXT,
            UserType TEXT,
            MentorID INTEGER,
            MenteeID INTEGER,
            IsActive INTEGER DEFAULT 1,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Mentor
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Mentor (
            MentorID INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT,
            Email TEXT,
            Expertise TEXT,
            IsActive INTEGER DEFAULT 1,
            JoinedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Mentee
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Mentee (
            MenteeID INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT,
            Email TEXT,
            Goal TEXT,
            IsActive INTEGER DEFAULT 1,
            JoinedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Program
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Program (
            ProgramID INTEGER PRIMARY KEY AUTOINCREMENT,
            ProgramName TEXT,
            StartDate TEXT,
            EndDate TEXT,
            Description TEXT,
            Status TEXT DEFAULT 'Active'
        )
    ''')

    # Match
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Match (
            MatchID INTEGER PRIMARY KEY AUTOINCREMENT,
            ProgramID INTEGER,
            MentorID INTEGER,
            MenteeID INTEGER,
            MatchDate TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Meeting
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Meeting (
            MeetingID INTEGER PRIMARY KEY AUTOINCREMENT,
            MatchID INTEGER,
            MeetingDate TEXT,
            Notes TEXT,
            Status TEXT DEFAULT 'Scheduled'
        )
    ''')

    # Achievement
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Achievement (
            AchievementID INTEGER PRIMARY KEY AUTOINCREMENT,
            MenteeID INTEGER,
            MentorID INTEGER,
            AchievementType TEXT,
            Title TEXT,
            Organisation TEXT,
            AchievementDate TEXT,
            Verified INTEGER DEFAULT 1,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Feedback
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Feedback (
            FeedbackID INTEGER PRIMARY KEY AUTOINCREMENT,
            MeetingID INTEGER,
            Rating INTEGER,
            Comments TEXT,
            SubmittedBy TEXT,
            SubmittedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --- AUTO MIGRATIONS ---
    migrations = [
        ("Mentor", "IsActive", "INTEGER DEFAULT 1"),
        ("Mentee", "IsActive", "INTEGER DEFAULT 1"),
        ("Login", "IsActive", "INTEGER DEFAULT 1"),
        ("Meeting", "Status", "TEXT DEFAULT 'Scheduled'"),
        ("Program", "Description", "TEXT"),
        ("Program", "Status", "TEXT DEFAULT 'Active'"),
        ("Feedback", "SubmittedBy", "TEXT"),
    ]

    for table, column, col_type in migrations:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass

    # Ensure default admin exists
    cursor.execute("SELECT * FROM Login WHERE Username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO Login (Username, Password, UserType, IsActive) VALUES ('admin', 'admin123', 'Admin', 1)")

    conn.commit()
    conn.close()

init_admin_tables()

def log_activity(activity):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('INSERT INTO ActivityLog (Activity) VALUES (?)', (activity,))
    conn.commit()
    conn.close()

def admin_required():
    return session.get('user_type') == 'Admin'

# ============================================================
# ADMIN DASHBOARD & MANAGEMENT
# ============================================================

@app.route('/admin')
def admin():
    if not admin_required():
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT MentorID, Name, Email, Expertise, IsActive FROM Mentor WHERE IsActive = 1 ORDER BY Name')
    active_mentors = cursor.fetchall()

    cursor.execute('SELECT MentorID, Name, Email, Expertise, IsActive FROM Mentor WHERE IsActive = 0 ORDER BY Name')
    archived_mentors = cursor.fetchall()

    cursor.execute('SELECT MenteeID, Name, Email, Goal, IsActive FROM Mentee WHERE IsActive = 1 ORDER BY Name')
    active_mentees = cursor.fetchall()

    cursor.execute('SELECT MenteeID, Name, Email, Goal, IsActive FROM Mentee WHERE IsActive = 0 ORDER BY Name')
    archived_mentees = cursor.fetchall()

    cursor.execute('SELECT ProgramID, ProgramName, StartDate, EndDate, Description, Status FROM Program ORDER BY StartDate DESC')
    programs = cursor.fetchall()

    cursor.execute('''
        SELECT
            Meeting.MeetingID,
            Meeting.MeetingDate,
            Mentor.Name,
            Mentee.Name,
            Meeting.Notes,
            Meeting.Status
        FROM Meeting
        INNER JOIN Match ON Meeting.MatchID = Match.MatchID
        INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
        INNER JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
        ORDER BY Meeting.MeetingDate DESC
    ''')
    meetings = cursor.fetchall()

    cursor.execute('''
        SELECT
            Match.MatchID,
            Mentor.Name,
            Mentee.Name,
            COALESCE(Program.ProgramName, 'General') AS ProgramName,
            Match.MatchDate,
            Match.ProgramID,
            Match.MentorID,
            Match.MenteeID
        FROM Match
        INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
        INNER JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
        LEFT JOIN Program ON Match.ProgramID = Program.ProgramID
        ORDER BY Match.MatchDate DESC
    ''')
    matches = cursor.fetchall()

    edit_match_id = request.args.get('edit_match')
    match_to_edit = None
    if edit_match_id:
        cursor.execute('''
            SELECT MatchID, ProgramID, MentorID, MenteeID 
            FROM Match WHERE MatchID = ?
        ''', (edit_match_id,))
        match_to_edit = cursor.fetchone()

    cursor.execute('SELECT Activity, CreatedAt FROM ActivityLog ORDER BY CreatedAt DESC LIMIT 30')
    activities = cursor.fetchall()

    conn.close()

    return render_template(
        'admin.html',
        mentors=active_mentors,
        archived_mentors=archived_mentors,
        mentees=active_mentees,
        archived_mentees=archived_mentees,
        programs=programs,
        meetings=meetings,
        matches=matches,
        match_to_edit=match_to_edit,
        activities=activities
    )

# --- ADMIN PAIR & MATCH ROUTES ---

@app.route('/admin/matches/add', methods=['POST'])
def admin_add_match():
    if not admin_required():
        return redirect(url_for('dashboard'))

    program_id = request.form.get('program_id')
    mentor_id = request.form.get('mentor_id')
    mentee_id = request.form.get('mentee_id')

    if not mentor_id or not mentee_id:
        flash('Both Mentor and Mentee must be selected to pair.', 'danger')
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT MatchID FROM Match 
        WHERE MentorID = ? AND MenteeID = ? AND (ProgramID = ? OR (ProgramID IS NULL AND ? IS NULL))
    ''', (mentor_id, mentee_id, program_id, program_id))

    if cursor.fetchone():
        conn.close()
        flash('This Mentor and Mentee are already paired in the selected program.', 'warning')
        return redirect(url_for('admin'))

    cursor.execute('SELECT Name, Email FROM Mentor WHERE MentorID = ?', (mentor_id,))
    mentor = cursor.fetchone()

    cursor.execute('SELECT Name, Email FROM Mentee WHERE MenteeID = ?', (mentee_id,))
    mentee = cursor.fetchone()

    prog_name = "General Mentorship Program"
    if program_id:
        cursor.execute('SELECT ProgramName FROM Program WHERE ProgramID = ?', (program_id,))
        p_row = cursor.fetchone()
        if p_row:
            prog_name = p_row[0]

    cursor.execute('''
        INSERT INTO Match (ProgramID, MentorID, MenteeID)
        VALUES (?, ?, ?)
    ''', (program_id if program_id else None, mentor_id, mentee_id))

    conn.commit()
    conn.close()

    m_name, m_email = (mentor[0], mentor[1]) if mentor else ('Mentor', '')
    me_name, me_email = (mentee[0], mentee[1]) if mentee else ('Mentee', '')

    log_activity(f'Paired Mentor "{m_name}" with Mentee "{me_name}" in {prog_name}')

    email_body = f"Hello,\n\nYou have been paired in the Mentorship Hub!\n\nProgram: {prog_name}\nMentor: {m_name}\nMentee: {me_name}\n\nLog in to your dashboard to view details and schedule meetings."
    sent_m = send_notification_email(m_email, "Mentorship Hub: New Pairing Assignment", email_body)
    sent_me = send_notification_email(me_email, "Mentorship Hub: New Pairing Assignment", email_body)

    if sent_m and sent_me:
        flash(f'Successfully paired {m_name} with {me_name}. Notification emails sent to both!', 'success')
    elif not SMTP_USER:
        flash(f'Successfully paired {m_name} with {me_name}. (Emails logged to terminal. Configure SMTP in app.py to send live emails).', 'info')
    else:
        flash(f'Paired {m_name} with {me_name}, but email delivery encountered an issue.', 'warning')

    return redirect(url_for('admin'))

@app.route('/admin/matches/<int:match_id>/edit', methods=['POST'])
def admin_edit_match(match_id):
    if not admin_required():
        return redirect(url_for('dashboard'))

    new_program_id = request.form.get('program_id')
    new_mentor_id = request.form.get('mentor_id')
    new_mentee_id = request.form.get('mentee_id')

    if not new_mentor_id or not new_mentee_id:
        flash('Mentor and Mentee selections are required.', 'danger')
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT ProgramID, MentorID, MenteeID FROM Match WHERE MatchID = ?', (match_id,))
    old_match = cursor.fetchone()

    if not old_match:
        conn.close()
        flash('Match not found.', 'danger')
        return redirect(url_for('admin'))

    cursor.execute('''
        UPDATE Match 
        SET ProgramID = ?, MentorID = ?, MenteeID = ?
        WHERE MatchID = ?
    ''', (new_program_id if new_program_id else None, new_mentor_id, new_mentee_id, match_id))

    cursor.execute('SELECT Name, Email FROM Mentor WHERE MentorID = ?', (new_mentor_id,))
    mentor = cursor.fetchone()

    cursor.execute('SELECT Name, Email FROM Mentee WHERE MenteeID = ?', (new_mentee_id,))
    mentee = cursor.fetchone()

    prog_name = "General Mentorship Program"
    if new_program_id:
        cursor.execute('SELECT ProgramName FROM Program WHERE ProgramID = ?', (new_program_id,))
        p_row = cursor.fetchone()
        if p_row:
            prog_name = p_row[0]

    conn.commit()
    conn.close()

    m_name, m_email = (mentor[0], mentor[1]) if mentor else ('Mentor', '')
    me_name, me_email = (mentee[0], mentee[1]) if mentee else ('Mentee', '')

    log_activity(f'Updated Pairing #{match_id}: Mentor "{m_name}", Mentee "{me_name}", Program "{prog_name}"')

    update_email_body = f"Hello,\n\nYour mentorship pairing details have been updated.\n\nUpdated Program: {prog_name}\nMentor: {m_name}\nMentee: {me_name}\n\nPlease check your dashboard for updated information."
    sent_m = send_notification_email(m_email, "Mentorship Hub: Pairing Updated", update_email_body)
    sent_me = send_notification_email(me_email, "Mentorship Hub: Pairing Updated", update_email_body)

    if sent_m and sent_me:
        flash('Pairing updated successfully. Notification emails sent to both!', 'success')
    elif not SMTP_USER:
        flash('Pairing updated successfully. (Emails logged to terminal. Configure SMTP in app.py for live emails).', 'info')
    else:
        flash('Pairing updated. Email delivery encountered an issue.', 'warning')

    return redirect(url_for('admin'))

@app.route('/admin/matches/<int:match_id>/delete', methods=['POST'])
def admin_delete_match(match_id):
    if not admin_required():
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT Mentor.Name, Mentor.Email, Mentee.Name, Mentee.Email, COALESCE(Program.ProgramName, 'General')
        FROM Match
        JOIN Mentor ON Match.MentorID = Mentor.MentorID
        JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
        LEFT JOIN Program ON Match.ProgramID = Program.ProgramID
        WHERE Match.MatchID = ?
    ''', (match_id,))
    match_data = cursor.fetchone()

    if not match_data:
        conn.close()
        flash('Pairing not found.', 'danger')
        return redirect(url_for('admin'))

    m_name, m_email, me_name, me_email, prog_name = match_data

    cursor.execute('DELETE FROM Feedback WHERE MeetingID IN (SELECT MeetingID FROM Meeting WHERE MatchID = ?)', (match_id,))
    cursor.execute('DELETE FROM Meeting WHERE MatchID = ?', (match_id,))
    cursor.execute('DELETE FROM Match WHERE MatchID = ?', (match_id,))

    conn.commit()
    conn.close()

    log_activity(f'Unpaired Mentor "{m_name}" and Mentee "{me_name}"')

    unpair_email_body = f"Hello,\n\nNotice: Your mentorship pairing for '{prog_name}' has been ended by the administrator.\n\nIf you have questions, please contact your program administrator."
    sent_m = send_notification_email(m_email, "Mentorship Hub: Pairing Ended", unpair_email_body)
    sent_me = send_notification_email(me_email, "Mentorship Hub: Pairing Ended", unpair_email_body)

    if sent_m and sent_me:
        flash(f'Successfully unpaired {m_name} and {me_name}. Unpairing emails sent.', 'success')
    elif not SMTP_USER:
        flash(f'Successfully unpaired {m_name} and {me_name}. (Emails logged to terminal. Configure SMTP in app.py for live emails).', 'info')
    else:
        flash(f'Unpaired {m_name} and {me_name}. Email delivery encountered an issue.', 'warning')

    return redirect(url_for('admin'))

# --- ADMIN MENTOR MANAGEMENT ---

@app.route('/admin/mentors/add', methods=['POST'])
def admin_add_mentor():
    if not admin_required():
        return redirect(url_for('dashboard'))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    expertise = request.form.get('expertise', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not name or not email or not username or not password:
        flash('Name, email, username and password are required.', 'danger')
        return redirect(url_for('admin'))

    if not EMAIL_REGEX.match(email):
        flash('Please enter a valid email address.', 'danger')
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            'INSERT INTO Mentor (Name, Email, Expertise, IsActive) VALUES (?, ?, ?, 1)',
            (name, email, expertise)
        )
        mentor_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO Login (Username, Password, UserType, MentorID, IsActive)
            VALUES (?, ?, 'Mentor', ?, 1)
        ''', (username, password, mentor_id))

        conn.commit()
        log_activity(f'Mentor added: {name}')
        flash('Mentor added successfully.', 'success')

    except sqlite3.IntegrityError:
        conn.rollback()
        flash('Username may already exist.', 'danger')

    finally:
        conn.close()

    return redirect(url_for('admin'))

@app.route('/admin/mentors/<int:mentor_id>/delete', methods=['POST'])
def admin_delete_mentor(mentor_id):
    return admin_toggle_mentor_status(mentor_id)

@app.route('/admin/mentors/<int:mentor_id>/toggle-status', methods=['POST'])
def admin_toggle_mentor_status(mentor_id):
    if not admin_required():
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT Name, IsActive FROM Mentor WHERE MentorID = ?', (mentor_id,))
    mentor = cursor.fetchone()

    if not mentor:
        conn.close()
        flash('Mentor not found.', 'danger')
        return redirect(url_for('admin'))

    name, current_status = mentor
    new_status = 0 if current_status == 1 else 1
    action_text = "deactivated (archived)" if new_status == 0 else "reactivated"

    cursor.execute('UPDATE Mentor SET IsActive = ? WHERE MentorID = ?', (new_status, mentor_id))
    cursor.execute('UPDATE Login SET IsActive = ? WHERE MentorID = ? AND UserType = "Mentor"', (new_status, mentor_id))

    conn.commit()
    conn.close()

    log_activity(f'Mentor {action_text}: {name}')
    flash(f'Mentor "{name}" has been {action_text}.', 'success')
    return redirect(url_for('admin'))

# --- ADMIN MENTEE MANAGEMENT ---

@app.route('/admin/mentees/add', methods=['POST'])
def admin_add_mentee():
    if not admin_required():
        return redirect(url_for('dashboard'))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    goal = request.form.get('goal', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not name or not email or not username or not password:
        flash('Name, email, username and password are required.', 'danger')
        return redirect(url_for('admin'))

    if not EMAIL_REGEX.match(email):
        flash('Please enter a valid email address.', 'danger')
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            'INSERT INTO Mentee (Name, Email, Goal, IsActive) VALUES (?, ?, ?, 1)',
            (name, email, goal)
        )
        mentee_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO Login (Username, Password, UserType, MenteeID, IsActive)
            VALUES (?, ?, 'Mentee', ?, 1)
        ''', (username, password, mentee_id))

        conn.commit()
        log_activity(f'Mentee added: {name}')
        flash('Mentee added successfully.', 'success')

    except sqlite3.IntegrityError:
        conn.rollback()
        flash('Username may already exist.', 'danger')

    finally:
        conn.close()

    return redirect(url_for('admin'))

@app.route('/admin/mentees/<int:mentee_id>/delete', methods=['POST'])
def admin_delete_mentee(mentee_id):
    return admin_toggle_mentee_status(mentee_id)

@app.route('/admin/mentees/<int:mentee_id>/toggle-status', methods=['POST'])
def admin_toggle_mentee_status(mentee_id):
    if not admin_required():
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT Name, IsActive FROM Mentee WHERE MenteeID = ?', (mentee_id,))
    mentee = cursor.fetchone()

    if not mentee:
        conn.close()
        flash('Mentee not found.', 'danger')
        return redirect(url_for('admin'))

    name, current_status = mentee
    new_status = 0 if current_status == 1 else 1
    action_text = "deactivated (archived)" if new_status == 0 else "reactivated"

    cursor.execute('UPDATE Mentee SET IsActive = ? WHERE MenteeID = ?', (new_status, mentee_id))
    cursor.execute('UPDATE Login SET IsActive = ? WHERE MenteeID = ? AND UserType = "Mentee"', (new_status, mentee_id))

    conn.commit()
    conn.close()

    log_activity(f'Mentee {action_text}: {name}')
    flash(f'Mentee "{name}" has been {action_text}.', 'success')
    return redirect(url_for('admin'))

# --- PROGRAM & MEETING SETUP & FEEDBACK ---

@app.route('/admin/programs/add', methods=['POST'])
def admin_add_program():
    if not admin_required():
        return redirect(url_for('dashboard'))

    program_name = request.form.get('program_name', '').strip()
    start_date = request.form.get('start_date', '').strip()
    end_date = request.form.get('end_date', '').strip()
    description = request.form.get('description', '').strip()

    if not program_name or not start_date or not end_date:
        flash('Program name, start date, and end date are required.', 'danger')
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        INSERT INTO Program (ProgramName, StartDate, EndDate, Description)
        VALUES (?, ?, ?, ?)
    ''', (program_name, start_date, end_date, description))

    conn.commit()
    conn.close()

    log_activity(f'Program added: {program_name}')
    flash('Program added successfully.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/programs/<int:program_id>/delete', methods=['POST'])
def admin_delete_program(program_id):
    if not admin_required():
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT ProgramName FROM Program WHERE ProgramID = ?', (program_id,))
    program = cursor.fetchone()

    if not program:
        conn.close()
        flash('Program not found.', 'danger')
        return redirect(url_for('admin'))

    program_name = program[0]
    cursor.execute('DELETE FROM Match WHERE ProgramID = ?', (program_id,))
    cursor.execute('DELETE FROM Program WHERE ProgramID = ?', (program_id,))

    conn.commit()
    conn.close()

    log_activity(f'Program deleted: {program_name}')
    flash('Program deleted successfully.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/meetings/add', methods=['POST'])
def admin_add_meeting():
    if not admin_required():
        return redirect(url_for('dashboard'))

    match_id = request.form.get('match_id')
    meeting_date = request.form.get('meeting_date', '').strip()
    notes = request.form.get('notes', '').strip()

    if not match_id or not meeting_date:
        flash('Match and meeting date are required.', 'danger')
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Meeting (MatchID, MeetingDate, Notes, Status)
        VALUES (?, ?, ?, 'Scheduled')
    ''', (match_id, meeting_date, notes))
    conn.commit()

    cursor.execute('''
        SELECT Mentor.Email, Mentee.Email, Mentor.Name, Mentee.Name
        FROM Match
        JOIN Mentor ON Match.MentorID = Mentor.MentorID
        JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
        WHERE Match.MatchID = ?
    ''', (match_id,))
    info = cursor.fetchone()
    conn.close()

    if info:
        m_email, me_email, m_name, me_name = info
        msg_body = f"Hello,\n\nA new meeting has been scheduled between {m_name} and {me_name}.\n\nDate & Time: {meeting_date}\nNotes: {notes}"
        send_notification_email(m_email, "Mentorship Hub: New Meeting Scheduled", msg_body)
        send_notification_email(me_email, "Mentorship Hub: New Meeting Scheduled", msg_body)

    log_activity(f'Meeting scheduled for {meeting_date}')
    flash('Meeting scheduled successfully.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/meetings/<int:meeting_id>/cancel', methods=['POST'])
def admin_cancel_meeting(meeting_id):
    if not admin_required():
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT MeetingDate FROM Meeting WHERE MeetingID = ?', (meeting_id,))
    meeting = cursor.fetchone()

    if not meeting:
        conn.close()
        flash('Meeting not found.', 'danger')
        return redirect(url_for('admin'))

    cursor.execute('UPDATE Meeting SET Status = "Cancelled" WHERE MeetingID = ?', (meeting_id,))
    conn.commit()
    conn.close()

    log_activity(f'Meeting cancelled: {meeting[0]}')
    flash('Meeting cancelled successfully.', 'success')
    return redirect(url_for('admin'))

@app.route('/meetings/<int:meeting_id>/feedback', methods=['POST'])
def submit_feedback(meeting_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    rating = request.form.get('rating')
    comments = request.form.get('comments', '').strip()

    if not rating:
        flash('Please select a star rating.', 'danger')
        return redirect(url_for('meetings'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Feedback (MeetingID, Rating, Comments, SubmittedBy)
        VALUES (?, ?, ?, ?)
    ''', (meeting_id, rating, comments, session.get('user_name')))
    
    cursor.execute('UPDATE Meeting SET Status = "Completed" WHERE MeetingID = ?', (meeting_id,))
    conn.commit()
    conn.close()

    flash('Thank you! Your feedback has been recorded.', 'success')
    return redirect(url_for('meetings'))

# --- GENERAL & DASHBOARD ROUTES ---

@app.route('/')
def home():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if session.get('user_type') == 'Admin':
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if session.get('user_type') == 'Mentor':
        cursor.execute('SELECT Name, Email, Expertise FROM Mentor WHERE MentorID = ?', (session.get('person_id'),))
        profile = cursor.fetchone()

        cursor.execute('''
            SELECT DISTINCT Program.ProgramName, Program.StartDate, Program.EndDate
            FROM Program
            INNER JOIN Match ON Program.ProgramID = Match.ProgramID
            WHERE Match.MentorID = ?
            ORDER BY Program.StartDate
        ''', (session.get('person_id'),))
        programs = cursor.fetchall()

        cursor.execute('''
            SELECT DISTINCT Mentee.Name, Mentee.Goal
            FROM Mentee
            INNER JOIN Match ON Mentee.MenteeID = Match.MenteeID
            WHERE Match.MentorID = ? AND Mentee.IsActive = 1
            ORDER BY Mentee.Name
        ''', (session.get('person_id'),))
        mentees = cursor.fetchall()

        cursor.execute('''
            SELECT Meeting.MeetingID, Meeting.MeetingDate, Mentee.Name, Meeting.Notes, Meeting.Status
            FROM Meeting
            INNER JOIN Match ON Meeting.MatchID = Match.MatchID
            INNER JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
            WHERE Match.MentorID = ?
            ORDER BY Meeting.MeetingDate DESC
        ''', (session.get('person_id'),))
        meetings = cursor.fetchall()

        template = 'mentor_dashboard.html'
    else:
        cursor.execute('SELECT Name, Email, Goal FROM Mentee WHERE MenteeID = ?', (session.get('person_id'),))
        profile = cursor.fetchone()

        cursor.execute('''
            SELECT DISTINCT Program.ProgramName, Program.StartDate, Program.EndDate
            FROM Program
            INNER JOIN Match ON Program.ProgramID = Match.ProgramID
            WHERE Match.MenteeID = ?
            ORDER BY Program.StartDate
        ''', (session.get('person_id'),))
        programs = cursor.fetchall()

        cursor.execute('''
            SELECT DISTINCT Mentor.Name, Mentor.Expertise
            FROM Mentor
            INNER JOIN Match ON Mentor.MentorID = Match.MentorID
            WHERE Match.MenteeID = ? AND Mentor.IsActive = 1
            ORDER BY Mentor.Name
        ''', (session.get('person_id'),))
        mentors = cursor.fetchall()

        cursor.execute('''
            SELECT Meeting.MeetingID, Meeting.MeetingDate, Mentor.Name, Meeting.Notes, Meeting.Status
            FROM Meeting
            INNER JOIN Match ON Meeting.MatchID = Match.MatchID
            INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
            WHERE Match.MenteeID = ?
            ORDER BY Meeting.MeetingDate DESC
        ''', (session.get('person_id'),))
        meetings = cursor.fetchall()

        cursor.execute('''
            SELECT Meeting.MeetingDate, Mentor.Name, Meeting.Notes
            FROM Meeting
            INNER JOIN Match ON Meeting.MatchID = Match.MatchID
            INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
            WHERE Match.MenteeID = ? AND Meeting.Status = 'Scheduled'
            ORDER BY Meeting.MeetingDate ASC
            LIMIT 1
        ''', (session.get('person_id'),))
        next_meeting = cursor.fetchone()

        cursor.execute('''
            SELECT AVG(Feedback.Rating), COUNT(Feedback.FeedbackID)
            FROM Feedback
            INNER JOIN Meeting ON Feedback.MeetingID = Meeting.MeetingID
            INNER JOIN Match ON Meeting.MatchID = Match.MatchID
            WHERE Match.MenteeID = ?
        ''', (session.get('person_id'),))
        feedback_summary = cursor.fetchone()

        cursor.execute('''
            SELECT AchievementType, Title, Organisation, AchievementDate
            FROM Achievement
            WHERE MenteeID = ?
            ORDER BY AchievementDate DESC
        ''', (session.get('person_id'),))
        achievements = cursor.fetchall()

        template = 'dashboard.html'

    conn.close()

    dashboard_data = {
        'user_name': session.get('user_name', ''),
        'profile': profile,
        'programs': programs,
        'meetings': meetings,
    }

    if session.get('user_type') == 'Mentor':
        dashboard_data['mentees'] = mentees
    else:
        dashboard_data['mentors'] = mentors
        dashboard_data['achievements'] = achievements
        dashboard_data['next_meeting'] = next_meeting
        dashboard_data['feedback_summary'] = feedback_summary

    try:
        return render_template(template, **dashboard_data)
    except:
        return render_template('mentee_dashboard.html', **dashboard_data)

@app.route('/mentor_dashboard')
def mentor_dashboard():
    if session.get('user_type') != 'Mentor':
        return redirect(url_for('dashboard'))
    return dashboard()

@app.route('/mentee_dashboard')
def mentee_dashboard():
    if session.get('user_type') != 'Mentee':
        return redirect(url_for('dashboard'))
    return dashboard()

@app.route('/programs')
def programs():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    programs = conn.execute('SELECT ProgramName, StartDate, EndDate, Description, Status FROM Program ORDER BY StartDate DESC').fetchall()
    conn.close()
    return render_template('programs.html', programs=programs)

@app.route('/meetings')
def meetings():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    if session.get('user_type') == 'Mentor':
        query = '''SELECT Meeting.MeetingID, Meeting.MeetingDate, Mentee.Name, Meeting.Notes, Meeting.Status, Feedback.Rating, Feedback.Comments
                   FROM Meeting 
                   INNER JOIN Match ON Meeting.MatchID = Match.MatchID
                   INNER JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
                   LEFT JOIN Feedback ON Meeting.MeetingID = Feedback.MeetingID
                   WHERE Match.MentorID = ? ORDER BY Meeting.MeetingDate DESC'''
    else:
        query = '''SELECT Meeting.MeetingID, Meeting.MeetingDate, Mentor.Name, Meeting.Notes, Meeting.Status, Feedback.Rating, Feedback.Comments
                   FROM Meeting 
                   INNER JOIN Match ON Meeting.MatchID = Match.MatchID
                   INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
                   LEFT JOIN Feedback ON Meeting.MeetingID = Feedback.MeetingID
                   WHERE Match.MenteeID = ? ORDER BY Meeting.MeetingDate DESC'''
    meetings_data = conn.execute(query, (session.get('person_id'),)).fetchall()
    conn.close()
    return render_template('meetings.html', meetings=meetings_data, user_type=session.get('user_type'))

@app.route('/achievements')
def achievements():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    achievements = conn.execute('''
        SELECT AchievementType, Title, Organisation, AchievementDate
        FROM Achievement WHERE MenteeID = ? ORDER BY AchievementDate DESC
    ''', (session.get('person_id'),)).fetchall() if session.get('user_type') == 'Mentee' else []
    conn.close()
    return render_template('achievements.html', achievements=achievements)

@app.route('/achievements/add', methods=['POST'])
def add_achievement():
    if session.get('user_type') != 'Mentee':
        return redirect(url_for('dashboard'))

    ach_type = request.form.get('achievement_type', '').strip()
    title = request.form.get('title', '').strip()
    org = request.form.get('organisation', '').strip()
    ach_date = request.form.get('achievement_date', '').strip()

    if not title or not ach_date:
        flash('Title and date are required.', 'danger')
        return redirect(url_for('achievements'))

    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        INSERT INTO Achievement (MenteeID, AchievementType, Title, Organisation, AchievementDate)
        VALUES (?, ?, ?, ?, ?)
    ''', (session.get('person_id'), ach_type, title, org, ach_date))
    conn.commit()
    conn.close()

    flash('Achievement recorded successfully!', 'success')
    return redirect(url_for('achievements'))

@app.route('/mentees')
def mentees():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if session.get('user_type') != 'Mentor':
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT Mentee.MenteeID, Mentee.Name, Mentee.Email, Mentee.Goal, Mentee.IsActive
        FROM Mentee
        INNER JOIN Match ON Mentee.MenteeID = Match.MenteeID
        WHERE Match.MentorID = ? AND Mentee.IsActive = 1
        ORDER BY Mentee.Name
    ''', (session.get('person_id'),))
    mentee_list = cursor.fetchall()
    conn.close()

    return render_template('mentees.html', mentees=mentee_list)

@app.route('/mentees/add', methods=['POST'])
def add_mentee():
    if session.get('user_type') != 'Mentor':
        return redirect(url_for('dashboard'))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    goal = request.form.get('goal', '').strip()

    if not name or not email:
        flash('Name and email are required.', 'danger')
        return redirect(url_for('mentees'))

    if not EMAIL_REGEX.match(email):
        flash('Please enter a valid email address.', 'danger')
        return redirect(url_for('mentees'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Mentee (Name, Email, Goal, IsActive) VALUES (?, ?, ?, 1)', (name, email, goal))
    mentee_id = cursor.lastrowid
    
    cursor.execute('''
        INSERT INTO Match (ProgramID, MentorID, MenteeID)
        SELECT Match.ProgramID, ?, ?
        FROM Match WHERE Match.MentorID = ? LIMIT 1
    ''', (session.get('person_id'), mentee_id, session.get('person_id')))
    conn.commit()
    conn.close()

    flash('Mentee added successfully.', 'success')
    return redirect(url_for('mentees'))

@app.route('/mentees/<int:mentee_id>/edit', methods=['POST'])
def edit_mentee(mentee_id):
    if session.get('user_type') != 'Mentor':
        return redirect(url_for('dashboard'))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    goal = request.form.get('goal', '').strip()

    if not name or not email:
        flash('Name and email are required.', 'danger')
        return redirect(url_for('mentees'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE Mentee SET Name = ?, Email = ?, Goal = ? WHERE MenteeID = ?', (name, email, goal, mentee_id))
    conn.commit()
    conn.close()

    flash('Mentee updated successfully.', 'success')
    return redirect(url_for('mentees'))

@app.route('/mentees/<int:mentee_id>/delete', methods=['POST'])
def delete_mentee(mentee_id):
    if session.get('user_type') != 'Mentor':
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE Mentee SET IsActive = 0 WHERE MenteeID = ?', (mentee_id,))
    cursor.execute('UPDATE Login SET IsActive = 0 WHERE MenteeID = ? AND UserType = "Mentee"', (mentee_id,))
    conn.commit()
    conn.close()

    flash('Mentee archived successfully.', 'success')
    return redirect(url_for('mentees'))

@app.route('/mentors')
def mentors():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT MentorID, Name, Email, Expertise FROM Mentor WHERE IsActive = 1 ORDER BY Name')
    mentor_list = cursor.fetchall()
    conn.close()

    return render_template('mentors.html', mentors=mentor_list)

@app.route('/mentors/add', methods=['POST'])
def add_mentor():
    if session.get('user_type') != 'Mentor' and session.get('user_type') != 'Admin':
        return redirect(url_for('dashboard'))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    expertise = request.form.get('expertise', '').strip()

    if not name or not email:
        flash('Name and email are required.', 'danger')
        return redirect(url_for('mentors'))

    conn = sqlite3.connect(DB_PATH)
    conn.execute('INSERT INTO Mentor (Name, Email, Expertise, IsActive) VALUES (?, ?, ?, 1)', (name, email, expertise))
    conn.commit()
    conn.close()

    flash('Mentor added successfully.', 'success')
    return redirect(url_for('mentors'))

@app.route('/mentors/<int:mentor_id>/edit', methods=['POST'])
def edit_mentor(mentor_id):
    if session.get('user_type') != 'Mentor' and session.get('user_type') != 'Admin':
        return redirect(url_for('dashboard'))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    expertise = request.form.get('expertise', '').strip()

    if not name or not email:
        flash('Name and email are required.', 'danger')
        return redirect(url_for('mentors'))

    conn = sqlite3.connect(DB_PATH)
    conn.execute('UPDATE Mentor SET Name = ?, Email = ?, Expertise = ? WHERE MentorID = ?', (name, email, expertise, mentor_id))
    conn.commit()
    conn.close()

    flash('Mentor updated successfully.', 'success')
    return redirect(url_for('mentors'))

@app.route('/mentors/<int:mentor_id>/delete', methods=['POST'])
def delete_mentor(mentor_id):
    if session.get('user_type') != 'Mentor' and session.get('user_type') != 'Admin':
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE Mentor SET IsActive = 0 WHERE MentorID = ?', (mentor_id,))
    cursor.execute('UPDATE Login SET IsActive = 0 WHERE MentorID = ? AND UserType = "Mentor"', (mentor_id,))
    conn.commit()
    conn.close()

    flash('Mentor archived successfully.', 'success')
    return redirect(url_for('mentors'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/students')
def students():
    return render_template('students.html')

@app.route('/teachers')
def teachers():
    return render_template('teachers.html')

@app.route('/subjects')
def subjects():
    return render_template('subjects.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            error = 'Username and password are required.'
        else:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''SELECT LoginID, Username, Password, UserType, MentorID, MenteeID, IsActive FROM Login WHERE Username = ?''', (username,))
            account = cursor.fetchone()

            if not account:
                error = 'Wrong username.'
            elif account[6] == 0:
                error = 'Your account has been deactivated. Please contact the administrator.'
            elif account[2] != password and not check_password_hash(account[2], password):
                error = 'Wrong password.'
            else:
                session['user_type'] = account[3]

                if account[3] == 'Mentor':
                    session['person_id'] = account[4]
                elif account[3] == 'Mentee':
                    session['person_id'] = account[5]
                else:
                    session['person_id'] = None

                if account[3] == 'Mentor':
                    cursor.execute('SELECT Name FROM Mentor WHERE MentorID = ?', (session['person_id'],))
                elif account[3] == 'Mentee':
                    cursor.execute('SELECT Name FROM Mentee WHERE MenteeID = ?', (session['person_id'],))
                else:
                    person = None

                if account[3] != 'Admin':
                    person = cursor.fetchone()
                
                session['user_name'] = person[0] if (account[3] != 'Admin' and person) else account[1]
                conn.close()
                
                if account[3] == 'Admin':
                    return redirect(url_for('admin'))
                elif account[3] == 'Mentor':
                    return redirect(url_for('mentor_dashboard'))
                else:
                    return redirect(url_for('mentee_dashboard'))

            conn.close()
    
    return render_template('login.html', error=error)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
