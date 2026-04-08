from abc import ABC


class Base(ABC):
    def __init__(self, inline: bool = True):
        self.inline = inline