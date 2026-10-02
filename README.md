# HBC Project Cost Control System

A beginner-friendly internal cost-control app for HBC Seef Lusail project tracking.

## Features
- Dashboard with KPI cards and charts
- Add/Edit transactions
- Search and filter transactions
- Excel import and export
- GL mapping and supplier management
- Basic budget vs actual summary
- SQLite database with audit fields
- Local database backup

## Run locally

1. Open a terminal in this folder.
2. Create a virtual environment:
   python -m venv .venv
3. Activate it:
   - Windows PowerShell: .\.venv\Scripts\Activate.ps1
   - Windows Command Prompt: .venv\Scripts\activate.bat
4. Install requirements:
   pip install -r requirements.txt
5. Start the app:
   streamlit run app.py

## Notes
This is Version 1, designed to work locally and expand later to multi-user usage.
