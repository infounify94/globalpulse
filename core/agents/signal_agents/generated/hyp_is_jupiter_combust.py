"""
Auto-Generated Feature Module: is_jupiter_combust
Description: Jupiter is combust when in the same sign as the Sun.
"""

import pandas as pd

def extract(doc):
    return {'is_jupiter_combust': 1 if doc.get('jupiter_sign') == doc.get('sun_sign') else 0}

class GeneratedFeature:
    def compute_features(self, df_or_row):
        # Handles either a single dictionary row or a full pandas DataFrame
        if isinstance(df_or_row, dict):
            return extract(df_or_row)
        elif hasattr(df_or_row, 'apply'):
            # Apply over rows
            res = df_or_row.apply(lambda r: pd.Series(extract(r.to_dict())), axis=1)
            return pd.concat([df_or_row, res], axis=1)
        return df_or_row
