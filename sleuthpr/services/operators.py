from typing import Any

try:
    import re2 as re
except ImportError:
    print("Cannot find re2, switching to insecure default")
    import re


class Operator:
    def __init__(self, name: str, label: str):
        self.name = name
        self.label = label

    def evaluate(self, leval: Any, reval: Any) -> bool:
        raise NotImplementedError()


class GreaterThan(Operator):
    def evaluate(self, leval: Any, reval: Any) -> bool:
        if isinstance(leval, list):
            if isinstance(reval, int):
                return len(leval) > reval
            else:
                raise ValueError("Cannot compare a non-int to a list")
        return leval > reval


class GreaterThanOrEqual(Operator):
    def evaluate(self, leval: Any, reval: Any) -> bool:
        if isinstance(leval, list):
            if isinstance(reval, int):
                return len(leval) >= reval
            else:
                raise ValueError("Cannot compare a non-int to a list")
        return leval >= reval


class LessThan(Operator):
    def evaluate(self, leval: Any, reval: Any) -> bool:
        if isinstance(leval, list):
            if isinstance(reval, int):
                return len(leval) < reval
            else:
                raise ValueError("Cannot compare a non-int to a list")
        return leval < reval


class LessThanOrEqual(Operator):
    def evaluate(self, leval: Any, reval: Any) -> bool:
        if isinstance(leval, list):
            if isinstance(reval, int):
                return len(leval) <= reval
            else:
                raise ValueError("Cannot compare a non-int to a list")
        return leval <= reval


class Equal(Operator):
    def evaluate(self, leval: Any, reval: Any) -> bool:
        if isinstance(leval, list):
            if isinstance(reval, int):
                return len(leval) == reval
            else:
                return reval in leval
        return leval == reval


class NotEqual(Operator):
    def evaluate(self, leval: Any, reval: Any) -> bool:
        if isinstance(leval, list):
            if isinstance(reval, int):
                return len(leval) != reval
            else:
                return reval not in leval
        return leval != reval


class Matches(Operator):
    def evaluate(self, leval: Any, reval: Any) -> bool:
        ptn = re.compile(reval)
        if isinstance(leval, list):
            for item in leval:
                if ptn.match(item):
                    return True
            return False
        return ptn.match(leval) is not None


OPERATORS = {
    ">": GreaterThan(">", "Greater than"),
    ">=": GreaterThanOrEqual(">=", "Greater than or equal to"),
    "<": LessThan("<", "Less than"),
    "<=": LessThanOrEqual("<=", "Less than or equal to"),
    "=": Equal("=", "Equal to"),
    "!=": NotEqual("!=", "Not equal to"),
    "<>": NotEqual("<>", "Not equal to"),
    "~=": Matches("~=", "Matches regular expression pattern"),
}
