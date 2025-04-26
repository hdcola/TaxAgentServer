from income_tax_agent import playwright_helper


async def get_all_t3() -> list | str:
    """
    Get all T3 slips from the current member.

    Returns:
        list: A list containing only the T3 slip information
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Use a more specific selector that targets only the div elements containing "T3:" text
    # This targets the exact elements containing T3 labels
    t3_elements = page.locator('div.tocLabel').filter(has_text='T3:')
    all_t3s = await t3_elements.all()

    t3_values = []
    for t3 in all_t3s:
        t3_values.append(await t3.inner_text())

    return t3_values

async def get_t3_info(name: str) -> str | list[dict]:
    """
    Select a specific T3 slip by its name and extract all input fields information.

    This function navigates to the specified T3 slip and extracts information from all
    input fields found on the page, including their titles, box numbers, and values.

    Args:
        name: The name of the T3 slip to select (e.g., "T3: BBC")

    Returns:
        str | list[dict]: Either an error message as a string if the operation fails,
                          or a list of dictionaries with each containing:
                          - 'title': The label of the input field
                          - 'box': The box number (if available)
                          - 'value': The current value in the input field (if any)
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Use a more specific selector that targets only the div elements containing "T3:" text
    # This targets the exact elements containing T3 labels
    t3_elements = page.locator('div.tocLabel').filter(has_text='T3:')
    all_t3s = await t3_elements.all()

    t3_found = False
    for t3 in all_t3s:
        if name in await t3.inner_text():
            await t3.click()
            t3_found = True
            break

    if not t3_found:
        return f"T3 slip '{name}' not found."
    
    await page.wait_for_timeout(1000)  # Wait for the page to load

    fieldsets = page.locator('fieldset')
    count = await fieldsets.count()

    formatted_fields = []

    for i in range(count):
        fieldset = fieldsets.nth(i)
        item = {}

         # Try to find the title/label
        title_element = fieldset.locator('.int-label').first
        title = await title_element.inner_text() if await title_element.count() > 0 else ""

        # Try to find the box number
        box_element = fieldset.locator('.boxNumberContent').first
        box = await box_element.inner_text() if await box_element.count() > 0 else ""

        # Try to find the input value
        input_element = fieldset.locator('input[type="text"]').first
        value = await input_element.input_value() if await input_element.count() > 0 else ""

        # Only add the field if we found a title
        if title:
            item['title'] = title.strip()
            item['box'] = box.strip() if box else None
            item['value'] = value.strip() if value else None

            formatted_fields.append(item)

    return formatted_fields


if __name__ == "__main__":
    import asyncio

    async def main():
        t3_slips = await get_all_t3()
        print(t3_slips)
        result = await get_t3_info("T3: stanly")
        print(result)

    asyncio.run(main())