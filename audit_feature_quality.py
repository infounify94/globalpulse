import os
import pandas as pd
import numpy as np

def run_feature_quality_audit():
    dataset_file = "datasets/train_2008_2023.parquet"
    if not os.path.exists(dataset_file):
        dataset_file = "../" + dataset_file
        if not os.path.exists(dataset_file):
            print("Dataset not found for feature audit.")
            return
            
    df = pd.read_parquet(dataset_file)
    # Drop non-numeric
    numeric_df = df.select_dtypes(include=[np.number])
    
    # Check for constant or zero variance
    variances = numeric_df.var()
    constant_features = variances[variances == 0].index.tolist()
    
    # Check for high correlation (> 0.95)
    corr_matrix = numeric_df.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    high_corr = [column for column in upper.columns if any(upper[column] > 0.95)]
    
    report = pd.DataFrame({
        "Check": ["Constant / Zero Variance Features", "Highly Correlated Features (>0.95)"],
        "Count": [len(constant_features), len(high_corr)],
        "Features": [", ".join(constant_features[:10]) + ("..." if len(constant_features) > 10 else ""),
                     ", ".join(high_corr[:10]) + ("..." if len(high_corr) > 10 else "")]
    })
    report.to_csv("scientific_audit/correlation_report.csv", index=False)
    
    print("Feature Quality Audit complete.")

if __name__ == "__main__":
    run_feature_quality_audit()
