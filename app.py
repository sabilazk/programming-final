
import streamlit as st
import datetime
import calendar
import smtplib
from email.mime.text import MIMEText
from typing import List, Dict
import re

st.set_page_config(page_title="Study Organizer", layout="wide")

# ---------------------------
# SESSION STATE INITIALIZE
# ---------------------------
if "schedule" not in st.session_state:
    
    st.session_state.schedule = {
        "Monday": [],
        "Tuesday": [],
        "Wednesday": [],
        "Thursday": [],
        "Friday": [],
        "Saturday": [],
        "Sunday": []
    }

if "tasks" not in st.session_state:
   
    st.session_state.tasks = []

if "email_config" not in st.session_state:
    st.session_state.email_config = {"sender": "", "password": "", "to": ""}


# ---------------------------
# UTIL FUNCTIONS
# ---------------------------
def parse_start_time(time_str: str):
    """
    Try to extract a starting time (hh:mm) from a time string like '07:50-09:30' or '07:50–09:30' or '10:00'.
    Returns tuple (hour, minute) or large value if not found to push to bottom.
    """
    if not time_str:
        return (99, 99)
    
    m = re.search(r"([01]?\d|2[0-3])[:\.]([0-5]\d)", time_str)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (99, 99)


def send_email(subject: str, body: str):
    sender = st.session_state.email_config.get("sender", "")
    password = st.session_state.email_config.get("password", "")
    to = st.session_state.email_config.get("to", "")

    if not (sender and password and to):
        return False, "Email not configured."

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
        server.login(sender, password)
        server.sendmail(sender, [to], msg.as_string())
        server.quit()
        return True, "Email sent."
    except Exception as e:
        return False, f"Email error: {e}"


def check_and_notify_tasks():
    """
    Check tasks for upcoming deadlines (<= 2 days), produce in-app notifications
    and send email for tasks not yet 'notified'.
    """
    today = datetime.date.today()
    notifications = []
    for t in st.session_state.tasks:
        if t.get("done"):
            continue
        delta = (t["deadline"] - today).days
        if delta <= 2:
            notifications.append(f"'{t['title']}' deadline dalam {delta} hari (deadline: {t['deadline']})")
            if not t.get("notified"):
                
                subject = "Reminder Tugas — Study Organizer"
                body = f"Reminder: Tugas '{t['title']}' akan deadline pada {t['deadline']}.\n\nIni email otomatis dari Study Organizer."
                ok, msg = send_email(subject, body)
                
                t["notified"] = True
                if not ok:
                    
                    notifications.append(f" Email gagal dikirim: {msg}")
    return notifications


def weekday_name_from_date(dt: datetime.date):
    return dt.strftime("%A") 


# ---------------------------
# UI Title & sidebar
# ---------------------------
st.title("Study Organizer")
st.write("Manage weekly classes (by day), tasks with deadlines, see calendar and weekly table.")

menu = st.sidebar.radio(
    "Menu",
    ["Weekly Table", "Manage Classes", "Tasks & Deadlines", "Calendar", "Email Settings"]
)

st.sidebar.markdown("---")
st.sidebar.write("Tips: untuk notifikasi email gunakan Gmail App Password (2FA+App Password).")


# ===========================
# PAGE: WEEKLY TABLE (All Week)
# ===========================
if menu == "Weekly Table":
    st.header("Weekly Table")
    
    times = set()
    for day_items in st.session_state.schedule.values():
        for item in day_items:
            times.add(item.get("time", "").strip())

    
    sorted_times = sorted(times, key=lambda s: parse_start_time(s))
    
    if not sorted_times:
        st.info("Belum ada jadwal. Tambah mata kuliah di menu 'Manage Classes'.")
    else:
        
        import pandas as pd
        columns = ["Time"] + list(st.session_state.schedule.keys())  
        rows = []
        for t in sorted_times:
            row = {"Time": t}
            for day in st.session_state.schedule.keys():
                
                matches = [f"{c['course']} ({c['room']})" if c.get("room") else c['course']
                           for c in st.session_state.schedule[day] if c.get("time", "").strip() == t]
                row[day] = "\n".join(matches)
            rows.append(row)
        df = pd.DataFrame(rows, columns=columns)
        
        st.subheader("Weekly Schedule Table")
        st.table(df)


# ===========================
# PAGE: Manage Classes
# ===========================
elif menu == "Manage Classes":
    st.header("Manage Weekly Classes")

    col_add, col_view = st.columns([1, 1])
    with col_add:
        st.subheader("Add Class")
        day = st.selectbox("Day", list(st.session_state.schedule.keys()), key="add_day_select")
        course = st.text_input("Course name", key="add_course_input")
        room = st.text_input("Room (e.g. C212 / Online)", key="add_room_input")
        time = st.text_input("Time (e.g. 07:50–09:30)", key="add_time_input")
        if st.button("Add Class", key="add_class_btn"):
            if not course.strip():
                st.error("Course name cannot be empty.")
            else:
                st.session_state.schedule[day].append({
                    "course": course.strip(),
                    "room": room.strip() or "—",
                    "time": time.strip() or "—"
                })
                st.success(f"Added '{course}' to {day}.")
                
                st.experimental_rerun()

    with col_view:
        st.subheader("View Day Schedule")
        day_view = st.selectbox("Choose day to preview", list(st.session_state.schedule.keys()), key="preview_day_select")
        items = st.session_state.schedule[day_view]
        if not items:
            st.info("No classes on this day.")
        else:
            for idx, it in enumerate(items):
                st.write(f"- **{it['time']}** — {it['course']}  ({it['room']})")

    st.write("---")
    st.subheader("Delete Class")
    del_day = st.selectbox("Choose day to delete from", list(st.session_state.schedule.keys()), key="del_day_select")
    if st.session_state.schedule[del_day]:
        formatted = [f"{it['time']} — {it['course']} ({it['room']})" for it in st.session_state.schedule[del_day]]
        del_idx = st.selectbox("Pick class to delete", list(range(len(formatted))), format_func=lambda i: formatted[i], key="del_idx_select")
        if st.button("Delete Selected Class", key="delete_class_btn"):
            st.session_state.schedule[del_day].pop(del_idx)
            st.success("Class deleted.")
            st.experimental_rerun()
    else:
        st.info("No class to delete on selected day.")


# ===========================
# PAGE: Tasks & Deadlines
# ===========================
elif menu == "Tasks & Deadlines":
    st.header("Tasks & Deadlines")

    
    with st.form("add_task_form", clear_on_submit=True):
        t_name = st.text_input("Task title", key="task_title_input")
        t_deadline = st.date_input("Deadline", value=datetime.date.today(), key="task_deadline_input")
        submitted = st.form_submit_button("Add Task")
        if submitted:
            if not t_name.strip():
                st.error("Task title cannot be empty.")
            else:
                st.session_state.tasks.append({
                    "title": t_name.strip(),
                    "deadline": t_deadline,
                    "done": False,
                    "notified": False
                })
                st.success("Task added.")
                st.experimental_rerun()

    st.write("---")
    st.subheader("Task List (Checklist)")
    if not st.session_state.tasks:
        st.info("No tasks yet.")
    else:
        
        st.session_state.tasks.sort(key=lambda x: x["deadline"])
        for i, task in enumerate(list(st.session_state.tasks)):
            cols = st.columns([4, 1, 1, 1])
            with cols[0]:
                status = "✅" if task["done"] else "❗"
                st.markdown(f"**{task['title']}** — _{task['deadline']}_  {status}")
            with cols[1]:
                done_val = st.checkbox("Done", value=task["done"], key=f"task_done_{i}")
                if done_val != task["done"]:
                    task["done"] = done_val
                    st.experimental_rerun()
            with cols[2]:
                if st.button("Delete", key=f"task_delete_{i}"):
                    st.session_state.tasks.pop(i)
                    st.success("Task deleted.")
                    st.experimental_rerun()
            with cols[3]:
                days_left = (task["deadline"] - datetime.date.today()).days
                if days_left < 0:
                    st.write("Late")
                else:
                    st.write(f"{days_left}d")


# ===========================
# PAGE: Calendar (Month Grid)
# ===========================
elif menu == "Calendar":
    st.header("Calendar View — Classes & Tasks")

    
    colm1, colm2 = st.columns([2, 1])
    with colm1:
        sel_year = st.selectbox("Year", [datetime.date.today().year - 1, datetime.date.today().year, datetime.date.today().year + 1], index=1, key="cal_year")
        sel_month = st.selectbox("Month", list(range(1, 13)), index=datetime.date.today().month - 1, format_func=lambda m: calendar.month_name[m], key="cal_month")
    with colm2:
        st.write(" ")

    year = int(sel_year)
    month = int(sel_month)

    
    cal = calendar.Calendar(firstweekday=0) 
    month_days = cal.monthdayscalendar(year, month)  

    
    events_by_date = {} 
    days_in_month = [d for week in month_days for d in week if d != 0]
    for d in days_in_month:
        dt = datetime.date(year, month, d)
        events_by_date[dt] = []

    
    for dt in list(events_by_date.keys()):
        weekday_name = dt.strftime("%A")  
        classes = st.session_state.schedule.get(weekday_name, [])
        for c in classes:
           
            text = f"{c.get('time','-')} {c.get('course','-')} ({c.get('room','-')})"
            events_by_date[dt].append(("class", text))

    
    for task in st.session_state.tasks:
        dt = task["deadline"]
        if dt in events_by_date:
            events_by_date[dt].append(("task", f"Deadline: {task['title']}"))

    
    st.markdown("""
    <style>
    .calendar-table {
        border-collapse: collapse;
        width: 100%;
    }
    .calendar-table th {
        padding: 8px;
        background: #f0f6ff;
        border: 1px solid #d0e3ff;
        font-weight: 600;
    }
    .calendar-table td {
        padding: 8px;
        border: 1px solid #e6eefc;
        vertical-align: top;
        height: 110px;
    }
    .date-number {
        font-weight: 700;
        margin-bottom: 6px;
    }
    .class-event {
        background: #E8F6FF;
        padding: 4px;
        margin-bottom: 4px;
        border-radius: 4px;
        font-size: 13px;
    }
    .task-event {
        background: #FFF3CD;
        padding: 4px;
        margin-bottom: 4px;
        border-radius: 4px;
        font-size: 13px;
    }
    .today {
        border: 2px solid #6fb3ff;
    }
    </style>
    """, unsafe_allow_html=True)

    
    html = "<table class='calendar-table'>"
   
    headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    html += "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"

    today = datetime.date.today()
    for week in month_days:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td></td>"
            else:
                dt = datetime.date(year, month, day)
                classes_and_tasks = events_by_date.get(dt, [])
                
                extra_class = "today" if dt == today else ""
                cell_html = f"<div class='{extra_class}'><div class='date-number'>{day}</div>"
                
                for typ, txt in classes_and_tasks[:6]:
                    safe_txt = txt.replace("<", "&lt;").replace(">", "&gt;")
                    if typ == "class":
                        cell_html += f"<div class='class-event'>{safe_txt}</div>"
                    else:
                        cell_html += f"<div class='task-event'>{safe_txt}</div>"
                
                if len(classes_and_tasks) > 6:
                    cell_html += f"<div style='font-size:12px;color:#666'>+{len(classes_and_tasks)-6} more</div>"
                cell_html += "</div>"
                html += f"<td>{cell_html}</td>"
        html += "</tr>"
    html += "</table>"

    st.markdown(html, unsafe_allow_html=True)

    st.write("---")
    st.subheader("Day details")
    
    sel_day = st.date_input("Select date to view details", value=today, key="select_calendar_date")
   
    details = events_by_date.get(sel_day, [])
    if not details:
        st.info("No events on this date.")
    else:
        for typ, txt in details:
            if typ == "class":
                st.success(f"Class: {txt}")
            else:
                st.warning(f"Task: {txt}")


# ===========================
# PAGE: Email Settings
# ===========================
elif menu == "Email Settings":
    st.header("Email Reminder Settings")
    st.write("Fill your Gmail and App Password (from Google Account > Security > App passwords).")
    st.session_state.email_config["sender"] = st.text_input("Sender Gmail (example@gmail.com)", value=st.session_state.email_config.get("sender",""), key="email_sender")
    st.session_state.email_config["password"] = st.text_input("Gmail App Password", type="password", value=st.session_state.email_config.get("password",""), key="email_password")
    st.session_state.email_config["to"] = st.text_input("Recipient Email", value=st.session_state.email_config.get("to",""), key="email_to")

    if st.button("Save Email Settings", key="save_email_btn"):
        st.success("Email settings saved to session state.")


# ===========================
# Always show notifications at bottom (in-app)
# ===========================
st.write("---")
st.subheader("Notifications")
notifs = check_and_notify_tasks()
if notifs:
    for n in notifs:
        st.error(n)
else:
    st.info("No urgent tasks within 2 days.")


