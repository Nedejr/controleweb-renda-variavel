# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

st.set_page_config(
    page_title="ControleWeb - Renda Variável",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

"""
# :material/query_stats: ControleWeb - Renda Variável

## Análise comparativa de ações

Compare facilmente o desempenho de diferentes ações.
"""

""  # Add some space.

cols = st.columns([1, 4])
# Will declare right cell later to avoid showing it when no data.

STOCKS = [
    "ITSA4.SA",
    "WIZC3.SA",
    "SOJA3.SA",
    "TAEE11.SA",
    "GOAU4.SA",
    "CSAN3.SA",
    "VALE3.SA",
    "XPLG11.SA",
    "MXRF11.SA",
    "BTHF11.SA",
    "IRDM11.SA",
    "RECT11.SA",
    "HASH11.SA",
]

DEFAULT_STOCKS = [
    "ITSA4.SA",
    "WIZC3.SA",
    "SOJA3.SA",
    "TAEE11.SA",
    "GOAU4.SA",
    "CSAN3.SA",
    "VALE3.SA",
    "XPLG11.SA",
    "MXRF11.SA",
    "BTHF11.SA",
    "IRDM11.SA",
    "RECT11.SA",
    "HASH11.SA",
]


def stocks_to_str(stocks):
    return ",".join(stocks)


if "tickers_input" not in st.session_state:
    st.session_state.tickers_input = st.query_params.get(
        "stocks", stocks_to_str(DEFAULT_STOCKS)
    ).split(",")


# Callback to update query param when input changes
def update_query_param():
    if st.session_state.tickers_input:
        st.query_params["stocks"] = stocks_to_str(st.session_state.tickers_input)
    else:
        st.query_params.pop("stocks", None)


top_left_cell = cols[0].container(
    border=True, height="stretch", vertical_alignment="center"
)

with top_left_cell:
    # Selectbox for stock tickers
    tickers = st.multiselect(
        "Selecione as ações",
        options=sorted(set(STOCKS) | set(st.session_state.tickers_input)),
        default=st.session_state.tickers_input,
        placeholder="Escolha ações para comparar. Ex: PETR4.SA",
        accept_new_options=True,
    )

# Time horizon selector
horizon_map = {
    "1 Mês": "1mo",
    "3 Meses": "3mo",
    "6 Meses": "6mo",
    "1 Ano": "1y",
    "5 Anos": "5y",
    "10 Anos": "10y",
    "20 Anos": "20y",
}

with top_left_cell:
    # Buttons for picking time horizon
    horizon = st.pills(
        "Período",
        options=list(horizon_map.keys()),
        default="6 Meses",
    )

tickers = [t.upper() for t in tickers]

# Update query param when text input changes
if tickers:
    st.query_params["stocks"] = stocks_to_str(tickers)
else:
    # Clear the param if input is empty
    st.query_params.pop("stocks", None)

if not tickers:
    top_left_cell.info("Escolha algumas ações para comparar", icon=":material/info:")
    st.stop()


right_cell = cols[1].container(
    border=True, height="stretch", vertical_alignment="center"
)


@st.cache_resource(show_spinner=False)
def load_data(tickers, period):
    tickers_obj = yf.Tickers(tickers)
    data = tickers_obj.history(period=period)
    if data is None:
        raise RuntimeError("O YFinance não retornou dados.")
    return data["Close"]


# Load the data
try:
    data = load_data(tickers, horizon_map[horizon])
except yf.exceptions.YFRateLimitError as e:
    st.warning(
        "O YFinance está limitando as requisições :(\nTente novamente mais tarde."
    )
    load_data.clear()  # Remove the bad cache entry.
    st.stop()

empty_columns = data.columns[data.isna().all()].tolist()

if empty_columns:
    st.error(f"Erro ao carregar dados para os tickers: {', '.join(empty_columns)}.")
    st.stop()

# Normalize prices (start at 1)
normalized = data.div(data.iloc[0])

latest_norm_values = {normalized[ticker].iat[-1]: ticker for ticker in tickers}
max_norm_value = max(latest_norm_values.items())
min_norm_value = min(latest_norm_values.items())

bottom_left_cell = cols[0].container(
    border=True, height="stretch", vertical_alignment="center"
)

with bottom_left_cell:
    cols = st.columns(2)
    cols[0].metric(
        "Melhor ação",
        max_norm_value[1],
        delta=f"{round(max_norm_value[0] * 100)}%",
        width="content",
    )
    cols[1].metric(
        "Pior ação",
        min_norm_value[1],
        delta=f"{round(min_norm_value[0] * 100)}%",
        width="content",
    )


# Plot normalized prices
with right_cell:
    st.altair_chart(
        alt.Chart(
            normalized.reset_index().melt(
                id_vars=["Date"], var_name="Ação", value_name="Preço normalizado"
            )
        )
        .mark_line()
        .encode(
            alt.X("Date:T"),
            alt.Y("Preço normalizado:Q").scale(zero=False),
            alt.Color("Ação:N"),
        )
        .properties(height=400)
    )

""
""

# Plot individual stock vs peer average
"""
## Ações individuais vs média do grupo

Para a análise abaixo, a "média do grupo" ao analisar a ação X sempre
exclui a própria ação X.
"""

# if len(tickers) <= 1:
#     st.warning("Escolha 2 ou mais ações para compará-las")
#     st.stop()

NUM_COLS = 4
cols = st.columns(NUM_COLS)

for i, ticker in enumerate(tickers):
    # Calculate peer average (excluding current stock)
    peers = normalized.drop(columns=[ticker])
    peer_avg = peers.mean(axis=1)

    # Create DataFrame with peer average.
    plot_data = pd.DataFrame(
        {
            "Date": normalized.index,
            ticker: normalized[ticker],
            "Média do grupo": peer_avg,
        }
    ).melt(id_vars=["Date"], var_name="Série", value_name="Preço")

    chart = (
        alt.Chart(plot_data)
        .mark_line()
        .encode(
            alt.X("Date:T"),
            alt.Y("Preço:Q").scale(zero=False),
            alt.Color(
                "Série:N",
                scale=alt.Scale(
                    domain=[ticker, "Média do grupo"], range=["red", "gray"]
                ),
                legend=alt.Legend(orient="bottom"),
            ),
            alt.Tooltip(["Date", "Série", "Preço"]),
        )
        .properties(title=f"{ticker} vs Média do grupo", height=300)
    )

    cell = cols[(i * 2) % NUM_COLS].container(border=True)
    cell.write("")
    cell.altair_chart(chart, width="stretch")

    # Create Delta chart
    plot_data = pd.DataFrame(
        {
            "Date": normalized.index,
            "Delta": normalized[ticker] - peer_avg,
        }
    )

    chart = (
        alt.Chart(plot_data)
        .mark_area()
        .encode(
            alt.X("Date:T"),
            alt.Y("Delta:Q").scale(zero=False),
        )
        .properties(title=f"{ticker} - Média do grupo", height=300)
    )

    cell = cols[(i * 2 + 1) % NUM_COLS].container(border=True)
    cell.write("")
    cell.altair_chart(chart, width="stretch")

""
""

"""
## Dados brutos
"""

data
