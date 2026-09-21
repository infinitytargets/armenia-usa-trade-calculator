import streamlit as st
from datetime import date

TODAY = date(2026, 9, 21)

st.set_page_config(page_title="Armenia Dried Fruit Export Calculator", page_icon="🍑", layout="centered")

SOURCES = {
    "arm_src": "https://exim.src.am/en",
    "eu_a2m": "https://trade.ec.europa.eu/access-to-markets/en/my-trade-assistant",
    "us_hts": "https://hts.usitc.gov/",
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

def eu_link(country, hs6):
    return (
        "https://trade.ec.europa.eu/access-to-markets/en/search"
        f"?destination={country}&origin=AM&product={hs6}"
    )

st.title("🍑 Armenia → Export Calculator")
st.caption(f"Dried fruit • official-source-first • checkpoint: {TODAY.isoformat()}")

st.subheader("1. Destination")
destination = st.selectbox("Market", ["European Union", "United States", "China"])

if destination == "European Union":
    eu_country = st.selectbox("EU destination country", list(EU_COUNTRIES))
    destination_code = EU_COUNTRIES[eu_country]
else:
    eu_country = None
    destination_code = None

st.subheader("2. Product")
product_name = st.selectbox("Product", list(PRODUCTS))
hs6, hs_note = PRODUCTS[product_name]
st.caption(
    f"Candidate HS-6: **{hs6}** — {hs_note}. "
    "Final national tariff line must be verified in the official destination tariff."
)

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
st.caption("Planning value only. Actual customs valuation depends on the destination authority and transaction facts.")

st.subheader("6. Import duty")
if destination == "European Union":
    duty_source = eu_link(destination_code, hs6)
    source_name = f"EU Access2Markets — {eu_country}"
elif destination == "United States":
    duty_source = SOURCES["us_hts"]
    source_name = "USITC Harmonized Tariff Schedule"
else:
    duty_source = SOURCES["china_mof"]
    source_name = "China Ministry of Finance"

st.markdown(f"Official tariff source: [{source_name}]({duty_source})")
duty_status = st.selectbox("Duty status", ["MANUAL REVIEW", "VERIFIED", "CONDITIONAL"], index=0)
duty_rate = st.number_input("Verified import duty (%)", min_value=0.0, value=0.0, step=0.10)
duty = customs_value * duty_rate / 100
if duty_status != "VERIFIED":
    st.warning("Duty is not verified. Enter a rate only after checking the official source.")

st.subheader("7. Import tax / VAT")
if destination == "European Union":
    st.caption("EU import VAT is destination-country and product dependent. Do not automatically use the standard VAT rate for food.")
elif destination == "United States":
    st.caption("The USA has no federal VAT. State/local sales tax is separate and is not automatically included here.")
else:
    st.caption("China import VAT must be verified for the exact tariff line and tax treatment.")

tax_status = st.selectbox("Import tax / VAT status", ["MANUAL REVIEW", "VERIFIED", "CONDITIONAL"], index=0)
tax_rate = st.number_input("Verified import tax / VAT (%)", min_value=0.0, value=0.0, step=0.10)
tax_base = customs_value + duty
import_tax = tax_base * tax_rate / 100
if tax_status != "VERIFIED" and tax_rate != 0:
    st.warning("This tax rate is not marked as officially verified.")

st.subheader("8. Customs / other import costs")
broker = st.number_input("Customs broker / clearance (USD)", min_value=0.0, value=100.0, step=25.0)
inspection = st.number_input("Inspection / certification / handling (USD)", min_value=0.0, value=0.0, step=25.0)
other_import = st.number_input("Other import costs (USD)", min_value=0.0, value=0.0, step=25.0)

st.subheader("9. Landed cost")
landed = goods_value + freight + insurance + other_logistics + duty + import_tax + broker + inspection + other_import
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
    st.markdown(f"- [Armenia SRC ExIm — official trade/tariff portal]({SOURCES['arm_src']})")
    st.markdown(f"- [EU Access2Markets]({SOURCES['eu_a2m']})")
    if destination == "European Union":
        st.markdown(f"- [Exact EU query: Armenia → {eu_country} → HS {hs6}]({duty_source})")
    st.markdown(f"- [USITC HTS]({SOURCES['us_hts']})")
    st.markdown(f"- [China Ministry of Finance]({SOURCES['china_mof']})")
    st.info("VERIFIED means the rate was checked against the official source for the exact product classification, Armenian origin, destination and date. The app never silently treats an unverified rate as 0%.")

with st.expander("Calculation breakdown"):
    st.write(f"Goods value: {money(goods_value)}")
    st.write(f"Freight: {money(freight)}")
    st.write(f"Insurance: {money(insurance)}")
    st.write(f"Other logistics: {money(other_logistics)}")
    st.write(f"Planning customs value: {money(customs_value)}")
    st.write(f"Import duty: {money(duty)}")
    st.write(f"Import tax / VAT: {money(import_tax)}")
    st.write(f"Broker / clearance: {money(broker)}")
    st.write(f"Inspection / certification / handling: {money(inspection)}")
    st.write(f"Other import costs: {money(other_import)}")
    st.write(f"Landed cost: {money(landed)}")
    st.write(f"Revenue: {money(revenue)}")
    st.write(f"Gross profit: {money(profit)}")

st.caption("Official-source-first prototype: legal/tariff values are verified separately; commercial logistics and selling-price values are user inputs.")
