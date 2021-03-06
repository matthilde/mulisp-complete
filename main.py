#!/usr/bin/env python3
#
# Small lisp
#
import re
from ast import literal_eval as le
from dis import opmap, dis
import dis as dism
import sys
from typing import Any
from dataclasses import dataclass
from functools import partial
import inspect as i

instrs = type("ins", (object,), opmap)
ptr = type("ptr", (object,), dict(__annotations__={"val":Any}))
code_type = (lambda: 0).__code__.__class__

parse_lisp = lambda mu: (_parselisp:=lambda tokens: (a:=True,ast:=[],
    [(token:=tokens.pop(0),
    ast.append([lambda:token,
    lambda:_parselisp(tokens),
    lambda:int(token),
    lambda:['quote', _parselisp(tokens) # i think quote makes more sense tbh
            if len(token) == 2 \
            and token[1] == "(" else token[1:]],
    lambda:['quote', le(token)],
    lambda:['list', *_parselisp(tokens)] 
        ][
        0+int(token=='(')+int(bool(re.match(r"[+-]?\d+", token)))*2+ \
        int(token.startswith("'"))*3+int(token.startswith('"'))*4+ \
        int(token=='@(')*5]()) \
        if token!=')' and not token.startswith(';') else (a:=False))[-1] for _ in \
        iter(lambda:tokens!=[] and a, False)], ast)[-1],
              _parselisp(re.findall(r""";.*$|".*?[^\\]"|'[\w\-]+|'\(|'|@\(|[()]|[^\s()']+|[()]""",mu)))[-1]

macros = {}

# this typo was perfect, keep comiler lmao
# cldnlfnvlfnlnvf
# cumiler :floshed:
cumiler = lambda ast, name = "<toplevel>", filename = "<interactive>", fastnames = [], bytecode = None, argcount = 0, flags = 0: (
    bytecode := [] if bytecode is None else bytecode, # sowwy, got carried away
    throw := (0 for _ in ()).throw,
    required_stacksize := [0],
    add_stacksize := lambda n: (
        required_stacksize.append(required_stacksize[-1] + n)
    ),
    nlocals := [len(fastnames)],
    inc_nlocals := lambda: nlocals.__setitem__(0, nlocals[0]+1),
    consts := [None],
    push_nil := [instrs.LOAD_CONST, 0],
    names := [],
    addmacro := macros.__setitem__, # *admiring you writing code*
    insert_const := lambda el: (
        consts.append(el) if el not in consts else None,
        bytecode.extend([instrs.LOAD_CONST, consts.index(el)]),
    ),
    quote := lambda ast: (
        el := ast[0],
        {
            str: lambda: insert_const(el),
            int: lambda: insert_const(el),
            list:lambda: compile_el(el[1]) 
                if len(el) == 2 and el[0] == "unquote" 
                else (
                add_stacksize(len(el)),
                [quote([e]) for e in el],
                bytecode.extend([instrs.BUILD_TUPLE, len(el)]),
                add_stacksize(-len(el))
            )
        }[type(el)]()
    ),
    make_a_lambda := lambda ast, fname = "<lisp lambda>": (
            add_stacksize(1),
            flags := 0,
            (ast.pop(0), flags := flags | i.CO_COROUTINE)
             if ast[0] == ['quote', 'async'] else None,
            bytecode.extend([instrs.LOAD_CONST, len(consts),
                             instrs.LOAD_CONST, len(consts)+1,
                             instrs.MAKE_FUNCTION, 0,]),
            fargs := ast[0],
            argcount := len(ast[0]),
            (
                fargs.__setitem__(-1, fargs[-1][1:]), 
                argcount := argcount - 1,
                flags := flags | i.CO_VARARGS
            ) if len(fargs) > 0 and fargs[-1].startswith("&")
            else None,
            consts.extend([cumiler(ast[1:], fastnames = list(fargs), flags = flags, 
                    argcount = argcount, name=fname), fname]),
            add_stacksize(-1)),
    compile_block := lambda ast: (
        [(
            compile_el(el),
            bytecode.extend([instrs.POP_TOP, 0])
        ) for el in ast[:-1]],
        compile_el(ast[-1])
    ),
    addimport := lambda ast, fromi = 0: (
        modname:=ast[0],
        consts.append(0) if 0 not in consts else None,
        names.append(modname) if modname not in consts else None,
        level:=consts.index(0),

        bytecode.extend([instrs.LOAD_CONST, level,
                        instrs.LOAD_CONST, fromi,
                        instrs.IMPORT_NAME, names.index(modname)])
    ),
    asm_metamods := {
        "inc-nlocals": inc_nlocals,
        "add-stacksize": add_stacksize,
        "make-a-lambda": lambda ast, name = "<lisp lambda>":
            make_a_lambda(ast_to_list(ast), name)

    },
    unquote := lambda quoted: (
        quoted[1] if isinstance(quoted, list) and len(quoted) > 0 and quoted[0] == "quote" else quoted
    ),
    builtins := { # require 
        "compmacro": lambda ast: (
            addmacro(ast[0], cumiler(ast[1:], name=ast[0])),
            bytecode.extend(push_nil) # bc defmacro has to be an expression
        ),
        "quote": quote,
        ".": lambda ast: ( # attribute access
            obj := ast[0],
            path := ast[1:],
            compile_el(obj),
            [(
                bytecode.extend([instrs.LOAD_ATTR, len(names)]),
                names.append(segment)
            ) for segment in path]
        ),
        # "mu": lambda _: print("IMPORTANT COMPILER MESSAGE: mu :pleading_face:"), # ok now imma shower for real lol
        "higher-abstraction-of-very-important-stuff": lambda _: bytecode.extend([instrs.NOP, 0, *push_nil]), # please keep it lmao
        "when": lambda ast:
            compile_el(["print", ["quote", "amogus"]] 
            if ast == ["the", "impostor", "is", "sus"]
            else ["print", ["quote", "when what?"]]),
        "setq": lambda ast: (
            compile_el(ast[1]),
            bytecode.extend([instrs.STORE_NAME, len(names), 
                            *push_nil]),
            inc_nlocals() if ast[0] not in names else None,
            names.append(ast[0]),
        ),  
        "\\": make_a_lambda,
        "lambda": make_a_lambda,
        "defn": lambda ast: (
            make_a_lambda(ast[1:], fname = ast[0]),
            (inc_nlocals(), names.append(ast[0])) if ast[0] \
            not in names else None,
            bytecode.extend([instrs.STORE_NAME, names.index(ast[0]),
                             *push_nil])
        ),
        "do": compile_block,
        "if": lambda ast: (
            expr:=ast[0], then:=ast[1], els:=ast[2],
            # :thonk:
            # fuck
            compile_el(expr),
            pjif:=len(bytecode)+1,
            bytecode.extend([instrs.POP_JUMP_IF_FALSE, 0]), # will be changed later
            compile_el(then),
            jf:=len(bytecode)+1,
            bytecode.extend([instrs.JUMP_FORWARD, 0]),
            bytecode.__setitem__(pjif, len(bytecode)),
            compile_el(els),
            bytecode.__setitem__(jf, len(bytecode)-jf) # I think that's it
        ),
        "while": lambda ast: (
            cond:=ast[0], expr:=ast[1:],

            (inc_nlocals(), names.append("_iterator")) if "_iterator" not in names else None,
            bytecode.extend([*push_nil, instrs.STORE_NAME, names.index("_iterator")]),
            begin:=len(bytecode), # we gotta jump here till false
            compile_el(cond),
            pjif:=len(bytecode)+1,
            
            bytecode.extend([instrs.POP_JUMP_IF_FALSE, 0]),
            [compile_el(x) for x in expr],
            
            bytecode.extend([instrs.STORE_NAME, names.index("_iterator")]),
            bytecode.extend([instrs.JUMP_ABSOLUTE, begin]),
            bytecode.__setitem__(pjif, len(bytecode)),
            bytecode.extend([instrs.LOAD_NAME, names.index("_iterator")])
        ),
        "for": lambda ast: (
            itervar:=ast[0], itertr:=ast[1], expr:=ast[2:],
            (names.append(itervar), inc_nlocals()) if itervar not in names else None,

            compile_el(itertr),
            bytecode.extend([instrs.GET_ITER, 0]),
            begin:=len(bytecode),
            bytecode.extend([instrs.FOR_ITER, 0]),
            bytecode.extend([instrs.STORE_NAME, names.index(itervar)]),
            [compile_el(x) for x in expr],
            bytecode.extend([instrs.POP_TOP, 0, instrs.JUMP_ABSOLUTE, begin]),
            bytecode.__setitem__(begin+1, len(bytecode)-begin-2),
            bytecode.extend([instrs.LOAD_NAME, names.index(itervar)])
        ),
        "catch": lambda ast: (
            add_stacksize(2),
            xtr:=ast[1:], catch:=ast[0],
            setup_finally := len(bytecode) + 1,
            bytecode.extend([instrs.SETUP_FINALLY, 0]), # will be filled in, shows where the handler code is
            compile_block(xtr),
            bytecode.extend([instrs.POP_BLOCK, 0]),
            jump_forward := len(bytecode) + 1,
            bytecode.extend([instrs.JUMP_FORWARD, 0]),
            bytecode.__setitem__(setup_finally, len(bytecode) - setup_finally - 1),
            names.append("exn") if "exn" not in names else None,
            namei := names.index("exn"),
            bytecode.extend([instrs.POP_TOP, 0,
                             instrs.STORE_NAME, namei]),
            compile_el(catch),
            bytecode.__setitem__(jump_forward, len(bytecode) - jump_forward-1),
            add_stacksize(-2)
        ),
        "raise": lambda ast: (
            (add_stacksize(1), add_stacksize(-1)) if len(ast) > 1
            else None,
            throw(ValueError("raise cannot have more than 2 arguments")) if len(ast) > 2 else None,
            [compile_el(el) for el in ast],
            bytecode.extend([instrs.RAISE_VARARGS, len(ast)])
            # no return value as the stack is going byebye anyways
        ),
        "import": lambda ast: (
            addimport(ast),
            bytecode.extend([instrs.STORE_GLOBAL, names.index(ast[0]),
                            *push_nil])
        ),
        "importfrom": lambda ast: (
            modname := ast[0],
            limit_to := ast[1:],
            fromi := len(consts),
            consts.append(tuple(limit_to)),
            addimport([modname], fromi = fromi),
            bytecode.extend([instrs.IMPORT_STAR, 0, *push_nil])
        ),
        "await": lambda ast: (
            compile_el(ast[0]),
            bytecode.extend([instrs.GET_AWAITABLE, 0,
                             *push_nil,
                             instrs.YIELD_FROM, 0])
        ),
        "compile-exprs": lambda ast: [compile_el(el) for el in ast],
        "asm": lambda ast: (
            labels := {},
            buf := [],
            extrafuncs := {
                "label": lambda name: labels.__setitem__(name, len(bytecode))
            },
            extrafuncs.update(asm_metamods),
            add_instr := lambda name, arg = 0: (
                opcode := opmap[name.upper()],
                arg := unquote(arg) if arg != "nil" else None,
                arg := [
                    lambda: arg,
                    lambda: (
                        names.append(arg) if arg not in names else None,
                        names.index(arg)
                    )[-1],
                    lambda: (
                        consts.append(arg) if arg not in consts else None,
                        consts.index(arg)
                    )[-1]
                ][int(opcode in dism.hasname)
                + 2 * int(opcode in dism.hasconst)](),
                buf.extend([opcode, arg])
            ),
            [(
                extrafuncs[instr[0]](*instr[1:])
                if instr[0] in extrafuncs
                else add_instr(*instr)
            ) for instr in ast],
            bytecode.extend(map(lambda x: x if not isinstance(x, str) else labels[x], buf))
        ),
        "tailrecurse": lambda ast: (
            [(
                compile_el(el),
                bytecode.extend([instrs.STORE_FAST, idx])
            ) for idx, el in enumerate(ast)],
            bytecode.extend([instrs.JUMP_ABSOLUTE, 0])
        )
    },
    ast_to_tuple := lambda ast: tuple(ast_to_tuple(el) for el in ast) if isinstance(ast, list) else ast,
    ast_to_list := lambda ast: [ast_to_list(el) for el in ast] if isinstance(ast, tuple) else ast,
    expand_macro := lambda name, args: compile_el(ast_to_list(eval_lisp(macros[name], new_globals({"args": ast_to_tuple(args)})))),
    compile_el := lambda el: { # compiles ast to py bytecode
        str: lambda: (
            # what are you doing >
            # fixing le error.>
            bytecode.extend([instrs.LOAD_FAST, fastnames.index(el)])
            if el in fastnames else 
            bytecode.extend([instrs.LOAD_NAME, len(names)]),
            names.append(el)
        ),
        list: lambda: (
            func := el[0],
            is_str := isinstance(func, str),
            [
                lambda: (
                    add_stacksize(len(el)),
                    [compile_el(e) for e in el],
                    bytecode.extend([instrs.CALL_FUNCTION, len(el)-1]),
                    add_stacksize(-len(el))
                ),
                lambda: expand_macro(func, el[1:]),
                lambda: builtins[func](el[1:])
            ][int(is_str and func in macros)
            + int(is_str and func in builtins) * 2]()
        ),
        int: lambda: insert_const(el)
    }[type(el) if not isinstance(el, tuple) else list](),
    compile_block(ast),
    bytecode.extend([instrs.RETURN_VALUE, 0]),
    code_type(argcount, 0, 0, nlocals[0], max(required_stacksize) + 5, flags, bytes(bytecode), tuple(consts), tuple(names), tuple(fastnames), filename, name, 1, b"", (), ())
)[-1]

new_globals = lambda glob, name = "__main__": (
    globals := {**predefs, **glob},
    globals.__setitem__("eval", partial(eval_lisp, globals=globals)),
    globals
)[-1]
eval_lisp = lambda code, globals: eval(code, globals)

fold = lambda f, acc, stuff: [(acc:=f(acc, x)) for x in stuff][-1]
predefs = {
    "+": lambda *args: fold(lambda x,y:x+y, args[0], args[1:]),
    "-": lambda *args: fold(lambda x,y:x-y, args[0], args[1:]),
    "*": lambda *args: fold(lambda x,y:x*y, args[0], args[1:]),
    "/": lambda *args: fold(lambda x,y:x//y, args[0], args[1:]),

    "=": lambda *args: all((args[0] == x for x in args[1:])),
    "!=": lambda *args: any((args[0] != x for x in args[1:])),
    ">": lambda x, y: x > y,
    "<": lambda x, y: x < y,
    ">=": lambda x, y: x >= y,
    "<=": lambda x, y: x <= y,
    "not": lambda x: not x, 

    "print": print,
    "input": input,
    "substr": lambda quote, s, e=0: quote[s:e] if e else quote[s:],

    "list": lambda *a: tuple(a),
    "pylist": list,
    "head": lambda l: l[0],
    "tail": lambda l: l[1:],
    "last": lambda l: l[-1],
    "nth": lambda l, i: l[i],
    "varargc": lambda f, a, kw = {}: f(*a, **kw),
    "fold": fold,
    "is-matthilde-cute": lambda: True,  # :pout: # :poutback:
    "cons": dataclass(
        type("cons", (object,), 
        {"__annotations__": {"car": Any, "cdr": Any}})
    ),
    "car": lambda o: o.car,
    "cdr": lambda o: o.cdr,
    "true": True,
    "false": False, # :galaxybrain:
    "nil": None,
    "starts-with?": str.startswith,
    "ends-with?": str.endswith
}   


# TODO: delet this
compile_lisp = lambda code: cumiler(parse_lisp(code))

if __name__ == "__main__":
    import readline
    sys.path.append(".")
    print("the cumiler")
    glob = new_globals({})
    while True:
        s = input("lisp> ")
        while (c:=s.count('(') - s.count(')')) > 0:
            s += "\n" + input("..... " + "  " * c)
        ps = [x for x in parse_lisp(s) if type(x) != str or not x.startswith(';')]
        # To fix:
        #  - Do not eval when there is an empty list :worry:
        debug = False

        if ps != []:
            code = cumiler(ps)
            dis(code) # :worry:
            if debug:
                for attr in dir(code):
                    print(attr, ":", getattr(code, attr))
            try:
                print(repr(eval_lisp(code, glob)))
            except Exception as e:
                print(f"{type(e).__name__}: {str(e)}")