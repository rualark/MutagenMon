import datetime


def format_current_datetime():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def format_datetime_from_timestamp(i):
    return datetime.datetime.fromtimestamp(i).strftime("%Y-%m-%d %H:%M:%S")


def format_dict(d):
    st = ""
    for key, val in d.items():
        if st:
            st += ", "
        st += "%s: '%s'" % (key, val)
    return st


def format_status(d):
    st = ""
    for key, val in d.items():
        if st:
            st += ". "
        st += key + ": "
        first = 1
        for key2, val2 in val.items():
            if not first:
                st += ', '
            else:
                first = 0
            st += key2 + "=" + str(val2)
    return st


def get_matching_open_parenth(st, i):
    stack = []
    for x in reversed(range(i)):
        if st[x] == '(':
            if not stack:
                return x
            else:
                stack.pop()
        if st[x] == ')':
            stack.append(1)


def test_matching_open_parenth():
    st = "asdf ( df) (d(e)erf) ( adf)"
    print(st, get_matching_open_parenth(st, len(st) - 1))
    st = "asdf ( df) (d(e)erf) ( adf (qwer ))"
    print(st, get_matching_open_parenth(st, len(st) - 1))
    st = "asdf ( df) (d(e)erf) ( adf (qwer )asd)"
    print(st, get_matching_open_parenth(st, len(st) - 1))

