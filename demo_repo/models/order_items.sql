select
    order_id,
    customer_id,
    product_id,
    order_date,
    return_date,
    order_total,
    cast(null as varchar) as notes
from {{ ref('orders') }}
