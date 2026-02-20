SAP_FIELD_MAPPING = [
    ("Supplier", "supplier", "text"),
    ("Invoice date", "invoice_date", "date"),
    ("Posting Date", "posting_date", "date"),
    ("Reference", "reference", "text"),
    ("Amount", "amount", "number"),
    ("Tax Amount", "tax_amount", "number")
]

def get_mapping():
    return SAP_FIELD_MAPPING
