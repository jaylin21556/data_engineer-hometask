"""
Ingest the 5 baseball CSV files from S3 landing into curated Delta tables.
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType
)
import sys

LANDING_PATH = "s3://data-platform-prod-landing/raw/"
CURATED_PATH = "s3://data-platform-prod-curated/baseball/"

# Defining schemas explicitly so we catch column changes early
BATTING_SCHEMA = StructType([
    StructField("playerID", StringType(), False),
    StructField("yearID", IntegerType(), False),
    StructField("stint", IntegerType(), False),
    StructField("teamID", StringType(), False),
    StructField("lgID", StringType(), True),
    StructField("G", IntegerType(), True),
    StructField("AB", IntegerType(), True),
    StructField("R", IntegerType(), True),
    StructField("H", IntegerType(), True),
    StructField("2B", IntegerType(), True),
    StructField("3B", IntegerType(), True),
    StructField("HR", IntegerType(), True),
    StructField("RBI", IntegerType(), True),
    StructField("SB", IntegerType(), True),
    StructField("CS", IntegerType(), True),
    StructField("BB", IntegerType(), True),
    StructField("SO", IntegerType(), True),
    StructField("IBB", IntegerType(), True),
    StructField("HBP", IntegerType(), True),
    StructField("SH", IntegerType(), True),
    StructField("SF", IntegerType(), True),
    StructField("GIDP", IntegerType(), True),
])

SALARIES_SCHEMA = StructType([
    StructField("yearID", IntegerType(), False),
    StructField("teamID", StringType(), False),
    StructField("lgID", StringType(), True),
    StructField("playerID", StringType(), False),
    StructField("salary", DoubleType(), False),
])

PEOPLE_SCHEMA = StructType([
    StructField("playerID", StringType(), False),
    StructField("birthYear", IntegerType(), True),
    StructField("birthMonth", IntegerType(), True),
    StructField("birthDay", IntegerType(), True),
    StructField("birthCountry", StringType(), True),
    StructField("birthState", StringType(), True),
    StructField("birthCity", StringType(), True),
    StructField("deathYear", IntegerType(), True),
    StructField("deathMonth", IntegerType(), True),
    StructField("deathDay", IntegerType(), True),
    StructField("deathCountry", StringType(), True),
    StructField("deathState", StringType(), True),
    StructField("deathCity", StringType(), True),
    StructField("nameFirst", StringType(), True),
    StructField("nameLast", StringType(), True),
    StructField("nameGiven", StringType(), True),
    StructField("weight", IntegerType(), True),
    StructField("height", IntegerType(), True),
    StructField("bats", StringType(), True),
    StructField("throws", StringType(), True),
    StructField("debut", StringType(), True),
    StructField("finalGame", StringType(), True),
    StructField("retroID", StringType(), True),
    StructField("bbrefID", StringType(), True),
])

SCHOOLS_SCHEMA = StructType([
    StructField("schoolID", StringType(), False),
    StructField("name_full", StringType(), True),
    StructField("city", StringType(), True),
    StructField("state", StringType(), True),
    StructField("country", StringType(), True),
])

COLLEGE_PLAYING_SCHEMA = StructType([
    StructField("playerID", StringType(), False),
    StructField("schoolID", StringType(), False),
    StructField("yearID", IntegerType(), True),
])

# (csv filename, schema, partition columns, key columns for null checks)
TABLE_CONFIGS = [
    ("Batting",        BATTING_SCHEMA,          ["yearID"], ["playerID", "yearID", "teamID"]),
    ("People",         PEOPLE_SCHEMA,           None,       ["playerID"]),
    ("Salaries",       SALARIES_SCHEMA,         ["yearID"], ["playerID", "yearID", "teamID"]),
    ("Schools",        SCHOOLS_SCHEMA,          None,       ["schoolID"]),
    ("CollegePlaying", COLLEGE_PLAYING_SCHEMA,  None,       ["playerID", "schoolID"]),
]


def get_spark() -> SparkSession:
    builder = (
        SparkSession.builder
        .appName("ingest-baseball-data")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
    )
    return builder.getOrCreate()


def read_csv(spark: SparkSession, path: str, schema: StructType) -> DataFrame:
    """Read CSV with a fixed schema — no inference overhead."""
    return (
        spark.read
        .option("header", "true")
        .option("mode", "PERMISSIVE")
        .option("columnNameOfCorruptRecord", "_corrupt")
        .schema(schema)
        .csv(path)
    )


def run_dq_checks(df: DataFrame, table_name: str, key_cols: list[str]) -> DataFrame:
    """
    Pretty basic DQ — just drops rows with null keys and flags
    any weird year values. Logs everything so we can see what got
    filtered in the job output.
    """
    total = df.count()

    not_null_condition = F.lit(True)
    for col_name in key_cols:
        if col_name in df.columns:
            not_null_condition = not_null_condition & F.col(col_name).isNotNull()

    clean_df = df.filter(not_null_condition)
    dropped = total - clean_df.count()

    if dropped > 0:
        print(f"[DQ] {table_name}: dropped {dropped}/{total} rows with null keys")

    # sanity check on year — baseball data goes back to 1871
    if "yearID" in clean_df.columns:
        invalid_years = clean_df.filter(
            (F.col("yearID") < 1850) | (F.col("yearID") > 2030)
        ).count()
        if invalid_years > 0:
            print(f"[DQ] {table_name}: {invalid_years} rows with yearID outside 1850-2030")

    print(f"[DQ] {table_name}: {clean_df.count()} rows passed checks")
    return clean_df


def write_delta(df: DataFrame, path: str, partition_cols: list[str] | None) -> None:
    writer = df.write.format("delta").mode("overwrite").option("overwriteSchema", "true")

    if partition_cols:
        writer = writer.partitionBy(*partition_cols)

    writer.save(path)
    print(f"[WRITE] Delta table written to {path}")


def main():
    spark = get_spark()

    landing = LANDING_PATH
    curated = CURATED_PATH

    # try to grab paths from Databricks widgets
    try:
        landing = dbutils.widgets.get("landing_path")
        curated = dbutils.widgets.get("curated_path")
    except Exception:
        if len(sys.argv) >= 3:
            landing = sys.argv[1]
            curated = sys.argv[2]

    print(f"Landing path: {landing}")
    print(f"Curated path: {curated}")

    for table_name, schema, partition_cols, key_cols in TABLE_CONFIGS:
        print(f"\n{'='*60}")
        print(f"Processing: {table_name}")
        print(f"{'='*60}")

        csv_path = f"{landing}{table_name}.csv"
        delta_path = f"{curated}{table_name.lower()}"

        df = read_csv(spark, csv_path, schema)
        df_clean = run_dq_checks(df, table_name, key_cols)
        write_delta(df_clean, delta_path, partition_cols)

    print("\nDone — all tables ingested.")
    spark.stop()


if __name__ == "__main__":
    main()
