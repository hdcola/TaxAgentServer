from typing import Optional
from income_tax_agent import playwright_helper
from income_tax_agent.ufile.ufile_t3 import get_t3_info


async def update_t3(name: str, value: str, title: Optional[str] = None, box: Optional[str] = None) -> str:
    """
    Update a specific T3 slip by its name or box.

    Args:
        name: The name of the T5 slip to update (e.g., "T5: BBC")
        value: The new value to set in the input field
        title: The title of the input field to update (at least one of title or box is required)
        box: The box number of the input field to update (at least one of title or box is required)

    Returns:
        str: A message indicating whether the operation was successful or not. 
            If no corresponding title and box are found, return all titles and boxes.
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    if not title and not box:
        return "Either title or box must be provided to update the T3 slip."

    t3_elements = page.locator('div.tocLabel').filter(has_text='T3:')
    counts = await t3_elements.count()

    if counts == 0:
        return f"T3 slip with name '{name}' not found."

    await t3_elements.filter(has_text=name).first.click()
    await page.wait_for_timeout(500)  # Give more time for the UI to update

    fieldsets = page.locator('fieldset')
    fieldset_count = await fieldsets.count()

    if fieldset_count == 0:
        return "No fieldsets found in the T3 slip."

    for i in range(fieldset_count):
        fieldset = fieldsets.nth(i)

        # Try to find the title/label
        title_element = fieldset.locator('.int-label').first
        title_text = await title_element.inner_text() if await title_element.count() > 0 else ""

        # Try to find the box number
        box_element = fieldset.locator('.boxNumberContent').first
        box_text = await box_element.inner_text() if await box_element.count() > 0 else ""

        # Try to find the input value
        input_element = fieldset.locator('input[type="text"]').first

        # Check if this is the correct fieldset based on title and box number
        match_title = title is None or title_text == title
        match_box = box is None or box in box_text

        if match_title and match_box:
            if await input_element.count() > 0:
                await input_element.fill(value)
                # type tab to move focus away
                await input_element.press("Tab")
                return f"Successfully updated T3 slip: {name} - {title} (Box {box}): {value}"

    all_info = await get_t3_info(name)
    return f"Fieldset with title '{title}' and box '{box}' not found in T3 slip: {name}. \n All info: {all_info}"

if __name__ == "__main__":
    import asyncio

    async def main():
        # results = await update_t3(name="T3: Morgan", box=49, title="Actual amount of eligible dividends", value="666")
        # print(results)
        results = await update_t3("T3: BOC", "123", box="51")
        print(results)

    asyncio.run(main())
