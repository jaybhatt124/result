import streamlit as st
import sqlite3
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# =========================================================
# 🔧 CONFIG
# =========================================================
TEACHER_CODE = "1234"
GOOGLE_CREDENTIALS = "credentials.json"

# =========================================================
# 🗄️ DATABASE
# =========================================================
def get_db():
    conn = sqlite3.connect("results.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment TEXT,
            name TEXT,
            department TEXT,
            semester INTEGER,
            subject TEXT,
            marks INTEGER,
            exam_name TEXT,
            academic_year TEXT
        )
    """)

    return conn

# =========================================================
# 📊 GOOGLE SHEET READER
# =========================================================
def read_sheet(sheet_url):

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        GOOGLE_CREDENTIALS,
        scope
    )

    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).sheet1

    headers = [h.strip().lower() for h in sheet.row_values(1)]
    rows = sheet.get_all_records()

    return headers, rows

# =========================================================
# 🎨 UI CONFIG
# =========================================================
st.set_page_config(
    page_title="Result Viewing System",
    page_icon="🎓",
    layout="centered"
)

st.title("🎓 Student Result Viewing System")

menu = st.sidebar.selectbox(
    "Select Portal",
    ["Student Portal", "Teacher Portal"]
)

db = get_db()

# =========================================================
# 📚 DROPDOWN DATA
# =========================================================
departments = [
    "-- Select Department --",
    "COMPUTER",
    "IT",
    "ELECTRICAL",
    "CIVL",
    "MECHANICAL",
    "CDDM",
    "AUTOMOBILE"
]

semesters = [
    "-- Select Sem --",
    1,2,3,4,5,6,7,8
]

# =========================================================
# 🎓 STUDENT PORTAL
# =========================================================
if menu == "Student Portal":

    st.header("📄 View Your Result")

    enrollment = st.text_input("Enrollment Number")

    department = st.selectbox(
        "Select Department",
        departments
    )

    semester = st.selectbox(
        "Select Semester",
        semesters
    )

    if st.button("View Result"):

        if (
            department == "-- Select Department --"
            or semester == "-- Select Sem --"
            or enrollment == ""
        ):
            st.error("Please fill all fields")
            st.stop()

        cur = db.cursor()

        cur.execute("""
            SELECT * FROM results
            WHERE enrollment = ?
            AND semester = ?
            AND department = ?
        """, (enrollment, semester, department))

        rows = cur.fetchall()

        if rows:

            info = dict(rows[0])

            st.success("✅ Result Found")

            # Student Info
            st.subheader("Student Information")
            st.write(f"**Name:** {info['name']}")
            st.write(f"**Enrollment:** {info['enrollment']}")
            st.write(f"**Department:** {info['department']}")
            st.write(f"**Semester:** {info['semester']}")
            st.write(f"**Exam:** {info['exam_name']}")
            st.write(f"**Academic Year:** {info['academic_year']}")

            # Marks Table
            marks = {
                r["subject"]: r["marks"]
                for r in rows
            }

            df = pd.DataFrame(
                marks.items(),
                columns=["Subject", "Marks"]
            )

            st.subheader("📊 Marks")
            st.table(df)

        else:
            st.error("❌ No result found")

# =========================================================
# 👨‍🏫 TEACHER PORTAL
# =========================================================
else:

    st.header("🧑‍🏫 Teacher Result Upload")

    code = st.text_input(
        "Enter Teacher Code",
        type="password"
    )

    if code != TEACHER_CODE:
        st.warning("Enter valid teacher code to continue")
        st.stop()

    st.success("Access Granted ✅")

    # Dropdowns
    department = st.selectbox(
        "Select Department",
        departments
    )

    semester = st.selectbox(
        "Select Semester",
        semesters
    )

    sheet_url = st.text_input("Google Sheet URL")

    if st.button("Upload / Update Result"):

        # Validation
        if (
            department == "-- Select Department --"
            or semester == "-- Select Sem --"
            or sheet_url == ""
        ):
            st.error("Please fill all fields")
            st.stop()

        try:
            headers, rows = read_sheet(sheet_url)

            IGNORE_COLS = {
                "enrollment",
                "name",
                "department",
                "exam_name",
                "academic_year"
            }

            subjects = [
                h for h in headers
                if h not in IGNORE_COLS
            ]

            cur = db.cursor()

            # Delete old data
            cur.execute("""
                DELETE FROM results
                WHERE department = ?
                AND semester = ?
            """, (department, semester))

            # Insert new
            for row in rows:
                for sub in subjects:

                    cur.execute("""
                        INSERT INTO results
                        (enrollment, name, department,
                         semester, subject, marks,
                         exam_name, academic_year)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row["enrollment"],
                        row["name"],
                        department,
                        semester,
                        sub,
                        int(row.get(sub, 0)),
                        row["exam_name"],
                        row["academic_year"]
                    ))

            db.commit()

            st.success("✅ Result Uploaded Successfully")

        except Exception as e:
            import traceback
            st.error("❌ Upload Failed")
            st.text(traceback.format_exc())
