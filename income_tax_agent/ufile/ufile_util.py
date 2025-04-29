from income_tax_agent import playwright_helper


async def get_all_slips_elements(slip_type: str) -> list:
    """
    Get all slips of the specified type (e.g. T3, T5) from the current member.

    Args:
        slip_type: The type of slip to retrieve (e.g., "T3", "T5")

    Returns:
        list: A list containing only the specified slip information
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Use a more specific selector that targets only the div elements containing the specified slip type
    # This targets the exact elements containing the slip labels
    slip_elements = page.locator(
        'div.tocLabel').filter(has_text=f'{slip_type}:')
    all_slips = await slip_elements.all()

    return (page, all_slips)


async def add_serial(slip_type: str) -> str:
    """
    Add a serial number to the current member's tax bill of the specified type (e.g. T3)

    Args:
        name: The name of the tax bill of the type (e.g., "T3")

    Returns:
        str: Updated Tax List
    """
    page, all_elements = await get_all_slips_elements(slip_type)
    index = 1

    for element in all_elements:
        await element.click()
        await page.wait_for_timeout(2000)
        input_element = page.get_by_label(
            f'Enter Text. This {slip_type} slip was issued by. ')
        name = await input_element.input_value()
        print(f"Updating {name}")

        # If there's a # in the string, remove # and everything after it
        if "#" in name:
            name = name.split("#")[0]
        # If the string is longer than 27 characters, truncate to the first 27 characters
        if len(name) > 27:
            name = name[:27]
        # Append an index to the name, pad with zero if the number is less than 10
        if index < 10:
            name = name + "#" + str(index).zfill(2)
        else:
            name = name + "#" + str(index)
        index += 1

        await input_element.fill(name)
        await input_element.press("Tab")


async def get_all_slips(slip_type: str) -> str:
    """
    Get all slips of the specified type (e.g. T3, T5) from the current member.

    Args:
        slip_type: The type of slip to retrieve (e.g., "T3", "T5")

    Returns:
        str: A list containing only the specified slip information
    """
    page, all_slips = await get_all_slips_elements(slip_type)

    slip_values = []
    for slip in all_slips:
        slip_values.append(await slip.inner_text())

    return str(slip_values)


async def list_all_slips_summary(slip_type: str) -> list:
    """
    List all slips summary of the specified type (e.g. T3, T5) from the current member.

    Args:
        slip_type: The type of slip to retrieve (e.g., "T3", "T5")

    Returns:
        list: A list containing dictionaries with slip summary information
    """
    page, all_slips = await get_all_slips_elements(slip_type)

    formatted_fields = []
    for slip in all_slips:
        fieldset = slip.locator('fieldset').first


if __name__ == "__main__":
    import asyncio

    async def main():
        result = await get_all_slips("T3")
        print(result)

    asyncio.run(main())
