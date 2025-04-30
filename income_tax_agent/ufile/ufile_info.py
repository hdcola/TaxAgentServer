from income_tax_agent import playwright_helper


async def get_slip_info(name: str, include_null_values=False, include_title=False) -> list[dict]:
    """
    Select a specific slip by its name and extract all input fields information.

    This function navigates to the specified slip and extracts information from all
    input fields found on the page, including their titles, box numbers, and values.

    Args:
        name: The name of the slip to select (e.g., "T3: BBC")
        include_null_values: If True, include fields with null values in the output.


    Returns:
        list[dict]: A list of dictionaries with each containing:
                     - 'title': The label of the input field
                     - 'box': A list of box numbers (if available)
                     - 'value': The current value in the input field (if any)
    """

    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    slip_elements = page.locator('div.tocLabel').filter(has_text=name)
    count = await slip_elements.count()

    if count == 0:
        return f"Slip with name '{name}' not found."

    # Give the page a moment to load the T5 content
    await page.wait_for_timeout(1000)
    # Find all fieldsets that contain input fields (similar to the test.html structure)
    fieldsets = page.locator('fieldset')
    count = await fieldsets.count()

    # Create a new list to store the formatted field data
    formatted_fields = []

    # Process each fieldset individually
    for i in range(count):
        fieldset = fieldsets.nth(i)
        item = {}

        # Try to find the title/label
        title_element = fieldset.locator('.int-label').first
        title = await title_element.inner_text() if await title_element.count() > 0 else ""

        boxs_element = fieldset.locator('.boxNumberContent')
        boxs = await boxs_element.all()

        box_list = []
        if len(boxs) > 0:
            for box_element in boxs:
                box = await box_element.inner_text() if await box_element.count() > 0 else ""
                if box:
                    box_list.append(box.strip())

        # Try to find the input value
        input_element = fieldset.locator('input[type="text"]').first
        value = await input_element.input_value() if await input_element.count() > 0 else ""

        # Only add the field if we found a title
        if title:
            if include_title:
                # If include_title is True, add the title to the item
                item['title'] = title.strip()
            item['box'] = box_list
            item['value'] = value.strip() if value else None

            # Add the item to the formatted_fields list based on include_null_values parameter
            if include_null_values or item['value'] is not None:
                # Only add items if include_null_values is True or the value is not None
                formatted_fields.append(item)

    return formatted_fields


if __name__ == "__main__":
    import asyncio

    async def main():
        # Example usage
        name = "T3: CIBC MONEY MARKET FUND#01"
        slip_info = await get_slip_info(name)
        print(slip_info)

    asyncio.run(main())
