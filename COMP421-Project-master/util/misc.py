

def argmax(sequence):
    max_value = -float("inf")
    argmax_value = -1

    for i, value in enumerate(sequence):
        if value > max_value:
            argmax_value = i
            max_value = value

    return argmax_value
