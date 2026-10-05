import marimo

__generated_with = "0.25.1"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import plotly.express as px
    import polars as pl

    return mo, pl, px


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
def _():
    from abc import ABC, abstractmethod
    from dataclasses import dataclass

    @dataclass
    class Workload:
        volume_tb: float
        queries_per_day: float
        active_hours_per_day: float
        active_hours_month: float
        plage_horaire: float
        is_continuous: bool
        days_in_month: int = 30

    @dataclass
    class AnalyticalEngine(ABC):
        name: str
        storage_price_per_tb: float = 23.0

        def calculate_storage_cost(self, w: Workload) -> float:
            return w.volume_tb * self.storage_price_per_tb

        @abstractmethod
        def calculate_compute_cost(self, w: Workload) -> float:
            pass

        def calculate_total_cost(self, w: Workload) -> float:
            return self.calculate_compute_cost(w) + self.calculate_storage_cost(w)

    @dataclass
    class RDSPostgreSQL(AnalyticalEngine):
        def calculate_compute_cost(self, w: Workload) -> float:
            return 30.0  # Prix fixe du serveur

    @dataclass
    class AmazonAthena(AnalyticalEngine):
        def calculate_compute_cost(self, w: Workload) -> float:
            # 5$ par To scanné avec opti de 10%
            return (w.queries_per_day * (w.volume_tb * 0.10) * 5) * w.days_in_month

    @dataclass
    class GoogleBigQuery(AnalyticalEngine):
        def calculate_compute_cost(self, w: Workload) -> float:
            # 6.25$ par To scanné avec opti 10% + 1er To gratuit
            total_scanned = (w.queries_per_day * (w.volume_tb * 0.10)) * w.days_in_month
            billable_scanned = max(0.0, total_scanned - 1.0)
            return billable_scanned * 6.25

    @dataclass
    class HourlyComputeEngine(AnalyticalEngine):
        hourly_rate: float = 0.0

        def calculate_compute_cost(self, w: Workload) -> float:
            return w.active_hours_month * self.hourly_rate

    @dataclass
    class MotherDuck(AnalyticalEngine):
        def calculate_compute_cost(self, w: Workload) -> float:
            if w.is_continuous:
                md_hours_day = w.plage_horaire
            else:
                md_hours_day = w.queries_per_day * (5 / 3600)  # 5 secondes / requête
            md_hours_month = md_hours_day * w.days_in_month
            billable_hours = max(0.0, md_hours_month - 10.0)  # 10h gratuites
            return billable_hours * 0.73

        def calculate_storage_cost(self, w: Workload) -> float:
            # Override pour intégrer les 10 Go gratuits
            billable_storage = max(0.0, w.volume_tb - 0.01)
            return billable_storage * self.storage_price_per_tb

    return (
        AmazonAthena,
        GoogleBigQuery,
        HourlyComputeEngine,
        MotherDuck,
        RDSPostgreSQL,
        Workload,
    )


@app.cell(hide_code=True)
def _(
    AmazonAthena,
    GoogleBigQuery,
    HourlyComputeEngine,
    MotherDuck,
    RDSPostgreSQL,
    Workload,
    frequence,
    mo,
    pl,
    plage_horaire,
    px,
    volume_gb,
):
    freq_val = frequence.value
    ph_val = plage_horaire.value

    # --- 1. Constitution du Workload ---
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

    active_hours_per_day = queries_per_day * (1 / 60)  # Règle des 60s min
    active_hours_per_day = min(active_hours_per_day, ph_val)

    workload = Workload(
        volume_tb=volume_gb.value / 1000.0,
        queries_per_day=queries_per_day,
        active_hours_per_day=active_hours_per_day,
        active_hours_month=active_hours_per_day * 30,
        plage_horaire=ph_val,
        is_continuous=(freq_val == "En continu / Live"),
    )

    # --- 2. Initialisation des Moteurs (Règles métiers) ---
    engines = [
        RDSPostgreSQL(name="RDS PostgreSQL"),
        AmazonAthena(name="Amazon Athena"),
        GoogleBigQuery(name="Google BigQuery"),
        HourlyComputeEngine(name="Snowflake (XS)", hourly_rate=2.60),
        HourlyComputeEngine(name="Redshift Serverless", hourly_rate=2.88),
        HourlyComputeEngine(name="ClickHouse Cloud", hourly_rate=0.35),
        HourlyComputeEngine(name="Microsoft Fabric (F2)", hourly_rate=0.36),
        MotherDuck(name="MotherDuck"),
    ]

    # --- 3. Exécution et Rendu ---
    moteurs = [e.name for e in engines]
    couts = [e.calculate_total_cost(workload) for e in engines]

    df = pl.DataFrame({"Moteur": moteurs, "Coût Mensuel (€)": couts})

    fig = px.bar(
        df,
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
    # 📊 Simulateur choix DWH // Architecture Refactorisée (OOP)
    """)
    return


@app.cell(hide_code=True)
def _(fig, frequence, mo, plage_horaire, volume_gb):
    mo.vstack(
        [
            mo.hstack(
                [
                    mo.vstack(
                        [mo.md("### ⚙️ Paramètres"), volume_gb, plage_horaire, frequence]
                    ),
                    mo.ui.plotly(fig),
                ],
                widths=[1, 3],
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ### 📖 Récapitulatif des Hypothèses & Liens Officiels

    *Le stockage est uniformisé à ~23 € / To / mois pour tous les acteurs.*

    *   **Amazon RDS for PostgreSQL :** Serveur classique H24 (~30 €/mois de base). Facturation fixe indépendante de la charge analytique. [Pricing RDS](https://aws.amazon.com/rds/postgresql/pricing/)
    *   **Amazon Athena :** 100% Serverless (~5,00 $/To scanné). Le modèle simule une optimisation Parquet limitant le scan à 10% du volume total par requête. [Pricing Athena](https://aws.amazon.com/athena/pricing/)
    *   **Google BigQuery :** Serverless au scan (~6,25 $/To scanné). Le **1er Téraoctet scanné chaque mois est gratuit**. [Pricing BigQuery](https://cloud.google.com/bigquery/pricing)
    *   **Snowflake (XS) :** Entrepôt premium (~2,60 €/h). Chaque requête réveille le moteur pour un minimum de 60 secondes. [Pricing Snowflake](https://www.snowflake.com/en/data-cloud/pricing-options/)
    *   **Amazon Redshift Serverless :** Moteur premium AWS (~2,88 €/h pour le plancher à 8 RPU). Mécanique de réveil identique à Snowflake. [Pricing Redshift](https://aws.amazon.com/redshift/pricing/)
    *   **Microsoft Fabric (F2) :** Data Warehouse Azure (~0.36 €/h). Modèle de capacité avec mise en veille automatique, idéal pour démarrer petit. [Pricing Fabric](https://azure.microsoft.com/en-us/pricing/details/microsoft-fabric/)
    *   **ClickHouse Cloud :** Analytique temps-réel (~0,35 €/h). Conçu pour encaisser des flux continus sans faire exploser la facture horaire. [Pricing ClickHouse](https://clickhouse.com/pricing)
    *   **MotherDuck :** Hybride local/cloud (~0,73 €/h). **Facturation à la seconde** sans minimum d'une minute par requête. Intègre un **Free Tier généreux de 10h de calcul et 10 Go de stockage par mois**. [Pricing MotherDuck](https://motherduck.com/pricing/)
    """)
    return


if __name__ == "__main__":
    app.run()
