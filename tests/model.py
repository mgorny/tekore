import json
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

from tekore._model.serialise import (
    JSONEncoder,
    Model,
    ModelList,
    StrEnum,
    Timestamp,
    UnknownModelAttributeWarning,
)


class E(StrEnum):
    a = "a"
    b = "b"
    c = "c"


class ECaps(StrEnum):
    a = "A"
    b = "B"
    c = "C"


class TestEnumCaseInsensitive:
    def test_all_caps(self):
        assert E["A"] == E.a
        assert E["B"] == E.b
        assert E["C"] == E.c

    def test_all_lowercase(self):
        assert E["a"] is E.a
        assert E["b"] is E.b
        assert E["c"] is E.c

    def test_in_caps(self):
        assert ECaps.a in ECaps
        assert ECaps.b in ECaps
        assert ECaps.c in ECaps

    def test_all_caps_caps_keys(self):
        assert ECaps["A"] == ECaps.a
        assert ECaps["B"] == ECaps.b
        assert ECaps["C"] == ECaps.c

    def test_all_lowercase_caps_keys(self):
        assert ECaps["a"] is ECaps.a
        assert ECaps["b"] is ECaps.b
        assert ECaps["c"] is ECaps.c

    def test_non_destructive_iter(self):
        # Should not change caps when iterating or accessing values in other means
        for e in ECaps:
            assert e.upper() == e


class TestSerialisableEnum:
    def test_enum_repr_shows_enum(self):
        assert "E.a" in repr(E.a)

    def test_enum_str_is_name(self):
        e = StrEnum("e", "a b c")
        assert str(e.a) == "a"

    def test_enum_is_sortable(self):
        enums = list(E)[::-1]
        assert sorted(enums) == enums[::-1]


class TestJSONEncoder:
    def test_enum_encoded_is_quoted_str(self):
        enum = Enum("enum", "a b c")
        encoded = JSONEncoder().encode(enum.a)
        assert encoded == '"' + str(enum.a) + '"'

    def test_default_types_preserved(self):
        d = {"items": "in", "this": 1}
        encoded = JSONEncoder().encode(d)
        default = json.dumps(d)
        assert encoded == default

    def test_timestamp_encoded_is_quoted_str(self):
        t = Timestamp.from_string("2019-01-01T12:00:00Z")
        encoded = JSONEncoder().encode(t)

        assert encoded == '"' + str(t) + '"'

    def test_non_serialisable_item_raises(self):
        class C:
            pass

        c = C()
        with pytest.raises(TypeError):
            JSONEncoder().encode(c)


class TestTimestamp:
    def test_timestamp_initialisable_from_string(self):
        Timestamp.from_string("2019-01-01T12:00:00Z")

    def test_incorrect_format_raises(self):
        with pytest.raises(ValueError):
            Timestamp.from_string("2019-01-01")

    def test_timestamp_formatted_back_to_string(self):
        time_str = "2019-01-01T12:00:00Z"
        t = Timestamp.from_string(time_str)
        assert str(t) == time_str

    def test_initialisable_with_microsecond_precision(self):
        Timestamp.from_string("2019-01-01T12:00:00.000000Z")

    def test_initialisable_with_millisecond_precision(self):
        Timestamp.from_string("2019-01-01T12:00:00.00Z")


@dataclass(repr=False)
class Data(Model):
    i: int


module = "tekore._model.serialise"


class TestSerialisableDataclass:
    def test_json_dataclass_serialised(self):
        dict_in = {"i": 1}
        data = Data(**dict_in)
        dict_out = json.loads(data.json())
        assert dict_in == dict_out

    def test_repr(self):
        data = Data(i=1)
        assert "Data" in repr(data)

    def test_long_repr(self):
        @dataclass(repr=False)
        class LongContainer(Model):
            attribute_1: int = 1
            attribute_2: int = 2
            attribute_3: int = 3
            attribute_4: int = 4
            attribute_5: int = 5

        @dataclass(repr=False)
        class LongData(Model):
            data: LongContainer
            optional_list: Optional[List[LongContainer]]
            data_list: List[LongContainer]
            builtin_list: List[int]
            raw_dict: dict
            string: str
            boolean: bool

        data = LongData(
            LongContainer(),
            [LongContainer() for _ in range(20)],
            [LongContainer() for _ in range(20)],
            list(range(10)),
            {str(k): k for k in range(20)},
            "really long string which will most probably be cut off" * 2,
            True,
        )
        repr(data)

    def test_asbuiltin_members_recursed_into(self):
        @dataclass(repr=False)
        class Container(Model):
            d: List[Data]

            def __post_init__(self):
                self.d = [Data(**i) for i in self.d]

        dict_in = {"d": [{"i": 1}, {"i": 2}]}
        data = Container(**dict_in)
        dict_out = data.asbuiltin()
        assert dict_in == dict_out

    def test_asbuiltin_returns_dict_representation(self):
        data = Data(i=1)
        d = data.asbuiltin()
        assert d == {"i": 1}

    def test_pprint_called_with_dict(self):
        pprint = MagicMock()
        data = Data(i=1)

        with patch(module + ".pprint", pprint):
            data.pprint()
            pprint.assert_called_with({"i": 1}, depth=None, compact=True)

    def test_keyword_arguments_passed_to_pprint(self):
        pprint = MagicMock()
        data = Data(i=1)
        kwargs = {"compact": False, "depth": None, "kw": "argument"}

        with patch(module + ".pprint", pprint):
            data.pprint(**kwargs)
            pprint.assert_called_with({"i": 1}, **kwargs)

    def test_enum_in_dataclass(self):
        @dataclass(repr=False)
        class C(Model):
            v: E

        c = C(E.a)
        assert isinstance(c.asbuiltin()["v"], str)
        assert c.json() == '{"v": "a"}'

    def test_timestamp_in_dataclass(self):
        @dataclass(repr=False)
        class C(Model):
            v: Timestamp

        c = C(Timestamp.from_string("2019-01-01T12:00:00Z"))
        assert isinstance(c.asbuiltin()["v"], str)
        assert c.json() == '{"v": "2019-01-01T12:00:00Z"}'


class TestModel:
    def test_unknown_attribute_passed(self):
        with pytest.warns(UnknownModelAttributeWarning):
            data = Data.from_kwargs({"i": 1, "u": 2})

        assert data.u == 2
        assert "u" not in data.json()


class TestModelList:
    def test_list_of_dataclasses_serialised(self):
        list_in = [{"i": 1}, {"i": 2}]
        data = ModelList(Data(**i) for i in list_in)
        list_out = json.loads(data.json())
        assert list_in == list_out

    def test_repr(self):
        list_in = [{"i": 1}, {"i": 2}]
        data = ModelList(Data(**i) for i in list_in)

        assert "Data" in repr(data)
