# 📊 Financial Statement Analyzer

**Financial Statement Analyzer** is an interactive, production-grade **Streamlit web app** that allows users to explore and analyze financial statements of any publicly listed company.  
It performs **exploratory financial statement analysis**, computing key ratios such as **ROA**, **ROE**, and **Current Ratio**, while visualizing company performance trends using real-time data fetched via **Yahoo Finance API**.


---

## 🚀 Features

- 🏢 **Company Search:** Enter a ticker (e.g., `AAPL`, `TSLA`, `INFY.NS`) to fetch real-time data  
- 📈 **Interactive Dashboard:** Visualize ROA, ROE, Current Ratios, and stock price trends  
- 📊 **Financial Metrics:** Automatically calculates key performance indicators  
- 🔄 **Auto Refresh:** Optional toggle to refresh dashboard periodically  
- 💾 **Data Preview:** View income statement, balance sheet, and ratios in structured tables  
- 🧠 **Smart UI:** Built using `streamlit-shadcn-ui` for a clean, modern interface  

---

## 🧱 Tech Stack

| Component | Technology |
|------------|-------------|
| **Frontend / UI** | [Streamlit](https://streamlit.io/) + [streamlit-shadcn-ui](https://pypi.org/project/streamlit-shadcn-ui/) |
| **Data Source** | [Yahoo Finance API](https://pypi.org/project/yfinance/) |
| **Visualization** | [Plotly](https://plotly.com/python/) |
| **Data Handling** | Pandas, NumPy |
| **Language** | Python 3.9+ |

---

## 📂 Project Structure

financial_statement_analyzer/
│
├── app.py # Main Streamlit application
├── services/
│ └── finance_api.py # (Optional) API handler for future backend separation
├── utils/
│ └── ratio_calculator.py # (Optional) Ratio computation logic
└── requirements.txt


---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository
```bash
git clone https://github.com/yourusername/financial-statement-analyzer.git
cd financial-statement-analyzer
```
```bash
python -m venv venv
source venv/bin/activate   # (Linux/Mac)
venv\Scripts\activate      # (Windows)
```
```bash
pip install -r requirements.txt
```
```bash
streamlit run app.py
```
