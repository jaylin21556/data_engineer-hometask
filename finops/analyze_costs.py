"""
parse aws_costs.csv and spit out numbers
I used in the cost analysis writeup.
"""
import csv
from collections import defaultdict

def analyze():
    costs_by_service = defaultdict(float)
    tag_presence = {"App": 0, "Env": 0, "Owner": 0, "CostCenter": 0}
    total_rows = 0

    with open("../aws_costs.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            amount = float(row["amount"])
            service_key = f"{row['service']}|{row['usage_type']}"
            costs_by_service[service_key] += amount

            # check which tags are actually populated
            for tag in tag_presence:
                if row.get(tag, "").strip():
                    tag_presence[tag] += 1

    total_spend = sum(costs_by_service.values())

    print("=" * 60)
    print("COST DRIVERS (sorted by spend)")
    print("=" * 60)
    for key, amount in sorted(costs_by_service.items(), key=lambda x: -x[1]):
        service, usage = key.split("|")
        pct = (amount / total_spend) * 100
        print(f"  {service:20s} {usage:30s} ${amount:>10.2f}  ({pct:.1f}%)")

    print(f"\n  {'TOTAL':20s} {'':30s} ${total_spend:>10.2f}")

    print(f"\n{'=' * 60}")
    print("TAG COVERAGE")
    print("=" * 60)
    for tag, count in tag_presence.items():
        pct = (count / total_rows) * 100
        print(f"  {tag:15s} {count}/{total_rows} ({pct:.0f}%)")


if __name__ == "__main__":
    analyze()
