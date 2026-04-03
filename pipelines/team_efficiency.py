"""
Builds a team-year efficiency table from Batting and Salaries.

Key:
- Aggregates batting stats across all players AND stints per team-year.
- Left joins salary data so teams without salary info still show up.
- Handles division by zero for BA/SLG and HR_per_Million.
- Overwrites the output each run for idempotency.
- SLG = (H + 2B + 2*3B + 3*HR) / AB
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
import sys
import os


def get_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("team-year-efficiency")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .getOrCreate()
    )


def build_team_efficiency(batting_df: DataFrame, salaries_df: DataFrame) -> DataFrame:

    # roll up batting to team-year, treating nulls as 0
    batting_agg = (
        batting_df
        .groupBy("teamID", "yearID")
        .agg(
            F.sum(F.coalesce(F.col("AB"), F.lit(0))).alias("AB"),
            F.sum(F.coalesce(F.col("H"), F.lit(0))).alias("H"),
            F.sum(F.coalesce(F.col("2B"), F.lit(0))).alias("2B"),
            F.sum(F.coalesce(F.col("3B"), F.lit(0))).alias("3B"),
            F.sum(F.coalesce(F.col("HR"), F.lit(0))).alias("HR"),
        )
    )

    salary_agg = (
        salaries_df
        .groupBy("teamID", "yearID")
        .agg(
            F.sum("salary").alias("total_payroll")
        )
    )

    result = (
        batting_agg.alias("b")
        .join(
            salary_agg.alias("s"),
            on=["teamID", "yearID"],
            how="left"
        )
        .select(
            F.col("b.teamID"),
            F.col("b.yearID"),
            F.col("s.total_payroll"),
            F.col("b.AB"),
            F.col("b.H"),
            F.col("b.HR"),

            F.round(
                F.col("b.H").cast("double") /
                F.when(F.col("b.AB") == 0, None).otherwise(F.col("b.AB")),
                4
            ).alias("BA"),

            F.round(
                (F.col("b.H") + F.col("b.`2B`") + 2 * F.col("b.`3B`") + 3 * F.col("b.HR")).cast("double") /
                F.when(F.col("b.AB") == 0, None).otherwise(F.col("b.AB")),
                4
            ).alias("SLG"),

            F.round(
                F.col("b.HR").cast("double") /
                F.when(F.col("s.total_payroll") == 0, None)
                 .when(F.col("s.total_payroll").isNull(), None)
                 .otherwise(F.col("s.total_payroll") / 1000000.0),
                4
            ).alias("HR_per_Million"),
        )
        .orderBy("yearID", "teamID")
    )

    return result


def main():
    spark = get_spark()

    # default to the data dir next to this script
    data_path = os.path.join(os.path.dirname(__file__), "..", "Platform_Engineer_Take_Home_Data")
    output_path = os.path.join(os.path.dirname(__file__), "..", "output", "team_efficiency")

    if len(sys.argv) >= 3:
        data_path = sys.argv[1]
        output_path = sys.argv[2]

    batting_df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .csv(os.path.join(data_path, "Batting.csv"))
    )

    salaries_df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .csv(os.path.join(data_path, "Salaries.csv"))
    )

    result = build_team_efficiency(batting_df, salaries_df)

    print("\n=== Team Efficiency (first 10 rows) ===")
    result.show(10, truncate=False)
    print(f"Total rows: {result.count()}")

    # try Delta first, fall back to Parquet if delta jars aren't available
    try:
        (
            result.write
            .format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .partitionBy("yearID")
            .save(output_path)
        )
        print(f"\nWrote Delta table to: {output_path}")
    except Exception:
        parquet_path = output_path + "_parquet"
        (
            result.write
            .format("parquet")
            .mode("overwrite")
            .partitionBy("yearID")
            .save(parquet_path)
        )
        print(f"\nDelta not available, wrote Parquet to: {parquet_path}")

    spark.stop()


if __name__ == "__main__":
    main()
