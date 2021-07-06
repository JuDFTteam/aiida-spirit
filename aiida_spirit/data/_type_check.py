# -*- coding: utf-8 -*-
"""
Type checking of spirit input parameters
"""

# import formatting info
import numpy as np
from ._formatting_info import (_single_bools, _array_bools, _single_ints,
                               _array_ints, _single_floats, _array_floats,
                               _single_strings)


def validate_range(key, val, minval=None, maxval=None):
    """Check if value is within range given by minval and maxval"""
    if minval is not None:
        if val < minval:
            raise ValueError(
                f'Value of {key} is smaller than allowed range ({val} < {minval}).'
            )
    if maxval is not None:
        if val > maxval:
            raise ValueError(
                f'Value of {key} is bigger than allowed range ({val} > {maxval}).'
            )


def validate_int(key, val, minval=None, maxval=None):
    """validate integer"""
    # check type
    if not isinstance(val, int):
        raise TypeError(
            f'Type of {key} is not a single integer ({val}, {type(val)}).')
    # check range
    validate_range(key, val, minval, maxval)


def validate_float(key, val, minval=None, maxval=None, allow_int=True):
    """validate float"""
    # check type
    isfloat = isinstance(val, float)
    isint = isinstance(val, int)
    if not (isfloat or (allow_int and isint)):
        raise TypeError(
            f'Type of {key} is not a single float ({val}, {type(val)}).')
    # check range
    validate_range(key, val, minval, maxval)


def validate_bool(key, val):
    """validate boolean"""
    if not isinstance(val, bool):
        raise TypeError(
            f'Type of {key} is not a boolean ({val}, {type(val)}).')


def validate_array(key, val, len_check=None, minval=None, maxval=None):
    """Validate array input"""
    # check if type is ok
    try:
        # this raises a TypeError if input is, for example, integer
        _ = len(val)
        # convert to numpy array
        val = np.array(val)
    except TypeError:
        raise TypeError(
            f'Array input {key} is not an array-like object ({val}).')

    # check shape of the array
    if len(val) < 1:
        raise ValueError(f'Array input {key} has length 0 ({val}).')
    if len_check is not None:
        if len(val) != len_check:
            raise ValueError(
                f'Array input {key} has wrong length. Expected {len_check} but got {len(val)}.'
            )

    for vv in val.reshape(-1):
        # check type?
        # check value range
        validate_range(key, vv, minval=minval, maxval=maxval)


def convert_bool(val):
    """convert boolean to 1/0 integer for writing"""
    if val:
        return 1
    return 0


def validate_string(key, val, allowed_strings=None):
    """Validate string input"""
    if not isinstance(val, str):
        raise TypeError(f'Type of {key} is not a string')
    if allowed_strings is not None:
        if val not in allowed_strings:
            raise ValueError(
                f'String input {key} is not in the allowed list of strings ({val} not in {allowed_strings}).'
            )


def verify_input_para(key, val):
    """check input parameter for consistency and convert to string. Return the string version"""

    val_string = ''

    if key in _single_bools:
        validate_bool(key, val)
        val_string = f'{convert_bool(val)}'

    elif key in _array_bools:
        validate_array(key, val, len_check=_array_bools[key])
        for vv in val:
            validate_bool(key, vv)
            val_string += f' {convert_bool(vv)}'

    elif key in _single_ints:
        validate_int(key, val, _single_ints[key][0], _single_ints[key][1])
        val_string += f' {val}'

    elif key in _array_ints:
        validate_array(key, val, _array_ints[key][0])
        for vv in val:
            validate_int(key, vv, _array_ints[key][1], _array_ints[key][2])
            val_string += f' {vv}'

    elif key in _single_floats:
        validate_float(key, val, _single_floats[key][0],
                       _single_floats[key][1])
        val_string += f' {val}'

    elif key in _array_floats:
        validate_array(key, val, len_check=_array_floats[key][0])
        for vv in val:
            validate_float(key, vv, _array_floats[key][1],
                           _array_floats[key][2])
            val_string += f' {vv}'

    elif key in _single_strings:
        validate_string(key, val, allowed_strings=_single_strings[key])
        val_string = val

    else:

        raise ValueError(
            f'Unkown key {key} with value {val}. Check your input parameters.')

    return val_string


def validate_input_dict(params_dict):
    """Go through the complete parameters dict and validate the inputs"""
    for key, val in params_dict.items():
        _ = verify_input_para(key, val)
