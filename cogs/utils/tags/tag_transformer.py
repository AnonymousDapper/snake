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


import math

import operator as op

from lark import Tree, v_args, Transformer

LITERAL_TYPES = (int, float, str, bool, type(None))

# Value-restricted math.pow
def safe_pow(n_1, n_2):
    if n_1 > 200000 or n_2 > 500:
        raise ValueError("One or more operands are too large")

    return op.pow(n_1, n_2)

class LazySlice:
    def __init__(self, start, stop=float('inf'), step=1):
        self.start = start
        self.stop = stop
        self.step = step

        __metaclass__ = slice

    def __eq__(self, other):
        return (self.start == other.start) and (self.stop == other.stop) and (self.step == other.step)

    def __reduce__(self):
        return (LazySlice, (self.start, self.stop, self.step))

    def __repr__(self):
        return f"<LazySlice({self.start}, {self.stop}, {self.step})>"

    def indices(self, length):
        print(length)

        return (self.start, min(length, self.stop), self.step)


class StagTransformer(Transformer):
    # Replace TEXT node with inner text
    @v_args(inline=True)
    def text(self, n):
        return str(n)


    # Str -> Operator func replacements
    @v_args(inline=True)
    def number(self, n):
        if n.type == "DEC_NUMBER":
            return int(n)

        elif n.type == "HEX_NUMBER":
            return int(n, 16)

        elif n.type == "OCT_NUMBER":
            return int(n, 8)

        elif n.type == "BIN_NUMBER":
            return int(n, 2)

        elif n.type == "FLOAT_NUMBER":
            return float(n)

    @v_args(inline=True)
    def lor_op(self, n):
        return lambda l, r: l or r

    @v_args(inline=True)
    def land_op(self, n):
        return lambda l, r: l and r

    @v_args(inline=True)
    def bit_op(self, n):
        if n == "|":
            return op.or_

        elif n == "^":
            return op.xor

        elif n == "&":
            return op.and_

        elif n == ">>":
            return op.rshift

        elif n == "<<":
            return op.lshift

    @v_args(inline=True)
    def eq_op(self, n):
        if n == "==":
            return op.eq

        elif n == "!=":
            return op.ne

    @v_args(inline=True)
    def cmp_op(self, n):
        if n == "<":
            return op.lt

        elif n == "<=":
            return op.le

        elif n == ">=":
            return op.ge

        elif n == ">":
            return op.gt

        elif n == "in":
            return op.contains

    @v_args(inline=True)
    def add_op(self, n):
        if n == "+":
            return op.add

        elif n == "-":
            return op.sub

    @v_args(inline=True)
    def mul_op(self, n):
        if n == "*":
            return op.mul

        elif n == "/":
            return op.truediv

        elif n == "%":
            return op.mod

        elif n == "**":
            return safe_pow

        elif n == "//":
            return op.floordiv

    @v_args(inline=True)
    def unary_op(self, n):
        if n == "not":
            return op.not_

        elif n == "-":
            return op.neg

        elif n == "~":
            return op.invert

        elif n == "+":
            return op.pos

    # Replace single-child exprs with child
    @v_args(tree=True)
    def unary_expr(self, tree):
        if len(tree.children) == 1:
            return tree.children[0]

        else:
            if isinstance(tree.children[1], LITERAL_TYPES):
                return tree.children[0](tree.children[1])

            else:
                return tree

    # Remove 'literal' node from tree
    @v_args(inline=True)
    def literal(self, n):
        if hasattr(n, "type"):
            if n.type == "TRUE":
                return True

            elif n.type == "FALSE":
                return False

            elif n.type == "NONE":
                return None

            elif n.type == "STRING":
                return n[1:-1]

        else:
            return n

    # Replace NAME token with string
    @v_args(tree=True)
    def ident(self, tree):
        tree.children = [str(tree.children[0])]

        return tree

    # Flatten range_comp node
    @v_args(tree=True)
    def range(self, tree):
        tree.children = tree.children[0].children

        return tree

    # Flatten subscript_list node
    @v_args(tree=True)
    def index(self, tree):
        tree.children = [
            tree.children[0],
            *tree.children[1].children
        ]

        return tree

    # Transform subscript_list node to python slice
    # @v_args(tree=True)
    # def subscript_list(self, tree):
    #     children = tree.children
    #     start, stop, step = 0, None, 1

    #     for child in children:
    #         if child.data == "subscript_start":
    #             start = child.children[0]

    #         if child.data == "subscript_end":
    #             stop = child.children[0]

    #         if child.data == "subscript_step":
    #             step = child.children[0]

    #     return (start, stop, step)


    # Replace infix_call node with fun_call
    @v_args(inline=True)
    def infix_call(self, l, op, r):
        return Tree("fun_call", [
            op,
            Tree("fun_args", [l, r])
        ])

    # Literal inlining
    @v_args(tree=True)
    def or_test(self, tree):
        l, op_fn, r = tree.children

        if isinstance(l, LITERAL_TYPES) and isinstance(r, LITERAL_TYPES):
            return op_fn(l, r)

        else:

            return tree


    # Literal inlining
    @v_args(tree=True)
    def and_test(self, tree):
        l, op_fn, r = tree.children

        if isinstance(l, LITERAL_TYPES) and isinstance(r, LITERAL_TYPES):
            return op_fn(l, r)

        else:

            return tree

    # Literal inlining
    @v_args(tree=True)
    def is_test(self, tree):
        print(tree)
        l, r = tree.children

        if isinstance(l, LITERAL_TYPES) and isinstance(r, LITERAL_TYPES):
            return op.is_(l, r)

        else:

            return tree

    # Literal inlining
    @v_args(tree=True)
    def is_not_test(self, tree):
        print(tree)
        l, r = tree.children

        if isinstance(l, LITERAL_TYPES) and isinstance(r, LITERAL_TYPES):
            return op.is_not(l, r)

        else:

            return tree

    # Literal inlining
    @v_args(tree=True)
    def bitwise_expr(self, tree):
        l, op_fn, r = tree.children

        if isinstance(l, LITERAL_TYPES) and isinstance(r, LITERAL_TYPES):
            return op_fn(l, r)

        else:

            return tree

    # Literal inlining
    @v_args(tree=True)
    def eq_expr(self, tree):
        l, op_fn, r = tree.children

        if isinstance(l, LITERAL_TYPES) and isinstance(r, LITERAL_TYPES):
            return op_fn(l, r)

        else:

            return tree

    # Literal inlining
    @v_args(tree=True)
    def cmp_expr(self, tree):
        l, op_fn, r = tree.children

        if isinstance(l, LITERAL_TYPES) and isinstance(r, LITERAL_TYPES):
            return op_fn(l, r)

        else:

            return tree

    # Literal inlining
    @v_args(tree=True)
    def add_expr(self, tree):
        l, op_fn, r = tree.children

        if isinstance(l, LITERAL_TYPES) and isinstance(r, LITERAL_TYPES):
            return op_fn(l, r)

        else:

            return tree

    # Literal inlining
    @v_args(tree=True)
    def mul_expr(self, tree):
        l, op_fn, r = tree.children

        if isinstance(l, LITERAL_TYPES) and isinstance(r, LITERAL_TYPES):
            return op_fn(l, r)

        else:

            return tree