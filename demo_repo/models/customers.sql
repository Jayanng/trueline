select
    customer_id,
    cust_email,
    customer_name
from {{ ref('customers_raw') }}
