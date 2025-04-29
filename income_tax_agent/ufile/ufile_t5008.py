from income_tax_agent import playwright_helper


async def get_all_t5008() -> str:
    """
    Get all T5008 slips from the current member.

    Returns:
        list: A list containing only the T5008 slip information
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # Use a more specific selector that targets only the div elements containing "T5008:" text
    # This targets the exact elements containing T5008 labels
    t5008_elements = page.locator('div.tocLabel').filter(has_text='T5008: ')
    all_t5008s = await t5008_elements.all()

    t5008_values = []
    for t5008 in all_t5008s:
        t5008_values.append(await t5008.inner_text())

    return str(t5008_values)


async def remove_all_t5008() -> str:
    """
    Remove all T5008 slips from the current member.

    Returns:
        str: A message indicating whether the operation was successful or not
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    # get all button, class=tocIconRemove airia-label have Remove Item. T5008:
    all_remove = await page.locator("button.tocIconRemove[aria-label^='Remove Item. T5008:']").all()
    for remove in all_remove:
        # print aria-label of the button
        aria_label = await remove.get_attribute("aria-label")
        print(f"Removing: {aria_label}")

        await page.evaluate("""
            window.confirm = function(message) {
                console.log('Intercepted confirm: "' + message + '". Returning true.');
                return true; // directly return true to simulate user confirmation
            };
        """)

        # Click on the remove button
        await remove.click()
        # Wait for the UI to update
        await page.wait_for_timeout(1000)

    return "Successfully removed all T5008 slips"

if __name__ == "__main__":
    import asyncio

    async def main():
        # t5008_slips = await get_all_t5008()
        # print(t5008_slips)
        result = await remove_all_t5008()
        print(result)

    asyncio.run(main())
