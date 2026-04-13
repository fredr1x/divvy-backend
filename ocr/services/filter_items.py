def filter(results: list):
    
    receipt = results
    to_remove_price_none = []
    for i, item in enumerate(receipt["items"]):
        if item["price"] is None:
            to_remove_price_none.append(i)

    for i in sorted(to_remove_price_none, reverse=True):
        receipt["items"].pop(i)

    return receipt
