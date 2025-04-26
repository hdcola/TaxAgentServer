from income_tax_agent import playwright_helper

async def get_all_t4a() -> list | str:
    """
    Get all T4A slips from the current member.

    Returns:
        list: A list containing only the T4A slip information
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Use a more specific selector that targets only the div elements containing "T4A:" text
    # This targets the exact elements containing T4A labels
    t4a_elements = page.locator('div.tocLabel').filter(has_text='T4A:')
    all_t4as = await t4a_elements.all()

    t4a_values = []
    for t4a in all_t4as:
        t4a_values.append(await t4a.inner_text())

    return t4a_values

async def get_t4a_info(name: str) -> str | list[dict]:
    """
    Select a specific T4A slip by its name and extract all input fields information.

    This function navigates to the specified T4A slip and extracts information from all
    input fields found on the page, including their titles, box numbers, and values.

    Args:
        name: The name of the T4A slip to select (e.g., "T4A: Company A")

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

    # Use a more specific selector that targets only the div elements containing "T4A:" text
    # This targets the exact elements containing T4A labels
    t4a_elements = page.locator('div.tocLabel').filter(has_text='T4A:')
    all_t4as = await t4a_elements.all()

    t4a_found = False
    for t4a in all_t4as:
        if name in await t4a.inner_text():
            await t4a.click()
            t4a_found = True
            break

    if not t4a_found:
        return f"T4A slip with name '{name}' not found."

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


        select_element = fieldset.locator("select").first
        option = await select_element.locator(f'option[value="{await select_element.input_value()}"]').inner_text() \
            if await select_element.count() > 0 else ""

        # Try to find the box number
        box_element = fieldset.locator('.boxNumberContent').first
        box = await box_element.inner_text() if await box_element.count() > 0 else ""
        if box == "016":
            title = "Pension or superannuation"
        if box == "018":
            title = "Lump-sum payments"
        if box == "024":
            title = "Annuities"
        if box == "RL1-O" or box == "028+":
            title = "OTHER INFORMATION"
        if box == "" and title == "":
            title = "Footnotes relating to specific T-slip entries and Box 135 (RL-2, Box 235)"

        # Try to find the input value
        input_element = fieldset.locator('input[type="text"]').first
        select_element = fieldset.locator("select").first
        date_eletment = fieldset.locator('input[mask="00-00-0000"]').first
        if await input_element.count() > 0:
            value = await input_element.input_value()  
        elif await select_element.count() > 0:
            value = await select_element.locator(f'option[value="{await select_element.input_value()}"]').inner_text()
        elif await date_eletment.count() > 0:
            value = await date_eletment.evaluate("el => el.value")
        else:
            value = ""

        # Only add the field if we found a title
        if title:
            item['title'] = title.strip()
            item['option'] = option.strip() if option else None
            item['box'] = box.strip() if box else None
            item['value'] = value.strip() if value else None

            formatted_fields.append(item)

    return formatted_fields

if __name__ == "__main__":
    import asyncio

    from playwright.async_api import async_playwright

    async def main():

            members = await get_all_t4a()
            print(members)
            result = await get_t4a_info("T4A: Company C")
            print(result)
            for item in members:
                result = await get_t4a_info(item)
                print(result)

    asyncio.run(main())
