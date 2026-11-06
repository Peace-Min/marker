from types import SimpleNamespace
from marker.renderers.chunk import json_to_chunks

for page_number, block_number in ((0, 6), (12, 27)):
    leaf = SimpleNamespace(id=f"/page/{page_number}/Text/1", block_type="Text", html="<p>Example</p>",
                           children=None, images={}, polygon=[[0, 0], [10, 0], [10, 10], [0, 10]],
                           bbox=[0, 0, 10, 10], section_hierarchy={})
    page = SimpleNamespace(id=f"/page/{page_number}/Page/{block_number}", block_type="Page", children=[leaf])
    chunks = json_to_chunks(page, set())
    assert chunks[0].page == page_number
print("PASS chunk page index is independent of page block number")
