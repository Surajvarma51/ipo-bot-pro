"""
Calculates the maximum retail-allowed lots for an IPO, and validates
a requested quantity against it -- based on the lot size and cutoff
(upper band) price, both of which are visible directly in the open
IPO table row.
"""

import re

RETAIL_CAP = 200000  # ₹2,00,000 retail investment cap

def parse_ipo_row_info(row_text):
    """Extracts lot size and price band from an IPO row's text.
    Returns (lot_size, price_low, price_high) or (None, None, None)
    if the pattern isn't found."""
    qty_match = re.search(r"(\d+)\s*Qty\.", row_text)
    price_match = re.search(r"(\d+)\s*-\s*(\d+)", row_text)

    lot_size = int(qty_match.group(1)) if qty_match else None
    price_low = int(price_match.group(1)) if price_match else None
    price_high = int(price_match.group(2)) if price_match else None

    return lot_size, price_low, price_high

def calculate_max_lots(lot_size, cutoff_price, retail_cap=RETAIL_CAP):
    """Returns the maximum number of lots allowed under the retail cap."""
    if not lot_size or not cutoff_price:
        return None
    amount_per_lot = lot_size * cutoff_price
    return retail_cap // amount_per_lot

def validate_quantity(quantity, lot_size, cutoff_price, retail_cap=RETAIL_CAP):
    """Returns (True, None) if quantity is a valid multiple of the lot
    size and within the retail cap, or (False, reason) if not."""
    if not lot_size or not cutoff_price:
        return False, "Could not determine lot size or price band for this IPO."

    if quantity % lot_size != 0:
        return False, f"Quantity {quantity} is not a multiple of the lot size ({lot_size})."

    lots_requested = quantity // lot_size
    max_lots = calculate_max_lots(lot_size, cutoff_price, retail_cap)

    if lots_requested < 1:
        return False, "Quantity must be at least one lot."
    if lots_requested > max_lots:
        total_value = quantity * cutoff_price
        return False, (f"{lots_requested} lots (₹{total_value:,}) exceeds the retail cap "
                        f"of ₹{retail_cap:,}. Maximum allowed is {max_lots} lots "
                        f"(₹{max_lots * lot_size * cutoff_price:,}).")

    return True, None