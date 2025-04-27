from income_tax_agent import playwright_helper


async def update_t3(
    name: str = "",
    box: str = "0",
    title: str = "",
    value: str = "",
) -> str | list[dict]:
    """
    Update or extract information from a T3 slip based on provided fill_data.

    Args:
        name (str, optional): The name of the T3 slip (e.g., "stanly"). Defaults to an empty string.
        box (str, optional): The box number to match. Defaults to 0.
        title (str, optional): The title to match. Defaults to an empty string.
        value (str, optional): The value to fill in the matched input field. Defaults to an empty string.

    Returns:
        A message indicating whether the operation was successful or not.
        If there are mutiple titles under one box number, returns
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    t3_elements = page.locator('div.tocLabel').filter(has_text='T3:')
    counts = await t3_elements.count()

    if counts == 0:
        return "No T3 slips found."

    await t3_elements.filter(has_text=name).first.click()

    fieldsets = page.locator('fieldset')
    fieldset_count = await fieldsets.count()

    if fieldset_count == 0:
        return "No fieldsets found in the T3 slip."

    #  打印调试信息
    # for i in range(fieldset_count):
    #     fieldset = fieldsets.nth(i)
    #     text = await fieldset.inner_text()
    #     print(f"Fieldset {i+1} content:\n{text}\n")

    for i in range(fieldset_count):
        fieldset = fieldsets.nth(i)

        box_element = fieldset.locator('.boxNumberContent').first
        if await box_element.count() == 0:
            continue  # 这个fieldset没有box number，跳过

        box_text = (await box_element.inner_text()).strip()

        if box_text == box:  # box 是你传入的参数
            # 找到了对应的fieldset！
            print(f"Found fieldset for box {box}: Fieldset {i+1}")
            input_element = fieldset.locator('input[type="text"]').first
            original_value = await input_element.input_value()
            if original_value == value:
                return f"Box {box} already has the value {value}. No need to update or fill, replace it with a different value."
            elif original_value == "" or original_value == "0":
                await input_element.click()
                await input_element.fill(value)
                await input_element.evaluate("element => element.blur()")
                return f"Filled box {box} with value {value} successfully."
            elif original_value != value:
                await input_element.click()
                await input_element.fill(value)
                await input_element.evaluate("element => element.blur()")
                return f"Updated box {box} from {original_value} to {value} successfully."

    # for i in range (fieldset_count):
    #     fieldset = fieldsets.nth(i)

    #     print(f"Processing fieldset {i + 1} of {fieldset_count}...", fieldset)
    #     box_elements = fieldset.locator('.boxNumberContent').first
    #     box_text = await box_elements.inner_text()

    #     if box_text.stirp() == str(box):
    #         input_locator = fieldset.locator('input[type="text"][aria-hidden="false"]').first
    #         await input_locator.fill(value)
    #         return f"Filled box {box} with value {value} successfully."

    return 'T3 slip clicked successfully.'

if __name__ == "__main__":
    import asyncio

    async def main():
        # results = await update_t3(name="T3: Morgan", box=49, title="Actual amount of eligible dividends", value="666")
        # print(results)
        results = await update_t3(name="T3: BOC", box=30, value="166")
        print(results)

    asyncio.run(main())
