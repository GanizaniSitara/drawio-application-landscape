class PageObject:
    def __init__(self, width):
        self.width = width
        self.row_id = None  # Row identifier, None initially

def pack_objects(objects, page_width):
    rows = []
    current_row = []
    current_width = 0
    row_id = 0  # Start row identifiers at 0

    for obj in objects:
        if current_width + obj.width <= page_width:
            current_row.append(obj)
            current_width += obj.width
        else:
            # Assign row ID to objects in the current row
            for item in current_row:
                item.row_id = row_id
            row_id += 1  # Move to the next row ID for the next row
            rows.append(current_row)
            current_row = [obj]
            current_width = obj.width

    # Handle last row
    if current_row:
        for item in current_row:
            item.row_id = row_id
        rows.append(current_row)

    return rows

# Example usage
objects = [PageObject(width) for width in [100, 200, 150, 80, 60, 250]]
page_width = 360
pack_objects(objects, page_width)

# Now each object has a row_id assigned, and you can render them based on that
objects.sort(key=lambda x: (x.row_id, -x.width))  # Sort by row_id, then by width within each row

for obj in objects:
    print(f"Object Width: {obj.width}, Row ID: {obj.row_id}")
