import pandas as pd
import re
import json

# 1. Load the raw data
df = pd.read_csv('medicare_raw.csv')

def extract_medical_costs(text):
    if pd.isna(text):
        return {}
    
    patterns = {
        "primary_doctor": r"Primary doctor:\s*(.*?)(?=Specialist:|$)",
        "specialist": r"Specialist:\s*(.*?)(?=Your maximum annual out-of-pocket costs:|$)",
        "max_out_of_pocket": r"maximum annual out-of-pocket costs:\s*(.*?)(?=Annual medical deductible:|$)",
        "medical_deductible": r"Annual medical deductible:\s*(.*?)(?=Inpatient Hospital:|$)",
        "inpatient_hospital": r"Inpatient Hospital:\s*(.*?)(?=Routine exams - Hearing:|$)",
        "hearing_coverage": r"Hearing:\s*(.*?)(?=Dental:|$)",
        "dental_coverage": r"Dental:\s*(.*?)(?=Vision:|$)",
        "vision_coverage": r"Vision:\s*(.*?)(?=Limits may apply|$)"
    }

    extracted = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, str(text), re.IGNORECASE | re.DOTALL)
        if match:
            extracted[key] = match.group(1).strip().rstrip('.')
        else:
            extracted[key] = "Not specified"
            
    return extracted

def extract_drug_costs(text):
    if pd.isna(text):
        return {}
        
    text_str = str(text)
    
    # Catch plans without standard Part D text
    if "No Part D drug coverage" in text_str or "Drugs covered separately" in text_str:
        return {
            "drug_deductible": text_str.strip('., '),
            "preferred_pharmacies": "N/A",
            "standard_pharmacies": "N/A"
        }

    # Extract the deductible and specific pharmacy tiers
    # We use lookaheads for words like "Plan", "Your drug", or "If you" to stop capturing before the boilerplate disclaimers start
    patterns = {
        "drug_deductible": r"Drug deductible:\s*(.*?)(?=Preferred retail pharmac|Standard retail pharmac|You pay|Plan|If you|$)",
        "preferred_pharmacies": r"Preferred retail pharmacies:\s*(.*?)(?=Standard retail pharmac|Plan|Your drug costs|If you|$)",
        "standard_pharmacies": r"Standard retail pharmac(?:ies|y):\s*(.*?)(?=Preferred retail pharmac|Plan|Your drug costs|If you|$)"
    }

    extracted = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text_str, re.IGNORECASE | re.DOTALL)
        if match:
            extracted[key] = match.group(1).strip().rstrip('.;')
        else:
            extracted[key] = "Not specified"
            
    return extracted

# 2. Apply extractions
extracted_medical_df = df['Co-pays maximum out-of-pocket deductible'].apply(extract_medical_costs).apply(pd.Series)

# Rename the original columns
df = df.rename(columns={
    'Co-pay after deductibles $0 to $2,400': 'drug_coverage_initial_raw',
    'Co-pay after deductibles $2,400 and up': 'drug_coverage_catastrophic',
    'Part B only': 'part_b_only'
})

# Apply the new drug extraction to the renamed raw column
extracted_drug_df = df['drug_coverage_initial_raw'].apply(extract_drug_costs).apply(pd.Series)

# 3. Merge EVERYTHING back together
clean_df = pd.concat([
    df[['Companies', 'Name', 'Plan Number', 'Phone', 'Website', 'Monthly premium', 'part_b_only', 'Star rating', 'drug_coverage_catastrophic']], 
    extracted_medical_df,
    extracted_drug_df,
    df[['Co-pays maximum out-of-pocket deductible', 'drug_coverage_initial_raw']] # Kept as raw backups
], axis=1)

# 4. Handle N/A values and Export
clean_df = clean_df.fillna("N/A")
records = clean_df.to_dict(orient='records')

with open('medicare_cleaned.json', 'w') as f:
    json.dump(records, f, indent=2)

print(f"Successfully cleaned {len(records)} plans, including pharmacy tiers.")