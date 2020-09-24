from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import Dict
from typing import List

import pyparsing as pp

from sleuthpr import registry
from sleuthpr.models import ConditionVariableType


class ParsedExpression:
    def __init__(self, text: str):
        self.expression = expr.parseString(text)[0]

        self.variables: List[ConditionVariableType] = []

        def collect_vars(token):
            if isinstance(token, Identifier):
                self.variables.append(registry.get_condition_variable_type(token.name))

        self.expression.visit(collect_vars)

    def execute(self, **context):
        return self.expression.eval(context)


class Expression:
    def __init__(self, tokens):
        self.and_conditions = tokens[::2]

    def generate(self):
        return (
            "("
            + " OR ".join(
                (and_condition.generate() for and_condition in self.and_conditions)
            )
            + ")"
        )

    def eval(self, context: Dict):
        for cond in self.and_conditions:
            result = cond.eval(context)
            if result:
                return True

        return False

    def visit(self, visitor: Callable[[Any], None]):
        visitor(self)
        for cond in self.and_conditions:
            cond.visit(visitor)


class AndCondition:
    def __init__(self, tokens):
        self.conditions = tokens[::2]

    def generate(self):
        result = " AND ".join((condition.generate() for condition in self.conditions))
        if len(self.conditions) > 1:
            result = "(" + result + ")"
        return result

    def eval(self, context: Dict):
        for cond in self.conditions:
            result = cond.eval(context)
            if not result:
                return False

        return True

    def visit(self, visitor: Callable[[Any], None]):
        visitor(self)
        for cond in self.conditions:
            cond.visit(visitor)


class Condition:
    def __init__(self, tokens):
        self.identifier = tokens[0][0]
        self.op = tokens[0][1]
        self.rval = tokens[0][2]

    def generate(self):
        return " ".join((self.identifier.generate(), self.op, self.rval.generate()))

    def eval(self, context: Dict):
        leval = self.identifier.eval(context)
        reval = self.rval.eval(context)
        if self.op == "=":
            return leval == reval
        elif self.op == "!=" or self.op == "<>":
            return leval != reval
        elif self.op == "<":
            return leval < reval
        elif self.op == ">":
            return leval > reval
        elif self.op == "<=":
            return leval <= reval
        elif self.op == ">=":
            return leval <= reval
        raise ValueError()

    def visit(self, visitor: Callable[[Any], None]):
        visitor(self)
        self.identifier.visit(visitor)
        visitor(op)
        self.rval.visit(visitor)


class String:
    def __init__(self, result):
        self.value = result[0]

    def generate(self):
        return "'{}'".format(self.value)

    def eval(self, context: Dict):
        return self.value

    def visit(self, visitor: Callable[[Any], None]):
        visitor(self)
        visitor(self.value)


class Number:
    def __init__(self, result):
        self.value = result[0]

    def generate(self):
        return self.value

    def eval(self, context: Dict):
        return int(self.value)

    def visit(self, visitor: Callable[[Any], None]):
        visitor(self)
        visitor(self.value)


class Identifier:
    def __init__(self, result):
        self.name = result[0]

    def generate(self):
        return self.name

    def eval(self, context: Dict):
        return context.get(self.name)

    def visit(self, visitor: Callable[[Any], None]):
        visitor(self)
        visitor(self.name)


lparen = pp.Suppress("(")
rparen = pp.Suppress(")")

and_ = pp.Literal("AND")
or_ = pp.Literal("OR")

op = pp.oneOf(("=", "!=", ">", ">=", "<", "<="))

alphaword = pp.Word(pp.alphanums + "_")
string = pp.QuotedString(quoteChar="'").setParseAction(String)

number = (
    pp.Word(pp.nums) + pp.Optional("." + pp.OneOrMore(pp.Word(pp.nums)))
).setParseAction(Number)

identifier = alphaword.setParseAction(Identifier)


expr = pp.Forward()

condition = pp.Group(identifier + (op + (string | number))).setParseAction(Condition)

condition = condition | (lparen + expr + rparen)

and_condition = (condition + pp.ZeroOrMore(and_ + condition)).setParseAction(
    AndCondition
)

expr << (and_condition + pp.ZeroOrMore(or_ + and_condition))
expr = expr.setParseAction(Expression)
