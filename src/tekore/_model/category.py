from dataclasses import dataclass
from typing import List

from .base import Identifiable
from .member import Image
from .paging import OffsetPaging
from .serialise import ModelList


@dataclass(repr=False)
class Category(Identifiable):
    """Spotify tag category."""

    href: str
    icons: List[Image]
    name: str

    def __post_init__(self):
        self.icons = ModelList(Image.from_kwargs(i) for i in self.icons)


@dataclass(repr=False)
class CategoryPaging(OffsetPaging):
    """Paging of categories."""

    items: List[Category]

    def __post_init__(self):
        self.items = ModelList(Category.from_kwargs(c) for c in self.items)
