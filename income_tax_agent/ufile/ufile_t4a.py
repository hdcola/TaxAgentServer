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
        input_element = fieldset.locator('input[type="text"][aria-hidden="false"]').first
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

async def smart_select_option(select_element, target_text: str):
    options = select_element.locator('option')
    option_count = await options.count()

    exact_match = None
    partial_match = None
    all_options_data = []

    for i in range(option_count):
        option = options.nth(i)
        option_text = (await option.inner_text()).strip()
        option_value = await option.get_attribute('value')

        if not option_value:
            continue

        all_options_data.append({'text': option_text, 'value': option_value})
        
        if option_text.lower() == target_text.lower():
            exact_match = option_value
            break

        if partial_match is None and target_text.lower() in option_text.lower():
            partial_match = option_value

    if exact_match:
        await select_element.select_option(value=exact_match)
        print(f"Selected by exact match: '{target_text}'")
        return None

    if partial_match:
        await select_element.select_option(value=partial_match)
        print(f"Selected by partial match: '{target_text}'")
        return None

    else:
        return all_options_data


async def update_t4a_info(name: str, title: str, option:str, box: str, value:str) -> str:
    """
    Select a specific T4A slip and update its fields based on the given data.

    Args:
        name: The name of the T4A slip to select (e.g., "T4A: Company A")
        title: The label of the input field to match
        option: The option to match (if available)
        box: The box number (if available)If the box number has fewer than 3 digits, pad with leading zeros to make it 3 digits. For example:'5' -> '005'
        value: The value to set in the input field. If the field is a date, it should be in the format "MM-DD-YYYY".

    Returns:
        str: Result message indicating success or failure
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Find and click the T4A slip tab
    t4a_elements = page.locator('div.tocLabel').filter(has_text='T4A:')
    all_t4as = await t4a_elements.all()

    for t4a in all_t4as:
        if name in await t4a.inner_text():
            await t4a.click()
            break
    else:
        return f"T4A slip with name '{name}' not found."

    await page.wait_for_timeout(1000)

    # Get all fieldsets
    fieldsets = page.locator('fieldset')
    count = await fieldsets.count()

    matched_fieldset = None
    matched_reason = ""
    titles = []
    options = []

    for i in range(count):
        fieldset = fieldsets.nth(i)

        # Get box number
        box_element = fieldset.locator('.boxNumberContent').first
        current_box = await box_element.inner_text() if await box_element.count() > 0 else ""
        current_box = current_box.strip()

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
        return {"error": f"No matching option or title found. Check found options", "options": options, "titles": titles}

    # Update value
    input_element = matched_fieldset.locator('input[type="text"][aria-hidden="false"]').first
    select_element = matched_fieldset.locator("select").first
    date_element = matched_fieldset.locator('input[mask="00-00-0000"]').first

    if await input_element.count() > 0:
        await input_element.fill(value.strip())
    elif await select_element.count() > 0:
        select_result = await smart_select_option(select_element, value)
        if select_result is not None:
            return {"error": f"No matching option found for '{value}'", "options": select_result}
        
    elif await date_element.count() > 0:
        await date_element.evaluate('(el, val) => el.value = val', value.strip())
    else:
        return f"Field matched by {matched_reason}, but no editable input/select/date element found."

    return f"T4A field updated successfully by {matched_reason}."

if __name__ == "__main__":
    import asyncio

    from playwright.async_api import async_playwright

    async def main():

            members = await get_all_t4a()
            print(members)
            # result = await get_t4a_info(members[0])
            # print(result)
            # for item in members:
            #     result = await get_t4a_info(item)
            #     print(result)
            result = await update_t4a_info(members[0], "", "","111", "new content only")
            # result = await update_t4a_info(members[0], "", "","C-10", "10-10-2024")
            # result = await update_t4a_info(members[0], "", "Registered pension plan","016", "777")
            # result = await update_t4a_info(members[0], "", "Note - Special tax withheld (RL-2)","", "999")
            # result = await update_t4a_info(members[0], "", "Note - Special tax withheld","", "999")
            print(result)

    asyncio.run(main())