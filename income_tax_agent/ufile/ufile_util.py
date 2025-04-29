from income_tax_agent import playwright_helper


async def add_serial(slip_type: str) -> str:
    """
    Add a serial number to the current member's tax bill of the specified type (e.g. T3)

    Args:
        name: The name of the tax bill of the type (e.g., "T3")

    Returns:
        str: Updated Tax List
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    elements = page.locator('div.tocLabel').filter(has_text=f'{slip_type}:')
    all_t3s = await elements.all()
    count = await elements.count()
    print(f"Found {count} {slip_type} slips")
    index = 1

    for t3 in all_t3s:
        await t3.click()
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


if __name__ == "__main__":
    import asyncio

    async def main():
        result = await add_serial("T5")
        print(result)

    asyncio.run(main())
