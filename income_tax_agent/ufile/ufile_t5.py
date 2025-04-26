from income_tax_agent import playwright_helper


async def get_all_t5() -> list | str:
    """
    Get all T5 slips from the current member.

    Returns:
        list: A list containing only the T5 slip information
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Use a more specific selector that targets only the div elements containing "T5:" text
    # This targets the exact elements containing T5 labels
    t5_elements = page.locator('div.tocLabel').filter(has_text='T5:')
    all_t5s = await t5_elements.all()

    t5_values = []
    for t5 in all_t5s:
        t5_values.append(await t5.inner_text())

    return t5_values


async def add_t5(name: str) -> str:
    """
    Add a new T5 slip to the current member.

    Args:
        name: The name of the T5 slip to add (e.g., "T5: BBC")

    Returns:
        str: A message indicating whether the operation was successful or not
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Click on the "Interest, investment income and carrying charges" div
    await page.get_by_role("button", name="Interest, investment income").first.click()
    await page.wait_for_timeout(1000)  # Wait for the UI to update
    # Click on the "T5 - Investment" add button
    await page.get_by_role("button", name="Add Item. T5 - Investment").click()
    await page.wait_for_timeout(1000)  # Wait for the UI to update
    # Input the name of the T5 slip
    await page.get_by_role(
        "textbox", name="Enter Text. This T5 slip was").fill(name)

    return f"Successfully added T5 slip: {name}"


async def update_t5(name: str, title: str, box: str, value: str) -> str:
    """
    Update a specific T5 slip by its name.

    This function navigates to the specified T5 slip and updates the input field with the provided value.

    Args:
        name: The name of the T5 slip to update (e.g., "T5: BBC")
        title: The title of the input field to update
        box: The box number of the input field to update
        value: The new value to set in the input field

    Returns:
        str: A message indicating whether the operation was successful or not
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Find the T5 element with the given name
    t5_elements = page.locator('div.tocLabel').filter(has_text=name)
    count = await t5_elements.count()

    if count == 0:
        return f"T5 slip with name '{name}' not found."

    # Get the main container element for this T5
    t5_element = t5_elements.first

    try:
        # Click directly on the T5 to make sure it's selected
        await t5_element.click()
        await page.wait_for_timeout(500)  # Give more time for the UI to update

        # Find all fieldsets that contain input fields (similar to the test.html structure)
        fieldsets = page.locator('fieldset')
        count = await fieldsets.count()

        # Process each fieldset individually
        for i in range(count):
            fieldset = fieldsets.nth(i)
            item = {}

            # Try to find the title/label
            title_element = fieldset.locator('.int-label').first
            title_text = await title_element.inner_text() if await title_element.count() > 0 else ""

            # Check if this is the correct fieldset based on title and box number
            if title_text == title and box in title_text:
                # Try to find the input value
                input_element = fieldset.locator('input[type="text"]').first
                if await input_element.count() > 0:
                    await input_element.fill(value)
                    return f"Successfully updated T5 slip: {name} - {title} (Box {box})"
                else:
                    return f"Input element not found for T5 slip: {name} - {title} (Box{box})"
        return f"Fieldset with title '{title}' and box '{box}' not found in T5 slip: {name}."
    except Exception as e:
        return f"Error updating T5 slip: {str(e)}"


async def remove_t5(name: str) -> str:
    """
    Remove a specific T5 slip by its name.

    This function navigates to the specified T5 slip and removes it from the current member.

    Args:
        name: The name of the T5 slip to remove (e.g., "T5: BBC")

    Returns:
        str: A message indicating whether the operation was successful or not
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Find the T5 element with the given name
    t5_elements = page.locator('div.tocLabel').filter(has_text=name)
    count = await t5_elements.count()

    if count == 0:
        return f"T5 slip with name '{name}' not found."

    try:

        remove_button = page.locator(
            f'button.tocIconRemove[aria-hidden="false"][aria-label*="{name}"]').first
        await page.evaluate("""
            window.originalConfirm = window.confirm; // store the original confirm function, optional
            window.confirm = function(message) {
                console.log('Intercepted confirm: "' + message + '". Returning true.');
                return true; // directly return true to simulate user confirmation
            };
        """)

        # Debug: Check if button is found and visible
        # if await remove_button.count() == 0:
        #     remove_button = page.locator(
        #         f'button.tocIconRemove[aria-label*="{name}"]')
        # Click the remove button
        await remove_button.click()
        return f"Successfully removed T5 slip: {name}"
    except Exception as e:
        return f"Error updating T5 slip: {str(e)}"


async def get_t5_info(name: str) -> str | list[dict]:
    """
    Select a specific T5 slip by its name and extract all input fields information.

    This function navigates to the specified T5 slip and extracts information from all
    input fields found on the page, including their titles, box numbers, and values.

    Args:
        name: The name of the T5 slip to select (e.g., "T5: BBC")

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

    # Filter for elements that start with either 'T5: ' or 'T5 '
    t5_elements = page.locator('div.tocLabel').filter(lambda el:
                                                      el.inner_text().startswith('T5: ') or el.inner_text().startswith('T5 '))
    all_t5s = await t5_elements.all()

    t5_found = False
    for t5 in all_t5s:
        if name in await t5.inner_text():
            await t5.click()
            t5_found = True
            break

    if not t5_found:
        return f"T5 slip with name '{name}' not found."

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

    from playwright.async_api import async_playwright

    async def main():
        members = await get_all_t5()
        print(members)
        # result = await get_t5_info("T5: BBC")
        # print(result)
        result = await remove_t5("T5: abcd")
        print(result)
        # result = await add_t5("abcd")
        # print(result)

    asyncio.run(main())
