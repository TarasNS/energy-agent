"""The five slides on docs/presentation.html. Owner: Lead.

Edit the text here, then run make docs. Keep each slide to a headline and at most three short items.
"""

SLIDES = [
    dict(tone="dark", kicker="Energy 4.0 Harness", title="Ask. Check. Approve.",
         sub="A chat assistant for solar and battery portfolios.", foot="First proof of concept · synthetic data", items=[]),
    dict(tone="light", kicker="The problem", title="Useful AI is hard to trust.", sub="", foot="", items=[
        ("Wrong numbers", "A model can make up a figure."),
        ("Data in the wrong place", "Company data should not go to just any model."),
        ("Actions without people", "An assistant should never act alone."),
    ]),
    dict(tone="paper", kicker="The solution", title="A chat that shows its work.", sub="", foot="", items=[
        ("1  Ask", "A manager asks in plain words."),
        ("2  Calculate", "Tested code makes every number."),
        ("3  Approve", "A person decides what happens next."),
    ]),
    dict(tone="dark", kicker="Why you can trust it", title="Three promises.", sub="", foot="", items=[
        ("Numbers from code", "The server hides any number the tools did not return."),
        ("Actions need a person", "The model proposes. It cannot approve."),
        ("Everything audited", "Every proposal and approval is logged."),
    ]),
    dict(tone="light", kicker="Where we stand", title="Three minutes, then real data.", sub="", foot="", items=[
        ("Today", "Built from scratch by five people from one spec: 13 KPIs, nine tools and a chat with charts, on synthetic data."),
        ("Next", "One real data source, then a second workflow."),
        ("Decision", "Which data source do we validate first?"),
    ]),
]
