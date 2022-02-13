from ast import Sub
from pathlib import Path

from pyteal import *
from pyteal.types import require_type

RETURN_PREFIX = Bytes("base16", "151f7c75")

identity_selector = MethodSignature("identity(uint64)uint64")
itchy_selector = MethodSignature("itchy(uint64,uint64)uint64")
increment_selector = MethodSignature("increment(uint64)void")
fib1_selector = MethodSignature("fib1(uint64)uint64")
fib2_selector = MethodSignature("fib2(uint64)uint64")
linearTransformation_selector = MethodSignature(
    "linearTransformation(uint64,uint64,uint64,uint64,uint64,uint64)void"
)


@Subroutine(TealType.uint64)
def tradfac(n):
    return If(n <= Int(1)).Then(Int(1)).Else(n * tradfac(n - Int(1)))


def approval_tfac():
    return tradfac(Int(17))


@Subroutine(TealType.none)
def fac(n, y: ScratchVar):
    return (
        If(n <= Int(1))
        .Then(y.store(Int(1)))
        .Else(
            Seq(
                fac(n - Int(1), y),
                y.store(n * y.load()),
            )
        )
    )


def approval_z1():
    n = ScratchVar()
    y = ScratchVar()
    return Seq(
        [
            n.store(Int(10)),
            y.store(Int(0)),
            fac(n, y),
            Approve(),
        ]
    )


def approval_z2():
    n = ScratchVar(slotId=17)
    y = ScratchVar(slotId=42)
    return Seq(
        [
            n.store(Int(10)),
            y.store(Int(0)),
            fac(n, y),
            Approve(),
        ]
    )


@Subroutine(TealType.uint64)
def xyzD(x: ScratchVar, y: ScratchVar, z):
    return Seq(
        x.store(x.load() + Int(1)),
        y.store(y.load() + Int(2)),
        x.load() + y.load() + z,
    )


def approval_xyzD():
    x = ScratchVar(TealType.uint64)
    y = ScratchVar(TealType.uint64)
    a = ScratchVar(TealType.uint64, 142)
    b = ScratchVar(TealType.uint64, 143)
    return Seq(
        [
            a.store(Int(100)),
            b.store(Int(200)),
            x.store(Int(1)),
            y.store(Int(2)),
            Pop(xyz(x, y, Int(3))),
            Pop(xyz(x, y, x.load() + y.load())),
            Pop(xyz(x, y, x.load() + y.load())),
            Pop(xyz(a, b, Int(177))),
            Pop(a.load() + b.load()),
            Approve(),
        ]
    )


@Subroutine(TealType.uint64)
def xyz(x: ScratchVar, y: ScratchVar, z):
    return Seq(
        x.store(x.load() + Int(1)),
        y.store(y.load() + Int(2)),
        x.load() + y.load() + z,
    )


def approval_xyz():
    x = ScratchVar(TealType.uint64, 45)
    y = ScratchVar(TealType.uint64, 46)
    a = ScratchVar(TealType.uint64, 142)
    b = ScratchVar(TealType.uint64, 143)
    return Seq(
        [
            a.store(Int(100)),
            b.store(Int(200)),
            x.store(Int(1)),
            y.store(Int(2)),
            Pop(xyz(x, y, Int(3))),
            Pop(xyz(x, y, x.load() + y.load())),
            Pop(xyz(x, y, x.load() + y.load())),
            Pop(xyz(a, b, Int(177))),
            Pop(a.load() + b.load()),
            Approve(),
        ]
    )


@Subroutine(TealType.none)
def identity(x: ScratchVar):
    return x.store(x.load())


def approval_identity():
    x = ScratchVar(TealType.uint64, 42)
    y = ScratchVar(TealType.uint64, 43)
    return Seq(
        [
            x.store(Int(11)),
            identity(x),
            y.store(Int(17)),
            identity(y),
            x.store(Int(99)),
            identity(x),
            y.store(Int(101)),
            identity(y),
            Approve(),
        ]
    )


# I no longer believe this should be supported

# @Subroutine(TealType.uint64)
# def itchy(dynamic_scratcher: ScratchVar, regular_scratcher: ScratchVar) -> Expr:
#     dyn_idx = dynamic_scratcher.index()
#     reg_idx = regular_scratcher.index()
#     stop_val = regular_scratcher.load()
#     return_val = stop_val + dynamic_scratcher.load()
#     dynamic_scratcher = ScratchVar(TealType.uint64, dyn_idx + Int(5))
#     dynamic_scratcher.store(return_val)
#     return Seq(
#         If(stop_val > Int(0))
#         .Then(
#             Seq(
#                 regular_scratcher.store(stop_val - Int(1)),
#                 dynamic_scratcher.store(
#                     return_val + itchy(dynamic_scratcher, regular_scratcher)
#                 ),
#             )
#         )
#         .Else(
#             Log(
#                 Concat(
#                     Bytes("dyn_idx:"),
#                     Itob(dyn_idx),
#                     Bytes("dyn_val:"),
#                     Itob(dynamic_scratcher.load()),
#                     Bytes("reg_idx:"),
#                     Itob(reg_idx),
#                     Bytes("reg_val:"),
#                     Itob(regular_scratcher.load()),
#                 )
#             )
#         ),
#         return_val,
#     )


# def approval_itchy():
#     regular_scratcher = ScratchVar(TealType.uint64)
#     dynamic_scratcher = ScratchVar(TealType.uint64, regular_scratcher.index() + Int(5))

#     return Cond(
#         [
#             Txn.application_args[0] == itchy_selector,
#             Return(
#                 Seq(
#                     regular_scratcher.store(Int(1)),
#                     dynamic_scratcher.store(Int(1)),
#                     itchy(dynamic_scratcher, regular_scratcher),
#                 )
#             ),
#         ],
#     )


@Subroutine(TealType.none)
def increment(x: ScratchVar):
    return Seq(x.store(x.load() + Int(1)))


def approval_increment():
    x = ScratchVar(TealType.uint64, 128)

    return Cond(
        [
            Txn.application_args[0] == increment_selector,
            Return(
                Seq(
                    x.store(Int(41)),
                    increment(x),
                    x.load() == Int(42),
                )
            ),
        ],
    )


@Subroutine(TealType.none)
def linearTransformation(a, b, c, d, x: ScratchVar, y: ScratchVar):
    newX = a * x.load() + b * y.load()
    newY = c * x.load() + d * y.load()
    return Seq(
        x.store(newX),
        y.store(newY),
    )


def approval_trans():
    x = ScratchVar(TealType.uint64, 127)
    y = ScratchVar(TealType.uint64, 128)

    # positive affine transformation
    a = Int(1)
    b = Int(3)
    c = Int(1)
    d = Int(5)
    return Cond(
        [
            Txn.application_args[0] == linearTransformation_selector,
            Return(
                Seq(
                    x.store(Int(17)),
                    y.store(Int(42)),
                    linearTransformation(a, b, c, d, x, y),
                    Assert(x.load() == Int(143)),
                    Assert(y.load() == Int(227)),
                    linearTransformation(a, b, c, d, x, y),
                    Assert(x.load() == Int(824)),
                    y.load() == Int(1278),
                )
            ),
        ],
    )


@Subroutine(TealType.none)
def addAndPlaceSumInFirstArg(a: ScratchVar, b: Expr):
    return a.store(a.load() + b)


def approval_add100():
    value = ScratchVar(TealType.uint64)
    return Seq(
        value.store(Int(1)),
        addAndPlaceSumInFirstArg(value, Int(100)),
        Log(Itob(value.load())),  # value should now be 101
        Approve(),
    )


@Subroutine(TealType.none)
def fib_swap_step(a: ScratchVar, b: ScratchVar):
    return Seq(
        b.store(b.load() + a.load()),
        a.store(b.load() - a.load()),
    )


@Subroutine(TealType.uint64)
def fib1(n):
    i = ScratchVar(TealType.uint64)
    a = ScratchVar(TealType.uint64)
    b = ScratchVar(TealType.uint64)
    init = Seq(
        i.store(Int(0)),
        a.store(Int(0)),
        b.store(Int(1)),
    )
    cond = i.load() < n - Int(1)
    iter = i.store(i.load() + Int(1))

    return Seq(
        If(n < Int(2))
        .Then(
            Seq(
                uint64_log4return(n),
                Return(n),
            )
        )
        .Else(
            Seq(
                For(init, cond, iter).Do(Seq(fib_swap_step(a, b))),
                uint64_log4return(b.load()),
                Return(b.load()),
            )
        ),
    )


@Subroutine(TealType.uint64)
def fib2(n):
    i = ScratchVar(TealType.uint64)
    a = ScratchVar(TealType.uint64)
    b = ScratchVar(TealType.uint64)

    init = Seq(
        i.store(Int(0)),
        a.store(Int(0)),
        b.store(Int(1)),
    )
    cond = i.load() < n - Int(1)
    iter = i.store(i.load() + Int(1))
    return Seq(
        If(n < Int(2))
        .Then(
            Seq(
                uint64_log4return(n),
                Return(n),
            )
        )
        .Else(
            Seq(
                For(init, cond, iter).Do(
                    Seq(
                        b.store(b.load() + a.load()),
                        a.store(b.load() - a.load()),
                    )
                ),
                uint64_log4return(b.load()),
                Return(b.load()),
            )
        ),
    )


@Subroutine(TealType.none)
def uint64_log4return(value):
    require_type(value, TealType.uint64)
    return Log(Concat(RETURN_PREFIX, Itob(value)))


def approval_fib2():
    x = ScratchVar(TealType.uint64, 128)

    return Cond(
        [Txn.application_id() == Int(0), Approve()],
        [
            Txn.on_completion() == OnComplete.DeleteApplication,
            Return(Txn.sender() == Global.creator_address()),
        ],
        [
            Txn.on_completion() == OnComplete.UpdateApplication,
            Return(Txn.sender() == Global.creator_address()),
        ],
        [Txn.on_completion() == OnComplete.CloseOut, Approve()],
        [Txn.on_completion() == OnComplete.OptIn, Approve()],
        [
            Txn.application_args[0] == fib1_selector,
            Return(Seq(Pop(fib1(Txn.application_args[1])), Int(1))),
        ],
        [
            Txn.application_args[0] == fib2_selector,
            Return(Seq(Pop(fib2(Txn.application_args[1])), Int(1))),
        ],
    )


def pyfib1(n: int = 0) -> int:
    if n < 2:
        return n

    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b

    return b


def pyfib2(n: int = 0) -> int:
    if n < 2:
        return n

    a, b = 0, 1
    for _ in range(n - 1):
        b = a + b
        a = b - a

    return b


def clear():
    return Return(Int(1))


def compile_and_save(approval, name):
    teal = Path.cwd() / "examples" / "application" / "teal"
    compiled = compileTeal(approval, mode=Mode.Application, version=6)
    with open(teal / (name + ".teal"), "w") as f:
        f.write(compiled)


if __name__ == "__main__":
    for n in range(43):
        assert pyfib1(n) == pyfib2(n), f"oops {n}: {pyfib1(n)} != {pyfib2(n)}"
    #     print(f"pyfib({n}) = {pyfib1(n):,}")

    # compile_and_save(clear(), "clear")
    # compile_and_save(approval_increment(), "increment")
    # compile_and_save(approval_trans(), "matrix")
    # compile_and_save(approval_add100(), "add100")
    # compile_and_save(approval_fib2(), "fib2")
    # compile_and_save(approval_identity(), "repetition")
    # compile_and_save(approval_xyz(), "xyz")
    # compile_and_save(approval_xyzD(), "xyzD")
    # compile_and_save(approval_z1(), "z1")
    compile_and_save(tradfac(), "tradfac")
    compile_and_save(approval_z2(), "z2")

    # Gone for good?
    # with open(teal / "itch_scratcher.teal", "w") as f:
    #     f.write(compileTeal(approval_itchy(), mode=Mode.Application, version=6))
