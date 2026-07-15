"""AST-based rewrite of a decorated function's loop.

Parses the decorated function's source once (cached by the caller),
locates its single top-level ``for`` loop, and rewrites the iterated
expression to run through a runtime ``_LoopContext`` -- the loop body
itself is left untouched. The rewritten function is recompiled and handed
back as a factory that also rebinds the original function's closure, so
helper functions/variables from its enclosing scope keep working.
"""

import ast
import inspect
import textwrap
from typing import Any, Callable, List, Tuple

from .exceptions import NotResumableError

_CTX_NAME = "__waypoint_ctx__"
_FACTORY_NAME = "__waypoint_factory__"


def _parse_function_def(func: Callable[..., Any]) -> ast.FunctionDef:
    try:
        source = inspect.getsource(func)
    except OSError as exc:
        raise NotResumableError(
            f"@checkpoint could not read the source of '{func.__qualname__}' "
            "(it has no accessible source, e.g. defined dynamically or in a "
            "REPL). Source access is required to make its loop resumable."
        ) from exc

    module = ast.parse(textwrap.dedent(source))
    func_def = module.body[0]
    if not isinstance(func_def, ast.FunctionDef):
        raise NotResumableError(
            f"@checkpoint expects to decorate a regular function; got "
            f"{type(func_def).__name__} for '{func.__qualname__}'."
        )
    func_def.decorator_list = []
    return func_def


def _is_enumerate_call(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "enumerate"
        and len(node.args) == 1
        and not node.keywords
    )


def _resolve_track_call(stmt: ast.For, func_name: str) -> Tuple[str, ast.expr]:
    """Return the (``_LoopContext`` method name, tracked expression) for
    this loop's target/iterable shape, or raise if the shape isn't
    supported (v1: a bare name, or an ``enumerate(...)`` pair)."""
    if isinstance(stmt.target, ast.Name):
        return "track", stmt.iter

    if (
        isinstance(stmt.target, ast.Tuple)
        and len(stmt.target.elts) == 2
        and all(isinstance(elt, ast.Name) for elt in stmt.target.elts)
        and _is_enumerate_call(stmt.iter)
    ):
        enumerate_call = stmt.iter
        assert isinstance(enumerate_call, ast.Call)
        return "track_enumerate", enumerate_call.args[0]

    raise NotResumableError(
        f"@checkpoint on '{func_name}' found a for-loop with an "
        "unpacking target (e.g. 'for i, item in ...'); v1 only "
        "supports a single loop variable ('for item in <sequence>:') "
        "or 'for i, item in enumerate(<sequence>):'."
    )


def _rewrite_loop_in_place(func_def: ast.FunctionDef) -> None:
    for stmt in func_def.body:
        if not isinstance(stmt, ast.For):
            continue

        loop_source = ast.unparse(stmt).splitlines()[0]
        method_name, tracked_expr = _resolve_track_call(stmt, func_def.name)
        stmt.iter = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=_CTX_NAME, ctx=ast.Load()),
                attr=method_name,
                ctx=ast.Load(),
            ),
            args=[tracked_expr, ast.Constant(value=loop_source)],
            keywords=[],
        )
        stmt.body.append(
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id=_CTX_NAME, ctx=ast.Load()),
                        attr="advance",
                        ctx=ast.Load(),
                    ),
                    args=[],
                    keywords=[],
                )
            )
        )
        return

    raise NotResumableError(
        f"@checkpoint could not find a top-level 'for item in <sequence>:' "
        f"loop in '{func_def.name}'. The loop must be a direct statement in "
        "the function body (not nested inside if/try/with)."
    )


def build_factory(func: Callable[..., Any]) -> Callable[[Any], Callable[..., Any]]:
    """Return ``make(ctx) -> transformed_func`` for the decorated ``func``.

    ``transformed_func`` behaves like ``func`` except its (single,
    top-level) loop runs through ``ctx``. Free variables ``func`` closes
    over are re-bound on every call from the original closure so mutable
    outer state (an API client, a shared counter) keeps working.
    """
    func_def = _parse_function_def(func)
    _rewrite_loop_in_place(func_def)

    freevars: List[str] = list(func.__code__.co_freevars)
    factory_args = ast.arguments(
        posonlyargs=[],
        args=[ast.arg(arg=_CTX_NAME)] + [ast.arg(arg=name) for name in freevars],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[],
    )
    factory_def = ast.FunctionDef(  # type: ignore[call-overload]
        name=_FACTORY_NAME,
        args=factory_args,
        body=[func_def, ast.Return(value=ast.Name(id=func_def.name, ctx=ast.Load()))],
        decorator_list=[],
        returns=None,
    )
    wrapper_module = ast.Module(body=[factory_def], type_ignores=[])
    ast.fix_missing_locations(wrapper_module)

    code = compile(wrapper_module, filename=f"<waypoint:{func.__qualname__}>", mode="exec")
    namespace: Any = {}
    exec(code, func.__globals__, namespace)
    factory_fn = namespace[_FACTORY_NAME]

    def make(ctx: Any) -> Callable[..., Any]:
        closure_values = [cell.cell_contents for cell in (func.__closure__ or ())]
        result: Callable[..., Any] = factory_fn(ctx, *closure_values)
        return result

    return make
