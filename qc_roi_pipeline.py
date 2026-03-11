#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QC ROI Pipeline — 全省统一外部变量 + MMM + 触发器 + 预算再分配

功能：
1) 外部变量构建（魁北克省）：
   - 天气（日/周）：Open‑Meteo ERA5 历史（支持在线抓取；离线/演示模式下生成可用的合成数据）
   - 省级节日（ICS 订阅源；离线模式内置 2025–2026 列表）
   - 建筑业假期（Construction Holiday；内置 2026 夏季/冬季）
2) 渠道与转化数据：读取周级 fact（如无则生成演示数据）
3) MMM（带 adstock & 饱和）估算各渠道增量贡献（近似）与边际 ROI
4) 预算再分配建议（保持总预算不变）
5) 触发器计划（基于天气/节日强度）
6) 输出多个 CSV：日/周天气、周事件、周KPI、触发器、预算建议

运行示例：
    python qc_roi_pipeline.py --start 2025-01-01 --end 2025-12-31 --demo 1
    
参数说明：
    --start / --end   ：日期范围（YYYY-MM-DD）
    --demo            ：为 1 时使用离线演示模式（不访问网络，自动生成数据并输出合理结果）
    --marketing_csv   ：可选，传入你的周度渠道事实数据 CSV（列结构见 README）
    --weights_csv     ：可选，省内城市人口/销量权重（city,weight）

注意：
    - 在线模式会访问 Open‑Meteo 与节日 ICS URL；演示模式不会访问网络。
    - 演示模式数据为合成数据，仅用于流程演示；真实评估请使用在线/官方数据源。
"""

import argparse
import sys
import os
from datetime import datetime, date, timedelta
import math
import json

from pathlib import Path
import numpy as np
import pandas as pd

# 尝试可选依赖（requests）；演示模式下允许没有 requests
try:
    import requests  # type: ignore
except Exception:
    requests = None

# ------------------------------
# 参数与常量
# ------------------------------
TZ = "America/Toronto"
BASE_URL_OPEN_METEO = "https://archive-api.open-meteo.com/v1/era5"
DAILY_VARS = [
    "temperature_2m_max","temperature_2m_min","temperature_2m_mean",
    "precipitation_sum","rain_sum","snowfall_sum","snow_depth","windgusts_10m_max"
]
QC_POINTS = {
    "Montreal": (45.5017, -73.5673),
    "Quebec_City": (46.8139, -71.2080),
    "Laval": (45.6066, -73.7124),
    "Gatineau": (45.4765, -75.7013),
    "Longueuil": (45.5312, -73.5181),
    "Sherbrooke": (45.4042, -71.8929),
    "Saguenay": (48.4168, -71.0657),
    "Trois_Rivieres": (46.3430, -72.5421),
    "Levis": (46.7382, -71.2465),
    "Terrebonne": (45.7000, -73.6333),
    "Rimouski": (48.4330, -68.5230),
    "Rouyn_Noranda": (48.2360, -79.0200),
}

# ------------------------------
# 工具函数
# ------------------------------
def daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)

def week_start_of_day(d: pd.Timestamp) -> date:
    return (d - pd.to_timedelta(d.weekday(), unit='D')).date()

# ------------------------------
# 1) 天气：在线抓取 + 演示模式合成
# ------------------------------

def fetch_open_meteo_daily(lat: float, lon: float, start_date: str, end_date: str, tz: str = TZ) -> pd.DataFrame:
    """在线模式：从 Open‑Meteo 拉取某坐标的日级天气。"""
    if requests is None:
        raise RuntimeError("requests 不可用；请在非演示模式下安装 requests 或使用 --demo 1")
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(DAILY_VARS),
        "timezone": tz
    }
    url = BASE_URL_OPEN_METEO
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data["daily"])  # keys: time + vars
    df["date"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
    df = df.drop(columns=["time"])  # 统一日索引
    df["lat"], df["lon"] = lat, lon
    return df


def synthesize_weather_daily(start: date, end: date) -> pd.DataFrame:
    """演示模式：生成可用的合成天气（全省 12 城市，带季节性与合理范围）。"""
    days = pd.date_range(start, end, freq='D')
    out = []
    rng = np.random.default_rng(42)
    for city, (lat, lon) in QC_POINTS.items():
        # 城市气候微调：纬度越高冬季更冷
        lat_factor = (lat - 45.0) * 0.6
        base_temp = []
        for d in days:
            # 季节性温度：
            doy = d.timetuple().tm_yday
            # 夏季峰值 ~ 22°C，冬季谷值 ~ -12°C；加城市纬度影响
            t_mean = 5 + 17 * math.sin(2*math.pi*(doy-172)/365.0) - lat_factor
            t_max  = t_mean + rng.normal(6, 2)
            t_min  = t_mean - rng.normal(7, 2)
            # 降水/降雪：冬季更多雪，夏季更多雨
            rain = max(0, rng.normal(3 if t_mean>0 else 1, 2))
            snow = max(0, rng.normal(0 if t_mean>0 else 2, 1.5))
            snow_depth = max(0, rng.normal( (0 if t_mean>0 else 5), 2))
            gust = max(10, rng.normal(35, 8))
            out.append({
                "date": d.to_pydatetime(),
                "city": city,
                "lat": lat,
                "lon": lon,
                "temperature_2m_mean": t_mean,
                "temperature_2m_max": t_max,
                "temperature_2m_min": t_min,
                "precipitation_sum": rain + (snow*0.5),
                "rain_sum": rain,
                "snowfall_sum": snow,
                "snow_depth": snow_depth,
                "windgusts_10m_max": gust,
            })
    df = pd.DataFrame(out)
    return df


def aggregate_province_daily(daily_city: pd.DataFrame, weights: pd.Series | None = None) -> pd.DataFrame:
    """城市→省级聚合（加权均值；量型变量用加权均值以便跨期比较）。"""
    df = daily_city.copy()
    if weights is None:
        weights = pd.Series(1.0, index=QC_POINTS.keys())
    weights = weights.reindex(QC_POINTS.keys()).fillna(0.0)
    weights = weights/weights.sum() if weights.sum()>0 else weights
    wdf = df.merge(weights.rename("w").reset_index().rename(columns={"index":"city"}), on="city", how="left")

    sum_vars  = ["precipitation_sum","rain_sum","snowfall_sum"]
    mean_vars = ["temperature_2m_mean","temperature_2m_max","temperature_2m_min","snow_depth","windgusts_10m_max"]

    def weighted_mean(x, w):
        x, w = np.asarray(x, float), np.asarray(w, float)
        return np.average(x, weights=w) if np.isfinite(w).sum()>0 and w.sum()>0 else np.nan

    rows = []
    for d, g in wdf.groupby("date"):
        out = {"date": d}
        out["cities_covered"] = g["city"].nunique()
        for v in mean_vars:
            out[v] = weighted_mean(g[v], g["w"]) 
            out[v+"_min"], out[v+"_max"] = g[v].min(), g[v].max()
        for v in sum_vars:
            out[v] = weighted_mean(g[v], g["w"]) 
            out[v+"_sum_if_equal_weight"] = g[v].mean() * g["city"].nunique()
        # HDD/CDD
        out["HDD18"] = max(0.0, 18.0 - out["temperature_2m_mean"]) if not math.isnan(out["temperature_2m_mean"]) else np.nan
        out["CDD22"] = max(0.0, out["temperature_2m_mean"] - 22.0) if not math.isnan(out["temperature_2m_mean"]) else np.nan
        rows.append(out)
    return pd.DataFrame(rows)


def weekly_aggregate(daily_province: pd.DataFrame) -> pd.DataFrame:
    d = daily_province.copy()
    d["week_start"] = pd.to_datetime(d["date"]).apply(week_start_of_day)
    weekly_mean_vars = ["temperature_2m_mean","temperature_2m_max","temperature_2m_min","snow_depth","windgusts_10m_max"]
    weekly_sum_vars  = ["precipitation_sum","rain_sum","snowfall_sum","HDD18","CDD22"]
    w = (d.groupby("week_start")
           .agg({**{v:"mean" for v in weekly_mean_vars}, **{v:"sum" for v in weekly_sum_vars}})
           .reset_index())
    # 异常/标准化（滚动 8 周）
    def add_anomaly_cols(df, cols, win=8):
        out = df.copy()
        for c in cols:
            ma = out[c].rolling(win, min_periods=4).mean()
            sd = out[c].rolling(win, min_periods=4).std()
            out[c+"_anomaly"] = out[c] - ma
            out[c+"_zscore"]  = (out[c] - ma) / sd.replace(0, np.nan)
        return out
    w = add_anomaly_cols(w, ["temperature_2m_mean","precipitation_sum","snowfall_sum","HDD18","CDD22"], win=8)
    return w

# ------------------------------
# 2) 节日与建筑假期（ICS 在线 + 内置离线）
# ------------------------------
QC_HOLIDAYS_2025_2026 = [
    # 2025（示例；依据公开来源整理）
    (date(2025,1,1), "New Year's Day"),
    (date(2025,4,18), "Good Friday"),
    (date(2025,4,21), "Easter Monday"),
    (date(2025,5,19), "National Patriots' Day"),
    (date(2025,6,24), "Fête nationale du Québec"),
    (date(2025,7,1), "Canada Day"),
    (date(2025,9,1), "Labour Day"),
    (date(2025,10,13), "Thanksgiving"),
    (date(2025,12,25), "Christmas"),
    # 2026
    (date(2026,1,1), "New Year's Day"),
    (date(2026,4,3), "Good Friday"),
    (date(2026,4,6), "Easter Monday"),
    (date(2026,5,18), "National Patriots' Day"),
    (date(2026,6,24), "Fête nationale du Québec"),
    (date(2026,7,1), "Canada Day"),
    (date(2026,9,7), "Labour Day"),
    (date(2026,10,12), "Thanksgiving"),
    (date(2026,12,25), "Christmas"),
]

CONSTRUCTION_HOLIDAYS = [
    # 2026 夏季（CCQ）
    (date(2026,7,19), date(2026,8,1)),
    # 2025 冬季（示例范围；部分落在 2026 年初）
    (date(2025,12,21), date(2026,1,3)),
]


def fetch_qc_holidays_ics(ics_url: str) -> pd.DataFrame:
    if requests is None:
        raise RuntimeError("requests 不可用；请在非演示模式下安装 requests 或使用内置列表")
    r = requests.get(ics_url, timeout=30)
    r.raise_for_status()
    lines = r.text.splitlines()
    events = []
    cur = {}
    for ln in lines:
        if ln.startswith("BEGIN:VEVENT"):
            cur = {}
        elif ln.startswith("DTSTART"):
            dtstr = ln.split(":")[1]
            cur["date"] = pd.to_datetime(dtstr).date()
        elif ln.startswith("SUMMARY"):
            cur["name"] = ln.split(":",1)[1]
        elif ln.startswith("END:VEVENT") and cur:
            events.append(cur)
    return pd.DataFrame(events).dropna()


def build_construction_days(ranges: list[tuple[date,date]]) -> pd.DataFrame:
    out = []
    for (s,e) in ranges:
        for d in daterange(s,e):
            out.append({"date": d, "name": "Construction Holiday"})
    return pd.DataFrame(out)


def weekly_events_from_daily(daily_events: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    anchor = pd.DataFrame({"week_start": pd.date_range(start, end, freq="W-MON").date})
    tmp = daily_events.copy()
    tmp["week_start"] = pd.to_datetime(tmp["date"]).apply(week_start_of_day)
    tmp["flag"] = 1
    wk = tmp.groupby("week_start")["flag"].sum().reset_index()
    return anchor.merge(wk, on="week_start", how="left").fillna({"flag":0})

# ------------------------------
# 3) 演示模式：生成渠道周度数据（可用的合成数据）
# ------------------------------

def synthesize_marketing_weekly(start: date, end: date, weekly_weather: pd.DataFrame, weekly_events: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(13)
    weeks = pd.date_range(start, end, freq="W-MON").date
    channels = ["Search","Social","Programmatic","RetailMedia","Email"]
    rows = []
    w = weekly_weather.set_index("week_start")
    e = weekly_events.set_index("week_start")
    for ws in weeks:
        # 基础需求指数：随季节变化（夏季旺，冬季淡）+ 天气影响
        base_demand = 100 + 30*math.sin(2*math.pi*((pd.Timestamp(ws).day_of_year-172)/365))
        demand_adj = -0.8*w.loc[ws,"HDD18"] + 0.6*w.loc[ws,"CDD22"] + 0.3*w.loc[ws,"precipitation_sum"]
        holiday_boost = 8.0*e.loc[ws,"is_qc_holiday"] if "is_qc_holiday" in e.columns else 0
        construction_shift = -3.0*e.loc[ws,"is_construction_holiday"] if "is_construction_holiday" in e.columns else 0
        demand = max(50, base_demand + demand_adj + holiday_boost + construction_shift + rng.normal(0,8))
        # 渠道分配：Search/RetailMedia 更贴近需求；Social/Programmatic 稍滞后
        cost_split = {
            "Search": 0.30,
            "RetailMedia": 0.25,
            "Social": 0.20,
            "Programmatic": 0.20,
            "Email": 0.05
        }
        total_cost = 50000 + 8000*e.loc[ws,"is_qc_holiday"] + 5000*e.loc[ws,"is_construction_holiday"] + rng.normal(0,2000)
        for ch in channels:
            cost = max(1000, total_cost * cost_split[ch] * (1 + rng.normal(0,0.05)))
            # 点击/转化：受温度与降水影响（室内/到家偏好）
            clicks = max(500, int(cost/1.2 + (w.loc[ws,"precipitation_sum"]*50) + rng.normal(0,200)))
            conv_rate = 0.02 + 0.004*(holiday_boost>0) + 0.002*(w.loc[ws,"CDD22"]>15) - 0.001*(w.loc[ws,"HDD18"]>15)
            conversions = max(50, int(clicks * max(0.005, conv_rate + rng.normal(0,0.001))))
            revenue = max(5000, conversions * (80 + 10*(ch in ["RetailMedia","Search"]) + rng.normal(0,5)))
            rows.append({
                "week_start": ws,
                "channel": ch,
                "subchannel": ch,
                "campaign_id": f"demo_{ch}",
                "geo": "QC",
                "impressions": int(clicks*20),
                "clicks": clicks,
                "cost": float(cost),
                "conversions": conversions,
                "revenue": float(revenue)
            })
    return pd.DataFrame(rows)

# ------------------------------
# 4) MMM：adstock + saturation + 岭回归（自实现）
# ------------------------------

def adstock_series(x: np.ndarray, theta: float = 0.5, L: int = 4) -> np.ndarray:
    y = np.zeros_like(x, dtype=float)
    for t in range(len(x)):
        y[t] = x[t]
        for l in range(1, L+1):
            if t - l >= 0:
                y[t] += (theta**l) * x[t-l]
    return y


def saturation_series(x: np.ndarray, k: float = 10000.0) -> np.ndarray:
    x = np.asarray(x, float)
    return x / (x + k)


def ridge_regression(X: np.ndarray, y: np.ndarray, alpha: float = 10.0) -> np.ndarray:
    """简单岭回归：beta = (X^T X + alpha*I)^-1 X^T y"""
    XTX = X.T @ X
    I = np.eye(XTX.shape[0])
    beta = np.linalg.pinv(XTX + alpha * I) @ (X.T @ y)
    return beta

# ------------------------------
# 5) 触发器计划
# ------------------------------

def build_triggers(weekly_weather: pd.DataFrame, weekly_events: pd.DataFrame) -> pd.DataFrame:
    tw = weekly_weather.merge(weekly_events, on="week_start", how="left").fillna(0)
    out = []
    for _, r in tw.iterrows():
        actions = []
        # 暴雪：雪深>8 或 snowfall_sum>10
        if (r.get("snow_depth",0)>8) or (r.get("snowfall_sum",0)>10):
            actions.append(("Programmatic","+15% 出价/预算，创意切换到到家/配送"))
        # 热浪：CDD22 > 20
        if r.get("CDD22",0)>20:
            actions.append(("RetailMedia","+10%，主推冷饮/防晒"))
        # 魁北克法定日
        if r.get("is_qc_holiday",0)>=1:
            actions.append(("Social","+20%，法语主视觉；Stories/短视频加频控"))
        # 建筑业假期
        if r.get("is_construction_holiday",0)>=3:
            actions.append(("Search","+10%，到店/旅游相关关键词扩容"))
        if actions:
            out.append({"week_start": r["week_start"], "actions": "; ".join([f"{a}:{b}" for a,b in actions])})
    return pd.DataFrame(out)

# ------------------------------
# 主流程
# ------------------------------

def main(args):
    start = pd.to_datetime(args.start).date()
    end   = pd.to_datetime(args.end).date()

    # 目录
    out_dir = Path(os.getcwd())

    # ===== 1) 天气 =====
    if args.demo:
        daily_city = synthesize_weather_daily(start, end)
    else:
        # 在线抓取所有城市
        city_frames = []
        for city, (lat, lon) in QC_POINTS.items():
            df_city = fetch_open_meteo_daily(lat, lon, args.start, args.end, TZ)
            df_city["city"] = city
            city_frames.append(df_city)
        daily_city = pd.concat(city_frames, ignore_index=True)

    # 省级聚合
    weights = None
    if args.weights_csv and os.path.exists(args.weights_csv):
        wdf = pd.read_csv(args.weights_csv)
        weights = pd.Series(wdf["weight"].values, index=wdf["city"].values)
    daily_province = aggregate_province_daily(daily_city, weights)
    daily_province.to_csv(out_dir/"qc_weather_features_daily.csv", index=False)

    weekly_weather = weekly_aggregate(daily_province)
    weekly_weather.to_csv(out_dir/"qc_weather_features_weekly.csv", index=False)

    # ===== 2) 事件（节日 + 建筑业假期） =====
    if args.demo:
        # 用内置列表
        holidays_df = pd.DataFrame({"date": [d for d,_ in QC_HOLIDAYS_2025_2026], "name": [n for _,n in QC_HOLIDAYS_2025_2026]})
    else:
        # 在线 ICS（Canada Holidays）
        ics_url = "https://canada-holidays.ca/ics/QC"
        holidays_df = fetch_qc_holidays_ics(ics_url)
    holidays_df["is_qc_holiday"] = 1

    construction_df = build_construction_days(CONSTRUCTION_HOLIDAYS)
    construction_df["is_construction_holiday"] = 1

    # 周级事件表
    wk_anchor = pd.DataFrame({"week_start": pd.date_range(start, end, freq="W-MON").date})
    def to_weekly_flag(df, flagcol):
        tmp = df[["date", flagcol]].copy()
        tmp["week_start"] = pd.to_datetime(tmp["date"]).apply(week_start_of_day)
        agg = tmp.groupby("week_start")[flagcol].sum().reset_index()
        return wk_anchor.merge(agg, on="week_start", how="left").fillna({flagcol:0})

    qc_holidays_week = to_weekly_flag(holidays_df, "is_qc_holiday")
    construction_week = to_weekly_flag(construction_df, "is_construction_holiday")
    weekly_events = (wk_anchor.merge(qc_holidays_week, on="week_start")
                              .merge(construction_week, on="week_start"))
    weekly_events.to_csv(out_dir/"qc_weekly_events.csv", index=False)

    # ===== 3) 渠道与转化数据 =====
    if args.marketing_csv and os.path.exists(args.marketing_csv):
        wk = pd.read_csv(args.marketing_csv, parse_dates=["week_start"])  # 使用真实数据
    else:
        wk = synthesize_marketing_weekly(start, end, weekly_weather, weekly_events)
    # 基础 KPI
    wk["roi_gross"] = wk["revenue"] / wk["cost"].replace(0, np.nan)
    wk["cvr"] = wk["conversions"] / wk["clicks"].replace(0, np.nan)
    wk["cpa"] = wk["cost"] / wk["conversions"].replace(0, np.nan)
    wk.to_csv(out_dir/"fact_marketing_week.csv", index=False)

    # 汇总报表
    report = (wk.groupby(["week_start","channel"]) [["cost","revenue","conversions"]]
              .sum().reset_index())
    report.to_csv(out_dir/"qc_weekly_kpi_by_channel.csv", index=False)

    # 合并外部变量（供后续 MMM）
    wk_merged = (wk.merge(weekly_weather, on="week_start", how="left")
                   .merge(weekly_events, on="week_start", how="left"))

    # ===== 4) MMM：adstock + saturation =====
    channels = ["Search","Social","Programmatic","RetailMedia","Email"]
    wk_merged = wk_merged.sort_values(["week_start","channel"]).copy()
    for ch in channels:
        mask = (wk_merged["channel"]==ch)
        costs = wk_merged.loc[mask,"cost"].fillna(0).values
        ad = adstock_series(costs, theta=0.5, L=4)
        sat= saturation_series(ad, k=10000)
        wk_merged.loc[mask, f"{ch}_sat"] = sat

    # 以周收入为因变量，聚合到周级
    model_df = (wk_merged.groupby("week_start", as_index=False)
                .agg({"revenue":"sum",
                      "Search_sat":"sum","Social_sat":"sum","Programmatic_sat":"sum","RetailMedia_sat":"sum","Email_sat":"sum",
                      "temperature_2m_mean":"mean","precipitation_sum":"sum","snowfall_sum":"sum",
                      "HDD18":"sum","CDD22":"sum",
                      "is_qc_holiday":"sum","is_construction_holiday":"sum"}))
    model_df = model_df.fillna(0)

    # 设计矩阵
    X_cols = ["Search_sat","Social_sat","Programmatic_sat","RetailMedia_sat","Email_sat",
              "temperature_2m_mean","precipitation_sum","snowfall_sum","HDD18","CDD22",
              "is_qc_holiday","is_construction_holiday"]
    X = model_df[X_cols].values
    y = model_df["revenue"].values

    # 标准化（防止数值差异影响回归）
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd==0] = 1.0
    Xs = (X - mu)/sd

    beta = ridge_regression(Xs, y, alpha=10.0)
    coefs = pd.Series(beta, index=X_cols)

    # 边际 ROI 近似（对应 sat 的单位变化带来的收入变化，折返到原尺度）
    scale = pd.Series(sd, index=X_cols)
    mrev = coefs/scale
    mroi = mrev[[c for c in X_cols if c.endswith("_sat")]]
    mroi.name = "marginal_revenue_per_unit_sat"

    # 预算再分配（保持当前总预算不变）
    last_week = wk_merged["week_start"].max()
    current_total = wk_merged[wk_merged["week_start"]==last_week]["cost"].sum()
    weights = mroi/mroi.sum() if mroi.sum()!=0 else mroi.copy()
    alloc = (weights * current_total).rename(lambda x: x.replace("_sat",""))
    alloc_df = alloc.reset_index()
    alloc_df.columns = ["channel_sat","suggested_budget"]
    alloc_df["channel"] = alloc_df["channel_sat"].str.replace("_sat","")
    alloc_df = alloc_df[["channel","suggested_budget"]]
    alloc_df.to_csv(out_dir/"qc_budget_reallocation.csv", index=False)

    # ===== 5) 触发器计划 =====
    triggers = build_triggers(weekly_weather, weekly_events)
    triggers.to_csv(out_dir/"qc_trigger_plan.csv", index=False)

    # 输出摘要
    print("\n=== Pipeline 完成 ===")
    print(f"时间范围：{start} 至 {end}")
    print("生成文件：")
    for fn in ["qc_weather_features_daily.csv","qc_weather_features_weekly.csv","qc_weekly_events.csv",
               "fact_marketing_week.csv","qc_weekly_kpi_by_channel.csv","qc_trigger_plan.csv",
               "qc_budget_reallocation.csv"]:
        p = out_dir/fn
        print(f" - {p} : {os.path.getsize(p)} bytes")

    print("\n边际收益（近似）")
    print(mroi)
    print("\n预算再分配建议（下周，保持总预算不变）：")
    print(alloc_df)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--demo", type=int, default=0)
    ap.add_argument("--marketing_csv", type=str, default="")
    ap.add_argument("--weights_csv", type=str, default="")
    args = ap.parse_args()

    try:
        main(args)
    except Exception as e:
        print("运行出错：", e)
        sys.exit(1)
