async def make_string_good_for_markdown(text, es_list=None):
    escapt_list = ['_', '*', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    if es_list is not None:
        escapt_list = es_list

    for el in escapt_list:
        text = text.replace(el, f'\\{el}')
    return text


async def pop_from_dict(dictionary: dict, keys: [str]) -> dict:
    for key in keys:
        dictionary.pop(key, None)
    return dictionary
