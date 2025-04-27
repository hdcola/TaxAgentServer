from income_tax_agent import playwright_helper
from income_tax_agent.ufile.ufile_t4a import smart_select_option

async def get_all_t4() -> list | str:
    """
    Get all T4 slips from the current member.

    Returns:
        list: A list containing only the T4 slip information
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Use a more specific selector that targets only the div elements containing "T4:" text
    # This targets the exact elements containing T4 labels
    t4_elements = page.locator('div.tocLabel').filter(has_text='T4/RL-1:')
    all_t4s = await t4_elements.all()

    t4_values = []
    for t4 in all_t4s:
        t4_values.append(await t4.inner_text())

    return t4_values

async def add_t4(name: str) -> str:
    """
    Add a new T4 slip to the current member.

    Args:
        name: The name of the T4 slip to add (e.g., "T4/RL-1: Company A")

    Returns:
        str: A message indicating whether the operation was successful or not
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Click on the "4A, T4FHSA and pension income" div
    await page.get_by_role("button", name="T4 and employment income").first.click()
    await page.wait_for_timeout(1000)  # Wait for the UI to update
    # Click on the "T4 - Pension, retirement, annuity, and other income (COVID-19 benefits)" add button
    await page.get_by_role("button", name="Add Item. T4 and RL-1 (Relevé 1) income earned in Quebec with QPP contributions").click()
    await page.wait_for_timeout(1000)  # Wait for the UI to update
    # Input the name of the T4 slip
    await page.get_by_role(
        "textbox", name="Enter Text. Employer's name.").fill(name)

    return f"Successfully added T4 slip: {name}"

async def remove_t4(name: str) -> str:
    """
    Remove a specific T4 slip by its name.

    This function navigates to the specified T4 slip and removes it from the current member.

    Args:
        name: The name of the T4 slip to remove (e.g., "T4: Company A")

    Returns:
        str: A message indicating whether the operation was successful or not
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Find the T5 element with the given name
    t4_elements = page.locator('div.tocLabel').filter(has_text=name)
    count = await t4_elements.count()

    if count == 0:
        return f"T4 slip with name '{name}' not found."

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

        await remove_button.click()
        return f"Successfully removed T4 slip: {name}"
    except Exception as e:
        return f"Error updating T4 slip: {str(e)}"
    

async def get_t4_info(name: str) -> str | list[dict]:
    """
    Select a specific T4 slip by its name and extract all input fields information.

    This function navigates to the specified T4 slip and extracts information from all
    input fields found on the page, including their titles, box numbers, and values.

    Args:
        name: The name of the T4 slip to select (e.g., "T4/RL-1: Company A")

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

    # Use a more specific selector that targets only the div elements containing "T4:" text
    # This targets the exact elements containing T4 labels
    t4_elements = page.locator('div.tocLabel').filter(has_text='T4/RL-1:')
    all_t4s = await t4_elements.all()

    t4_found = False
    for t4 in all_t4s:
        if name in await t4.inner_text():
            await t4.click()
            t4_found = True
            break

    if not t4_found:
        return f"T4 slip with name '{name}' not found."

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
        if box == "30":
            title = "Housing, board and lodging (RL-1 Box V)"
        if box == "" and title == "":
            title = "OTHER INFORMATION"

        # Try to find the input value
        input_element = fieldset.locator('input[type="text"][aria-hidden="false"]').first
        date_eletment = fieldset.locator('input[mask="00-00-0000"]').first
        if await input_element.count() > 0:
            value = await input_element.input_value()
        elif await date_eletment.count() > 0:
            value = await date_eletment.evaluate("el => el.value")
        elif await select_element.count() > 0:
            value = await select_element.locator(f'option[value="{await select_element.input_value()}"]').inner_text()
            option = None
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

async def update_t4_info(name: str, title: str, value:str, option:str = None, box: str = None) -> str:
    """
    Select a specific T4 slip and update its fields based on the given data.

    Args:
        name: The name of the T4 slip to select (e.g., "T4/RL-1: Company A")
        title: The label of the input field to match
        option: The option to match.(if available)
        box: The box number (if available). 
        value: The value to set in the input field. If the field is a date, it should be in the format "MM-DD-YYYY".

    Returns:
        str: Result message indicating success or failure
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Find and click the T4 slip tab
    t4_elements = page.locator('div.tocLabel').filter(has_text='T4/RL-1:')
    all_t4s = await t4_elements.all()

    for t4 in all_t4s:
        if name in await t4.inner_text():
            await t4.click()
            break
    else:
        return f"T4 slip with name '{name}' not found."

    await page.wait_for_timeout(1000)

    # Get all fieldsets
    fieldsets = page.locator('fieldset')
    count = await fieldsets.count()

    matched_fieldset = None
    matched_reason = ""
    titles = []
    options = []
    boxes = []

    if box == None:
        box = ""

    for i in range(count):
        fieldset = fieldsets.nth(i)

        # Get box number
        box_element = fieldset.locator('.boxNumberContent').first
        current_box = await box_element.inner_text() if await box_element.count() > 0 else ""
        current_box = current_box.strip()
        if current_box and current_box != "":
            boxes.append(current_box)

        # Get title
        title_element = fieldset.locator('.int-label').first
        current_title = await title_element.inner_text() if await title_element.count() > 0 else ""
        current_title = current_title.strip()
        if current_title != "":
            titles.append(current_title)

        # Get option
        select_element = fieldset.locator("select").first
        current_option = await select_element.locator(f'option[value="{await select_element.input_value()}"]').inner_text() \
            if await select_element.count() > 0 else ""
        if current_option != "":
            options.append(current_option)

        # Match by option
        if option and current_option.strip() == option.strip():
            matched_fieldset = fieldset
            matched_reason = "option"
            break

        # Match by box
        if box and current_box == box:
            matched_fieldset = fieldset
            matched_reason = "box number"
            break

        # Match by title only if no box matched
        if title and current_title == title.strip():
            matched_fieldset = fieldset
            matched_reason = "title"
            break

    if not matched_fieldset:
        return {"error": f"No matching option or title found. Check found options", "options": options, "titles": titles, "boxes": boxes}

    # Update value
    input_element = matched_fieldset.locator('input[type="text"][aria-hidden="false"]').first
    date_element = matched_fieldset.locator('input[mask="00-00-0000"]').first

    if await input_element.count() > 0:
        await input_element.fill(value.strip())
    elif await date_element.count() > 0:
        await date_element.evaluate('(el, val) => el.value = val', value.strip())
    elif await select_element.count() > 0:
        select_result = await smart_select_option(select_element, value)
        if select_result is not None:
            return {"error": f"No matching option found for '{value}'", "options": select_result}
    else:
        return f"Field matched by {matched_reason}, but no editable input/select/date element found."

    return f"T4 field updated successfully by {matched_reason}."

if __name__ == "__main__":
    import asyncio

    from playwright.async_api import async_playwright

    async def main():

            members = await get_all_t4()
            print(members)
            # for item in members:
            #     result = await get_t4_info(item)
            #     print(result)
            # result = await update_t4_info(members[0], "This employer received the Form RR-50 Option to Stop or Revoke QPP Contributions (yes/no)", "Yes")
            # result = await create_t4_option(members[0], "[102] lump-sum payments - non-resident services transferred to RRSP","987", "018")
            # result = await create_t4_option(members[0], "Note - Special tax withheld", "454")
            # print(result)
            # await add_t4("Company A")
            # await add_t4("Company B")
            # await remove_t4("Company B")

    asyncio.run(main())
