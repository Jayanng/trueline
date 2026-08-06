select
    order_id,
    customer_id,
    customers.cust_email as customer_email,
    order_total,
    case when order_total > 500 then 0.4 else 0.1 end as risk_score
from {{ ref('order_items') }}
left join {{ ref('customers') }} on customers.customer_id = order_items.customer_id