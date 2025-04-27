from income_tax_agent import playwright_helper

async def get_all_person_names():
    """
    Get all family members in current session.

    Returns:
        The title and name of the family head, spouse, and dependents.
    """
    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    family_numbers_list_elements = page.get_by_role("list", name="Family members")
    list_items = family_numbers_list_elements.locator("li")
    count = await list_items.count()

    names = []

    for i in range(count):
        list_item = list_items.nth(i)
        name_span  = list_item.locator("a > span").first
        if await name_span.count() > 0:
            name = (await name_span.inner_text()).strip()
            names.append(name)
    roles = []
    if count < 3:
        roles = names
    else:
        for idx, name in enumerate(names):
            if idx == 0:
                roles.append(f"Family Head: {name}")
            elif idx == 1:
                roles.append(f"Spouse: {name}")
            else:
                roles.append(f"Dependent: {name}")

    if count < 3:
        final_msg = "\n".join(roles)
    else:
        final_msg = f"Your Family Head is {roles[0].split(': ')[1]}, your Spouse is {roles[1].split(': ')[1]}, Your Dependents are listed below:\n" + "\n".join(f"- {n.split(': ')[1]}" for n in roles[2:])
    
    return final_msg

async def remove_person(name: str):
    """
    Remove a family member from the current session.
    
    Args:
        name: The name of the family member to remove.
        
    Returns:
        A message indicating whether the family member was removed successfully or not.
    """

    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"

    family_numbers_list_elements = page.get_by_role("list", name="Family members")
    list_items = family_numbers_list_elements.locator("li")
    count = await list_items.count()
    if count == 0:
        return "No family members found."
    
    for i in range(count):
        list_item = list_items.nth(i)
        name_span = list_item.locator('a > span').first
        if await name_span.count() == 0:
            continue
        name_text = (await name_span.inner_text()).strip()

        
        if name_text == name:

            member_btn = list_item.get_by_role("button")
            await member_btn.click()
            await page.wait_for_timeout(1500) # 切换成员网页加载速度特别慢，多给一点时间
            remove_button = page.locator('#displayRemoveAppItem')
            await page.evaluate("""
            window.originalConfirm = window.confirm; // store the original confirm function, optional
            window.confirm = function(message) {
                console.log('Intercepted confirm: "' + message + '". Returning true.');
                return true; // directly return true to simulate user confirmation
            };
            """)
            await remove_button.click()
            
            family_numbers_list_elements = page.get_by_role("list", name="Family members")
            new_list_items = family_numbers_list_elements.locator("li")
            new_count = await new_list_items.count()

            if new_count > 0:
                first_item = new_list_items.nth(0)
                first_button = first_item.get_by_role("button")
                await first_button.click()

            return f"Successfully removed family member: {name}"
    

   

    return f"Successfully removed family member: {name}"


async def add_spouse(first_name: str, last_name: str):
    """
    Add a spouse to the current session.
    
    Args:
        first_name: The first name of the spouse.
        last_name: The last name of the spouse.
        
    Returns:
        A message indicating whether the spouse was added successfully or not.
    """

    page = await playwright_helper.get_page()
    if page is None:
        return "Ufile didn't load, please try again"
    if await page.locator('div.spouseHide').count() > 0:
        return "Spouse already added."
    
    add_spouse_button = page.locator('#displayAddSpouse')
    if await add_spouse_button.count() == 0:
        return "Add spouse button not found."
    await add_spouse_button.click()
    await page.wait_for_timeout(5000)  

    identification_section = page.locator('div.tocLabel').filter(has_text='Identification')
    await identification_section.click()
    await page.wait_for_timeout(1000)

    await page.get_by_role("textbox", name="Enter Text. First name. You").fill(first_name)
    await page.get_by_role("textbox", name="Enter Text. Last name. You").fill(last_name)
    await page.wait_for_timeout(1000)
    await page.get_by_role("button", name="Next Page. CRA questions").click()
    await identification_section.click()
    # fieldsets = page.locator('fieldset')
    # fieldset_count = await fieldsets.count()

    # if fieldset_count == 0:
    #     return "No identification elements found."
    
    # for i in range(fieldset_count):
    #     id_element = fieldsets.nth(i)
    #     title_element = id_element.locator('.int-label').first
    #     input_element = id_element.locator('input[type="text"]').first
    

    return f"Successfully added spouse: {first_name} {last_name}"


if __name__ == "__main__":
    import asyncio

    async def main():
        names = await get_all_person_names()
        print(names)
        # result = await remove_person("Spouse")
        # result = await remove_person("John Doe")
        result = await add_spouse("John", "Doe")
        print(result)

    asyncio.run(main())