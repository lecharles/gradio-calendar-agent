def get_invoice_details_fn(invoice_id: str) -> str:
    return f"Details for invoice {invoice_id}: Paid, $123.45"

def refund_customer_fn(customer_id: str) -> str:
    return f"Customer {customer_id} has been refunded."

def bill_customer_fn(customer_id: str) -> str:
    return f"Customer {customer_id} has been billed $99.99."

from agents import function_tool

get_invoice_details = function_tool(get_invoice_details_fn)
refund_customer = function_tool(refund_customer_fn)
bill_customer = function_tool(bill_customer_fn)

if __name__ == "__main__":
    print(get_invoice_details_fn("12345"))
    print(refund_customer_fn("67890"))
    print(bill_customer_fn("54321"))

