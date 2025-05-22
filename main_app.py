import sys
import os
import re
import csv
import datetime
import fitz  # PyMuPDF
from collections import defaultdict, Counter
from statistics import mean
from cashew_csv_export import export_for_cashew
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QMessageBox, QCheckBox, QLineEdit, QDialog, QDialogButtonBox, QHBoxLayout
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

START_OF_RECORD_MARKER = re.compile(r'^[A-Z][a-z][a-z]\s\d{2},\s20\d{2}$')

class PhonePeTxn:
    def __init__(self, date, time, payee, txn_id, utr_no, payer, kind, amount):
        self.date = date
        self.time = time
        self.payee = payee
        self.txn_id = txn_id
        self.utr_no = utr_no
        self.payer = payer
        self.kind = kind
        self.amount = amount


    def to_row(self):
        return [self.date, self.time, self.payee, self.txn_id, self.utr_no, self.payer, self.kind, self.amount]
def get_output_path(pdf_path, suffix=".csv"):
    app_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(app_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.basename(pdf_path).replace(".pdf", suffix)
    return os.path.join(output_dir, base_name)

def extract_text_from_pdf(pdf_path, password=None):
    try:
        with fitz.open(pdf_path) as doc:
            if doc.needs_pass:
                if not password or not doc.authenticate(password):
                    raise RuntimeError("Password required or incorrect password.")
            text = ""
            for page in doc:
                text += page.get_text()
            return text
    except Exception as e:
        raise e

def parse_transactions(text):
    lines = text.strip().split('\n')
    records = []
    rec = []
    txns = []

    for l in lines:
        if START_OF_RECORD_MARKER.match(l):
            if rec:
                txn = try_all_parsers(rec)
                if txn:
                    txns.append(txn)
            rec = [l]
        else:
            rec.append(l)

    if rec:
        txn = try_all_parsers(rec)
        if txn:
            txns.append(txn)

    return txns

def try_all_parsers(rec):
    for parser in [mk_record_v1, mk_record_v2]:
        txn = parser(rec)
        if txn:
            return txn
    return None

def mk_record_v1(r):
    try:
        if len(r) < 8:
            return None
        # Check if r[2] is a known kind and r[3] starts with ₹ or is numeric
        if not r[3].lstrip().startswith("₹") and not r[3].replace(",", "").strip().replace(".", "").isdigit():
            return None
        dt = datetime.datetime.strptime(r[0] + " " + r[1], "%b %d, %Y %I:%M %p")
        kind = r[2].strip()
        amount_str = "₹" + r[3].replace("₹", "").replace(",", "").strip()
        payee = r[4].strip()
        txn_id = r[5].split()[-1] if len(r) > 5 else ""
        utr_no = "\t" + r[6].split()[-1] if len(r) > 6 else ""
        payer = r[8] if len(r) > 8 else ""
        return PhonePeTxn(
            date=dt.strftime("%Y-%m-%d"),
            time=dt.strftime("%I:%M %p"),
            payee=payee,
            txn_id=txn_id,
            utr_no=utr_no,
            payer=payer,
            kind=kind,
            amount=amount_str
        )
    except Exception:
        return None

def mk_record_v2(r):
    try:
        if len(r) < 8:
            return None
        if not any(keyword in r[2] for keyword in ["Paid to", "Received from", "Refund", "Payment to"]):
            return None

        dt = datetime.datetime.strptime(r[0] + " " + r[1], "%b %d, %Y %I:%M %p")
        payee = r[2].strip()
        txn_id = r[3].split()[-1]
        utr_no = "\t" + r[4].split()[-1]
        payer = r[5].strip()
        kind = r[6].strip()
        amount_line = r[8].strip() if len(r) > 8 and r[7].strip().endswith("INR") else r[7].strip()
        match = re.search(r'[\d,]+(?:\.\d+)?', amount_line)
        amount_val = float(match.group().replace(',', '')) if match else 0.0
        amount_str = f"₹{amount_val:.2f}"

        return PhonePeTxn(
            date=dt.strftime("%Y-%m-%d"),
            time=dt.strftime("%I:%M %p"),
            payee=payee,
            txn_id=txn_id,
            utr_no=utr_no,
            payer=payer,
            kind=kind,
            amount=amount_str
        )
    except Exception:
        return None

def write_csv(txns, output_file):
    with open(output_file, 'w', newline='', encoding='utf-8') as fo:
        writer = csv.writer(fo)
        writer.writerow(["Date", "Time", "Payee", "Transaction ID", "UTR No.", "Payer", "Type", "Amount"])
        for txn in txns:
            writer.writerow(txn.to_row())

def write_grouped_csv(txns, output_file):
    grouped = defaultdict(lambda: {"count": 0, "amount": 0.0})
    debit_amounts = defaultdict(float)
    credit_amounts = defaultdict(float)
    daily_spending = defaultdict(float)
    weekly_spending = defaultdict(float)
    monthly_spending = defaultdict(float)

    for txn in txns:
        amt = float(txn.amount.replace("₹", ""))
        key = (txn.kind, txn.payee)
        grouped[key]["count"] += 1
        grouped[key]["amount"] += amt

        if txn.kind == "DEBIT":
            debit_amounts[txn.payee] += amt
            daily_spending[txn.date] += amt
            week = datetime.datetime.strptime(txn.date, "%Y-%m-%d").isocalendar().week
            week_key = f"{txn.date[:4]}-W{week}"
            weekly_spending[week_key] += amt
            month_key = txn.date[:7]  # yyyy-mm
            monthly_spending[month_key] += amt
        elif txn.kind == "CREDIT":
            credit_amounts[txn.payee] += amt

    most_spent_to = max(debit_amounts.items(), key=lambda x: x[1], default=("None", 0))
    most_received_from = max(credit_amounts.items(), key=lambda x: x[1], default=("None", 0))
    most_spent_day = max(daily_spending.items(), key=lambda x: x[1], default=("None", 0))

    avg_day = mean(daily_spending.values()) if daily_spending else 0
    avg_week = mean(weekly_spending.values()) if weekly_spending else 0
    avg_month = mean(monthly_spending.values()) if monthly_spending else 0

    with open(output_file, 'w', newline='', encoding='utf-8') as fo:
        writer = csv.writer(fo)
        writer.writerow(["Type", "Payee", "Count", "Total Amount (₹)"])
        for (kind, payee), stats in grouped.items():
            writer.writerow([kind, payee, stats["count"], f"₹{stats['amount']:.2f}"])

        writer.writerow([])
        writer.writerow(["Summary"])
        writer.writerow(["Most Amount Sent To", most_spent_to[0], f"₹{most_spent_to[1]:.2f}"])
        writer.writerow(["Most Amount Received From", most_received_from[0], f"₹{most_received_from[1]:.2f}"])
        writer.writerow(["Most Spent Day", most_spent_day[0], f"₹{most_spent_day[1]:.2f}"])
        writer.writerow(["Average Daily Spend", f"₹{avg_day:.2f}"])
        writer.writerow(["Average Weekly Spend", f"₹{avg_week:.2f}"])
        writer.writerow(["Average Monthly Spend", f"₹{avg_month:.2f}"])

class PasswordDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enter PDF Password")
        self.setFixedSize(300, 120)

        layout = QVBoxLayout()
        self.label = QLabel("PDF is password protected. Enter password:")
        self.label.setFont(QFont("Helvetica", 10))
        layout.addWidget(self.label)

        self.input_line = QLineEdit()
        self.input_line.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.input_line)

        toggle_layout = QHBoxLayout()
        self.toggle_btn = QPushButton("Show")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self.toggle_password)
        toggle_layout.addWidget(self.toggle_btn)
        toggle_layout.addStretch()
        layout.addLayout(toggle_layout)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def toggle_password(self):
        if self.toggle_btn.isChecked():
            self.input_line.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setText("Hide")
        else:
            self.input_line.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setText("Show")

    def get_password(self):
        return self.input_line.text()

class PhonePeApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PhonePe PDF to CSV Converter")
        self.setFixedSize(500, 360)
        self.pdf_path = None

        layout = QVBoxLayout()

        self.title_label = QLabel("PhonePe PDF to CSV Converter")
        self.title_label.setFont(QFont("Helvetica", 16, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        self.select_btn = QPushButton("Select PhonePe PDF")
        self.select_btn.setFont(QFont("Helvetica", 12))
        self.select_btn.clicked.connect(self.select_pdf)
        layout.addWidget(self.select_btn)

        self.group_checkbox = QCheckBox("Generate grouped summary CSV")
        self.group_checkbox.setFont(QFont("Helvetica", 11))
        layout.addWidget(self.group_checkbox)

        self.cashew_checkbox = QCheckBox("Import data in Cashew App")
        self.cashew_checkbox.setFont(QFont("Helvetica", 11))
        layout.addWidget(self.cashew_checkbox)

        self.convert_btn = QPushButton("Convert to CSV")
        self.convert_btn.setFont(QFont("Helvetica", 12))
        self.convert_btn.clicked.connect(self.convert_to_csv)
        layout.addWidget(self.convert_btn)

        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Helvetica", 10))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def select_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if path:
            self.pdf_path = path
            self.status_label.setText(f"Selected: {os.path.basename(path)}")

    def convert_to_csv(self):
        if not self.pdf_path:
            QMessageBox.critical(self, "Error", "Please select a PDF file first.")
            return

        try:
            password = None
            try:
                text = extract_text_from_pdf(self.pdf_path)
            except RuntimeError:
                dlg = PasswordDialog()
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    password = dlg.get_password()
                    text = extract_text_from_pdf(self.pdf_path, password)
                else:
                    return

            txns = parse_transactions(text)
            if not txns:
                raise ValueError("No transactions found.")

            out_file = get_output_path(self.pdf_path, ".csv")
            write_csv(txns, out_file)

            grouped_file = None
            if self.group_checkbox.isChecked():
                grouped_file = get_output_path(self.pdf_path, "_grouped.csv")
                write_grouped_csv(txns, grouped_file)

            if self.cashew_checkbox.isChecked():
                cashew_file = export_for_cashew(txns,
                                                os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"))
                QMessageBox.information(self, "Cashew Export", f"Cashew App file created:\n{cashew_file}")

            msg = f"CSV created: {out_file}"
            if grouped_file:
                msg += f"\nGrouped CSV: {grouped_file}"

            QMessageBox.information(self, "Success", msg)

        except Exception as e:
            QMessageBox.critical(self, "Failed", str(e))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PhonePeApp()
    window.show()
    sys.exit(app.exec())
