
import pandas as pd
df = pd.read_parquet('data/Dades_Comptadors_anonymized_v2.parquet')
df.to_csv('data/Dades_Comptadors_anonymized_v2.csv', index=False)



