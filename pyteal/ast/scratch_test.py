import pytest

from .. import *

# this is not necessary but mypy complains if it's not included
from .. import CompileOptions

options = CompileOptions()


def test_scratch_init():
    assert ScratchSlot.nextSlotId == NUM_SLOTS
    slot = ScratchSlot()
    assert slot.byRef is False
    assert slot.isReservedSlot is False
    assert slot.idFromStack is False
    assert slot.id == NUM_SLOTS
    assert slot.nextSlotId == NUM_SLOTS + 1

    slot = ScratchSlot(42)
    assert slot.byRef is False
    assert slot.isReservedSlot is True
    assert slot.idFromStack is False
    assert slot.id == 42
    assert slot.nextSlotId == NUM_SLOTS + 1

    slot = ScratchSlot(idFromStack=True)
    assert slot.byRef is False
    assert slot.isReservedSlot is False
    assert slot.idFromStack is True
    assert slot.id == NUM_SLOTS + 1
    assert slot.nextSlotId == NUM_SLOTS + 2

    slot = ScratchSlot(43, idFromStack=True)
    assert slot.byRef is False
    assert slot.isReservedSlot is True
    assert slot.idFromStack is True
    assert slot.id == 43
    assert slot.nextSlotId == NUM_SLOTS + 2

    slot = ScratchSlot(44, idFromStack=False)
    assert slot.byRef is False
    assert slot.isReservedSlot is True
    assert slot.idFromStack is False
    assert slot.id == 44
    assert slot.nextSlotId == NUM_SLOTS + 2

    slot = ScratchSlot("ignored garbage", "also ignored", byRef=True)
    assert slot.byRef is True
    assert slot.isReservedSlot is True
    assert slot.idFromStack == "also ignored"
    assert slot.id == "ignored garbage"
    assert slot.nextSlotId == NUM_SLOTS + 2

    with pytest.raises(TealInputError) as e:
        ScratchSlot(-1)

    assert "must be in the range" in str(e)

    with pytest.raises(TealInputError) as e:
        ScratchSlot(NUM_SLOTS)

    assert "must be in the range" in str(e)

    with pytest.raises(TealInputError) as e:
        ScratchSlot(Int(42))

    assert "must be an int" in str(e)


def test_scratch_slot():
    slot = ScratchSlot()
    assert slot == slot
    assert slot.__hash__() == slot.__hash__()
    assert slot != ScratchSlot()

    with TealComponent.Context.ignoreExprEquality():
        assert (
            slot.store().__teal__(options)[0]
            == ScratchStackStore(slot).__teal__(options)[0]
        )
        assert (
            slot.store(Int(1)).__teal__(options)[0]
            == ScratchStore(slot, Int(1)).__teal__(options)[0]
        )

        assert slot.load().type_of() == TealType.anytype
        assert slot.load(TealType.uint64).type_of() == TealType.uint64
        assert (
            slot.load().__teal__(options)[0] == ScratchLoad(slot).__teal__(options)[0]
        )


def test_scratch_load_default():
    slot = ScratchSlot()
    expr = ScratchLoad(slot)
    assert expr.type_of() == TealType.anytype

    expected = TealSimpleBlock([TealOp(expr, Op.load, slot)])

    actual, _ = expr.__teal__(options)

    assert actual == expected


def test_scratch_load_type():
    for type in (TealType.uint64, TealType.bytes, TealType.anytype):
        slot = ScratchSlot()
        expr = ScratchLoad(slot, type)
        assert expr.type_of() == type

        expected = TealSimpleBlock([TealOp(expr, Op.load, slot)])

        actual, _ = expr.__teal__(options)

        assert actual == expected


def test_scratch_store():
    for value in (
        Int(1),
        Bytes("test"),
        App.globalGet(Bytes("key")),
        If(Int(1), Int(2), Int(3)),
    ):
        slot = ScratchSlot()
        expr = ScratchStore(slot, value)
        assert expr.type_of() == TealType.none

        expected, valueEnd = value.__teal__(options)
        storeBlock = TealSimpleBlock([TealOp(expr, Op.store, slot)])
        valueEnd.setNextBlock(storeBlock)

        actual, _ = expr.__teal__(options)

        assert actual == expected


def test_scratch_stack_store():
    slot = ScratchSlot()
    expr = ScratchStackStore(slot)
    assert expr.type_of() == TealType.none

    expected = TealSimpleBlock([TealOp(expr, Op.store, slot)])

    actual, _ = expr.__teal__(options)

    assert actual == expected


def test_scratch_assign_id():
    slot = ScratchSlot(255)
    expr = ScratchStackStore(slot)
    assert expr.type_of() == TealType.none

    expected = TealSimpleBlock([TealOp(expr, Op.store, slot)])

    actual, _ = expr.__teal__(options)

    assert actual == expected


def test_scratch_assign_id_invalid():
    with pytest.raises(TealInputError):
        slot = ScratchSlot(-1)

    with pytest.raises(TealInputError):
        slot = ScratchSlot(NUM_SLOTS)
