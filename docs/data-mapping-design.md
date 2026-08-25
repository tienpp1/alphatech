# Data Mapping Engine Specification

## 1. Overview & Architectural Role

The **Data Mapping Engine** (`apps.mapping`) transforms raw, heterogeneous tabular data ingested by `apps.integration` into validated canonical records adhering to the **Standard Data Model** (`apps.retail` or `apps.service_ops`).

```text
+-----------------------+     +-------------------------------+     +---------------------------+
| Raw Input Record      |     | Data Mapping Engine           |     | Canonical Standard Model  |
| (CSV / Excel / API)   | --> | 1. Field Mapping              | --> | (Validated & Ready for    |
| e.g. "tong_tien": "1.5M"|   | 2. Type Conversion            |     |  ORM Transactional Insert)|
|      "ma_kh": "KH001" |     | 3. Value Mapping              |     | e.g. revenue: 1500000.00  |
+-----------------------+     | 4. Business Transformation    |     |      customer_id: "KH001" |
                              | 5. AI-Assisted Mapping Rules  |     +---------------------------+
                              +-------------------------------+
```

---

## 2. The 5 Core Mapping Types

### Type 1: Field Mapping (Header Alias / Direct Rename)
Maps raw source column keys to canonical target attribute names.
- **Rule Definition**: `{"source_field": "tong_tien", "target_field": "revenue"}`
- **Concrete Example**:
  - *Input*: `{"tong_tien": 450000, "ma_kh": "KH_99"}`
  - *Output*: `{"revenue": 450000, "customer_id": "KH_99"}`

### Type 2: Type Conversion (Data Sanitization & Cast)
Converts unstructured string literals, regional timestamps, or unformatted numbers into standardized Python/Django primitives.
- **Supported Conversions**:
  - `STRING_TO_DECIMAL`: Strips currency symbols (`đ`, `$`, `VND`), commas, and periods (`"1.500.000 đ"` $\to$ `Decimal('1500000.00')`).
  - `STRING_TO_DATE`: Parses diverse date formats (`DD/MM/YYYY`, `YYYY-MM-DD`, `MM-DD-YYYY`) into ISO `date(YYYY, MM, DD)`.
  - `STRING_TO_DATETIME`: Parses timestamp strings with timezone normalization to `Asia/Ho_Chi_Minh` or `UTC`.
  - `STRING_TO_BOOLEAN`: Maps truthy/falsy strings (`"yes"`, `"1"`, `"true"`, `"có"`) $\to$ `True`.
- **Concrete Example**:
  - *Input*: `{"gia_ban": "1,250,000 VND", "ngay_tao": "25/08/2026 14:30"}`
  - *Output*: `{"unit_price": Decimal("1250000.00"), "order_timestamp": datetime(2026, 8, 25, 14, 30, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))}`

### Type 3: Value Mapping (Enumeration & Code Translation)
Normalizes disparate status codes, category tags, or boolean integers into canonical system enumerations.
- **Rule Definition**:
  ```json
  {
    "field": "trang_thai",
    "target_field": "status",
    "value_map": {
      "1": "COMPLETED",
      "0": "CANCELLED",
      "da_thanh_toan": "COMPLETED",
      "cho_xu_ly": "PENDING"
    },
    "default": "PENDING"
  }
  ```
- **Concrete Example**:
  - *Input*: `{"trang_thai": "da_thanh_toan"}`
  - *Output*: `{"status": "COMPLETED"}`

### Type 4: Business Transformation (Computed Expressions)
Calculates missing or derived target attributes using deterministic mathematical or string concatenation formulas.
- **Supported Operations**:
  - Arithmetic: `unit_price * quantity - discount`
  - Geo-Point Synthesis: `Point(float(kinh_do), float(vi_do))`
  - Full Name Formatting: `concat(ho, " ", ten)`
- **Concrete Example**:
  - *Input*: `{"so_luong": 5, "don_gia": 200000, "giam_gia": 50000}`
  - *Formula*: `subtotal = (so_luong * don_gia) - giam_gia`
  - *Output*: `{"subtotal": Decimal("950000.00")}`

### Type 5: AI-Assisted Mapping (Heuristic & Semantic Suggestion)
When an administrator uploads a new, unknown CSV/Excel sheet, the AI assistant inspects the header names and sample values, compares them against the Standard Data Model ontology, and suggests a `MappingRule` draft with a confidence score.
- **Mechanism**:
  1. Header semantic similarity matching using LLM / embeddings.
  2. Sample value inspection (e.g. detecting phone number patterns, date formats).
  3. Suggestion output format:
     ```json
     {
       "suggested_target_model": "Order",
       "confidence": 0.94,
       "mappings": [
         {"source": "so_don", "target": "order_number", "confidence": 0.98},
         {"source": "tien_hang", "target": "revenue", "confidence": 0.95, "type_conversion": "STRING_TO_DECIMAL"},
         {"source": "ngay_lap", "target": "order_date", "confidence": 0.96, "type_conversion": "STRING_TO_DATE"}
       ]
     }
     ```
  4. **Human Review Gate**: Administrator reviews and approves the mapping before execution.

---

## 3. Mapping Engine Input / Output Contract

### Input Contract (`MappingPayload`)
```python
{
    "workspace_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "mapping_rule_id": 42,
    "target_model": "Order",
    "raw_records": [
        {"so_hd": "HD001", "ngay_ban": "2026-08-25", "tong_tien": "1500000", "ma_kh": "CUST_01"},
        {"so_hd": "HD002", "ngay_ban": "2026-08-25", "tong_tien": "850000", "ma_kh": "CUST_02"}
    ]
}
```

### Output Contract (`TransformationResult`)
```python
{
    "status": "SUCCESS",
    "total_input_rows": 2,
    "valid_records_count": 2,
    "error_records_count": 0,
    "canonical_records": [
        {
            "order_number": "HD001",
            "order_date": "2026-08-25",
            "total_amount": "1500000.00",
            "customer_code": "CUST_01",
            "status": "COMPLETED"
        },
        {
            "order_number": "HD002",
            "order_date": "2026-08-25",
            "total_amount": "850000.00",
            "customer_code": "CUST_02",
            "status": "COMPLETED"
        }
    ],
    "errors": []
}
```
