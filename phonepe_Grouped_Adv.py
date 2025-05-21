import sys
import os
import re
import csv
import datetime
import fitz  # PyMuPDF
from collections import defaultdict
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
                txn = mk_record(rec)
                if txn:
                    txns.append(txn)
            rec = [l]
        else:
            rec.append(l)

    if rec:
        txn = mk_record(rec)
        if txn:
            txns.append(txn)

    return txns

def mk_record(r):
    try:
        if len(r) < 8:
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

def write_csv(txns, output_file):
    with open(output_file, 'w', newline='', encoding='utf-8') as fo:
        writer = csv.writer(fo)
        writer.writerow(["Date", "Time", "Payee", "Transaction ID", "UTR No.", "Payer", "Type", "Amount"])
        for txn in txns:
            writer.writerow(txn.to_row())

def write_grouped_csv(txns, output_file):
    grouped = defaultdict(lambda: {"count": 0, "amount": 0.0})

    for txn in txns:
        key = (txn.kind, txn.payee)
        grouped[key]["count"] += 1
        grouped[key]["amount"] += float(txn.amount.replace("\u20B9", ""))

    with open(output_file, 'w', newline='', encoding='utf-8') as fo:
        writer = csv.writer(fo)
        writer.writerow(["Type", "Payee", "Count", "Total Amount (\u20B9)"])
        for (kind, payee), stats in grouped.items():
            writer.writerow([kind, payee, stats["count"], f"₹{stats['amount']:.2f}"])

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
        self.setFixedSize(500, 300)
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

            out_file = self.pdf_path.replace(".pdf", ".csv")
            write_csv(txns, out_file)

            if self.group_checkbox.isChecked():
                grouped_file = self.pdf_path.replace(".pdf", "_grouped.csv")
                write_grouped_csv(txns, grouped_file)

            QMessageBox.information(self, "Success", f"CSV created: {out_file}" + (f"\nGrouped CSV: {grouped_file}" if self.group_checkbox.isChecked() else ""))
        except Exception as e:
            QMessageBox.critical(self, "Failed", str(e))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PhonePeApp()
    window.show()
    sys.exit(app.exec())
