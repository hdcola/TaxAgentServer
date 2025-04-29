from typing import Any
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


async def get_slip_info(page: Any) -> list:
    fieldsets = await page.locator('fieldset').all()
    formatted_fields = []

    for fieldset in fieldsets:
        # Try to find the title/label
        title_element = fieldset.locator('.int-label').first
        title = await title_element.inner_text() if await title_element.count() > 0 else ""

        # Try to find the box number
        box_element = fieldset.locator('.boxNumberContent').first
        box = await box_element.inner_text() if await box_element.count() > 0 else ""

        # Try to find the input value
        input_element = fieldset.locator('input[type="text"]').first
        value = await input_element.input_value() if await input_element.count() > 0 else ""

        item = {}

        # Only add the field if we found a title
        if title:
            item['title'] = title.strip()
            item['box'] = box.strip() if box else None
            item['value'] = value.strip() if value else None

            formatted_fields.append(item)
    return formatted_fields


async def get_slip_summary(page: Any) -> list:
    formatted_fields = await get_slip_info(page)
    # filter value is not None in formatted_fields
    filtered_fields = [
        field for field in formatted_fields if field['value'] is not None]
    return filtered_fields


async def list_all_slips_summary(slip_type: str) -> list:
    """
    List all slips summary of the specified type (e.g. T3, T5) from the current member.

    Args:
        slip_type: The type of slip to retrieve (e.g., "T3", "T5")

    Returns:
        str: A list containing dictionaries with slip summary information
    """
    page, all_slips = await get_all_slips_elements(slip_type)

    slip_summaries = []
    for slip in all_slips:
        await slip.click()
        await page.wait_for_timeout(2000)
        slip_summary = await get_slip_summary(page)

        slip_summaries.append(slip_summary)

    return slip_summaries


async def get_slips_summary(slip_type: str) -> str:
    """
    Get all slips summary of the specified type (e.g. T3, T5) from the current member.

    Args:
        slip_type: The type of slip to retrieve (e.g., "T3", "T5")

    Returns:
        str: A list containing dictionaries with slip summary information
    """
    slips_summary = await list_all_slips_summary(slip_type)
    items = ''
    # 遍历每个item,列出issuer和所有的box:value，把一条issue放在一行上
    for i in slips_summary:
        issuer = i[0]['value']
        item = f"Issuer: {issuer}, "
        for j in i:
            if j['box'] is not None:
                item += f"{j['box']}: {j['value']}, "
        item = item[:-2]  # 去掉最后的逗号和空格
        items += item + "\n"
    items = items[:-1]  # 去掉最后的换行符
    return items


if __name__ == "__main__":
    import asyncio

    async def main():
        result = await get_all_slips("T3")
        print(result)
        # result = await list_all_slips_summary("T3")
        # print(result)

    asyncio.run(main())
