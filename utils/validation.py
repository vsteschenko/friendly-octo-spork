import math
from datetime import datetime
from utils.categories import category_name, income_category_name

MAX_AMOUNT = 1_000_000_000


def parse_transaction_form(form, year, month, day):
    """Validate the add/edit transaction form.

    Returns (data, None) on success or (None, error message) on failure.
    `data` has: type, category, amount (negative for expenses), place, comment, timestamp.
    """
    tx_type = form.get('type')
    if tx_type == 'expense':
        category = form.get('expense-category')
        allowed = category_name
    elif tx_type == 'income':
        category = form.get('income-category')
        allowed = income_category_name
    else:
        return None, 'Invalid transaction type'

    if category not in allowed:
        return None, 'Select category'

    try:
        amount = float(form.get('amount', ''))
    except ValueError:
        return None, 'Invalid amount'
    if not math.isfinite(amount) or amount <= 0 or amount > MAX_AMOUNT:
        return None, 'Amount must be a positive number'

    place = form.get('place', '') or ''
    comment = form.get('comment', '') or ''
    if len(place) > 100:
        return None, 'Name of the place is too long'
    if len(comment) > 250:
        return None, 'Comment is too long'

    try:
        hour, minute = map(int, form.get('tx_time', '').split(':'))
        timestamp = datetime(year, month, day, hour, minute)
    except (ValueError, TypeError):
        return None, 'Invalid date or time'

    return {
        'type': tx_type,
        'category': category,
        'amount': -amount if tx_type == 'expense' else amount,
        'place': place,
        'comment': comment,
        'timestamp': timestamp,
    }, None
