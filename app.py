import streamlit as st
from datetime import date

TODAY = date(2026, 9, 21)

SOURCES = {
    "usitc": "https://hts.usitc.gov/",
    "cbp_candle": "https://rulings.cbp.gov/ruling/ny339704",
    "eec_ch34": "https://eec.eaeunion.org/upload/files/catr/ett/ru.34_2022_10.10.2022.pdf",
    "arm_exim": "https://exim.src.am/en",
    "arm_tax": "https://www.arlis.am/ru/acts/205620",
    "whitehouse_ieepa_end": "https://www.whitehouse.gov/presidential-actions/2026/02/ending-certain-tariff-actions/",
    "whitehouse_section122": "https://www.whitehouse.gov/presidential-actions/2026/02/imposing-a-temporary-import-surcharge-to-address-fundamental-international-payments-problems/",
}

PRODUCTS = {
    "Handmade scented soy candle": {
        "arm_hs": "3406 00 000 0",
        "us_hts": "3406.00.0000",
        "arm_duty": 6.5,
        "us_base_duty": 0.0,
        "arm_vat": 20.0,
        "us_general_extra": 0.0,
        "classification_status": "VERIFIED FOR DESCRIBED CANDLE",
        "classification_note": "CBP NY N339704 covers a poured natural soy-wax candle with fragrance oils, cotton wick and glass jar. Other constructions/decorative products can classify differently.",
    },
}


def money(v):
    return f"${v:,.2f}"


def pct(v):
    return f"{v:.2f}%"


def calculate_us(goods, freight, insurance, duty_rate, extra_rate, broker, mpf, hmf):
    customs_value = goods + freight + insurance
    duty = customs_value * duty_rate / 100
    extra = customs_value * extra_rate / 100
    fees = broker + mpf + hmf
    landed = customs_value + duty + extra + fees
    return customs_value, duty, extra, fees, landed


def calculate_arm(goods, freight, insurance, duty_rate, vat_rate, broker):
    customs_value = goods + freight + insurance
    duty = customs_value * duty_rate / 100
    vat_base = customs_value + duty
    vat = vat_base * vat_rate / 100
    landed = customs_value + duty + vat + broker
    return customs_value, duty, vat, landed

st.set_page_config(page_title="AM ↔ US Trade Calculator", page_icon="🧾", layout="wide")
st.title("🇦🇲 Armenia ↔ 🇺🇸 USA Trade Calculator")
st.caption(f"Official-source-first prototype • legal data checkpoint: {TODAY.isoformat()}")

with st.sidebar:
    st.header("Shipment")
    direction = st.radio("Direction", ["Armenia → USA", "USA → Armenia"])
    product_name = st.selectbox("Product profile", list(PRODUCTS.keys()))
    p = PRODUCTS[product_name]

    st.subheader("Commercial values")
    goods = st.number_input("Goods value (USD)", min_value=0.0, value=2500.0, step=100.0)
    freight = st.number_input("Freight to customs border (USD)", min_value=0.0, value=500.0, step=50.0)
    insurance = st.number_input("Insurance (USD)", min_value=0.0, value=0.0, step=10.0)
    quantity = st.number_input("Units", min_value=1, value=100, step=1)

    st.subheader("Commercial result")
    markup = st.number_input("Markup on landed cost (%)", min_value=0.0, value=100.0, step=5.0)

    st.subheader("Real-world fees")
    broker = st.number_input("Broker / customs clearance (USD)", min_value=0.0, value=0.0, step=25.0)
    mpf = st.number_input("US MPF (USD)", min_value=0.0, value=0.0, step=5.0)
    hmf = st.number_input("US HMF (USD)", min_value=0.0, value=0.0, step=5.0)

if direction == "Armenia → USA":
    st.header("Armenia → USA")

    a, b, c, d = st.columns(4)
    a.metric("US HTS", p["us_hts"])
    b.metric("US base duty", pct(p["us_base_duty"]))
    c.metric("Current general extra", pct(p["us_general_extra"]))
    d.metric("Armenian export VAT", "0%")

    st.success("For the selected candle profile, the tariff stack currently modeled is 0% US base duty + 0% general IEEPA/Section-122 surcharge.")

    cv, duty, extra, fees, landed = calculate_us(
        goods, freight, insurance,
        p["us_base_duty"], p["us_general_extra"], broker, mpf, hmf
    )
    sell = landed * (1 + markup / 100)
    profit = sell - landed

    st.subheader("Calculation")
    cols = st.columns(6)
    cols[0].metric("Customs value", money(cv))
    cols[1].metric("US base duty", money(duty))
    cols[2].metric("Extra tariff", money(extra))
    cols[3].metric("Fees entered", money(fees))
    cols[4].metric("Landed cost", money(landed))
    cols[5].metric("Target selling", money(sell))

    if quantity:
        st.caption(f"Landed cost per unit: {money(landed / quantity)} • Target selling per unit: {money(sell / quantity)} • Gross profit: {money(profit)}")

    st.subheader("Evidence / legal status")
    rows = [
        ["US classification", p["us_hts"], "VERIFIED", "CBP NY N339704", SOURCES["cbp_candle"]],
        ["US Column 1 base duty", "0%", "VERIFIED", "USITC HTS", SOURCES["usitc"]],
        ["IEEPA reciprocal additional duty", "Terminated Feb. 2026", "VERIFIED", "White House EO 14389", SOURCES["whitehouse_ieepa_end"]],
        ["Section 122 temporary surcharge", "Ended July 24, 2026", "VERIFIED", "White House proclamation", SOURCES["whitehouse_section122"]],
        ["Armenia export VAT", "0% for goods exported under customs procedure Export", "VERIFIED", "Armenia Tax Code Art. 65", SOURCES["arm_tax"]],
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True, column_config={
        0: "Item", 1: "Value", 2: "Status", 3: "Authority", 4: st.column_config.LinkColumn("Source")
    })

    st.warning("Before a live customs declaration, verify the exact origin, product construction, packaging/set configuration and any Chapter 99 measures on the entry date. The app never silently invents a tariff.")

else:
    st.header("USA → Armenia")

    a, b, c = st.columns(3)
    a.metric("EAEU / Armenia HS", p["arm_hs"])
    b.metric("Import duty", pct(p["arm_duty"]))
    c.metric("VAT", pct(p["arm_vat"]))

    cv, duty, vat, landed = calculate_arm(goods, freight, insurance, p["arm_duty"], p["arm_vat"], broker)
    sell = landed * (1 + markup / 100)

    cols = st.columns(5)
    cols[0].metric("Customs value", money(cv))
    cols[1].metric("Duty", money(duty))
    cols[2].metric("VAT", money(vat))
    cols[3].metric("Landed cost", money(landed))
    cols[4].metric("Target selling", money(sell))

    st.caption(f"VAT base = customs value + customs duty, per Armenia Tax Code. For the standard case modeled here: {money(cv)} + {money(duty)} = {money(cv + duty)}.")

    rows = [
        ["EAEU HS classification", p["arm_hs"], "VERIFIED", "EEC Common Customs Tariff", SOURCES["eec_ch34"]],
        ["Import customs duty", "6.5%", "VERIFIED", "EEC Common Customs Tariff", SOURCES["eec_ch34"]],
        ["Import VAT rate", "20%", "VERIFIED", "Armenia Tax Code Art. 63", SOURCES["arm_tax"]],
        ["VAT import tax base", "Customs value + customs duty (+ excise if applicable)", "VERIFIED", "Armenia Tax Code", SOURCES["arm_tax"]],
        ["SRC ExIm verification portal", "Official product/HS profile lookup", "VERIFIED SOURCE", "Armenia SRC", SOURCES["arm_exim"]],
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True, column_config={
        0: "Item", 1: "Value", 2: "Status", 3: "Authority", 4: st.column_config.LinkColumn("Source")
    })

st.divider()
st.subheader("Product classification warning")
st.write(p["classification_note"])

st.subheader("Architecture for the production version")
st.markdown("""
**Do not build this as a static tariff table.** The correct software architecture is:

1. **Product intake** — URL, description, material, function, dimensions, packaging, country of origin.
2. **HS engine** — generate candidate codes, not one blind answer.
3. **Authority verification** — USITC/CBP for US; SRC ExIm/EEC/Armenian legislation for Armenia.
4. **Tariff stack** — base duty + Chapter 99/Section 232/other measures + preferential treatment + exemptions.
5. **Tax engine** — VAT/excise and the correct tax base.
6. **Origin engine** — shipping country is not automatically country of origin.
7. **Compliance engine** — permits, restrictions, labeling and special controls.
8. **Evidence database** — every number stores source URL, authority, effective date, retrieval date and confidence/status.
9. **Calculator** — customs value → duty → taxes → fees → landed cost → unit cost → markup/profit.
10. **Audit mode** — user can see exactly why every number was used.

Allowed statuses: **VERIFIED**, **NOT VERIFIED**, **MANUAL REVIEW**, **EXPIRED**. Never replace NOT VERIFIED with an estimate without explicitly labeling it as an estimate.
""")

st.info("This prototype is intentionally conservative: it calculates only from values with an identified legal/source basis and lets the user enter real logistics/clearance fees rather than pretending those costs are fixed.")
