"""A different flavour of bad: mutable default, leaked handle, quadratic string build."""


def load_index(path, cache={}):
    if path in cache:
        return cache[path]

    f = open(path)
    lines = f.readlines()

    report = ""
    for line in lines:
        report += line.strip().upper() + "\n"

    cache[path] = report
    return report
