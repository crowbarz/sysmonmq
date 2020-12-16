"""SysMonMQ utility functions."""

import logging
from copy import copy
import yaml
import slugify as slugify_mod

from .const import APP_NAME
from .debug import is_debug_level

_LOGGER = logging.getLogger(APP_NAME)


## Source: https://stackoverflow.com/a/7205107 (modified so b overwrites a where there is a conflict)
# def merge(a, b, path=None):
def merge(
    a, b, limit=None, merge_none=False, replace_lists=False, replace_type=True, level=1
):
    """Recursively merges dict b into dict a."""
    if is_debug_level(9):
        _LOGGER.debug(
            ">>> merge(limit=%s, merge_none=%s, replace_lists=%s, replace_type=%s, level=%d): a:\n%s--\nb:\n%s",
            limit,
            merge_none,
            replace_lists,
            replace_type,
            level,
            yaml.dump(a),
            yaml.dump(b).rstrip(),
        )
    for key in b:
        if key in a:
            if not replace_type and (
                a[key] is not None and type(a[key]) is not type(b[key])
            ):
                pass  # don't replace a[key] if types differ
            elif isinstance(b[key], dict):
                if limit is None or limit >= 1:  ## merge only up to limit
                    # merge to deep copy dict and to honour limit
                    if a[key] is None or type(a[key]) is not dict:
                        a[key] = {}  # force a[key] to be a dict
                    new_limit = None if limit is None else limit - 1
                    merge(
                        a[key],
                        b[key],
                        limit=new_limit,
                        merge_none=merge_none,
                        replace_lists=replace_lists,
                        replace_type=replace_type,
                        level=level + 1,
                    )
                else:
                    pass  # don't merge to a[key] if beyond limit
            elif isinstance(b[key], list):
                if limit is None or limit >= 1:  ## merge only up to limit
                    if a[key] is None or type(a[key]) is not list:
                        a[key] = []  # force a[key] to be a list
                    if replace_lists:
                        a[key] = b[key][:]  # replace a[key] with shallow copy of b[key]
                    else:
                        a[key].extend(b[key])  # append b[key] to a[key]
                else:
                    pass  # don't replace a[key] if beyond limit
            elif b[key] is None and not merge_none:
                pass  # don't change a[key] if b[key] is None
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                a[key] = b[key]  # b overwrites a
        elif b[key] is None and not merge_none:
            pass  # leave key in a alone
        elif isinstance(b[key], dict):
            if limit is None or limit >= 1:  ## merge only up to limit
                # merge to deep copy dict and to honour limit
                a[key] = {}
                new_limit = None if limit is None else limit - 1
                merge(
                    a[key],
                    b[key],
                    limit=new_limit,
                    merge_none=merge_none,
                    replace_lists=replace_lists,
                    replace_type=replace_type,
                    level=level + 1,
                )
            else:
                pass  # don't copy dict if beyond limit
        elif isinstance(b[key], list):
            if limit is None or limit >= 1:  ## merge only up to limit
                a[key] = b[key][:]  # replace a[key] with shallow copy of b[key]
            else:
                pass  # don't copy list if beyond limit
        else:
            a[key] = b[key]
    if is_debug_level(9):
        _LOGGER.debug(
            ">>> merge(level=%s): result:\n%s%s",
            level,
            yaml.dump(a),
            "==" if level == 1 else "--",
        )
    return a


def deepcopy(d: dict) -> dict:
    nd = dict()
    merge(nd, d, merge_none=True)
    return nd


## Source: https://stackoverflow.com/questions/31433989/return-copy-of-dictionary-excluding-specified-keys
def without_keys(d, keys):
    return d if keys == [] else {k: v for k, v in d.items() if k not in keys}


def with_keys(d, keys):
    return [] if keys == [] else {k: v for k, v in d.items() if k in keys}


def read_file(file):
    """Return the contents of a file."""
    with open(file) as f:
        data = f.read().rstrip()
        return data


def checkOptions(opts, all_opts, req_opts=[], section="top_level"):  # -> err(boolean)
    return not check_opts(opts, all_opts, req_opts, section)


def check_opts(opts, all_opts, req_opts=[], section="top_level"):  # -> status(bool)
    ok = True
    for opt in opts:
        if not opt in all_opts:
            _LOGGER.error('invalid option "%s" in "%s"', opt, section)
            ok = False
    for opt in req_opts:
        if opts.get(opt) is None:
            _LOGGER.error('required option "%s" missing in "%s"', opt, section)
            ok = False
    return ok


def inherit_opts(opts, base_opts):
    """Inherit options with value None."""
    if is_debug_level(9):
        _LOGGER.debug(
            ">>> inherit_options(): opts:\n%s--\nbase_opts:\n%s--",
            yaml.dump(opts),
            yaml.dump(with_keys(base_opts, opts.keys())),
        )
    for k, v in opts.items():
        if k in opts and v is None:
            opts[k] = base_opts.get(k)
    if is_debug_level(9):
        _LOGGER.debug(">>> inherit_options(): result:\n%s==", yaml.dump(opts))


def slugify(text):
    return slugify_mod.slugify(text, separator="_")
