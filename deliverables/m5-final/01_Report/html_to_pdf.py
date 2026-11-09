import sys
from playwright.sync_api import sync_playwright
src,dst=sys.argv[1],sys.argv[2]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); pg.goto('file://'+src); pg.wait_for_timeout(800)
    pg.pdf(path=dst, format='A4', print_background=True, display_header_footer=True, header_template='<span></span>',
           footer_template='<div style="width:100%;text-align:center;font-size:8px;color:#777"><span class="pageNumber"></span></div>',
           margin={'top':'20mm','bottom':'18mm','left':'20mm','right':'20mm'})
    b.close()
