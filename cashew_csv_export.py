import csv
import datetime
import os

def export_for_cashew(txns, output_dir, payee_category_map=None):
    payee_category_map = payee_category_map or {}
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

            # Use user category mapping if available, else txn.category attr if present, else empty
            category = ""
            if txn.payee in payee_category_map:
                category = payee_category_map[txn.payee]
            elif has_category:
                category = getattr(txn, 'category', "")
            note = getattr(txn, 'note', "") if has_note else ""

            title = txn.payee or ("Received" if txn.kind == "CREDIT" else "Paid")

            writer.writerow([formatted_date, amount, category, title, note, ""])

    return filepath
