import json
from datetime import datetime
from decimal import Decimal


class JsonBuilder:
    __slots__ = ()

    def build(self, data, indent: int = 4):
        return json.dumps(
            data,
            default=self._serialize,
            ensure_ascii=False,
            indent=indent,
        )

    @staticmethod
    def _serialize(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")