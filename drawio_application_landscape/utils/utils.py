def reduce_font_size(font_size,steps=2):
    standard_sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72, 96]
    if int(font_size) in standard_sizes:
        index = standard_sizes.index(int(font_size))
        if index >= steps:
            return standard_sizes[index - steps]
        else:
            raise ValueError("No smaller standard size available.")
    else:
        raise ValueError(f"Font size is not a standard size. Font size: {font_size}")