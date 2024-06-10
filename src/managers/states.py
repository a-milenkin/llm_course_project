from telebot.asyncio_handler_backends import State, StatesGroup


class MyStatesGroup(list, StatesGroup):
    def __init__(self):
        super().__init__()
        for name, value in self.__class__.__dict__.items():
            if isinstance(value, State):
                self.append(value)


class MyState(State):
    def __eq__(self, other):
        return self.name == other

    def __hash__(self):
        return hash(self.name)
