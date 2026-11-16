"""Bounded Vietnamese catalog questions; facts still come from the scoped tool."""
import re
from decimal import Decimal, InvalidOperation


def _has(text, terms):
    return any(re.search(r'\b' + re.escape(term) + r'\b', text) for term in terms)


def clarification(message):
    return {'intent': 'AMBIGUOUS', 'tools': [], 'parameters': {}, 'clarification_question': message}


_AMOUNT = r'\d+(?:[.,]\d+)*\s*(?:trieu|tr|nghin|ngan|k|vnd|dong|d)?'


def _money(text):
    match = re.fullmatch(r'(\d+(?:[.,]\d+)*)\s*(trieu|tr|nghin|ngan|k|vnd|dong|d)?', text.strip())
    if not match:
        raise ValueError('Invalid currency amount')
    number, unit = match.groups()
    if unit in {'trieu', 'tr', 'nghin', 'ngan', 'k'}:
        if not re.fullmatch(r'\d+(?:[.,]\d{1,2})?', number):
            raise ValueError('Ambiguous scaled currency')
        value = Decimal(number.replace(',', '.')) * (1000000 if unit in {'trieu', 'tr'} else 1000)
    else:
        if re.fullmatch(r'\d+', number):
            value = Decimal(number)
        elif re.fullmatch(r'\d{1,3}([.,])\d{3}(?:\1\d{3})*', number):
            value = Decimal(number.replace('.', '').replace(',', ''))
        else:
            raise ValueError('Ambiguous VND amount')
        if not unit and value < 1000:
            raise ValueError('Currency unit required')
    if value > Decimal('9999999999.99'):
        raise ValueError('Amount exceeds catalog precision')
    return str(value)


def parse_catalog_question(query, norm, category, limit):
    """Return a canonical read-only request, a clarification, or None."""
    query = re.sub(r'^(?:(?:cho tôi biết|cho toi biet|vui lòng|vui long|xin)\s+)+', '', query.strip(), flags=re.I)
    product = bool(category) or _has(norm, ['san pham', 'mat hang', 'sku'])
    high = _has(norm, ['gia cao nhat', 'gia lon nhat', 'dat nhat', 'mac nhat', 'gia giam dan', 'gia tu cao den thap'])
    low = _has(norm, ['gia thap nhat', 'gia nho nhat', 're nhat', 'gia tang dan', 'gia tu thap den cao'])
    named_price = _has(norm, ['gia bao nhieu', 'gia la bao nhieu', 'bao nhieu tien', 'bang gia', 'gia cua'])
    bound = re.search(r'\b(?:duoi|tren|tu|toi da|toi thieu|khong qua|khong vuot qua)\s+\d', norm)
    if not product or not (high or low or named_price or bound):
        return None
    if high and low:
        return clarification('Bạn muốn tìm giá cao nhất hay thấp nhất? Tôi chưa chọn một trong hai tiêu chí trái ngược.')
    if _has(norm, ['khong phai', 'khong lay', 'ngoai tru', 'khong mua', 'usd', 'eur', 'dollar', 'do la']):
        return clarification('Bộ lọc hiện hỗ trợ tên/mã và khoảng giá VND; điều kiện loại trừ hoặc ngoại tệ cần được bạn làm rõ, tôi chưa chạy truy vấn thiếu điều kiện.')
    policy = _has(norm, ['chinh sach', 'quy dinh', 'quy trinh', 'huong dan', 'tai lieu'])
    sales = _has(norm, ['doanh thu', 'doanh so', 'ban chay', 'ban nhieu', 'ban cham', 'gia von', 'loi nhuan'])
    if policy or sales:
        if (high or low or bound) and sales:
            return clarification('Bạn muốn xếp hạng theo giá niêm yết hay doanh số/doanh thu? Đây là các tiêu chí khác nhau.')
        return None
    if _has(norm, ['con hang', 'ton kho', 'chi nhanh', 'con o', 'quan', 'ram', 'ssd', 'cpu', 'pin', 'bao hanh']):
        return clarification('Tôi có thể tra giá niêm yết theo tên/mã sản phẩm và ngân sách. Điều kiện tồn kho, chi nhánh hoặc cấu hình cần kiểm tra riêng; bạn hãy cho mã sản phẩm/tiêu chí ưu tiên.')
    params = {'category': category, 'sort_by': 'unit_price', 'sort_order': 'ASC' if low or (bound and not high) else 'DESC',
              'limit': min(20, max(1, limit)), 'min_price_inclusive': True, 'max_price_inclusive': True}
    try:
        between = re.search(r'\btu\s+(' + _AMOUNT + r')\s+(?:den|toi)\s+(' + _AMOUNT + r')(?![\w.,])', norm)
        if between:
            params.update(min_price=_money(between[1]), max_price=_money(between[2]))
            if Decimal(params['min_price']) > Decimal(params['max_price']):
                raise ValueError('Reversed bounds')
        if bound:
            matches = list(re.finditer(r'\b(duoi|tren|toi da|toi thieu|khong qua|khong vuot qua|tu)\s+(' + _AMOUNT + r')(?![\w.,])', norm))
            if not matches:
                raise ValueError('Incomplete bound')
            for match in matches:
                amount = _money(match[2])
                lower = match[1] in {'tren', 'toi thieu', 'tu'}
                key = 'min_price' if lower else 'max_price'
                include = match[1] not in {'tren', 'duoi'}
                previous = params.get(key)
                if previous is None or (Decimal(amount) > Decimal(previous) if lower else Decimal(amount) < Decimal(previous)):
                    params[key], params[key + '_inclusive'] = amount, include
                elif Decimal(amount) == Decimal(previous):
                    params[key + '_inclusive'] = params[key + '_inclusive'] and include
            if 'min_price' in params and 'max_price' in params and Decimal(params['min_price']) > Decimal(params['max_price']):
                raise ValueError('Reversed intersection')
    except (ValueError, InvalidOperation):
        return clarification('Bạn hãy ghi ngân sách rõ đơn vị, ví dụ dưới 20 triệu hoặc từ 10 triệu đến 20 triệu; tôi chưa áp dụng bộ lọc giá chưa rõ.')

    # Names/SKUs remain literal data for the bounded ORM filter, never SQL or instructions.
    brands = re.findall(r'\b(?:asus|dell|lenovo|acer|msi|apple|hp|samsung)\b', query, re.I)
    if len(set(b.lower() for b in brands)) > 1:
        return clarification('Bạn hãy chọn một hãng/tên sản phẩm cho mỗi lần tra giá để tôi không bỏ sót điều kiện.')
    quoted = re.search(r'["“]([^"”]{1,120})["”]', query)
    named = re.search(r'^(.+?)\s+(?:giá|gia)\s+(?:là\s+|la\s+)?(?:bao nhiêu|bao nhieu)', query, re.I)
    prefix_name = re.search(r'^(?:giá của|gia cua|giá|gia)\s+(.+?)(?:\s+(?:là|la|bao nhiêu|bao nhieu)|[?!]|$)', query, re.I) if named_price else None
    term = quoted[1] if quoted else (named[1] if named else (prefix_name[1] if prefix_name else None))
    if term:
        term = re.sub(r'^(?:(?:cho tôi biết|cho toi biet|vui lòng|vui long|xin|chiếc|chiec|sản phẩm|san pham|laptop|điện thoại|dien thoai|sku)\s+)+', '', term, flags=re.I).strip(' ?!.')
        if term and len(term) <= 120:
            params['search'] = term
    else:
        if brands:
            tail = query[re.search(r'\b' + re.escape(brands[0]) + r'\b', query, re.I).start():]
            term = re.split(r'\s+(?:có|co|giá|gia|đắt|dat|mắc|mac|rẻ|re|dưới|duoi|trên|tren|từ|tu|với|voi|đang|dang|nào|nao|và|va|tối|toi|không|khong)\b', tail, maxsplit=1, flags=re.I)[0].strip(' ?!.')
            params['search'] = term[:120]
    return {'intent': 'CATALOG_LIST', 'tools': ['get_product_catalog_summary'], 'parameters': params}
