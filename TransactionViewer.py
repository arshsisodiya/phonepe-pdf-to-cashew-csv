from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
import plotly.graph_objects as go
import pandas as pd
import os

class TransactionViewer(QWidget):
    def __init__(self, all_path, grouped_path=None, cashew_path=None):
        super().__init__()
        self.setWindowTitle("Transaction Viewer")
        self.resize(1000, 600)

        self.all_path = all_path
        self.grouped_path = grouped_path
        self.cashew_path = cashew_path

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # All transactions tab
        self.all_tab = QWidget()
        self.tabs.addTab(self.all_tab, "All Transactions")
        self.init_tab(self.all_tab, self.all_path)

        # Grouped summary tab
        if self.grouped_path and os.path.exists(self.grouped_path):
            self.grouped_tab = QWidget()
            self.tabs.addTab(self.grouped_tab, "Grouped Summary")
            self.init_tab(self.grouped_tab, self.grouped_path)
            print("Grouped summary CSV found:", self.grouped_path)
            print("Adding Summary (Pie Chart) tab...")

            self.add_summary_chart_tab(self.grouped_path)
            print("Number of tabs after adding summary tab:", self.tabs.count())

        # Cashew export tab
        if self.cashew_path and os.path.exists(self.cashew_path):
            self.cashew_tab = QWidget()
            self.tabs.addTab(self.cashew_tab, "Cashew Export")
            self.init_tab(self.cashew_tab, self.cashew_path)

    def init_tab(self, tab, file_path):
        layout = QVBoxLayout()
        tab.setLayout(layout)

        table = QTableWidget()
        layout.addWidget(table)

        tab.table = table
        tab.file_path = file_path

        self.load_data(tab)

    def load_data(self, tab):
        df = pd.read_csv(tab.file_path)

        table = tab.table
        table.clear()
        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns)

        for row_idx, row in df.iterrows():
            for col_idx, val in enumerate(row):
                table.setItem(row_idx, col_idx, QTableWidgetItem(str(val)))

    def add_summary_chart_tab(self, grouped_path):
        try:
            df = pd.read_csv(grouped_path)

            if 'Payee' in df.columns and 'Total Amount' in df.columns:
                # Clean and prepare
                df['Amount'] = df['Total Amount'].astype(str).str.replace('₹', '').str.replace(',', '').str.strip()
                df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
                df = df[df['Amount'].notna() & (df['Amount'] > 0)]

                df_sorted = df.sort_values(by='Amount', ascending=False)
                top_15 = df_sorted.head(15)
                others = df_sorted.iloc[15:]

                others_total = others['Amount'].sum()

                final_labels = top_15['Payee'].tolist()
                final_values = top_15['Amount'].tolist()

                if others_total > 0:
                    final_labels.append("Others")
                    final_values.append(others_total)

                # Pie chart
                fig = go.Figure(
                    data=[go.Pie(
                        labels=final_labels,
                        values=final_values,
                        hovertemplate='%{label}<br>₹%{value:,.2f}<br>%{percent}',
                        textinfo='percent',
                        name=''
                    )]
                )
                fig.update_layout(title_text="Top 15 Groups + Others (Transaction Summary)")

                # Summary stats
                most_sent_to = top_15.iloc[0]['Payee']
                most_sent_amt = top_15.iloc[0]['Amount']

                # Load all transactions
                try:
                    all_df = pd.read_csv(self.all_path)
                    all_df['Amount'] = all_df['Amount'].astype(str).str.replace('₹', '').str.replace(',',
                                                                                                     '').str.strip()
                    all_df['Amount'] = pd.to_numeric(all_df['Amount'], errors='coerce')
                    all_df['Date'] = pd.to_datetime(all_df['Date'], errors='coerce')

                    debits = all_df[all_df['Type'].str.lower() == 'debit']
                    day_spend = debits.groupby(debits['Date'].dt.date)['Amount'].sum()
                    most_spent_day = day_spend.idxmax()
                    most_spent_day_amt = day_spend.max()

                    date_range = (debits['Date'].max() - debits['Date'].min()).days + 1
                    total_spent = debits['Amount'].sum()
                    avg_daily = total_spent / date_range
                    avg_weekly = avg_daily * 7
                    avg_monthly = avg_daily * 30

                except Exception as e:
                    print("Failed to load all transaction stats:", e)
                    most_spent_day = "N/A"
                    most_spent_day_amt = avg_daily = avg_weekly = avg_monthly = 0

                stats_html = f"""
                <div style="
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background-color: rgba(255, 255, 255, 0.95);
                    padding: 10px 14px;
                    border-radius: 10px;
                    font-family: Arial, sans-serif;
                    font-size: 12px;
                    color: #222;
                    box-shadow: 0 3px 8px rgba(0, 0, 0, 0.1);
                    max-width: 260px;
                    z-index: 9999;
                    line-height: 1.3;
                ">
                    <b style="font-size: 14px; display: block; margin-bottom: 8px; color: #333;">Summary Stats</b>
                    <ul style="list-style-type: none; padding-left: 14px; margin: 0;">
                        <li style="margin-bottom: 6px;"><b>Most Amount Sent To:</b> {most_sent_to}<br>₹{most_sent_amt:,.2f}</li>
                        <li style="margin-bottom: 6px;"><b>Most Spent Day:</b> {most_spent_day}<br>₹{most_spent_day_amt:,.2f}</li>
                        <li style="margin-bottom: 6px;"><b>Average Daily Spend:</b> ₹{avg_daily:,.2f}</li>
                        <li style="margin-bottom: 6px;"><b>Average Weekly Spend:</b> ₹{avg_weekly:,.2f}</li>
                        <li><b>Average Monthly Spend:</b> ₹{avg_monthly:,.2f}</li>
                    </ul>
                </div>
                """

                chart_html = fig.to_html(include_plotlyjs='cdn', full_html=False)
                full_html = f"<html><body>{stats_html}{chart_html}</body></html>"

                webview = QWebEngineView()
                webview.setHtml(full_html)

                chart_widget = QWidget()
                layout = QVBoxLayout()
                layout.addWidget(webview)
                chart_widget.setLayout(layout)

                self.tabs.addTab(chart_widget, "Summary")

        except Exception as e:
            print("Error creating summary chart:", e)
