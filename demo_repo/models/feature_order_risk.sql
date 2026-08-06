select
    order_id,
    customer_id,
    return_date,
    order_total,
    case when return_date is not null then 1.0 else 0.0 end as risk_score
from {{ ref('order_items') }}
