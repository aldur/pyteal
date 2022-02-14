from sys import implementation
from typing import Callable, List, Optional, Union, TYPE_CHECKING
from inspect import Parameter, isclass, signature

from ..types import TealType
from ..ir import TealOp, Op, TealBlock
from ..errors import TealInputError, TealInternalError, verifyTealVersion
from .expr import Expr
from .seq import Seq
from .scratchvar import ScratchVar

if TYPE_CHECKING:
    from ..compiler import CompileOptions


class SubroutineDefinition:
    PARAM_TYPES = (Expr, ScratchVar)

    @classmethod
    def param_type_names(cls) -> List[str]:
        return list(map(lambda t: t.__name__, cls.PARAM_TYPES))

    nextSubroutineId = 0

    def __init__(
        self,
        implementation: Callable[..., Expr],
        returnType: TealType,
        nameStr: str = None,
    ) -> None:
        super().__init__()
        self.id = SubroutineDefinition.nextSubroutineId
        SubroutineDefinition.nextSubroutineId += 1

        if not callable(implementation):
            raise TealInputError("Input to SubroutineDefinition is not callable")

        sig = signature(implementation)

        for name, param in sig.parameters.items():
            if param.kind not in (
                Parameter.POSITIONAL_ONLY,
                Parameter.POSITIONAL_OR_KEYWORD,
            ):
                raise TealInputError(
                    "Function has a parameter type that is not allowed in a subroutine: parameter {} with type {}".format(
                        name, param.kind
                    )
                )

            if param.default != Parameter.empty:
                raise TealInputError(
                    "Function has a parameter with a default value, which is not allowed in a subroutine: {}".format(
                        name
                    )
                )

        for var, var_type in implementation.__annotations__.items():
            if var == "return" and not (
                isclass(var_type) and issubclass(var_type, Expr)
            ):
                raise TealInputError(
                    "Function has return of disallowed type {}. Only subtype of Expr is allowed".format(
                        var_type
                    )
                )

            if var != "return" and var_type not in self.PARAM_TYPES:
                raise TealInputError(
                    "Function has parameter {} of disallowed type {}. Only the types {} are allowed".format(
                        var, var_type, self.param_type_names()
                    )
                )

        self.implementation = implementation
        self.implementationParams = sig.parameters
        self.returnType = returnType

        self.declaration: Optional["SubroutineDeclaration"] = None
        self.__name = self.implementation.__name__ if nameStr is None else nameStr

    def isRefArg(self, arg: str) -> bool:
        anns = self.implementation.__annotations__
        return arg in anns and anns[arg] is ScratchVar

    def getDeclaration(
        self,
    ) -> "SubroutineDeclaration":
        if self.declaration is None:
            # lazy evaluate subroutine
            self.declaration = evaluateSubroutine(self)
        return self.declaration

    def name(self) -> str:
        return self.__name

    def argumentCount(self) -> int:
        return len(self.implementationParams)

    def invoke(self, args: List[Union[Expr, ScratchVar]]) -> "SubroutineCall":
        if len(args) != self.argumentCount():
            raise TealInputError(
                "Incorrect number of arguments for subroutine call. Expected {} arguments, got {}".format(
                    self.argumentCount(), len(args)
                )
            )

        for i, arg in enumerate(args):
            if not isinstance(arg, SubroutineDefinition.PARAM_TYPES):
                raise TealInputError(
                    "Argument {} at index {} of subroutine call has incorrect type {}".format(
                        i, arg, type(arg)
                    )
                )

        return SubroutineCall(self, args)

    # def scratchVars(self, callback: "SubroutineCall" = None) -> List[ScratchVar]:
    # def scratchVars(self) -> List[ScratchVar]:
    #     # arg_vars = []
    #     # for i, arg in enumerate(self.implementationParams.keys()):
    #     #     if self.isRefArg(arg):
    #     #         # assert (
    #     #         #     callback
    #     #         # ), "internal error: provided no SubroutineCall but have pass-by-ref arg [{}]".format(
    #     #         #     arg
    #     #         # )

    #     #         sv = callback.args[i]
    #     #         # assert isinstance(
    #     #         #     sv, ScratchVar
    #     #         # ), "internal error: arg [{}] should be a ScratchVar but instead is a {}".format(
    #     #         #     arg, type(sv)
    #     #         # )
    #     #         sv._by_ref = True
    #     #     else:
    #     #         sv = ScratchVar()
    #     #         sv._by_ref = False

    #     #     arg_vars.append(sv)
    #     # return arg_vars
    #     def make_scratch_var(arg):
    #         sv = ScratchVar()
    #         sv._by_ref = self.isRefArg(arg)
    #         return sv

    #     return list(map(make_scratch_var, self.implementationParams.keys()))

    def __str__(self):
        return "subroutine#{}".format(self.id)

    def __eq__(self, other):
        if isinstance(other, SubroutineDefinition):
            return self.id == other.id and self.implementation == other.implementation
        return False

    def __hash__(self):
        return hash(self.id)


SubroutineDefinition.__module__ = "pyteal"


class SubroutineDeclaration(Expr):
    def __init__(self, subroutine: SubroutineDefinition, body: Expr) -> None:
        super().__init__()
        self.subroutine = subroutine
        self.body = body

    def __teal__(self, options: "CompileOptions"):
        return self.body.__teal__(options)

    def __str__(self):
        return '(SubroutineDeclaration "{}" {})'.format(
            self.subroutine.name(), self.body
        )

    def type_of(self):
        return self.body.type_of()

    def has_return(self):
        return self.body.has_return()


SubroutineDeclaration.__module__ = "pyteal"


class SubroutineCall(Expr):
    def __init__(
        self, subroutine: SubroutineDefinition, args: List[Union[Expr, ScratchVar]]
    ) -> None:
        super().__init__()
        self.subroutine = subroutine
        self.args = args

        for i, arg in enumerate(args):
            if self._arg_type(i) == TealType.none:
                raise TealInputError(
                    "Subroutine argument {} at index {} evaluates to TealType.none".format(
                        arg, i
                    )
                )

    def _arg_type(self, arg_idx: int) -> TealType:
        arg = self.args[arg_idx]
        if isinstance(arg, Expr):
            return arg.type_of()
        if isinstance(arg, ScratchVar):
            return arg.type
        raise TealInputError(
            "Subroutine argument {} at index {} was of unexpected Python type {}".format(
                arg, arg_idx, type(arg)
            )
        )

    def _subroutine_args(self):
        ca = []
        for i, arg in enumerate(self.args):
            if isinstance(arg, Expr):
                ca.append(arg)
            elif isinstance(arg, ScratchVar):
                # TODO: Zeph - this is ONE BIG REASON WHY IT'S ALL BROKEN
                # get the index for the implemented pass-by-ref ScratchVar:
                ca.append(arg.index())
            else:
                raise TealInternalError(
                    "cannot interpert arg {} at index {} as call argument because of unexpected Python type {}".format(
                        arg, i, type(arg)
                    )
                )
        return ca

    def __teal__(self, options: "CompileOptions"):
        verifyTealVersion(
            Op.callsub.min_version,
            options.version,
            "TEAL version too low to use SubroutineCall expression",
        )

        op = TealOp(self, Op.callsub, self.subroutine)
        return TealBlock.FromOp(options, op, *self._subroutine_args())

    def __str__(self):
        ret_str = '(SubroutineCall "' + self.subroutine.name() + '" ('
        for a in self.args:
            ret_str += " " + a.__str__()
        ret_str += "))"
        return ret_str

    def type_of(self):
        return self.subroutine.returnType

    def has_return(self):
        return False


SubroutineCall.__module__ = "pyteal"


class SubroutineFnWrapper:
    def __init__(
        self,
        fnImplementation: Callable[..., Expr],
        returnType: TealType,
        name: str = None,
    ) -> None:
        self.subroutine = SubroutineDefinition(
            fnImplementation, returnType=returnType, nameStr=name
        )

    def __call__(self, *args: Union[Expr, ScratchVar], **kwargs) -> Expr:
        if len(kwargs) != 0:
            raise TealInputError(
                "Subroutine cannot be called with keyword arguments. Received keyword arguments: {}".format(
                    ",".join(kwargs.keys())
                )
            )
        return self.subroutine.invoke(list(args))

    def name(self) -> str:
        return self.subroutine.name()

    def type_of(self):
        return self.subroutine.getDeclaration().type_of()

    def has_return(self):
        return self.subroutine.getDeclaration().has_return()


SubroutineFnWrapper.__module__ = "pyteal"


class Subroutine:
    """Used to create a PyTeal subroutine from a Python function.

    This class is meant to be used as a function decorator. For example:

        .. code-block:: python

            @Subroutine(TealType.uint64)
            def mySubroutine(a: Expr, b: Expr) -> Expr:
                return a + b

            program = Seq([
                App.globalPut(Bytes("key"), mySubroutine(Int(1), Int(2))),
                Approve(),
            ])
    """

    def __init__(self, returnType: TealType, name: str = None) -> None:
        """Define a new subroutine with the given return type.

        Args:
            returnType: The type that the return value of this subroutine must conform to.
                TealType.none indicates that this subroutine does not return any value.
        """
        self.returnType = returnType
        self.name = name

    def __call__(self, fnImplementation: Callable[..., Expr]) -> SubroutineFnWrapper:
        return SubroutineFnWrapper(
            fnImplementation=fnImplementation,
            returnType=self.returnType,
            name=self.name,
        )


Subroutine.__module__ = "pyteal"


def evaluateSubroutine(subroutine: SubroutineDefinition) -> SubroutineDeclaration:
    arg_count = subroutine.argumentCount()
    param_keys = subroutine.implementationParams.keys()

    if len(param_keys) != arg_count:
        raise TealInternalError(
            "subroutine {} had {} implementation params but an argument count of {}".format(
                subroutine, param_keys, arg_count
            )
        )

    argumentVars = [ScratchVar() for _ in range(arg_count)]
    loadedArgs = []
    for i, arg in enumerate(param_keys):
        # TODO: with the variable name "arg" in-hand, we could add labels to ScratchVars
        new_sv = argumentVars[i]
        if not subroutine.isRefArg(arg):
            loadedArgs.append(new_sv.load())
        else:
            body_sv = ScratchVar(TealType.uint64)
            body_sv.store(new_sv.index())

            argumentVars[i] = body_sv
            loadedArgs.append(body_sv.newByRef(TealType.anytype))

    subroutineBody = subroutine.implementation(*loadedArgs)

    if not isinstance(subroutineBody, Expr):
        raise TealInternalError(
            "Subroutine function does not return a PyTeal expression. Got type {}".format(
                type(subroutineBody)
            )
        )

    # need to reverse order of argumentVars because the last argument will be on top of the stack
    bodyOps = [var.slot.store() for var in argumentVars[::-1]]
    bodyOps.append(subroutineBody)

    return SubroutineDeclaration(subroutine, Seq(bodyOps))
