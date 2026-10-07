import os
import pandas as pd
import json

def get_file_size(file_path: str) -> int:
    return os.path.getsize(file_path)

def parse_csv(file_path: str):
    df = pd.read_csv(file_path)
    return extract_df_info(df)

def parse_excel(file_path: str):
    df = pd.read_excel(file_path)
    return extract_df_info(df)

def parse_json(file_path: str):
    with open(file_path, 'r') as f:
        data = json.load(f)
    if isinstance(data, list):
        df = pd.DataFrame(data)
    elif isinstance(data, dict):
        df = pd.DataFrame([data])
    else:
        raise ValueError("Unsupported JSON format for dataset")
    return extract_df_info(df)

from datetime import datetime

def extract_df_info(df: pd.DataFrame):
    df_preview = df.head(10).copy()
    for col in df_preview.columns:
        if pd.api.types.is_datetime64_any_dtype(df_preview[col]) or 'datetime' in str(df_preview[col].dtype):
            df_preview[col] = df_preview[col].astype(str)
            
    df_preview = df_preview.fillna("")
    
    preview = []
    for record in df_preview.to_dict(orient="records"):
        clean_record = {}
        for k, v in record.items():
            if pd.isna(v):
                clean_record[str(k)] = ""
            elif isinstance(v, (pd.Timestamp, datetime)):
                clean_record[str(k)] = v.isoformat()
            elif hasattr(v, "item"):
                clean_record[str(k)] = v.item()
            else:
                clean_record[str(k)] = v
        preview.append(clean_record)
        
    df_clean = df.fillna("")
    columns = {col: str(dtype) for col, dtype in df_clean.dtypes.items()}
    row_count = len(df_clean)
    return columns, row_count, preview
