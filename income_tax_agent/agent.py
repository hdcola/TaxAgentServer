from google.adk.agents import Agent

from income_tax_agent.ufile.ufile_t3 import get_all_t3, get_t3_info, add_t3, remove_t3
from income_tax_agent.ufile.ufile_t3_update import update_t3
from income_tax_agent.ufile.ufile_t5 import get_all_t5, get_t5_info, add_t5, remove_t5, update_t5
from income_tax_agent.ufile.ufile_person import get_all_person_names, remove_person, add_spouse
from income_tax_agent.ufile.ufile_t4 import get_all_t4, add_t4, remove_t4, get_t4_info, update_t4_info

root_agent = Agent(
    name="IncomeTaxAgent",
    model="gemini-2.0-flash-exp",
    description="You are a tax agent. You can help users fill out their tax returns.",
    instruction=(
        "You are a tax agent in Canada. You can help users fill out their tax returns. "
        "You can answer questions about tax returns, provide information about tax laws, and assist with the filing process. "
    ),
    tools=[get_all_t5, get_t5_info, get_all_t3, get_t3_info,
           update_t3, add_t3, remove_t3, add_t5, remove_t5, update_t5, get_all_person_names, remove_person, add_spouse, get_all_t4, add_t4, remove_t4, get_t4_info, update_t4_info],
)
