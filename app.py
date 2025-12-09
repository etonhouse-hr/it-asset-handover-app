import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_mail import Mail, Message
from config import Config
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

app = Flask(__name__)
app.config.from_object(Config)

mail = Mail(app)

# Initialize DB
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS handover (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            employee_name TEXT,
            iqama TEXT,
            job_title TEXT,
            department TEXT,
            asset_receipt_date TEXT,
            return_date TEXT,
            notes TEXT,
            item_name TEXT,
            model TEXT,
            serial TEXT,
            color TEXT,
            condition TEXT,
            accessories TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


@app.route("/", methods=["GET", "POST"])
def asset_form():
    if request.method == "POST":
        data = {k: request.form.get(k) for k in request.form.keys()}

        # Save submission to database
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO handover (
                date, employee_name, iqama, job_title, department,
                asset_receipt_date, return_date, notes,
                item_name, model, serial, color, condition, accessories
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("date"),
            data.get("employee_name"),
            data.get("iqama"),
            data.get("job_title"),
            data.get("department"),
            data.get("asset_receipt_date"),
            data.get("return_date"),
            data.get("notes"),
            data.get("item_name"),
            data.get("model"),
            data.get("serial"),
            data.get("color"),
            data.get("condition"),
            data.get("accessories")
        ))
        conn.commit()
        conn.close()

        return render_template("submitted.html")

    return render_template("form.html")


@app.route("/records")
def records():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM handover ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return render_template("records.html", rows=rows)


@app.route("/record/<int:record_id>/pdf")
def generate_pdf(record_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM handover WHERE id=?", (record_id,))
    r = c.fetchone()
    conn.close()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2 * cm, height - 2 * cm, "IT Asset Handover Form")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(2 * cm, height - 2.8 * cm, f"Record ID: {r[0]}")
    pdf.drawString(2 * cm, height - 3.4 * cm, f"Date: {r[1]}")

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2 * cm, height - 4.4 * cm, "Employee Information")

    emp_data = [
        ["Employee Name", r[2]],
        ["ID / Iqama Number", r[3]],
        ["Job Title", r[4]],
        ["Department", r[5]],
        ["Asset Receipt Date", r[6]],
        ["Return Date", r[7]],
        ["Notes", r[8]],
    ]

    table = Table(emp_data, colWidths=[6 * cm, 10 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    table.wrapOn(pdf, width, height)
    table.drawOn(pdf, 2 * cm, height - 12 * cm)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2 * cm, height - 13 * cm, "Asset Information")

    asset_data = [
        ["Item Name", r[9]],
        ["Model", r[10]],
        ["Serial Number", r[11]],
        ["Color", r[12]],
        ["Condition", r[13]],
        ["Accessories", r[14]],
    ]

    table2 = Table(asset_data, colWidths=[6 * cm, 10 * cm])
    table2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    table2.wrapOn(pdf, width, height)
    table2.drawOn(pdf, 2 * cm, height - 21 * cm)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2 * cm, height - 22 * cm, "Employee Acknowledgment")

    text = pdf.beginText(2 * cm, height - 23 * cm)
    text.setFont("Helvetica", 10)
    ack = (
        "I acknowledge receiving the above IT asset(s) in good working condition.\n"
        "I agree to safeguard the equipment, use it only for work purposes, and return it "
        "upon request or when leaving the organization.\n\n"
        "In case of loss, misuse, or damage caused by negligence, I accept full responsibility."
    )
    for line in ack.split("\n"):
        text.textLine(line)
    pdf.drawText(text)

    pdf.drawString(2 * cm, height - 27 * cm, "Employee Signature: ____________________________")
    pdf.drawString(2 * cm, height - 28 * cm, "IT Department: ________________________________")

    pdf.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name=f"handover_{record_id}.pdf",
                     mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True)
