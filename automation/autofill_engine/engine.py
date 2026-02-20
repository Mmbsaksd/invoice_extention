import asyncio
import logging
import os
from playwright.async_api import async_playwright

# Configuration & Logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class SAPAutomation:
    """Manages SAP web automation with support for CDP and standard modes."""
    
    def __init__(self, headless: bool = False):
        self.headless = headless

    async def fill_single_invoice(self, invoice_data: dict, sap_url: str, use_existing: bool = True, cdp_url: str = "http://127.0.0.1:9222"):
        """Fills exactly ONE invoice into SAP. Human MUST perform submission."""
        p = await async_playwright().start()
        browser = None
        try:
            if use_existing:
                browser, page = await self._connect_to_existing(p, sap_url, cdp_url)
            else:
                browser, page = await self._launch_new(p, sap_url)

            await page.bring_to_front()
            ref = invoice_data.get("reference", "Unknown")
            logger.info(f"Production Fill: {ref}")

            # 1. Fill all fields (with Precision Mapping)
            all_filled = await self._fill_all_fields(page, invoice_data)
            
            if all_filled:
                return {"status": "success", "message": f"Fill Complete: {ref}. Please verify and click Post."}
            else:
                return {"status": "error", "message": f"Partial Fill: {ref}. Some fields were skipped due to low confidence."}

        except Exception as e:
            logger.error(f"Fill Error: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            if browser and not use_existing: await browser.close()
            await p.stop()

    async def _connect_to_existing(self, p, sap_url, cdp_url):
        """Connects via CDP and exhaustively checks for a matching SAP tab."""
        import httpx
        logger.info(f"CDP PROBE: Checking if Chrome is alive at {cdp_url}...")
        
        try:
            async with httpx.AsyncClient() as client:
                probe = await client.get(f"{cdp_url.rstrip('/')}/json/list", timeout=2.0)
                tabs = probe.json()
        except Exception as probe_e:
            raise ConnectionError(
                f"Chrome is NOT listening on {cdp_url}. \n\n"
                "Please ensure you launched Chrome with: \n"
                '--remote-debugging-port=9222 --user-data-dir="C:\\temp\\chrome_dev"'
            )

        try:
            browser = await p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            raise ConnectionError(f"Failed to attach Playwright to CDP: {e}")
        
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        
        def normalize(u):
            u = u.lower().split("?")[0].split("#")[0]
            for prefix in ["https://", "http://", "file://", "www."]:
                u = u.replace(prefix, "")
            return u.strip("/")
        
        target = normalize(sap_url)
        for page in context.pages:
            if target in normalize(page.url) or normalize(page.url) in target:
                return browser, page
        
        for page in context.pages:
            if "sap" in page.url.lower():
                return browser, page

        if len(context.pages) == 1 and "about:blank" not in context.pages[0].url:
            return browser, context.pages[0]

        page = await context.new_page()
        await page.goto(sap_url, wait_until="domcontentloaded")
        return browser, page

    async def _launch_new(self, p, sap_url):
        browser = await p.chromium.launch(headless=self.headless)
        page = await (await browser.new_context()).new_page()
        await page.goto(sap_url, wait_until="domcontentloaded")
        return browser, page

    async def _fill_all_fields(self, page, data):
        from automation.field_mapper.mapper import get_mapping
        mapping = get_mapping()
        total_success = True
        for label, key, expected_type in mapping:
            val = data.get(key)
            if val:
                success = await self._fill_field(page, label, val, expected_type)
                if not success:
                    total_success = False
                await asyncio.sleep(0.1)
        return total_success

    async def _fill_field(self, page, label_text: str, val: str, expected_type: str) -> bool:
        try:
            clean_val = "".join(c for c in str(val) if c.isdigit() or c in ".-") if expected_type == "number" else str(val)
            result = await page.evaluate(self.SELECTOR_JS, [label_text, expected_type])
            if result['status'] == 'OK':
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(clean_val, delay=5)
                await page.keyboard.press("Tab")
                return True
        except: pass
        return False

    import os
    selector_path = os.path.join(os.path.dirname(__file__), "..", "selector_engine", "selector.js")
    SELECTOR_JS = ""
    if os.path.exists(selector_path):
        with open(selector_path, "r") as f:
            SELECTOR_JS = f.read() + "\n\n// Trigger the function\nreturn selectorLogic(arguments[0]);"

async def run_single_fill(invoice_data, url, use_existing=True):
    return await SAPAutomation().fill_single_invoice(invoice_data, url, use_existing)
