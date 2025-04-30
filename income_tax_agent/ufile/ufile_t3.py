from income_tax_agent import playwright_helper
from income_tax_agent.ufile.ufile_info import get_slip_info, format_to_string


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
                        - 'box': A list of box numbers (if available)
                        - 'value': The current value in the input field (if any)
    """
    formatted_fields = await get_slip_info(name, include_null_values=False, include_title=True)
    slip_type = name.split(":")[0].strip()

    return await format_to_string(slip_type, formatted_fields)


async def add_t3(name: str) -> str:
    """
    Create a new T3 slip with the specified name.

    Args:
        name: The name of the new T3 slip to create

    Returns:
        str: A message indicating the result of the operation
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    await page.get_by_role("button", name="Interest, investment income").first.click()
    await page.wait_for_timeout(1000)
    await page.get_by_role("button", name="Add Item. T3 - Trust income").click()
    await page.wait_for_timeout(1000)
    await page.get_by_role("textbox", name="Enter Text. This T3 slip was issued by. ").fill(name)
    await page.get_by_role("textbox", name="Enter Text. This T3 slip was issued by. ").press("Tab")

    return f"New T3 slip '{name}' created successfully."


async def remove_t3(name: str) -> str:
    """
    Remove a specific T3 slip by its name.

    This function navigates to the specified T3 slip and removes it from the current member.

    Args:
        name: The name of the T3 slip to remove (e.g., "T3: BBC")

    Returns:
        str: A message indicating whether the operation was successful or not 
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Find the T3 element with the given name
    t3_elements = page.locator('div.tocLabel').filter(has_text=name)
    count = await t3_elements.count()

    if count == 0:
        return f"T3 slip with name '{name}' not found."

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
        return f"Successfully removed T3 slip: {name}"
    except Exception as e:
        return f"Error updating T3 slip: {str(e)}"

if __name__ == "__main__":
    import asyncio

    async def main():
        # t3_slips = await get_all_t3()
        # print(t3_slips)
        result = await get_t3_info("T3: FIDELITY INVESTMENTS CANADA#24")
        print(result)
        # newT3 = await add_t3("BOC")
        # print(newT3)

    asyncio.run(main())
