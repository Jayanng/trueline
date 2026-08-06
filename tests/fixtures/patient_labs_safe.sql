select
    patient_id,
    observed_at,
    lactate_mmol_l,
    null as review_notes
from raw_patient_labs
