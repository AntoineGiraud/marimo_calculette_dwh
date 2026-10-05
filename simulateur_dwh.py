import marimo

__generated_with = "0.25.1"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import marimo as mo
    import pandas as pd

    return alt, mo


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
    scan_pct = mo.ui.slider(
        start=1, stop=100, value=10, step=1, label="% de données scannées par requête"
    )
    speed_sec_per_10gb = mo.ui.slider(
        start=0.1, stop=10.0, value=2.0, step=0.1, label="Vitesse (secondes par 10 Go)"
    )
    return frequence, plage_horaire, scan_pct, speed_sec_per_10gb, volume_gb


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
        seconds_per_10gb: float = 2.0

        def calculate_compute_cost(self, w: Workload) -> float:
            if w.is_continuous:
                daily_billed_hours = w.plage_horaire
            else:
                raw_duration_s = max(0.1, (w.volume_gb / 10.0) * self.seconds_per_10gb)
                billed_duration_s = max(
                    raw_duration_s, float(self.min_billing_seconds_per_query)
                )

                daily_billed_s = w.queries_per_day * billed_duration_s
                daily_billed_hours = daily_billed_s / 3600.0

            daily_billed_hours = min(daily_billed_hours, float(w.plage_horaire))
            monthly_billed_hours = daily_billed_hours * w.days_in_month

            billable_hours = max(0.0, monthly_billed_hours - self.free_hours_per_month)
            return billable_hours * self.hourly_rate

    @dataclass
    class ProvisionedComputeEngine(AnalyticalEngine):
        hourly_rate: float = 0.0

        def calculate_compute_cost(self, w: Workload) -> float:
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
    alt,
    frequence,
    plage_horaire,
    scan_pct,
    speed_sec_per_10gb,
    volume_gb,
):
    freq_val = frequence.value
    ph_val = plage_horaire.value
    scan_ratio = scan_pct.value / 100.0
    speed_val = speed_sec_per_10gb.value

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

    workload = Workload(
        volume_gb=volume_gb.value,
        volume_tb=volume_gb.value / 1000.0,
        queries_per_day=queries_per_day,
        plage_horaire=ph_val,
        is_continuous=(freq_val == "En continu / Live"),
    )

    # --- 2. Initialisation des Moteurs avec Paramètres Dynamiques ---
    engines = [
        ProvisionedComputeEngine(
            name="RDS PostgreSQL (On/Off)", hourly_rate=(30.0 / 730.0)
        ),
        GbScanComputeEngine(
            name="Amazon Athena",
            price_per_tb_scanned=5.0,
            scan_optimization_pct=scan_ratio,
        ),
        GbScanComputeEngine(
            name="Google BigQuery",
            price_per_tb_scanned=6.25,
            scan_optimization_pct=scan_ratio,
            free_tb_per_month=1.0,
        ),
        HourlyComputeEngine(
            name="Snowflake (XS)",
            hourly_rate=2.60,
            min_billing_seconds_per_query=60,
            seconds_per_10gb=speed_val,
        ),
        HourlyComputeEngine(
            name="Redshift Serverless",
            hourly_rate=2.88,
            min_billing_seconds_per_query=60,
            seconds_per_10gb=speed_val,
        ),
        HourlyComputeEngine(
            name="Microsoft Fabric (F2)",
            hourly_rate=0.36,
            min_billing_seconds_per_query=60,
            seconds_per_10gb=speed_val,
        ),
        HourlyComputeEngine(
            name="ClickHouse Cloud",
            hourly_rate=0.35,
            min_billing_seconds_per_query=0,
            seconds_per_10gb=speed_val,
        ),
        HourlyComputeEngine(
            name="MotherDuck",
            hourly_rate=0.73,
            min_billing_seconds_per_query=0,
            free_hours_per_month=10.0,
            free_storage_gb=10.0,
            seconds_per_10gb=speed_val,
        ),
    ]

    # --- 3. Exécution et Rendu ---
    moteurs = [e.name for e in engines]
    couts = [e.calculate_total_cost(workload) for e in engines]

    data = [{"Moteur": m, "Coût Mensuel (€)": c} for m, c in zip(moteurs, couts)]
    # 1. On trie notre liste de dictionnaires en Python selon le coût
    data = sorted(data, key=lambda x: x["Coût Mensuel (€)"])
    moteurs_tries = [d["Moteur"] for d in data]

    # 🎨 Personnalisation de la charte graphique
    domain = {
        "RDS PostgreSQL (On/Off)": "#FFC400",  #
        "Amazon Athena": "#FF9900",
        "Google BigQuery": "#1565C0",
        "Snowflake (XS)": "#29B5E8",
        "Redshift Serverless": "#FF7300",
        "Microsoft Fabric (F2)": "#48C561",
        "ClickHouse Cloud": "#000000",
        "MotherDuck": "#FFF200",
    }
    color_scale = alt.Scale(domain=domain.keys(), range=domain.values())

    # Utilisation de Altair avec la nouvelle palette
    base = alt.Chart(alt.Data(values=data)).encode(
        x=alt.X("Coût Mensuel (€):Q", title="Coût Mensuel (€)"),
        y=alt.Y("Moteur:N", sort=moteurs_tries, title=""),
    )

    bars = base.mark_bar().encode(
        color=alt.Color("Moteur:N", scale=color_scale, legend=None)
    )

    text = base.mark_text(
        align="left", baseline="middle", dx=3, color="#333333"
    ).encode(text=alt.Text("Coût Mensuel (€):Q", format=".2f"))

    chart = (bars + text).properties(
        title=alt.TitleParams(
            text=f"Estimation ({volume_gb.value} Go, {ph_val}h/j, {freq_val})",
            anchor="start",
            dx=10,
        ),
        width="container",
        height=400,
    )
    return (chart,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 📊 Simulateur choix DWH
    """)
    return


@app.cell(hide_code=True)
def _(
    chart,
    frequence,
    mo,
    plage_horaire,
    scan_pct,
    speed_sec_per_10gb,
    volume_gb,
):
    mo.vstack(
        [
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md("### ⚙️ Paramètres de charge"),
                            volume_gb,
                            plage_horaire,
                            frequence,
                            mo.md("---"),
                            mo.md("### 🔧 Hypothèses Moteurs"),
                            scan_pct,
                            speed_sec_per_10gb,
                        ]
                    ),
                    mo.ui.altair_chart(chart),
                ],
                widths=[1, 3],
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    _recap_moteurs = r"""
    ---
    ### 📖 Récapitulatif des Classes Mères & Liens Officiels

    *Le stockage est uniformisé à ~23 € / To / mois pour tous les acteurs.*

    #### `GbScanComputeEngine` (Facturation au Scan)
    - **Amazon Athena :** [Voir la grille tarifaire](https://aws.amazon.com/athena/pricing/)
    - **Google BigQuery :** 1er Téraoctet scanné gratuit/mois. [Voir la grille tarifaire](https://cloud.google.com/bigquery/pricing)

    #### `HourlyComputeEngine` (Facturation au temps d'éveil)
    - **Snowflake (XS) :** Pénalité de 60s minimum par requête. [Voir la grille tarifaire](https://www.snowflake.com/en/data-cloud/pricing-options/)
    - **Amazon Redshift Serverless :** Pénalité de 60s minimum par requête (Plancher 8 RPU). [Voir la grille tarifaire](https://aws.amazon.com/redshift/pricing/)
    - **Microsoft Fabric (F2) :** Pénalité de 60s minimum par requête. [Voir la grille tarifaire](https://azure.microsoft.com/en-us/pricing/details/microsoft-fabric/)
    - **ClickHouse Cloud :** Analytique temps-réel pur, facturé à la seconde. [Voir la grille tarifaire](https://clickhouse.com/pricing)
    - **MotherDuck :** Facturé à la seconde. Free Tier de 10h Compute & 10Go Storage. [Voir la grille tarifaire](https://motherduck.com/pricing/)

    #### `ProvisionedComputeEngine` (Facturation au serveur allumé)
    - **RDS PostgreSQL (On/Off) :** Allumé sur la plage horaire définie. [Voir la grille tarifaire](https://aws.amazon.com/rds/postgresql/pricing/)
    """

    _recap_limitations = r"""
    ---
    ### 🛑 Limites de ce notebook / modèle

    Afin de garder le simulateur lisible et concentré sur la tarification à l'usage, des éléments majeurs ont été volontairement exclus des calculs :

    1. **Les tickets d'entrée (Frais fixes d'abonnement) 🎫 :** Le graphique calcule la consommation pure (Compute & Storage). Il n'inclut pas les forfaits mensuels minimums requis par certains éditeurs pour accéder à un environnement de production multi-utilisateurs

    2. **Les performances réelles des moteurs ⚡ :** Le simulateur applique par défaut la même vitesse de traitement théorique (ex: 2s / 10 Go) à tous les moteurs. Dans la réalité, l'architecture interne change tout.    *MotherDuck (propulsé par DuckDB) ou ClickHouse sont réputés dans les benchmarks pour leur vélocité     👉️ [ClickBench — a Benchmark For Analytical DBMS](https://benchmark.clickhouse.com/)*

    3. **La concurrence et le nombre d'utilisateurs 👥 :** Le paramètre "Fréquence des requêtes" simule un flux linéaire. Il ne modélise pas l'impact de dizaines ou milliers d'utilisateurs simultanés (concurrency). Sans un cache agressif au niveau de l'outil BI, une forte concurrence modifie drastiquement le comportement des systèmes :
        - *Sur les **moteurs au scan** (Athena, BigQuery)* : 1000 utilisateurs = 1000 fois plus de scans = la facture explose.
        - *Sur les **moteurs provisionnés** (RDS)* : Le prix reste fixe, mais le serveur risque l'engorgement ou le crash.
        - *Sur les **moteurs à l'heure** (Snowflake, ClickHouse)* : Il faudra instancier des clusters plus gros (Scale-up/out) pour absorber la charge, ce qui augmentera le taux horaire de base.
    """

    # ⚠️ CORRECTION : on stocke le layout, on aligne en haut ("start"), et SURTOUT on le retourne !
    mo.hstack(
        [mo.md(_recap_moteurs), mo.md(_recap_limitations)],
        justify="start",
        align="start",  # Aligne les deux blocs de texte par le haut
        widths="equal",  # Répartit l'espace 50% / 50%
        gap="2rem",
    )
    return


if __name__ == "__main__":
    app.run()
