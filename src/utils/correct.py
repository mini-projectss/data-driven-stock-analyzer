#!/usr/bin/env python3
"""
resolve_yahoo_tickers.py

Reads tickers.txt (one entry per line, your current list),
queries Yahoo Finance search API for each line, and writes:

- corrected_tickers.txt  (one resolved ticker per line, e.g. ACC.BO)
- ticker_resolution_report.csv  (original, resolved_symbol, exchange, score, name, url)

Notes:
- Prefers BSE/BOM/.BO results, falls back to NSE/.NS if needed.
- Marks entries with no good match so you can manually inspect them.
- Requires `requests` and `pandas` in your virtualenv.
"""

import argparse
import json
import time
import urllib.parse
import requests
import pandas as pd

YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search?q={query}"

def search_yahoo(query):
    url = YAHOO_SEARCH_URL.format(query=urllib.parse.quote(query))
    headers = {
        "User-Agent": "python-requests/2.x (+https://github.com/)",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()

def best_pick(results, prefer_exchanges=("BOM","BSE","BOM:XBOM")):
    """
    results: the 'quotes' list from Yahoo search JSON.
    prefer_exchanges: tuple of exchange codes we'd prefer (BSE/BOM first).
    Returns (symbol, exchange, name, score, url) or (None, ...) if none.
    """
    if not results:
        return (None, None, None, 0.0, None)

    # Score each result: prefer exact symbol match (rare), then prefer exchange in prefer_exchanges
    best = None
    best_score = -1.0
    for r in results:
        symbol = r.get("symbol")
        exch = r.get("exchDisp") or r.get("exchange") or r.get("exchangeDisp")
        name = r.get("shortname") or r.get("longname") or r.get("name") or ""
        # base score from Yahoo relevance if available
        score = float(r.get("score", 0.0))
        # boost if exchange is preferred
        if exch:
            if any(p in str(exch).upper() for p in prefer_exchanges):
                score += 50.0
        # boost if symbol ends with .BO
        if symbol and symbol.upper().endswith(".BO"):
            score += 20.0
        # if name looks like the query, small boost
        # (we'll rely mainly on Yahoo's score)
        if score > best_score:
            best_score = score
            best = (symbol, exch, name, score, r.get("quoteType") or r.get("typeDisp") or r.get("exchangeTimezoneShortName"))
    return best if best_score > -1 else (None, None, None, 0.0, None)

def normalize_input_line(line):
    # remove trailing/leading whitespace, remove repeated dots, keep original for report
    s = line.strip()
    # strip any trailing .BO/.NS if user already included them — search with and without too
    s_no_suffix = s
    for suff in (".BO", ".NS", ".NASDAQ", ".NYSE", ".LS", ".L"):
        if s_no_suffix.upper().endswith(suff):
            s_no_suffix = s_no_suffix[: -len(suff)]
            break
    # replace common concatenation tokens to spaces (e.g. "INDIALTD" -> "INDIA LTD")
    # Basic heuristics: insert spaces before 'LTD', 'INDIA', 'LIMITED', 'INDIALTD'
    replacements = [("INDIALTD","INDIA LTD"), ("LTD","LTD"), ("INDIA","INDIA"), ("LIMITED","LIMITED")]
    s2 = s_no_suffix
    for a,b in replacements:
        s2 = s2.replace(a, " " + b + " ").replace(a.lower(), " " + b + " ")
    # collapse multiple spaces
    s2 = " ".join(s2.split())
    return s, s2

def resolve_all(input_file, out_txt="corrected_tickers.txt", out_csv="ticker_resolution_report.csv",
                pause=0.6):
    with open(input_file, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    rows = []
    resolved_symbols = []

    for i,ln in enumerate(lines, 1):
        orig, query_term = normalize_input_line(ln)
        # try a few queries in order:
        candidates_to_try = [
            query_term,
            orig,
            query_term + " bse",
            query_term + " bombay stock exchange",
            query_term + " company",
        ]
        best = (None, None, None, 0.0, None)
        for q in candidates_to_try:
            try:
                data = search_yahoo(q)
                quotes = data.get("quotes", []) + data.get("news", [])
                pick = best_pick(quotes)
                if pick and pick[0]:
                    # accept if score high enough or exchange is BSE
                    sym, exch, name, score, extra = pick
                    # simple acceptance criteria
                    if (sym and (str(exch).upper().find("BOM") >= 0 or str(sym).upper().endswith(".BO"))) or score > 20.0:
                        best = pick
                        break
                    # keep as fallback if score > current best
                    if pick[3] > best[3]:
                        best = pick
            except Exception as e:
                # transient error — print and continue
                print(f"[WARN] search failed for '{q}': {e}")
            time.sleep(pause)

        resolved = best[0] if best and best[0] else None
        exch = best[1] if best else None
        name = best[2] if best else None
        score = best[3] if best else 0.0
        url_hint = f"https://finance.yahoo.com/quote/{resolved}" if resolved else None

        if resolved:
            resolved_symbols.append(resolved)
        else:
            resolved_symbols.append("")  # placeholder

        rows.append({
            "original": orig,
            "query_term": query_term,
            "resolved_symbol": resolved or "",
            "exchange": exch or "",
            "name": name or "",
            "score": score,
            "yahoo_url": url_hint
        })
        print(f"[{i}/{len(lines)}] {orig} -> {resolved or 'NOT FOUND'} (score {score})")

    # write outputs
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    # write corrected list — only non-empty resolved symbols; for blanks, keep original commented for manual fix
    with open(out_txt, "w", encoding="utf-8") as f:
        for r in rows:
            if r["resolved_symbol"]:
                f.write(r["resolved_symbol"] + "\n")
            else:
                f.write("# NEED_MANUAL: " + r["original"] + "\n")

    print("Wrote:", out_txt, out_csv)
    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resolve company-name-like tickers to Yahoo Finance symbols.")
    parser.add_argument("--tickers", default="tickers.txt", help="Input file (one entry per line).")
    parser.add_argument("--out-txt", default="corrected_tickers.txt", help="Output corrected tickers TXT")
    parser.add_argument("--out-csv", default="ticker_resolution_report.csv", help="Detailed CSV report")
    parser.add_argument("--pause", type=float, default=0.6, help="Seconds pause between Yahoo queries (politeness)")
    args = parser.parse_args()

    resolve_all(args.tickers, out_txt=args.out_txt, out_csv=args.out_csv, pause=args.pause)
