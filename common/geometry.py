import numpy as np
def getRescaledDimensions(width, height, max_w, max_h):
    given_ratio = max_w / float(max_h)
    ratio = width / float(height)
    if ratio > given_ratio:
        first = max_w
    else:
        first = int(round(ratio * float(max_h)))
    if ratio <= given_ratio:
        second = max_h
    else:
        second = int(round(ratio * float(max_w)))
    return first, second

def ratio_to_decimal(ratio):
    return ratio.num / float(ratio.den)
