import render
from ampera_docx import AmperaDoc

def fn(pages):
    d = AmperaDoc("WorkHub Template\nSmoke Test", "AMP_WH_TST_001", "0.1", "12-Nov-2026", "WorkHub")
    d.toc()
    d.doc_info([("Prepared By", "Jim, Janagan, Jayasree"), ("Status", "Draft for review")])
    d.h("2. Executive Summary", 1)
    d.p("WorkHub replaces three Zoho apps with one web tool built by Ampera. This is body text in the template body font to check justification and spacing across a few lines of text so it wraps.")
    d.tiles([("57.5", "person-days committed"), ("63", "person-days available"), ("26.3", "in the Dec 1 slice")])
    d.callout("Key point", "A callout uses a navy left bar and a light fill.")
    d.h("3. Table check", 1)
    d.h("3.1 Sub heading", 2)
    d.table(["Field", "Detail", "Owner"], [["One", "Alpha **bold** and `mono`", "Jim"], ["Two", "Beta text\nsecond line", "Janagan"]], [1.2, 4.0, 1.3])
    d.bullets(["First bullet", "Second bullet with more words to wrap if needed"])
    d.closing(4, "Jim, Janagan, Jayasree", "Initial draft")
    return d

pdf, n, missing = render.build(fn, "_smoke.docx")
print(pdf, n, "pages; headings without page:", missing)
render.contact(pdf, "_ref/smoke.png", 0, 8, 4, 55)
