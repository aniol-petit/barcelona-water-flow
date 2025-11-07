
import pandas as pd
df = pd.read_parquet('Consum anomalies facturacio complet_anonymized.parquet')
df.to_csv('consum_dades.csv', index=False)



