# PhonePe PDF To Vashew CSV Exporter

**Description:**
A modern desktop app built with PyQt6 that allows you to convert your PhonePe transaction statement PDF into structured CSV files. It supports exporting data in formats compatible with budgeting apps like **Cashew**, providing flexibility, financial insights, and automation.

---

## 🚀 Features

### ✅ PDF to CSV Conversion

* Parse PhonePe PDF statements.
* Extracts Date, Time, Payee, Transaction ID, UTR No., Payer, Type (DEBIT/CREDIT), and Amount.

### 🔐 Password-Protected PDFs

* Secure handling of encrypted PDFs.
* Prompts user with a show/hide password input.

### 📊 Grouped Summary CSV (Optional)

* Groups data by Payee and Transaction Type.
* Calculates:

  * Most amount sent (receiver)
  * Most amount received (sender)
  * Day with the highest spending
  * Average daily, weekly, and monthly expenses

### 📥 Cashew App Export (Optional)

* Exports transactions in Cashew-compatible format:

  * `Date`, `Amount`, `Category`, `Title`, `Note`, `Account`
* Supports optional fields: `category` and `note`
* Debits appear as negative amounts, credits as positive
* Output file named like: `cashew-YYYY-MM-DD_HH-MM-SS.csv`

---

## 🛠 How to Use

### 1. Clone the repository

```bash
git clone https://github.com/arshsisodiya/phonepe-pdf-to-cashew-csv.git
cd phonepe-pdf-to-cashew-csv
```

### 2. Install dependencies

```bash
pip install PyQt6 PyMuPDF
```

### 3. Run the app

```bash
python main_app.py
```

### 4. Use the GUI

* **Select PhonePe PDF**: Choose your PDF file.
* **Enable Grouped Summary or Cashew Export**: Check the options as needed.
* **Click Convert**: CSV files will be generated.

---

## 📁 Output Files

* `PhonePe_Statement.csv`: Default transaction data
* `PhonePe_Statement_grouped.csv`: Grouped summary (if selected)
* `cashew-YYYY-MM-DD_HH-MM-SS.csv`: Cashew format file (if selected)

---

## 💡 Why This Tool?

PhonePe provides statements only in PDF format, which are hard to work with. This tool makes them useful:

* Analyze your spending trends.
* Import into finance apps like **Cashew**.
* Build personalized budgeting workflows.

---

## 📄 License

MIT License

---

## 🤝 Contributing

We welcome PRs and feature ideas! If you find issues or want to add integrations , feel free to contribute.

---
