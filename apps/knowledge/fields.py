"""
Dynamic vector field for dense embeddings.
Supports dynamic-dimension vector storage across environments.
Uses PostgreSQL 'vector' type when pgvector extension is available,
or falls back to 'jsonb' float array storage on non-elevated developer environments.
"""

import json
from typing import Any, List, Optional
from django.db import models
from django.core.exceptions import ValidationError


class DynamicVectorField(models.Field):
    """
    Stores dense vector embeddings with dynamic dimension support.
    """

    description = "Dense float vector embedding with dynamic dimension"

    def __init__(self, *args, dimensions: Optional[int] = None, **kwargs):
        self.dimensions = dimensions
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.dimensions is not None:
            kwargs["dimensions"] = self.dimensions
        return name, path, args, kwargs

    def db_type(self, connection):
        if connection.vendor == "postgresql":
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                    if cursor.fetchone():
                        if self.dimensions:
                            return f"vector({self.dimensions})"
                        return "vector"
            except Exception:
                pass
            return "jsonb"
        return "text"

    def from_db_value(self, value, expression, connection) -> Optional[List[float]]:
        if value is None:
            return None
        if isinstance(value, list):
            return [float(x) for x in value]
        if isinstance(value, str):
            value = value.strip()
            # Handle PostgreSQL vector string literal format: "[0.1, 0.2, 0.3]"
            if value.startswith("[") and value.endswith("]"):
                try:
                    return [float(x.strip()) for x in value[1:-1].split(",") if x.strip()]
                except (ValueError, TypeError):
                    pass
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [float(x) for x in parsed]
            except Exception:
                pass
        return None

    def to_python(self, value: Any) -> Optional[List[float]]:
        if value is None or isinstance(value, list):
            if value is not None:
                return [float(x) for x in value]
            return None
        return self.from_db_value(value, None, None)

    def get_prep_value(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if hasattr(value, "tolist"):
            value = value.tolist()
        if isinstance(value, (list, tuple)):
            clean_floats = [float(x) for x in value]
            return json.dumps(clean_floats)
        return json.dumps(value)

    def value_to_string(self, obj) -> str:
        value = self.value_from_object(obj)
        return json.dumps(self.get_prep_value(value))
