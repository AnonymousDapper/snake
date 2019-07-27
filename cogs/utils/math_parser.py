# MIT License
#
# Copyright (c) 2018 AnonymousDapper
#
# Permission is hereby granted
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__all__ = ["MathParserError", "ParserError", "IllegalTokenError", "InvalidBinaryOpError", "InvalidUnaryOpError", "InvalidFunctionError", "InvalidNameError", "MathParser"]

import ast
import math

import operator as op

from .logger import get_logger

log = get_logger()

# Custom exception classes

class MathParserError(Exception):
    pass

class ParserError(MathParserError):
    pass

class IllegalTokenError(MathParserError):
    def __init__(self, node):
        super().__init__(f"Illegal token `{type(node).__name__}`")

class InvalidBinaryOpError(MathParserError):
    def __init__(self, node):
        super().__init__(f"Operation `{type(node.op).__name__}` is unsupported on `{type(node.left).__name__}` and `{type(node.right).__name__}`")

class InvalidCompareOpError(MathParserError):
    def __init__(self, op):
        super().__init__(f"Operation `{type(op).__name__}` ({op}) is not a valid comparison operator")

class InvalidUnaryOpError(MathParserError):
    def __init__(self, node):
        super().__init__(f"Operation `{type(node.op).__name__}` is unsupported on `{type(node.operand).__name__}`")

class InvalidFunctionError(MathParserError):
    def __init__(self, node):
        super().__init__(f"Function `{node.func.id}` is undefined")

class InvalidNameError(MathParserError):
    def __init__(self, node):
        super().__init__(f"Name `{node.id.lower()}` is undefined")


# Value-restricted math.pow
def safe_pow(n_1, n_2):
    if n_1 > 200000 or n_2 > 500:
        raise ValueError("One or more operands are too large")

    return op.pow(n_1, n_2)

# Parser class
class MathParser:
    # Allowable operators
    operators = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,

        ast.FloorDiv: op.floordiv,
        ast.Mod: op.mod,
        ast.Pow: safe_pow,

        ast.Invert: op.invert,
        ast.BitXor: op.xor,
        ast.BitOr: op.or_,
        ast.BitAnd: op.and_,
        ast.LShift: op.lshift,
        ast.RShift: op.rshift,

        ast.USub: op.neg,

        ast.Eq: op.eq,
        ast.NotEq: op.ne,
        ast.Lt: op.lt,
        ast.LtE: op.le,
        ast.Gt: op.gt,
        ast.GtE: op.ge
    }

    # Allowable functions
    functions = {
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "atan2": math.atan2,

        "sinh": math.sinh,
        "cosh": math.cosh,
        "tanh": math.tanh,
        "asinh": math.asinh,
        "acosh": math.acosh,
        "atanh": math.atanh,

        "degrees": math.degrees,
        "radians": math.radians,
        "hypot": math.hypot,
        "sqrt": math.sqrt,
        "fact": math.factorial,
        "abs": math.fabs,

        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "log1p": math.log1p,

        "exp": math.exp,
        "expm1": math.expm1,
        "pow": safe_pow,

        "ldexp": math.ldexp,
        "modf": math.modf,
        "trunc": math.trunc,
        "int": math.trunc,
        "gcd": math.gcd,
        "frexp": math.frexp,
        "fmod": math.fmod,
        "floor": math.floor,
        "ceil": math.ceil,

        "remainder": math.remainder,
        "trunc": math.trunc,

        "erf": math.erf,
        "erfc": math.erfc,
        "gamma": math.gamma,
        "lgamma": math.lgamma,
    }

    # Allowable names
    values = {
        "pi": math.pi,
        "e": math.e, # euler's number
        "inf": math.inf,
        "nan": math.nan,
        "tau": math.pi * 2,
        "c": 299792458, # speed of light in m/s
        "g": 9.80665, # standard gravity in m/s ^ 2
        "a": 6.02214076e23, # avogadro's number
        "atm": 101325, # standard atmosphere in Pa
        "h": 6.62607015e-34 # Planck's constant in Js
    }

    # Alias of __call__
    def run(self, text):
        return self.__call__(text)

    # List chunker for comparison chains
    def _sequential_chunks(self, arr, n=2):
        for i in range(0, len(arr)):
            yield arr[i:i + n]

    # Actual parsing here
    def _parse(self, node):
        log.debug(f"Parsing {ast.dump(node)}")

        # We have a plain number
        if isinstance(node, ast.Num):
            return node.n

        # Binary operation
        elif isinstance(node, ast.BinOp):
            op_name = type(node.op)

            if op_name in self.operators:
                left_op = node.left
                right_op = node.right

                return self.operators[op_name](self._parse(left_op), self._parse(right_op))

            else:
                raise InvalidBinaryOpError(node)

        # Unary operation
        elif isinstance(node, ast.UnaryOp):
            op_name = type(node.op)

            if op_name in self.operators:
                return self.operators[op_name](self._parse(node.operand))

            else:
                raise InvalidUnaryOpError(node)

        # Loading a name
        elif isinstance(node, ast.Name):
            var_name = node.id.lower()

            if isinstance(node.ctx, ast.Load):
                if var_name in self.values:
                    return self.values[var_name]

                else:
                    raise InvalidNameError(node)

            else:
                raise IllegalTokenError(node)

        # Calling a function
        elif isinstance(node, ast.Call):
            args = []

            # check/validate positional args
            for arg in node.args:
                if isinstance(arg, (ast.Name, ast.Num, ast.BinOp, ast.UnaryOp, ast.Call)):
                    args.append(self._parse(arg))

            # check/validate keyword args and run
            if len(node.keywords) == 0:
                if hasattr(node.func, "id"):
                    if node.func.id in self.functions:
                        return self.functions[node.func.id](*args)

                    else:
                        raise InvalidFunctionError(node)

                else:
                    raise IllegalTokenError(node)

            else:
                raise MathParserError("Function calls cannot have keyword arguments")

        # Comparison op
        elif isinstance(node, ast.Compare):
            ops_list = []
            for op in node.ops:
                op_name = type(op)

                if op_name in self.operators:
                    ops_list.append(self.operators[op_name])

                else:
                    raise InvalidCompareOpError(op)

            comparators = [self._parse(node.left)] + [self._parse(expr) for expr in node.comparators]

            if len(comparators) != len(ops_list) + 1:
                raise ParserError("Unbalanced operators and comparators")

            # [ [<lt>, [n_0, n_1]], [<gt>, [n_1, n_2]] ]
            result = all(data[0](data[1][0], data[1][1]) for data in zip(ops_list, list(self._sequential_chunks(comparators))[:-1]))

            return result

        else:
            raise IllegalTokenError(node)

    # Time to run the parser
    def __call__(self, text):
        try:
            expr = ast.parse(text, "<math>", mode="eval").body

        except Exception as e:
            raise ParserError(str(e)) from e

        return self._parse(expr)