from ctgan import CTGAN
import pandas as pd

def generate_synthetic_data(real_data, discrete_columns):
    # try:
        num_samples = len(real_data)
        ctgan = CTGAN(epochs=10)
        cat_cols = detect_discrete_columns(real_data)
        ctgan.fit(real_data, cat_cols)

        synthetic_data = ctgan.sample(num_samples)

        # Ensure the same column order
        synthetic_data = synthetic_data[real_data.columns]

        combined_data = real_data.copy()


        combined_data[discrete_columns] = synthetic_data[discrete_columns]

        return combined_data
    # except Exception as e:
    #     print(e)
    #     return None


def detect_discrete_columns(df, unique_threshold=20):
    discrete_cols = []
    for col in df.columns:
        unique_values = df[col].nunique(dropna=True)
        if df[col].dtype == 'object' or str(df[col].dtype) == 'category':
            discrete_cols.append(col)
        elif unique_values < unique_threshold:
            discrete_cols.append(col)
    return discrete_cols
