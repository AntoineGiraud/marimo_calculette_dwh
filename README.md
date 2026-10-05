# 📊 Simulateur de Coûts Data Warehouse / BI

Ce projet est un carnet interactif propulsé par [Marimo](https://marimo.io/) et 100% Python (Polars & Plotly).

Il permet de comparer visuellement les coûts de différentes architectures de bases de données analytiques selon des paramètres de charge personnalisables.

## ⚠️ Avertissement : Introduction & Sensibilisation

Ce simulateur a été conçu comme un **outil pédagogique d'introduction et de sensibilisation**. Son objectif premier est d'aider à comprendre les grandes mécaniques de dimensionnement et les philosophies de facturation des outils analytiques du marché.

**Les résultats fournis sont des estimations basées sur des hypothèses de calcul simplifiées (ex: coût de stockage lissé, requêtes aux durées moyennes, etc.). Ils ne doivent en aucun cas être pris pour argent comptant.** Pour une budgétisation réelle et précise, référez-vous toujours aux calculatrices de prix officielles des éditeurs Cloud.

### 🛑 Limites de ce notebook / modèle

Afin de garder le simulateur lisible et concentré sur la tarification à l'usage, deux éléments majeurs ont été volontairement exclus des calculs :
1. **Les tickets d'entrée (Frais fixes d'abonnement) 🎫 :** Le graphique calcule la consommation pure (Compute & Storage). Il n'inclut pas les forfaits mensuels minimums requis par certains éditeurs pour accéder à un environnement de production multi-utilisateurs
    - ex: **MotherDuck** nécessite un plan Standard à 250 $/mois pour des équipes de 10 personnes
    - ex: **ClickHouse** Cloud a un plancher de facturation autour de 53 $/mois
    - **D'autres** exigent souvent une réservations de crédits à l'avance
2. **Les performances réelles des moteurs ⚡ :** Le simulateur applique par défaut la même vitesse de traitement théorique (ex: 2s / 10 Go) à tous les moteurs. Dans la réalité, l'architecture interne change tout.\
   *MotherDuck (propulsé par DuckDB) ou ClickHouse sont réputés dans les benchmarks pour leur vélocité \
   👉️ [ClickBench — a Benchmark For Analytical DBMS](https://benchmark.clickhouse.com/)*
3. **La concurrence et le nombre d'utilisateurs 👥 :** Le paramètre "Fréquence des requêtes" simule un flux linéaire. Il ne modélise pas l'impact de dizaines ou milliers d'utilisateurs simultanés (concurrency). Sans un cache agressif au niveau de l'outil BI, une forte concurrence modifie drastiquement le comportement des systèmes :
   * *Sur les **moteurs au scan** (Athena, BigQuery)* : 1000 utilisateurs = 1000 fois plus de scans = la facture explose.
   * *Sur les **moteurs provisionnés** (RDS)* : Le prix reste fixe, mais le serveur risque l'engorgement ou le crash.
   * *Sur les **moteurs à l'heure** (Snowflake, ClickHouse)* : Il faudra instancier des clusters plus gros (Scale-up/out) pour absorber la charge, ce qui augmentera le taux horaire de base.

---

## 📖 Récapitulatif des Modèles & Liens Officiels

Pour standardiser la comparaison, le stockage est uniformisé à une moyenne de **~23 € / To / mois** pour tous les acteurs (prix moyen du stockage objet S3/GCS compressé). Les moteurs sont ensuite répartis en 3 grandes catégories :

### 1. `GbScanComputeEngine` (Facturation au Scan)
Ces moteurs Serverless facturent uniquement le volume de données lu par chaque requête. Le simulateur intègre une hypothèse ajustable d'optimisation (ex: 10% de scan réel grâce au format colonnes Parquet et au partitionnement).
* **Amazon Athena :** [Voir la grille tarifaire](https://aws.amazon.com/athena/pricing/)
* **Google BigQuery :** Intègre la gratuité du 1er Téraoctet scanné chaque mois. [Voir la grille tarifaire](https://cloud.google.com/bigquery/pricing)

### 2. `HourlyComputeEngine` (Facturation au temps d'éveil)
Ces moteurs s'endorment automatiquement en l'absence de requêtes, mais facturent le temps de calcul actif.
*Attention à la pénalité de 60s* : certains moteurs facturent un minimum incompressible d'une minute à chaque réveil. S'ils sont sollicités trop fréquemment (ex: requêtes toutes les 5 min), ils ne peuvent plus s'éteindre.
* **Snowflake (XS) :** Pénalité de 60s minimum par requête. [Voir la grille tarifaire](https://www.snowflake.com/en/data-cloud/pricing-options/)
* **Amazon Redshift Serverless :** Pénalité de 60s minimum par requête (Plancher 8 RPU). [Voir la grille tarifaire](https://aws.amazon.com/redshift/pricing/)
* **Microsoft Fabric (F2) :** Pénalité de 60s minimum par requête. Modèle de capacité Azure. [Voir la grille tarifaire](https://azure.microsoft.com/en-us/pricing/details/microsoft-fabric/)
* **ClickHouse Cloud :** Analytique temps-réel pur, facturé à la seconde sans pénalité. [Voir la grille tarifaire](https://clickhouse.com/pricing)
* **MotherDuck :** Facturé à la seconde. Modèle hybride intégrant un Free Tier généreux de 10h de calcul et 10 Go de stockage par mois. [Voir la grille tarifaire](https://motherduck.com/pricing/)

### 3. `ProvisionedComputeEngine` (Facturation au serveur allumé)
Modèle traditionnel où l'on paie l'infrastructure qu'elle soit utilisée ou non. Le simulateur est configuré pour n'allumer et ne facturer le serveur que sur la plage horaire d'ouverture de la BI sélectionnée.
* **RDS PostgreSQL (On/Off) :** [Voir la grille tarifaire](https://aws.amazon.com/rds/postgresql/pricing/)

---

## 🚀 Installation & Lancement

1. Assurez-vous d'avoir installé les dépendances requises :
   ```bash
   uv sync
   ```
2. Lancez l'application en mode édition ou exécution :
   ```bash
   uv run marimo edit simulateur_dwh.py
   # ou
   uv run marimo run simulateur_dwh.py
   ```