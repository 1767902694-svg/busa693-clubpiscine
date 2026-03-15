from fastapi import FastAPI
import pandas as pd
from pathlib import Path

app = FastAPI()

# Path to outputs folder
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"

@app.get("/")
def root():
    return {"message": "Forecast API is running"}

@app.get("/forecast")
def forecast():

    file_path = OUTPUT_DIR / "forecast_output.csv"

    df = pd.read_csv(file_path)

    return df.to_dict(orient="records")


@app.get("/forecast_by_store")
def forecast_by_store():

    file_path = OUTPUT_DIR / "forecast_output_by_store.csv"

    df = pd.read_csv(file_path)

    return df.to_dict(orient="records")