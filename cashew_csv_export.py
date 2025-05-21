import csv
import datetime
import os

def export_for_cashew(txns, output_dir):
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"cashew-{now}.csv"
    filepath = os.path.join(output_dir, filename)

    # Try detecting if extended fields are present (assuming attributes are set externally)
    has_category = hasattr(txns[0], 'category') if txns else False
    has_note = hasattr(txns[0], 'note') if txns else False

    with open(filepath, 'w', newline='', encoding='utf-8') as fo:
        writer = csv.writer(fo)
        writer.writerow(["Date", "Amount", "Category", "Title", "Note", "Account"])

        for txn in txns:
            dt = datetime.datetime.strptime(txn.date + " " + txn.time, "%Y-%m-%d %I:%M %p")
            formatted_date = dt.strftime("%d-%m-%Y %H:%M")

            amount = float(txn.amount.replace("₹", ""))
            amount = -amount if txn.kind == "DEBIT" else amount

            category = getattr(txn, 'category', "") if has_category else ""
            note = getattr(txn, 'note', "") if has_note else ""

            title = txn.payee or ("Received" if txn.kind == "CREDIT" else "Paid")

            writer.writerow([formatted_date, amount, category, title, note, ""])

    return filepath
