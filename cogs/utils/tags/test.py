import os

import operator as op

from lark import Lark, Tree

from lark.tree import pydot__tree_to_png

from tag_transformer import StagTransformer

parser = Lark.open("stag.lark", parser="lalr", start="stmt_list", debug=True, keep_all_tokens=False, propagate_positions=True)

# def sp():
#     global parser
#     parser = Lark.open("stag.lark", parser="lalr", start="_stmt", debug=True, keep_all_tokens=True, propagate_positions=True)

def p(s, r=False):
    tree = parser.parse(s)
    ntree = StagTransformer().transform(tree)
    print(ntree)
    print(ntree.pretty())

    if r:
        return ntree

def product(arr):
    result = 1
    for n in arr:
        result *= n

    return result

def plot(s, n="tree.png", pp=True):
    tree = p(s, r=True)
    pydot__tree_to_png(tree, n)

    if pp:
        os.system("photoqt " + n)
    print(tree)

def test(s):
    tree = p(s)

    new_parser = Parser()
    res = new_parser.run_parse(tree)
    print(res)

def run_test():
    with open("examples.stag", "r") as f:
        lines = f.read().split("\n")

    for idx, line in enumerate(lines):
        print(line)
        plot(line, n=f"imgs/test_{idx}.png", pp=False)


    # # List chunker for comparison chains
    # def _sequential_chunks(self, arr, n=2):
    #     print(f"Chunking {arr}")
    #     result = []

    #     for i in range(0, len(arr)):
    #         result.append(arr[i:i + n])

    #     return result[:-1]

    # # List chunker for split chunks
    # def _staggered_chunks(self, arr):
    #     print(f"S-Chunking {arr}")
    #     arr_len = len(arr)
    #     result = []

    #     for i in range(0, arr_len):
    #         result.append(arr[i * 2:(2 * i + 3)])

    #     return result[:int(arr_len / 2)]

    # def _compare_reduce(self, op_fn, comparators):
    #     result = []
    #     for [left, right] in self._sequential_chunks(comparators):
    #         result.append(op_fn(left, right))

    #     print(f"Reduce pass result: {result}")
    #     if len(result) > 1:
    #         return self._compare_reduce(op_fn, result)

    #     else:
    #         return result[0]

    # # Recursive reduction for comparison chains
    # def _compare_reduce_complex(self, arr):
    #     result = []
    #     for [left, op_fn, right] in self._staggered_chunks(arr):
    #         result.append(op_fn(left, right))

    #     print(f"Reduce complex pass result: {result}")
    #     if len(result) > 1:
    #         return self._compare_reduce_complex(result)