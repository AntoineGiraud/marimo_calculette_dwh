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
        volume_gb: float
        volume_tb: float
        queries_per_day: float
        plage_horaire: float
        is_continuous: bool
        days_in_month: int = 30

    @dataclass
    class AnalyticalEngine(ABC):
        name: str
        storage_price_per_tb: float = 23.0
        free_storage_gb: float = 0.0

        def calculate_storage_cost(self, w: Workload) -> float:
            billable_gb = max(0.0, w.volume_gb - self.free_storage_gb)
            return (billable_gb / 1000.0) * self.storage_price_per_tb

        @abstractmethod
        def calculate_compute_cost(self, w: Workload) -> float:
            pass

        def calculate_total_cost(self, w: Workload) -> float:
            return self.calculate_compute_cost(w) + self.calculate_storage_cost(w)

    @dataclass
    class GbScanComputeEngine(AnalyticalEngine):
        price_per_tb_scanned: float = 5.0
        scan_optimization_pct: float = 0.10
        free_tb_per_month: float = 0.0

        def calculate_compute_cost(self, w: Workload) -> float:
            tb_scanned_per_query = w.volume_tb * self.scan_optimization_pct
            monthly_scanned_tb = (
                tb_scanned_per_query * w.queries_per_day * w.days_in_month
            )
            billable_tb = max(0.0, monthly_scanned_tb - self.free_tb_per_month)
            return billable_tb * self.price_per_tb_scanned

    @dataclass
    class HourlyComputeEngine(AnalyticalEngine):
        hourly_rate: float = 0.0
        min_billing_seconds_per_query: int = 0
        free_hours_per_month: float = 0.0

        def calculate_compute_cost(self, w: Workload) -> float:
            if w.is_continuous:
                daily_billed_hours = w.plage_horaire
            else:
                # Hypothèse : 2 secondes de traitement par 10 Go de données
                raw_duration_s = max(1.0, (w.volume_gb / 10.0) * 2.0)
                # Application de la pénalité de déclenchement (ex: 60s pour Snowflake)
                billed_duration_s = max(
                    raw_duration_s, float(self.min_billing_seconds_per_query)
                )

                daily_billed_s = w.queries_per_day * billed_duration_s
                daily_billed_hours = daily_billed_s / 3600.0

            # Plafond : un moteur ne peut pas tourner plus d'heures qu'il n'y en a dans la journée
            daily_billed_hours = min(daily_billed_hours, float(w.plage_horaire))
            monthly_billed_hours = daily_billed_hours * w.days_in_month

            billable_hours = max(0.0, monthly_billed_hours - self.free_hours_per_month)
            return billable_hours * self.hourly_rate

    @dataclass
    class ProvisionedComputeEngine(AnalyticalEngine):
        hourly_rate: float = 0.0

        def calculate_compute_cost(self, w: Workload) -> float:
            # Pour être "fair", on allume et on paie le serveur uniquement sur la plage horaire définie
            uptime_hours_per_month = w.plage_horaire * w.days_in_month
            return uptime_hours_per_month * self.hourly_rate

    return (
        GbScanComputeEngine,
        HourlyComputeEngine,
        ProvisionedComputeEngine,
        Workload,
    )


@app.cell(hide_code=True)
def _(
    GbScanComputeEngine,
    HourlyComputeEngine,
    ProvisionedComputeEngine,
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

    # --- 1. Constitution du Workload (Agnostique) ---
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

    workload = Workload(
        volume_gb=volume_gb.value,
        volume_tb=volume_gb.value / 1000.0,
        queries_per_day=queries_per_day,
        plage_horaire=ph_val,
        is_continuous=(freq_val == "En continu / Live"),
    )

    # --- 2. Initialisation des Moteurs (Encapsulation Parfaite) ---
    engines = [
        # La Base Fixe (Éteinte la nuit pour être fair)
        ProvisionedComputeEngine(
            name="RDS PostgreSQL (On/Off)", hourly_rate=(30.0 / 730.0)
        ),
        # Les Moteurs au Scan
        GbScanComputeEngine(
            name="Amazon Athena", price_per_tb_scanned=5.0, scan_optimization_pct=0.10
        ),
        GbScanComputeEngine(
            name="Google BigQuery",
            price_per_tb_scanned=6.25,
            scan_optimization_pct=0.10,
            free_tb_per_month=1.0,
        ),
        # Les Moteurs au temps de Calcul (avec pénalité de 60s)
        HourlyComputeEngine(
            name="Snowflake (XS)", hourly_rate=2.60, min_billing_seconds_per_query=60
        ),
        HourlyComputeEngine(
            name="Redshift Serverless",
            hourly_rate=2.88,
            min_billing_seconds_per_query=60,
        ),
        HourlyComputeEngine(
            name="Microsoft Fabric (F2)",
            hourly_rate=0.36,
            min_billing_seconds_per_query=60,
        ),
        # Les Moteurs au temps de Calcul (Paiement à la seconde pure)
        HourlyComputeEngine(
            name="ClickHouse Cloud", hourly_rate=0.35, min_billing_seconds_per_query=0
        ),
        HourlyComputeEngine(
            name="MotherDuck",
            hourly_rate=0.73,
            min_billing_seconds_per_query=0,
            free_hours_per_month=10.0,
            free_storage_gb=10.0,
        ),
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

    mo.md("")
    return (fig,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 📊 Simulateur choix DWH // 3 Classes Mères
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
    ### 📖 Récapitulatif de la Modélisation Orientée Objet

    Le code a été simplifié autour de 3 grandes familles de facturation héritant toutes du stockage de base (23 € / To) :

    **1. `GbScanComputeEngine` (Facturation au Scan)**
    *   **Comportement :** Coût = *Volume total x 10% (Opti Parquet) x Prix au To scanné*.
    *   **Les moteurs :** Amazon Athena (5$/To) et Google BigQuery (6.25$/To avec 1 To offert).

    **2. `HourlyComputeEngine` (Facturation au temps d'éveil)**
    *   **Comportement (La Règle des 2s) :** On estime le calcul d'une requête BI moyenne à **2 secondes par tranche de 10 Go** de données.
    *   **La pénalité (Le minimum facturable) :** Certains moteurs facturent un minimum de **60 secondes** à chaque réveil (Snowflake, Redshift, Fabric). S'ils sont appelés trop souvent, ils n'arrivent plus à s'éteindre et la facture explose. D'autres facturent à la seconde près (MotherDuck, ClickHouse).
    *   **Les moteurs :** Snowflake (2.60€/h), Redshift (2.88€/h), Fabric (0.36€/h), ClickHouse (0.35€/h) et MotherDuck (0.73€/h avec 10h et 10Go offerts).

    **3. `ProvisionedComputeEngine` (Facturation au serveur allumé)**
    *   **Comportement (Le mode "Fair") :** Au lieu de facturer RDS 24h/24 comme avant, on présume qu'un script l'allume et l'éteint tous les jours selon la `Plage horaire` définie, pour être à armes égales avec le Serverless.
    *   **Le moteur :** RDS PostgreSQL (Tarif de base ~30€ ramené à un taux horaire).
    """)
    return


if __name__ == "__main__":
    app.run()
