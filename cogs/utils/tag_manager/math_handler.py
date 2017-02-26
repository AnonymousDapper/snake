""" Math parser """

import ast, math

import operator as op

class MathParserError(Exception):
    pass

class ParseError(MathParserError):
    pass

class IllegalTokenError(MathParserError):
    def __init__(self, node):
        super().__init__(f"Illegal operation `{type(node).__name__}`")

class InvalidBinaryOperatorError(MathParserError):
    def __init__(self, node):
        super().__init__(f"Cannot perform `{type(node.op).__name__}` on types `{type(node.left).__name__}` and `{type(node.right).__name__}`")

class InvalidUnaryOperatorError(MathParserError):
    def __init__(self, node):
        super().__init__(f"Cannot perform `{type(node.op).__name__}` on type `{type(node.operand).__name__}`")

class InvalidFunctionError(MathParserError):
    def __init__(self, node):
        super().__init__(f"No function called `{node.func.id}` found")

class InvalidConstantError(MathParserError):
    def __init__(self, node):
        super().__init__(f"No value called `{node.id.lower()}` found")

def safe_pow(n_1, n_2):
    if n_1 > 200000 or n_2 > 500:
        raise ValueError("One or more operands are too large")
    return op.pow(n_1, n_2)

class MathParser:
    # allowable operators
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

        ast.USub: op.neg
    }

    # allowable functions
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
    }

    # allowable variables
    values = {
        "pi": math.pi,
        "e": math.e,
        "inf": math.inf,
        "nan": math.nan,
        "tau": math.pi * 2,
        "pie": math.pi ** math.e,
    }

    def __init__(self, text, **kwargs):
        self.debug = kwargs.get("debug", False)
        self.logger = kwargs.get("logger", None)

        self.log(text)

        try:
            self.text = text
            self.expr = ast.parse(text, "<math>", mode="eval").body
        except Exception as e:
            print("errored", e)
            raise ParseError(str(e) + "test-asd") from e

    # Debug log
    def log(self, text):
        if self.debug:
            if self.logger is not None:
                self.logger.log(text)
            else:
                print(text)

    # Alias of __call__
    def run(self):
        return self.__call__()

    # Parse AST nodes
    def __parse(self, node):
        self.log(f"Parsing {ast.dump(node)}")

        if isinstance(node, ast.Num):
            return node.n

        elif isinstance(node, ast.BinOp):
            op_name = type(node.op)
            if op_name in self.operators:
                left_op = node.left
                right_op = node.right
                return self.operators[op_name](self._MathParser__parse(left_op), self._MathParser__parse(right_op))
            else:
                raise InvalidBinaryOperatorError(node)

        elif isinstance(node, ast.UnaryOp):
            op_name = type(node.op)
            if op_name in self.operators:
                return self.operators[op_name](self._MathParser__parse(node.operand))
            else:
                raise InvalidUnaryOperatorError(node)

        elif isinstance(node, ast.Name):
            var_name = node.id
            if isinstance(node.ctx, ast.Load):
                if var_name.lower() in self.values:
                    return self.values[var_name.lower()]
                else:
                    return InvalidConstantError(node)
            else:
                raise IllegalTokenError(node)

        elif isinstance(node, ast.Call):
            args = []

            for arg in node.args:
                if isinstance(arg, ast.Name) or isinstance(arg, ast.Num) or isinstance(arg, ast.BinOp) or isinstance(arg, ast.UnaryOp) or isinstance(arg, ast.Call):
                    args.append(self._MathParser__parse(arg))

            if len(node.keyworks) == 0:
                if hasattr(node.func, "id"):
                    if node.func.id in self.functions:
                        return self.functions[node.func.id](*args)
                    else:
                        raise InvalidFunctionError(node)
                else:
                    raise IllegalTokenError(node)
            else:
                raise MathParserError("Function calls cannot take keyword arguments")

        else:
            raise IllegalTokenError(node)

    # Run parser
    def __call__(self):
        return self._MathParser__parse(self.expr)