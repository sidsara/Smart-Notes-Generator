Set-Location "$PSScriptRoot"
conda run -n study python -m streamlit run app.py --server.port 8501
