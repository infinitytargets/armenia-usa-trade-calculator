import json
import re
from datetime import date
from urllib.parse import urlencode

import requests
import streamlit as st

TODAY = date(2026, 9, 21)
REQUEST_TIMEOUT = 15

st.set_page_config(page_title="Armenia Dried Fruit Export Calculator", page_icon="🍑", layout="centered")

SOURCES = {
    "arm_src": "https://exim.src.am/en",
    "eu_a2m": "https://trade.ec.europa.eu/access-to-markets/en/my-trade-assistant",
    "us_hts": "https://hts.usitc.gov/",
    "us_api": "https://hts.usitc.gov/reststop/search",
    "china_mof": "https://www.mof.gov.cn/jrttts/202404/t20240429_3933789.htm",
}

PRODUCTS = {
    "Dried apricots": ("081310", "Dried apricots"),
    "Raisins / dried grapes": ("080620", "Dried grapes / raisins"),
    "Dried figs": ("080420", "Figs, fresh or dried"),
    "Dried apples": ("081330", "Dried apples"),
    "Dried prunes": ("081320", "Prunes"),
    "Dried peaches": ("081340", "Other dried fruit; exact national line requires verification"),
    "Dried persimmons": ("081340", "Other dried fruit; exact national line requires verification"),
    "Mixed dried fruit": ("081350", "Mixtures of nuts or dried fruits"),
    "Other dried fruit": ("081340", "Other dried fruit; exact national line requires verification"),
}

EU_COUNTRIES = {
    "Germany": "DE", "France": "FR", "Italy": "IT", "Netherlands": "NL",
    "Poland": "PL", "Spain": "ES", "Belgium": "BE", "Austria": "AT",
    "Greece": "GR", "Czech Republic": "CZ",
}

def money(v):
    return f"USD {v:,.2f}"

def pct(v):
    return f"{v:.2f}%"

def extract_text_values(obj):
    values = []
    if isinstance(obj, dict):
        for value in obj.values():
            values.extend(extract_text_values(value))
    elif isinstance(obj, list):
        for value in obj:
            values.extend(extract_text_values(value))
    elif isinstance(obj, str):
        values.append(obj)
    return values

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_us_tariff(hs6):
    """Read current USITC HTS data and inspect Chapter 99/additional measures."""
    try:
        response = requests.get(
            SOURCES["us_api"],
            params={"keyword": hs6},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        return {"status": "SOURCE ERROR", "rate": None, "additional_rate": None, "message": str(exc), "source": SOURCES["us_api"]}

    texts = extract_text_values(data)
    matching = [x for x in texts if hs6.replace(".", "") in x.replace(".", "")]
    rate_candidates = []
    for text_value in matching + texts:
        for m in re.finditer(r"(?i)(?:MFN|general|column\s*1)[^%]{0,120}?(\d+(?:\.\d+)?)\s*%", text_value):
            rate_candidates.append(float(m.group(1)))
        if re.search(r"(?i)\bfree\b", text_value) and re.search(r"(?i)(MFN|general|column\s*1)", text_value):
            rate_candidates.append(0.0)

    rate = rate_candidates[0] if rate_candidates else None

    # Chapter 99 contains temporary/additional import measures. We expose a
    # review flag unless the official response can be mapped to an exact line.
    chapter99 = []
    for text_value in texts:
        if re.search(r"(?i)\b99\d{4}", text_value) and re.search(r"(?i)(additional|surcharge|tariff|duty)", text_value):
            chapter99.append(text_value[:500])

    if rate is not None:
        return {
            "status": "VERIFIED",
            "rate": rate,
            "additional_rate": None,
            "additional_status": "MANUAL REVIEW" if chapter99 else "REVIEW CHAPTER 99",
            "chapter99_matches": chapter99[:5],
            "message": "Base rate retrieved from the official USITC HTS. Chapter 99/additional measures require exact line and origin applicability review.",
            "source": SOURCES["us_api"],
        }

    return {
        "status": "MANUAL REVIEW",
        "rate": None,
        "additional_rate": None,
        "additional_status": "MANUAL REVIEW",
        "chapter99_matches": chapter99[:5],
        "message": "USITC responded, but the application could not safely map the returned data to a single legal rate.",
        "source": SOURCES["us_api"],
    }

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_eu_tariff(country_code, hs6):
    """Read the live Access2Markets results page for Armenia origin."""
    params = {"destination": country_code, "origin": "AM", "product": hs6}
    url = "https://trade.ec.europa.eu/access-to-markets/en/results?" + urlencode(params)
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "ArmeniaTradeCalculator/1.0"})
        response.raise_for_status()
        text = re.sub(r"\\s+", " ", response.text)
    except Exception as exc:
        return {"status": "SOURCE ERROR", "rate": None, "message": str(exc), "source": url}

    # Access2Markets publishes "Third country duty" followed by the tariff.
    patterns = [
        r"Third country duty.{0,1000}?Tariff:\\s*</?[^>]*>?(\\d+(?:\\.\\d+)?)%",
        r"Third country duty.{0,1000}?(\\d+(?:\\.\\d+)?)%",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return {
                "status": "VERIFIED",
                "rate": float(match.group(1)),
                "message": "Retrieved from the official EU Access2Markets results page.",
                "source": url,
            }

    return {
        "status": "MANUAL REVIEW",
        "rate": None,
        "message": "Access2Markets was reached, but no single third-country duty was safely extracted.",
        "source": url,
    }

TEDB_WSDL = "https://ec.europa.eu/taxation_customs/tedb/ws/VatRetrievalService"
CHINA_CUSTOMS_TAX_LOOKUP = "https://online.customs.gov.cn/ociswebserver/pages/jckspsl/index.html"

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_eu_vat(country_code, hs6):
    """Use the European Commission TEDB SOAP service for VAT rates by CN code."""
    cn_code = hs6 + "00"
    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
 xmlns:urn="urn:ec.europa.eu:taxud:tedb:services:v1:IVatRetrievalService"
 xmlns:urn1="urn:ec.europa.eu:taxud:tedb:services:v1:IVatRetrievalService:types">
 <soapenv:Header/>
 <soapenv:Body>
  <urn:retrieveVatRatesReqMsg>
   <urn1:memberStates><urn1:isoCode>{country_code}</urn1:isoCode></urn1:memberStates>
   <urn1:from>{TODAY.isoformat()}</urn1:from>
   <urn1:to>{TODAY.isoformat()}</urn1:to>
   <urn1:cnCodes><urn1:value>{cn_code}</urn1:value></urn1:cnCodes>
   <urn1:categories><urn1:identifier>FOODSTUFFS</urn1:identifier></urn1:categories>
  </urn:retrieveVatRatesReqMsg>
 </urn:Body>
</soapenv:Envelope>"""
    try:
        response = requests.post(
            TEDB_WSDL,
            data=envelope.encode("utf-8"),
            headers={
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "urn:ec.europa.eu:taxud:tedb:services:v1/VatRetrievalService/RetrieveVatRates",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        xml = response.text
        standard = re.search(r"<(?:[^:>]+:)?type>STANDARD</(?:[^:>]+:)?type>.*?<rate>.*?<value>([0-9.]+)</", xml, re.S)
        reduced = re.findall(r"<(?:[^:>]+:)?type>REDUCED</(?:[^:>]+:)?type>.*?<rate>.*?<value>([0-9.]+)</", xml, re.S)
        rates = [float(x) for x in reduced]
        if standard:
            rates.append(float(standard.group(1)))
        if rates:
            return {
                "status": "VERIFIED",
                "rate": min(rates),
                "message": f"Retrieved from European Commission TEDB for CN {cn_code}; FOODSTUFFS category included.",
                "source": TEDB_WSDL,
            }
    except Exception as exc:
        return {"status": "SOURCE ERROR", "rate": None, "message": str(exc), "source": TEDB_WSDL}
    return {
        "status": "MANUAL REVIEW",
        "rate": None,
        "message": "TEDB responded, but no unambiguous VAT rate was returned for this CN/category/date.",
        "source": TEDB_WSDL,
    }

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_china_tariff(hs6):
    return {
        "status": "MANUAL REVIEW",
        "rate": None,
        "message": "China Customs publishes the tariff/tax lookup, but the public page requires an interactive query. No tariff is guessed.",
        "source": CHINA_CUSTOMS_TAX_LOOKUP,
    }

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_china_vat(hs6):
    return {
        "status": "MANUAL REVIEW",
        "rate": None,
        "message": "China Customs must confirm the exact 10-digit line and applicable import VAT (9%/13% or another special treatment).",
        "source": CHINA_CUSTOMS_TAX_LOOKUP,
    }

def get_live_tariff(destination, hs6, eu_country=None):
    if destination == "United States":
        return fetch_us_tariff(hs6)
    if destination == "European Union":
        return fetch_eu_tariff(EU_COUNTRIES[eu_country], hs6)
    return fetch_china_tariff(hs6)

def get_live_tax(destination, hs6, eu_country=None):
    if destination == "European Union":
        return fetch_eu_vat(EU_COUNTRIES[eu_country], hs6)
    if destination == "United States":
        return {
            "status": "VERIFIED",
            "rate": 0.0,
            "message": "No US federal VAT. State/local sales taxes are separate from federal import duty and are not included.",
            "source": SOURCES["us_hts"],
        }
    return fetch_china_vat(hs6)

st.title("🍑 Armenia → Export Calculator")
st.caption(f"Dried fruit • live official-source tariff lookup • checkpoint: {TODAY.isoformat()}")

st.subheader("1. Destination")
destination = st.selectbox("Market", ["European Union", "United States", "China"])

if destination == "European Union":
    eu_country = st.selectbox("EU destination country", list(EU_COUNTRIES))
else:
    eu_country = None

st.subheader("2. Product")
product_name = st.selectbox("Product", list(PRODUCTS))
hs6, hs_note = PRODUCTS[product_name]
st.caption(f"HS-6 candidate: **{hs6}** — {hs_note}")

st.subheader("3. Shipment")
quantity_kg = st.number_input("Quantity (kg)", min_value=0.01, value=1000.0, step=100.0)
price_per_kg = st.number_input("Goods price (USD/kg)", min_value=0.0, value=3.20, step=0.10)
goods_value = quantity_kg * price_per_kg

st.subheader("4. Logistics")
freight = st.number_input("Freight to import point (USD)", min_value=0.0, value=700.0, step=50.0)
insurance = st.number_input("Insurance (USD)", min_value=0.0, value=50.0, step=10.0)
other_logistics = st.number_input("Other logistics in planning customs value (USD)", min_value=0.0, value=0.0, step=25.0)

st.subheader("5. Customs value")
customs_value = goods_value + freight + insurance + other_logistics
st.metric("Planning customs value", money(customs_value))
st.caption("Planning value only. Actual customs valuation depends on destination rules and transaction facts.")

st.subheader("6. Official tariff lookup")
with st.spinner("Checking official tariff source..."):
    tariff = get_live_tariff(destination, hs6, eu_country)

if tariff["status"] == "VERIFIED":
    duty_rate = tariff["rate"]
    st.success(f"Official tariff found: **{pct(duty_rate)}**")
else:
    duty_rate = st.number_input("Import duty — manual fallback (%)", min_value=0.0, value=0.0, step=0.10)
    st.warning(f"{tariff['status']}: {tariff['message']}")

st.caption(f"Source: [{tariff['source']}]({tariff['source']})")
duty = customs_value * duty_rate / 100

st.subheader("7. Import tax / VAT")
with st.spinner("Checking official tax source..."):
    tax_info = get_live_tax(destination, hs6, eu_country)

if tax_info["status"] == "VERIFIED":
    tax_rate = tax_info["rate"]
    st.success(f"Official import tax / VAT found: **{pct(tax_rate)}**")
else:
    tax_rate = st.number_input("Import tax / VAT — manual fallback (%)", min_value=0.0, value=0.0, step=0.10)
    st.warning(f"{tax_info['status']}: {tax_info['message']}")

st.caption(f"Tax source: [{tax_info['source']}]({tax_info['source']})")
tax_base = customs_value + duty
import_tax = tax_base * tax_rate / 100

st.subheader("8. Customs / other import costs")
broker = st.number_input("Customs broker / clearance (USD)", min_value=0.0, value=100.0, step=25.0)
inspection = st.number_input("Inspection / certification / handling (USD)", min_value=0.0, value=0.0, step=25.0)
other_import = st.number_input("Other import costs (USD)", min_value=0.0, value=0.0, step=25.0)

st.subheader("9. Landed cost")
landed = goods_value + freight + insurance + other_logistics + duty + additional_duty + import_tax + broker + inspection + other_import
landed_per_kg = landed / quantity_kg
st.metric("Landed cost", money(landed))
st.metric("Landed cost / kg", money(landed_per_kg))

st.subheader("10. Selling price")
selling_per_kg = st.number_input("Selling price (USD/kg)", min_value=0.0, value=7.00, step=0.10)
revenue = quantity_kg * selling_per_kg
profit = revenue - landed
profit_per_kg = profit / quantity_kg
margin = profit / revenue * 100 if revenue else 0.0

st.subheader("11. Final result")
a, b, c, d = st.columns(4)
a.metric("Landed / kg", money(landed_per_kg))
b.metric("Selling / kg", money(selling_per_kg))
c.metric("Profit / kg", money(profit_per_kg))
d.metric("Margin", pct(margin))

if profit >= 0:
    st.success(f"Gross profit for this shipment: {money(profit)}")
else:
    st.error(f"Gross loss for this shipment: {money(abs(profit))}")

with st.expander("Official sources & audit"):
    st.markdown(f"- [Armenia SRC ExIm]({SOURCES['arm_src']})")
    st.markdown(f"- [EU Access2Markets]({SOURCES['eu_a2m']})")
    st.markdown(f"- [USITC HTS]({SOURCES['us_hts']})")
    st.markdown(f"- [USITC HTS REST API]({SOURCES['us_api']})")
    st.markdown(f"- [China Ministry of Finance]({SOURCES['china_mof']})")
    st.write(f"Tariff status: **{tariff['status']}**")
    st.write(f"Tariff source: {tariff['source']}")
    st.write(f"Tariff message: {tariff['message']}")
    if destination == "United States":
        st.write(f"Additional measures status: **{tariff.get('additional_status', 'MANUAL REVIEW')}**")
        for item in tariff.get("chapter99_matches", []):
            st.caption(item)
    st.write(f"Tax status: **{tax_info['status']}**")
    st.write(f"Tax source: {tax_info['source']}")
    st.write(f"Tax message: {tax_info['message']}")
    st.info("Legal rates are never silently assumed to be 0%. If an official source cannot safely map the exact product/date, the calculator switches to MANUAL REVIEW.")

with st.expander("Calculation breakdown"):
    st.write(f"Goods value: {money(goods_value)}")
    st.write(f"Freight: {money(freight)}")
    st.write(f"Insurance: {money(insurance)}")
    st.write(f"Other logistics: {money(other_logistics)}")
    st.write(f"Planning customs value: {money(customs_value)}")
    st.write(f"Import duty: {money(duty)}")
    st.write(f"Additional duty / Chapter 99: {money(additional_duty)}")
    st.write(f"Import tax / VAT: {money(import_tax)}")
    st.write(f"Broker / clearance: {money(broker)}")
    st.write(f"Inspection / certification / handling: {money(inspection)}")
    st.write(f"Other import costs: {money(other_import)}")
    st.write(f"Landed cost: {money(landed)}")
    st.write(f"Revenue: {money(revenue)}")
    st.write(f"Gross profit: {money(profit)}")
