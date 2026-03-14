from fastapi import FastAPI
import pandas as pd

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Forecast API is running"}

@app.get("/forecast")
def forecast():

    data = {
        "month": ["Jan","Feb","Mar"],
        "forecast_sales":[1200,1350,1500]
    }

    return data