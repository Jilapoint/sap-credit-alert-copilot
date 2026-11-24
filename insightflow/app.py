"""InsightFlow: adaptive business analytics demo using Microsoft Foundry Model Router."""
import json
import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="InsightFlow | Microsoft Foundry", page_icon="📊", layout="wide")
st.title("📊 InsightFlow")
st.caption("Intelligent business analytics powered by Microsoft Foundry Model Router | Tech Call demo")

DATA_FILE = Path(__file__).with_name("sales_2026.csv")
if not DATA_FILE.exists():
    st.error("Missing sales_2026.csv. Run: python generate_data.py")
    st.stop()

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_FILE, parse_dates=["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    df["Profit"] = df["Revenue"] - df["Cost"]
    return df

@st.cache_resource
def get_client(endpoint: str):
    # For local development: run `az login` first.
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    project = AIProjectClient(endpoint=endpoint, credential=credential)
    client = project.get_openai_client()
    return client, project, credential


def get_context(df):
    """Precompute numeric facts in Python; use the LLM for interpretation."""
    monthly = df.groupby("Month", as_index=False)[["Revenue", "Cost", "Profit"]].sum()
    by_country = df.groupby("Country", as_index=False)[["Revenue", "Cost", "Profit"]].sum()
    by_category = df.groupby("ProductCategory", as_index=False)[["Revenue", "Cost", "Profit"]].sum()
    by_segment = df.groupby("CustomerSegment", as_index=False)[["Revenue", "Cost", "Profit"]].sum()
    country_month = df.groupby(["Country", "Month"], as_index=False)[["Revenue", "Cost", "Profit"]].sum()
    category_month = df.groupby(["ProductCategory", "Month"], as_index=False)[["Revenue", "Cost", "Profit"]].sum()
    for table in (monthly, by_country, by_category, by_segment, country_month, category_month):
        table["MarginPct"] = (100 * table["Profit"] / table["Revenue"]).round(2)
        for col in ("Revenue", "Cost", "Profit"):
            table[col] = table[col].round(2)
    def records(table):
        return table.to_dict(orient="records")
    return {"currency": "EUR", "year": 2026,
            "all_sales_revenue": round(float(df["Revenue"].sum()), 2),
            "all_sales_profit": round(float(df["Profit"].sum()), 2),
            "monthly": records(monthly), "by_country": records(by_country),
            "by_category": records(by_category), "by_segment": records(by_segment),
            "country_month": records(country_month), "category_month": records(category_month)}

PROMPTS = {
    "1 · Simple — factual": "Quel est le chiffre d'affaires total en France sur 2026 ? Réponds en une phrase avec la valeur exacte.",
    "2 · Intermediate — comparison": "Compare la France, l'Allemagne et l'Espagne sur 2026 : chiffre d'affaires, marge et différences significatives. Donne un petit tableau et deux conclusions.",
    "3 · Complex — strategic": "Le chiffre d'affaires augmente au fil de 2026 mais la marge se détériore au T4. Analyse les facteurs visibles dans les données par mois et par catégorie, distingue constat et hypothèse, puis propose trois actions commerciales priorisées avec les KPI à surveiller.",
}
SYSTEM = ("Tu es un analyste métier senior. Réponds en français à partir des données chiffrées "
          "fournies, sans inventer de faits. Les sommes, marges et agrégats ont été calculés en Python. "
          "Utilise ces valeurs sans les recalculer. Pour les causes, distingue corrélation, observation "
          "et hypothèse. Indique les limites de ce jeu de données fictif. Sois clair et concis.")


def ask_model(client, deployment: str, question: str, facts: dict):
    start = time.perf_counter()
    response = client.responses.create(
        model=deployment,
        instructions=SYSTEM,
        input=f"Question : {question}\n\nDonnées agrégées JSON :\n{json.dumps(facts, ensure_ascii=False)}",
    )
    duration = round(time.perf_counter() - start, 3)
    usage = response.usage
    return {
        "Deployment": deployment,
        "Model selected": response.model,
        "Latency (s)": duration,
        "Input tokens": getattr(usage, "input_tokens", None),
        "Output tokens": getattr(usage, "output_tokens", None),
        "Answer": response.output_text,
        "Question": question,
    }


df = load_data()
facts = get_context(df)
with st.sidebar:
    st.header("Foundry configuration")
    endpoint = st.text_input("Project endpoint", value=os.getenv("PROJECT_ENDPOINT", ""), help="Use the Foundry project endpoint, not the Azure OpenAI endpoint.")
    router = st.text_input("Model Router deployment", value=os.getenv("MODEL_ROUTER_DEPLOYMENT", "model-router"))
    baseline = st.text_input("Fixed model deployment", value=os.getenv("BASELINE_DEPLOYMENT", "gpt-4.1-mini"))
    compare = st.checkbox("Compare against fixed model", value=True)
    st.caption("Authentication: Azure CLI / DefaultAzureCredential. Run `az login` before Streamlit.")

c1, c2, c3 = st.columns(3)
c1.metric("Revenue 2026", f"€{df['Revenue'].sum():,.0f}")
c2.metric("Profit 2026", f"€{df['Profit'].sum():,.0f}")
c3.metric("Margin", f"{100*df['Profit'].sum()/df['Revenue'].sum():.1f}%")

with st.expander("Explore synthetic data", expanded=False):
    st.dataframe(df.head(20), use_container_width=True)
    monthly = df.groupby("Month")[['Revenue', 'Profit']].sum()
    st.line_chart(monthly)

scenario = st.selectbox("Choose the business scenario", list(PROMPTS))
question = st.text_area("Business question", value=PROMPTS[scenario], height=120)

if "history" not in st.session_state:
    st.session_state.history = []

def show_foundry_error(deployment: str, exc: Exception):
    status_code = getattr(exc, "status_code", None)
    st.error(f"Deployment '{deployment}' failed: {type(exc).__name__} ({status_code or 'unknown status'}): {exc}")
    if status_code == 404:
        st.info(
            f"Check that '{deployment}' is the exact **deployment name** in Microsoft Foundry, "
            "not a model name or routing mode. Also verify that the Project endpoint belongs "
            "to the Foundry resource that owns this deployment."
        )
    elif status_code in (401, 403):
        st.info("Check `az login`, your current Azure tenant/subscription, and Foundry RBAC permissions.")
    elif status_code == 429:
        st.info("Check deployment quota, rate limits and available model capacity.")


with st.sidebar:
    if st.button("Test selected deployment(s)", disabled=not bool(endpoint.strip())):
        try:
            test_client, _, _ = get_client(endpoint.strip())
            deployments_to_test = [router.strip()]
            if compare and baseline.strip() and baseline.strip() != router.strip():
                deployments_to_test.append(baseline.strip())
            for deployment in deployments_to_test:
                if not deployment:
                    st.warning("A deployment name is empty.")
                    continue
                try:
                    test_response = test_client.responses.create(
                        model=deployment,
                        input="Réponds simplement : OK."
                    )
                    st.success(f"{deployment}: OK (response model: {test_response.model})")
                except Exception as exc:
                    show_foundry_error(deployment, exc)
        except Exception as exc:
            st.error(f"Connection setup failed: {type(exc).__name__}: {exc}")


if st.button("▶ Analyze", type="primary", disabled=not bool(endpoint.strip())):
    try:
        client, _, _ = get_client(endpoint.strip())
        deployments_to_run = [router.strip()]
        if compare and baseline.strip() and baseline.strip() != router.strip():
            deployments_to_run.append(baseline.strip())
        results = []
        errors = []
        with st.spinner("Calling Microsoft Foundry..."):
            for deployment in deployments_to_run:
                if not deployment:
                    st.warning("A deployment name is empty.")
                    continue
                try:
                    results.append(ask_model(client, deployment, question, facts))
                except Exception as exc:
                    errors.append((deployment, exc))
        if results:
            st.session_state.history.extend(results)
            columns = st.columns(len(results))
            for col, result in zip(columns, results):
                with col:
                    st.subheader(result['Deployment'])
                    st.caption(f"Selected model: **{result['Model selected']}**")
                    st.metric("Latency", f"{result['Latency (s)']} s")
                    st.caption(f"Input: {result['Input tokens']} | Output: {result['Output tokens']} tokens")
                    st.markdown(result['Answer'])
        for deployment, exc in errors:
            show_foundry_error(deployment, exc)
    except Exception as exc:
        st.error(f"Connection setup failed: {type(exc).__name__}: {exc}")
        st.info("Verify the exact Foundry Project endpoint, Azure login and RBAC permissions.")

st.divider()
st.subheader("Benchmark history")
if st.session_state.history:
    history = pd.DataFrame(st.session_state.history)
    st.dataframe(history.drop(columns=["Answer", "Question"]), use_container_width=True)
    st.download_button("Download benchmark CSV", history.to_csv(index=False).encode("utf-8"),
                       file_name="model_router_benchmark.csv", mime="text/csv")
    st.caption("Tokens and latency are measured. Prices and answer quality require separate evaluation; no cost savings are assumed.")
else:
    st.info("Run at least one scenario to populate the benchmark table.")
