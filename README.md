# Armenia ↔ USA Trade Calculator

## Run on Mac

```bash
cd /path/to/armenia_usa_trade_calculator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The browser will open the local calculator.

## What is verified in this version

### Handmade scented soy candle — Armenia → USA
- US HTS candidate: `3406.00.0000` for the described soy candle profile, supported by CBP NY N339704.
- US Column 1 general duty: 0%.
- The IEEPA reciprocal tariff actions were terminated by EO 14389 in February 2026.
- The temporary Section 122 10% surcharge was effective only through July 24, 2026; therefore it is not added for the 2026-09-21 checkpoint.
- Armenia export VAT: 0% for goods exported under customs procedure Export.

### USA → Armenia
- EAEU HS: `3406 00 000 0`.
- EAEU Common Customs Tariff: 6.5% import duty.
- Armenia VAT: 20%.
- For import VAT, the tax base is customs value + customs duty (+ excise where applicable).

## Important

This is a calculation/research tool, not a customs declaration or binding classification decision. Exact classification and origin can change the result. The app therefore shows source evidence and warns before live use.

## Next production stage

- automated official-source retrieval;
- effective-date/versioned tariff database;
- Chapter 99 / Section 232 / anti-dumping / countervailing modules;
- country-of-origin rules;
- restrictions and permit database;
- customs-fee tables;
- PDF/Excel export;
- saved products and shipment scenarios;
- audit trail for every numeric value.
