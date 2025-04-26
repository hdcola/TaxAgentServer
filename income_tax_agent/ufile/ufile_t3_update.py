from income_tax_agent import playwright_helper

async def update_t3(name: str, fill_data: dict | None = None) -> str | list[dict]:
    """
    Update or extract information from a T3 slip based on provided fill_data.

    Args:
        name (str): The name of the T3 slip (e.g., "T3: stanly").
        fill_data (dict | None): Optional dictionary to auto-fill fields. Keys can be titles or box numbers.

    Returns:
        list[dict] | str: List of fields extracted, or an error message.
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"
    
    t3_elements = page.locator('div.tocLabel').filter(has_text='T3:')
    all_t3s = await t3_elements.all()

    t3_found = False
    for t3 in all_t3s:
        if name in await t3.inner_text():
            await t3.click()
            t3_found = True
            break
    
    if not t3_found:
        return f"T3 slip with name '{name}' not found."
    
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
        has_input = await input_element.count() > 0
        value = await input_element.input_value() if has_input else ""

        if title:
            item['title'] = title.strip()
            item['box'] = box.strip() if box else None
            item['value'] = value.strip() if value else None

            
            if fill_data and has_input:
                key_options = [title.strip(), box.strip() if box else None]
                for key in key_options:
                    if key and key in fill_data:
                        new_value = fill_data[key]
                        await input_element.fill(str(new_value))
                        break

            formatted_fields.append(item)

    return formatted_fields

if __name__ == "__main__":
    import asyncio

    async def main():
        # Example fill data
        test_fill_data = {
            "Actual amount of eligible dividends": "666",
            "Actual amount of dividends other than eligible dividends": "111",
            "Capital gains or losses after June 24, 2024": "222",
            "50": "333",
            "51": "444",
            "30": "1247892",
            "32": "5000000",
        }
        results = await update_t3("T3: Morgan", fill_data=test_fill_data)
        print(results)

    asyncio.run(main())