from typing import Any, Dict, Type, get_origin, get_type_hints


def clean_data(model: Type[object], data: Dict[str, Any]) -> Dict[str, Any]:
    hints = get_type_hints(model)
    return {
        key: _coerce(hints.get(key, Any), value) for key, value in data.items()
    }


def _coerce(param_type, value: Any) -> Any:
    if (
        get_origin(param_type) != list
        and isinstance(value, list)
        and len(value) == 1
    ):
        value = value[0]

    return value
