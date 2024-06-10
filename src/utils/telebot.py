import uuid
import typing


class UnlimitedCallbackData:
    """
    Callback data factory (with no restrictions on length of the data)
    This class will help you to work with CallbackQuery
    """

    def __init__(self, *parts, prefix: str, sep=':'):
        if not isinstance(prefix, str):
            raise TypeError(
                f'Prefix must be instance of str not {type(prefix).__name__}')
        if not prefix:
            raise ValueError("Prefix can't be empty")
        if sep in prefix:
            raise ValueError(f"Separator {sep!r} can't be used in prefix")

        self.prefix = prefix
        self.sep = sep

        self._part_names = parts
        self._cache = {}

    def new(self, *args, **kwargs) -> str:
        """
        Generate callback data

        :param args: positional parameters of CallbackData instance parts
        :param kwargs: named parameters
        :return: str
        """
        id = str(uuid.uuid4())
        self._cache[id] = {}
        args = list(args)

        data = [self.prefix]

        for part in self._part_names:
            value = kwargs.pop(part, None)
            if value is None:
                if args:
                    value = args.pop(0)
                else:
                    raise ValueError(f'Value for {part!r} was not passed!')

            # if value is not None and not isinstance(value, str):
            #     value = str(value)

            # if self.sep in value:
            #     raise ValueError(
            #         f"Symbol {self.sep!r} is defined as the separator and can't be used in parts' values"
            #     )

            # data.append(value)
            self._cache[id] = {**self._cache[id], part: value}

        if args or kwargs:
            raise TypeError('Too many arguments were passed!')

        callback_data = self.sep.join(data)

        if len(callback_data.encode()) > 64:
            raise ValueError('Resulted callback data is too long!')

        return f"{self.prefix}{self.sep}{id}"

    def parse(self, callback_data: str):
        raise Exception("Use parse_and_destroy instead.")

    def parse_and_destroy(self, callback_data: str) -> typing.Dict[str, str]:
        """
        Parse data from the callback data

        :param callback_data: string, use to telebot.types.CallbackQuery to parse it from string to a dict
        :return: dict parsed from callback data
        """

        prefix, id = callback_data.split(self.sep)
        if prefix != self.prefix:
            raise ValueError(
                "Passed callback data can't be parsed with that prefix.")
        # elif len(parts) != len(self._part_names):
        #     raise ValueError('Invalid parts count!')

        result = {'@': prefix, **self._cache[id]}
        del self._cache[id]

        # result.update(zip(self._part_names, parts))
        return result