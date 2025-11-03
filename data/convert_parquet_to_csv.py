
import pandas as pd
df = pd.read_parquet('Dades_Comptadors_anonymized.parquet')
df.to_csv('dades_comptadors.csv', index=False)
