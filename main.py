import marimo

__generated_with = "0.25.1"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import plotly.express as px

    return mo, px


@app.cell(hide_code=True)
def _(mo):
    volume_gb = mo.ui.slider(
        start=1, stop=2000, value=50, step=10, label="Volume de données (Go)"
    )
    plage_horaire = mo.ui.slider(
        start=1, stop=24, value=10, step=1, label="Plage horaire (h/jour)"
    )
    frequence = mo.ui.dropdown(
        options=[
            "1x/jour",
            "Toutes les heures",
            "Toutes les 30 min",
            "Toutes les 5 min",
            "En continu / Live",
        ],
        value="Toutes les 30 min",
        label="Fréquence des requêtes",
    )
    return frequence, plage_horaire, volume_gb


@app.cell(hide_code=True)
def _(frequence, mo, plage_horaire, px, volume_gb):
    days_in_month = 30
    storage_price_per_tb = 23  # € / To
    volume_tb = volume_gb.value / 1000.0
    storage_cost = volume_tb * storage_price_per_tb

    freq_val = frequence.value
    ph_val = plage_horaire.value

    if freq_val == "1x/jour":
        queries_per_day = 1
    elif freq_val == "Toutes les heures":
        queries_per_day = ph_val * 1
    elif freq_val == "Toutes les 30 min":
        queries_per_day = ph_val * 2
    elif freq_val == "Toutes les 5 min":
        queries_per_day = ph_val * 12
    else:
        queries_per_day = ph_val * 60

    active_hours_per_day = queries_per_day * (1 / 60)
    active_hours_per_day = min(active_hours_per_day, ph_val)
    active_hours_month = active_hours_per_day * days_in_month

    rds_cost = 30 + storage_cost

    athena_scan_cost = (queries_per_day * (volume_tb * 0.10) * 5) * days_in_month
    athena_cost = athena_scan_cost + storage_cost

    total_scanned_bq = (queries_per_day * (volume_tb * 0.10)) * days_in_month
    billable_scanned_bq = max(0, total_scanned_bq - 1.0)
    bq_scan_cost = billable_scanned_bq * 6.25
    bq_cost = bq_scan_cost + storage_cost

    snowflake_cost = (active_hours_month * 2.60) + storage_cost
    redshift_cost = (active_hours_month * 2.88) + storage_cost
    clickhouse_cost = (active_hours_month * 0.35) + storage_cost
    fabric_cost = (active_hours_month * 0.36) + storage_cost

    if volume_gb.value <= 10 and active_hours_per_day <= 2:
        motherduck_cost = 0.0
    else:
        motherduck_cost = (volume_tb * 10) + (active_hours_month * 0.10)

    moteurs = [
        "RDS PostgreSQL",
        "Amazon Athena",
        "Google BigQuery",
        "Snowflake (XS)",
        "Redshift Serverless",
        "ClickHouse Cloud",
        "Microsoft Fabric (F2)",
        "MotherDuck",
    ]

    couts = [
        rds_cost,
        athena_cost,
        bq_cost,
        snowflake_cost,
        redshift_cost,
        clickhouse_cost,
        fabric_cost,
        motherduck_cost,
    ]

    data = {"Moteur": moteurs, "Coût Mensuel (€)": couts}

    fig = px.bar(
        data,
        x="Coût Mensuel (€)",
        y="Moteur",
        orientation="h",
        color="Moteur",
        text_auto=".2f",
        title=f"Estimation ({volume_gb.value} Go, {ph_val}h/j, {freq_val})",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )

    fig.update_layout(
        yaxis={"categoryorder": "total descending"},
        showlegend=False,
        xaxis_title="Coût Mensuel (€)",
        yaxis_title="",
    )
    fig.update_traces(textposition="outside")

    mo.md('')
    return (fig,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 📊 Simulateur choix DWH // moteur analytique
    """)
    return


@app.cell(hide_code=True)
def _(fig, frequence, mo, plage_horaire, volume_gb):
    mo.vstack(
        [
            mo.hstack(
                [
                    mo.vstack([mo.md("### ⚙️ Paramètres"), volume_gb, plage_horaire, frequence]),
                    mo.ui.plotly(fig),
                ],
                widths=[1, 3],
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
