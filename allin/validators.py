from enum import Enum, EnumMeta
from typing import Any, Union, _AnnotatedAlias
from uuid import UUID

from msgspec import DecodeError, inspect, json


def _int_validator(value) -> int:
    try:
        return int(value)
    except ValueError as e:
        raise ValueError("A valid integer is required.") from e


def _float_validator(value) -> float:
    try:
        return float(value)
    except ValueError as e:
        raise ValueError("A valid number is required.") from e


CONVERTER_TYPES = Union[int, float, str, UUID, Enum, _AnnotatedAlias]
CONVERTER_FUNCS = {
    int: _int_validator,
    float: _float_validator,
}


def _is_requires_double_quotes(t: Any):
    ti = inspect.type_info(t, protocol="json")
    if isinstance(ti, (inspect.IntType, inspect.FloatType)):
        return False
    return True


class Validator:
    def __init__(self, param_type: CONVERTER_TYPES) -> None:
        self.param_type = param_type
        self.use_msgspec = isinstance(param_type, _AnnotatedAlias) or param_type is UUID
        self.requires_double_quotes = _is_requires_double_quotes(param_type)
        self.decoder = (
            json.Decoder(param_type)
            if self.use_msgspec
            else CONVERTER_FUNCS.get(param_type, param_type)
        )
        self._before_validate_fn = None
        if type(param_type) is EnumMeta:
            enum_type = getattr(param_type, "_member_type_", object)
            if enum_type is object:
                raise TypeError(
                    f"does not support dynamic values from enum {param_type!r}."
                )

            self._before_validate_fn = CONVERTER_FUNCS.get(enum_type)

    def validate(self, value: Any) -> tuple[bool, str]:
        err = False
        try:
            if callable(self._before_validate_fn):
                value = self._before_validate_fn(value)

            if self.use_msgspec:
                value = f'"{value}"' if self.requires_double_quotes else f"{value}"
                rv = self.decoder.decode(value)
            else:
                rv = self.decoder(value)
        except (ValueError, DecodeError) as e:
            rv = str(e)
            err = True
        return err, rv
