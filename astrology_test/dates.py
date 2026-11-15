"""Compute the astrology event dates used by run.py:
- Amavasya days (Amavasya tithi at New Delhi sunrise)
- Mercury retrograde periods (longitude speed < 0 at 15:30 IST)
- Jupiter in Ketu's nakshatras (Ashwini, Magha, Mula), sidereal Lahiri, at IST noon
All positions from the Swiss Ephemeris (pyswisseph, built-in Moshier mode).
Writes amavasya_dates.csv, mercury_retrograde_periods.csv, jupiter_ketu_periods.csv into data/."""
import datetime as dt
import swisseph as swe
import numpy as np
import pandas as pd

FLAG = swe.FLG_MOSEPH | swe.FLG_SPEED
DELHI = (77.2090, 28.6139, 216.0)  # lon, lat, alt (m)
IST = dt.timedelta(hours=5, minutes=30)


def jd_from_utc(t):
    return swe.julday(t.year, t.month, t.day, t.hour + t.minute / 60 + t.second / 3600)


def utc_from_jd(jd):
    y, m, d, h = swe.revjul(jd)
    return dt.datetime(y, m, d) + dt.timedelta(hours=h)


def elongation(jd):
    moon = swe.calc_ut(jd, swe.MOON, FLAG)[0][0]
    sun = swe.calc_ut(jd, swe.SUN, FLAG)[0][0]
    return (moon - sun) % 360.0


def sunrise_jd(day):
    """Sunrise at New Delhi for a civil IST date."""
    start_utc = dt.datetime(day.year, day.month, day.day) - IST  # IST midnight in UTC
    res, tret = swe.rise_trans(jd_from_utc(start_utc), swe.SUN, swe.CALC_RISE | swe.BIT_DISC_CENTER,
                               DELHI, 0, 0, FLAG)
    return tret[0]


def amavasya_days(start, end):
    """Civil IST dates whose sunrise falls inside the Amavasya tithi (elongation 348-360).
    Kshaya case (tithi holds no sunrise): assigned to the IST date on which the tithi starts.
    Vriddhi case (two sunrises): first date kept. Each Amavasya appears once."""
    rows = []
    day = start
    in_tithi_prev = False
    while day <= end:
        e = elongation(sunrise_jd(day))
        in_tithi = e >= 348.0
        if in_tithi and not in_tithi_prev:
            rows.append({"date": day, "case": "sunrise"})
        in_tithi_prev = in_tithi
        day += dt.timedelta(days=1)
    # kshaya check: find every new moon, confirm one row lies within +-2 days
    found = {r["date"] for r in rows}
    jd = jd_from_utc(dt.datetime(start.year, start.month, start.day))
    jd_end = jd_from_utc(dt.datetime(end.year, end.month, end.day))
    extra = []
    while jd < jd_end:
        # step to next new moon (elongation crosses 360 -> 0)
        e0 = elongation(jd)
        jd2 = jd + 0.25
        e1 = elongation(jd2)
        if e1 < e0:  # wrapped past 0 => new moon between jd and jd2
            # tithi start: elongation crosses 348, search back up to 2 days
            lo, hi = jd - 2.0, jd2
            for _ in range(60):
                mid = (lo + hi) / 2
                if (elongation(mid) - 348.0) % 360 < 12.0:
                    hi = mid
                else:
                    lo = mid
            start_ist = (utc_from_jd(hi) + IST).date()
            near = any(abs((d - start_ist).days) <= 2 for d in found)
            if not near:
                extra.append({"date": start_ist, "case": "kshaya"})
        jd = jd2
    out = pd.DataFrame(rows + extra).sort_values("date").reset_index(drop=True)
    return out


KETU_NAKSHATRAS = {"Ashwini": (0.0, 40 / 3), "Magha": (120.0, 120 + 40 / 3), "Mula": (240.0, 240 + 40 / 3)}


def jupiter_ketu_periods(start, end, merge_gap_days=60):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    rows = []
    day = start
    while day <= end:
        noon_utc = dt.datetime(day.year, day.month, day.day, 12) - IST
        lon = swe.calc_ut(jd_from_utc(noon_utc), swe.JUPITER, FLAG | swe.FLG_SIDEREAL)[0][0]
        nak = next((n for n, (a, b) in KETU_NAKSHATRAS.items() if a <= lon < b), None)
        rows.append((day, nak))
        day += dt.timedelta(days=1)
    df = pd.DataFrame(rows, columns=["date", "nak"])
    inside = df[df.nak.notna()]
    periods = []
    for _, r in inside.iterrows():
        if periods and (r.date - periods[-1]["end"]).days <= merge_gap_days and r.nak == periods[-1]["nak"]:
            periods[-1]["end"] = r.date
        else:
            periods.append({"nak": r.nak, "start": r.date, "end": r.date})
    return pd.DataFrame(periods)




def mercury_speed(ts_ist):
    utc = ts_ist - pd.Timedelta(hours=5, minutes=30)
    jd = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60)
    return swe.calc_ut(jd, swe.MERCURY, FLAG)[0][3]


def mercury_retrograde_periods(start, end):
    days = pd.date_range(start, end, freq="D")
    retro = np.array([mercury_speed(d + pd.Timedelta(hours=15, minutes=30)) < 0 for d in days])
    out, cur = [], None
    for d, r in zip(days, retro):
        if r and cur is None:
            cur = d
        if not r and cur is not None:
            out.append((cur, d - pd.Timedelta(days=1))); cur = None
    return pd.DataFrame(out, columns=["start", "end"])


if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    s, e = dt.date(2003, 12, 1), dt.date(2026, 11, 30)
    amavasya_days(s, e).to_csv("data/amavasya_dates.csv", index=False)
    mercury_retrograde_periods("2003-12-01", "2026-11-30").to_csv("data/mercury_retrograde_periods.csv", index=False)
    jupiter_ketu_periods(dt.date(2000, 1, 1), e).to_csv("data/jupiter_ketu_periods.csv", index=False)
    print("Wrote the three date files to data/")
