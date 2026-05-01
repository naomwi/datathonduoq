from __future__ import annotations

from math import floor, pi, sin

import numpy as np
import pandas as pd


TZ = 7.0


def jd_from_date(day: int, month: int, year: int) -> int:
    a = floor((14 - month) / 12)
    y = year + 4800 - a
    m = month + 12 * a - 3
    jd = day + floor((153 * m + 2) / 5) + 365 * y + floor(y / 4) - floor(y / 100) + floor(y / 400) - 32045
    if jd < 2299161:
        jd = day + floor((153 * m + 2) / 5) + 365 * y + floor(y / 4) - 32083
    return int(jd)


def jd_to_date(jd: int) -> tuple[int, int, int]:
    if jd > 2299160:
        a = jd + 32044
        b = floor((4 * a + 3) / 146097)
        c = a - floor((b * 146097) / 4)
    else:
        b = 0
        c = jd + 32082
    d = floor((4 * c + 3) / 1461)
    e = c - floor((1461 * d) / 4)
    m = floor((5 * e + 2) / 153)
    day = e - floor((153 * m + 2) / 5) + 1
    month = m + 3 - 12 * floor(m / 10)
    year = b * 100 + d - 4800 + floor(m / 10)
    return int(day), int(month), int(year)


def new_moon_day(k: int, timezone: float = TZ) -> int:
    t = k / 1236.85
    t2 = t * t
    t3 = t2 * t
    dr = pi / 180
    jd1 = 2415020.75933 + 29.53058868 * k + 0.0001178 * t2 - 0.000000155 * t3
    jd1 += 0.00033 * sin((166.56 + 132.87 * t - 0.009173 * t2) * dr)
    m = 359.2242 + 29.10535608 * k - 0.0000333 * t2 - 0.00000347 * t3
    mpr = 306.0253 + 385.81691806 * k + 0.0107306 * t2 + 0.00001236 * t3
    f = 21.2964 + 390.67050646 * k - 0.0016528 * t2 - 0.00000239 * t3
    correction = (
        (0.1734 - 0.000393 * t) * sin(m * dr)
        + 0.0021 * sin(2 * dr * m)
        - 0.4068 * sin(mpr * dr)
        + 0.0161 * sin(2 * dr * mpr)
        - 0.0004 * sin(3 * dr * mpr)
        + 0.0104 * sin(2 * dr * f)
        - 0.0051 * sin((m + mpr) * dr)
        - 0.0074 * sin((m - mpr) * dr)
        + 0.0004 * sin((2 * f + m) * dr)
        - 0.0004 * sin((2 * f - m) * dr)
        - 0.0006 * sin((2 * f + mpr) * dr)
        + 0.0010 * sin((2 * f - mpr) * dr)
        + 0.0005 * sin((2 * mpr + m) * dr)
    )
    if t < -11:
        delta_t = 0.001 + 0.000839 * t + 0.0002261 * t2 - 0.00000845 * t3 - 0.000000081 * t * t3
    else:
        delta_t = -0.000278 + 0.000265 * t + 0.000262 * t2
    return int(floor(jd1 + correction - delta_t + 0.5 + timezone / 24))


def sun_longitude(jdn: int, timezone: float = TZ) -> int:
    t = (jdn - 2451545.5 - timezone / 24) / 36525
    t2 = t * t
    dr = pi / 180
    m = 357.52910 + 35999.05030 * t - 0.0001559 * t2 - 0.00000048 * t * t2
    l0 = 280.46645 + 36000.76983 * t + 0.0003032 * t2
    dl = (1.914600 - 0.004817 * t - 0.000014 * t2) * sin(dr * m)
    dl += (0.019993 - 0.000101 * t) * sin(2 * dr * m) + 0.000290 * sin(3 * dr * m)
    longitude = (l0 + dl) * dr
    longitude = longitude - pi * 2 * floor(longitude / (pi * 2))
    return int(floor(longitude / pi * 6))


def lunar_month_11(year: int, timezone: float = TZ) -> int:
    off = jd_from_date(31, 12, year) - 2415021
    k = floor(off / 29.530588853)
    nm = new_moon_day(k, timezone)
    if sun_longitude(nm, timezone) >= 9:
        nm = new_moon_day(k - 1, timezone)
    return int(nm)


def leap_month_offset(a11: int, timezone: float = TZ) -> int:
    k = floor((a11 - 2415021.076998695) / 29.530588853 + 0.5)
    last = 0
    i = 1
    arc = sun_longitude(new_moon_day(k + i, timezone), timezone)
    while arc != last and i < 14:
        last = arc
        i += 1
        arc = sun_longitude(new_moon_day(k + i, timezone), timezone)
    return i - 1


def solar_to_lunar(date: pd.Timestamp, timezone: float = TZ) -> tuple[int, int, int, int, int]:
    day = int(date.day)
    month = int(date.month)
    year = int(date.year)
    day_number = jd_from_date(day, month, year)
    k = floor((day_number - 2415021.076998695) / 29.530588853)
    month_start = new_moon_day(k + 1, timezone)
    if month_start > day_number:
        month_start = new_moon_day(k, timezone)
    a11 = lunar_month_11(year, timezone)
    b11 = a11
    if a11 >= month_start:
        lunar_year = year
        a11 = lunar_month_11(year - 1, timezone)
    else:
        lunar_year = year + 1
        b11 = lunar_month_11(year + 1, timezone)
    lunar_day = day_number - month_start + 1
    diff = floor((month_start - a11) / 29)
    lunar_leap = 0
    lunar_month = diff + 11
    if b11 - a11 > 365:
        leap_diff = leap_month_offset(a11, timezone)
        if diff >= leap_diff:
            lunar_month = diff + 10
            if diff == leap_diff:
                lunar_leap = 1
    if lunar_month > 12:
        lunar_month -= 12
    if lunar_month >= 11 and diff < 4:
        lunar_year -= 1
    return int(lunar_day), int(lunar_month), int(lunar_year), int(lunar_leap), int(day_number)


def tet_date_for_solar_year(year: int, timezone: float = TZ) -> pd.Timestamp:
    dates = pd.date_range(f"{year}-01-15", f"{year}-02-25", freq="D")
    for date in dates:
        lunar_day, lunar_month, _, lunar_leap, _ = solar_to_lunar(date, timezone)
        if lunar_day == 1 and lunar_month == 1 and lunar_leap == 0:
            return pd.Timestamp(date.date())
    raise ValueError(f"Could not derive Tet date for {year}")


def add_lunar_calendar_features(df: pd.DataFrame, date_col: str = "Date") -> pd.DataFrame:
    out = df.copy()
    dates = pd.to_datetime(out[date_col])
    lunar = dates.apply(lambda d: solar_to_lunar(pd.Timestamp(d)))
    lunar_frame = pd.DataFrame(
        lunar.tolist(),
        columns=["lunar_day", "lunar_month", "lunar_year", "lunar_is_leap_month", "julian_day"],
        index=out.index,
    )
    out = pd.concat([out, lunar_frame], axis=1)
    years = sorted(dates.dt.year.unique())
    tet_map = {year: tet_date_for_solar_year(int(year)) for year in years}
    out["tet_date"] = dates.dt.year.map(tet_map)
    out["days_from_tet"] = (dates - out["tet_date"]).dt.days.astype(int)
    out["days_to_tet"] = -out["days_from_tet"]
    out["lunar_month_sin"] = np.sin(2 * np.pi * out["lunar_month"] / 12.0)
    out["lunar_month_cos"] = np.cos(2 * np.pi * out["lunar_month"] / 12.0)
    out["lunar_day_sin"] = np.sin(2 * np.pi * out["lunar_day"] / 30.0)
    out["lunar_day_cos"] = np.cos(2 * np.pi * out["lunar_day"] / 30.0)
    out["is_lunar_new_year"] = ((out["lunar_month"] == 1) & (out["lunar_day"] == 1)).astype(int)
    out["win_tet_pre14_1"] = out["days_from_tet"].between(-14, -1).astype(int)
    out["win_tet_pre7_1"] = out["days_from_tet"].between(-7, -1).astype(int)
    out["win_tet_0_3"] = out["days_from_tet"].between(0, 3).astype(int)
    out["win_tet_0_6"] = out["days_from_tet"].between(0, 6).astype(int)
    out["win_tet_post4_14"] = out["days_from_tet"].between(4, 14).astype(int)
    out["win_tet_post15_35"] = out["days_from_tet"].between(15, 35).astype(int)
    out["win_tet_wide"] = out["days_from_tet"].between(-14, 35).astype(int)
    return out
