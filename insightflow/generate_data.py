"""Create a reproducible, fictional 2026 European retail dataset."""
from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
rows = []
base = {"France": 125000, "Germany": 150000, "Spain": 85000}
categories = {"Electronics": 1.25, "Home": 0.95, "Office": 0.8}
for month in range(1, 13):
    for country, country_base in base.items():
        for category, factor in categories.items():
            for segment, segment_factor in [("Enterprise", 1.2), ("SMB", 0.8)]:
                seasonal = 1 + 0.015 * (month - 1)
                revenue = round(country_base * factor * segment_factor * seasonal * rng.uniform(0.9, 1.1), 2)
                # Q4 margin squeeze: rising costs despite revenue growth.
                cost_share = 0.71 if month <= 6 else (0.75 if month <= 9 else 0.84)
                if category == "Electronics":
                    cost_share += 0.035
                cost = round(revenue * cost_share * rng.uniform(0.98, 1.02), 2)
                rows.append({"Date": f"2026-{month:02d}-15", "Country": country,
                             "ProductCategory": category, "CustomerSegment": segment,
                             "Revenue": revenue, "Cost": cost,
                             "UnitsSold": int(round(revenue / rng.uniform(190, 360)))})
output = Path(__file__).with_name("sales_2026.csv")
pd.DataFrame(rows).to_csv(output, index=False)
print(f"Generated {len(rows)} rows: {output}")
