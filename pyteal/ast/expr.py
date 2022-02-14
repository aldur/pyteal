from abc import ABC, abstractmethod
from typing import Callable, Tuple, List, Union, TYPE_CHECKING

from attr import has

from ..ir import TealBlock, TealSimpleBlock, Op, tealop, LabelReference
from ..types import TealType


if TYPE_CHECKING:
    from ..compiler import CompileOptions


class Expr(ABC):
    """Abstract base class for PyTeal expressions."""

    ANONYMOUS_EXPR_CLASS_COUNT = 0

    def __init__(self):
        import traceback

        self.trace = traceback.format_stack()[0:-1]

    def getDefinitionTrace(self) -> List[str]:
        return self.trace

    def chainOp(
        self,
        # options: "CompileOptions",
        op: Op,
        op_args: List[tealop.IMMEDIATE_ARG_TYPE],
        block_args: List[Union["Expr", Callable[[], "Expr"]]],
        type_prefix: str = "AnonymousExpr",
        ttype: TealType = None,
        has_return: bool = None,
    ) -> "Expr":
        """Helper method for creating anonymous expressions. For Example:
        >>> parent_expr = some Expr object (e.g. Self if you're in a Expr subtype)
        >>> pop3 = parent_expr.chainOp(
                Op.pop, [], []
            ).chainOp(
                Op.pop, [], []
            ).chainOp(
                Op.pop, [], []
            )
        """
        return self.fromOp(
            self,
            # options,
            op,
            op_args,
            block_args,
            type_prefix=type_prefix,
            ttype=ttype,
            has_return=has_return,
        )

    @classmethod
    def fromOp(
        cls,
        parent: Union["Expr", None],
        # options: "CompileOptions",
        op: Op,
        op_args: List[tealop.IMMEDIATE_ARG_TYPE],
        block_args: List[Union["Expr", Callable[[], "Expr"]]],
        type_prefix: str = "AnonymousExpr",
        ttype: TealType = None,
        has_return: bool = None,
    ) -> "Expr":
        from . import ScratchSlot, SubroutineDefinition

        type_name = "{}_{}".format(type_prefix, cls.ANONYMOUS_EXPR_CLASS_COUNT + 1)

        def lazy_op_arg(
            op_arg: Union[
                tealop.IMMEDIATE_ARG_TYPE, Callable[[], tealop.IMMEDIATE_ARG_TYPE]
            ]
        ) -> tealop.IMMEDIATE_ARG_TYPE:
            if isinstance(
                op_arg, (int, str, LabelReference, ScratchSlot, SubroutineDefinition)
            ):
                return op_arg
            return op_arg()

        def lazy_op_args():
            return [lazy_op_arg(oa) for oa in op_args]

        def lazy_block_args():
            return [lazy_block_arg(ba) for ba in block_args]

        def lazy_block_arg(block_arg: Union["Expr", Callable[[], "Expr"]]) -> "Expr":
            if isinstance(block_arg, Expr):
                return block_arg
            return block_arg()

        def lazy_block_args():
            return [lazy_block_arg(ba) for ba in block_args]

        def __str__(_):
            return "{}(op={}, op_args={}, block_args={})".format(
                type_name, op, op_args, block_args
            )

        def __init__(self):
            super().__init__()
            self.parent = parent
            self.op = op
            self.type = TealType.anytype if ttype is None else ttype
            self.has_return = has_return

        def type_of(self):
            return self.type

        def _has_return(self):
            return self.has_return

        def __teal__(self, options):
            op = tealop.TealOp(self.parent, self.op, *lazy_op_args())
            return TealBlock.FromOp(options, op, *lazy_block_args())

        expr_type = type(
            type_name,
            (cls,),
            {
                "__init__": __init__,
                "type_of": type_of,
                "has_return": _has_return,
                "__str__": __str__,
                "__teal__": __teal__,
            },
        )

        expr = expr_type()
        cls.ANONYMOUS_EXPR_CLASS_COUNT += 1

        return expr

    @abstractmethod
    def type_of(self) -> TealType:
        """Get the return type of this expression."""
        pass

    @abstractmethod
    def has_return(self) -> bool:
        """Check if this expression always returns from the current subroutine or program."""
        pass

    @abstractmethod
    def __str__(self) -> str:
        """Get a string representation of this experssion."""
        pass

    @abstractmethod
    def __teal__(self, options: "CompileOptions") -> Tuple[TealBlock, TealSimpleBlock]:
        """Assemble TEAL IR for this component and its arguments."""
        pass

    def __lt__(self, other):
        from .binaryexpr import Lt

        return Lt(self, other)

    def __gt__(self, other):
        from .binaryexpr import Gt

        return Gt(self, other)

    def __le__(self, other):
        from .binaryexpr import Le

        return Le(self, other)

    def __ge__(self, other):
        from .binaryexpr import Ge

        return Ge(self, other)

    def __eq__(self, other):
        from .binaryexpr import Eq

        return Eq(self, other)

    def __ne__(self, other):
        from .binaryexpr import Neq

        return Neq(self, other)

    def __add__(self, other):
        from .binaryexpr import Add

        return Add(self, other)

    def __sub__(self, other):
        from .binaryexpr import Minus

        return Minus(self, other)

    def __mul__(self, other):
        from .binaryexpr import Mul

        return Mul(self, other)

    def __truediv__(self, other):
        from .binaryexpr import Div

        return Div(self, other)

    def __mod__(self, other):
        from .binaryexpr import Mod

        return Mod(self, other)

    def __pow__(self, other):
        from .binaryexpr import Exp

        return Exp(self, other)

    def __invert__(self):
        from .unaryexpr import BitwiseNot

        return BitwiseNot(self)

    def __and__(self, other):
        from .binaryexpr import BitwiseAnd

        return BitwiseAnd(self, other)

    def __or__(self, other):
        from .binaryexpr import BitwiseOr

        return BitwiseOr(self, other)

    def __xor__(self, other):
        from .binaryexpr import BitwiseXor

        return BitwiseXor(self, other)

    def __lshift__(self, other):
        from .binaryexpr import ShiftLeft

        return ShiftLeft(self, other)

    def __rshift__(self, other):
        from .binaryexpr import ShiftRight

        return ShiftRight(self, other)

    def And(self, other: "Expr") -> "Expr":
        """Take the logical And of this expression and another one.

        This expression must evaluate to uint64.

        This is the same as using :func:`And()` with two arguments.
        """
        from .naryexpr import And

        return And(self, other)

    def Or(self, other: "Expr") -> "Expr":
        """Take the logical Or of this expression and another one.

        This expression must evaluate to uint64.

        This is the same as using :func:`Or()` with two arguments.
        """
        from .naryexpr import Or

        return Or(self, other)


Expr.__module__ = "pyteal"
