"""Local LLM layer (LM Studio, OpenAI-compatible API).

The LLM never counts: it receives the profile computed by ``roche_poc.stats`` and
writes a short narrative. ``validation`` checks every figure it cites.

client       connection to the LM Studio server
prompts      profile -> compact facts -> prompt
summary      generate_summary()
validation   automatic check that cited numbers come from the facts
"""
