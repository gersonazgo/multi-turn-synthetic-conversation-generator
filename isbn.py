"""ISBN exercise"""
def is_valid(isbn):
    """ISBN function"""
    if not all(digit.isdecimal() or digit == "X" for digit in isbn):
        return False
    isbn = [number for number in isbn if number.isdecimal() or number == "X"]
    valid_x_digits = 10
    valid_x_position = 9
    print("len(isbn) != valid_x_digits")
    if len(isbn) != valid_x_digits:
        return False
    print("if X in isbn:")
    if "X" in isbn:
        x_index = isbn.index("X")
        if x_index != valid_x_position:
            return False
        isbn[valid_x_position] = "10"
    print("multiplier = 10")
    multiplier = 10
    total = 0
    for number in isbn:
        total += int(number) * multiplier
        multiplier -= 1
    print("Total")
    print(total)
    print("Fim")
    return total % 11 == 0
