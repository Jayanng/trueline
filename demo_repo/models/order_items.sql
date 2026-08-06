select
    order_id,
    customer_id,
    product_id,
    order_date,
    return_date,
    order_total
from {{ ref('orders') }}
