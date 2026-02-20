import asyncio
import logging
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
        
        # 1. Probe the port first to give a better error message
        try:
            async with httpx.AsyncClient() as client:
                probe = await client.get(f"{cdp_url.rstrip('/')}/json/list", timeout=2.0)
                tabs = probe.json()
                logger.info(f"CDP PROBE SUCCESS: Found {len(tabs)} open tabs/targets.")
        except Exception as probe_e:
            logger.error(f"CDP PROBE FAILED: {probe_e}")
            raise ConnectionError(
                f"Chrome is NOT listening on {cdp_url}. \n\n"
                "Please ensure you launched Chrome with: \n"
                '--remote-debugging-port=9222 --user-data-dir="C:\\temp\\chrome_dev"'
            )

        # 2. Connect Playwright
        try:
            browser = await p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            raise ConnectionError(f"Failed to attach Playwright to CDP: {e}")
        
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        
        def normalize(u):
            # Remove protocol, host-prefixes, query/hash, and trailing slash
            u = u.lower().split("?")[0].split("#")[0]
            for prefix in ["https://", "http://", "file://", "www."]:
                u = u.replace(prefix, "")
            return u.strip("/")
        
        target = normalize(sap_url)
        logger.info(f"Searching for target: {target}")
        
        # 1. Look for Exact or Substring Match
        for page in context.pages:
            normalized_page_url = normalize(page.url)
            logger.info(f"  Checking tab: {page.url} (Normalized: {normalized_page_url})")
            if target in normalized_page_url or normalized_page_url in target:
                logger.info(f"✅ FOUND MATCH: Reusing tab '{page.url}'")
                return browser, page
        
        # 2. Heuristic: If any page contains 'sap' in the URL, try it
        for page in context.pages:
            if "sap" in page.url.lower():
                logger.info(f"⚠️ HEURISTIC MATCH: Reusing suspicious tab '{page.url}'")
                return browser, page

        # 3. Fallback for single-tab sessions as a last resort
        if len(context.pages) == 1 and "about:blank" not in context.pages[0].url:
            logger.info(f"💡 FALLBACK: Reusing only open tab '{context.pages[0].url}'")
            return browser, context.pages[0]

        logger.info("❌ No matching tab found. Opening NEW tab.")
        page = await context.new_page()
        await page.goto(sap_url, wait_until="domcontentloaded")
        return browser, page

    async def _launch_new(self, p, sap_url):
        """Launches a fresh browser instance."""
        logger.info("STANDARD MODE: Launching fresh browser.")
        browser = await p.chromium.launch(headless=self.headless)
        page = await (await browser.new_context()).new_page()
        await page.goto(sap_url, wait_until="domcontentloaded")
        return browser, page

    async def _fill_all_fields(self, page, data):
        mapping = [
            ("Supplier", "supplier", "text"),
            ("Invoice date", "invoice_date", "date"),
            ("Posting Date", "posting_date", "date"),
            ("Reference", "reference", "text"),
            ("Amount", "amount", "number"),
            ("Tax Amount", "tax_amount", "number")
        ]
        total_success = True
        for label, key, expected_type in mapping:
            val = data.get(key)
            if val:
                success = await self._fill_field(page, label, val, expected_type)
                if not success:
                    total_success = False
                await asyncio.sleep(0.2)
        return total_success

    async def _fill_field(self, page, label_text: str, val: str, expected_type: str) -> bool:
        """Precision Mapping Engine (Section 9 & 10). Returns True if filled."""
        try:
            # Type-specific cleaning
            if expected_type == "number":
                clean_val = "".join(c for c in str(val) if c.isdigit() or c in ".-")
            else:
                clean_val = str(val)

            # Execution logic via JS for 95% confidence check
            result = await page.evaluate("""([labelText, type]) => {
                const getBestText = (el) => (el.innerText || el.textContent || "").trim().toLowerCase();
                const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea, [role="textbox"]'));
                
                // Tiered Matching Strategy
                let bestMatch = null;
                let confidence = 0;

                for (const input of inputs) {
                    const id = (input.id || "").toLowerCase();
                    const name = (input.name || "").toLowerCase();
                    const placeholder = (input.placeholder || "").toLowerCase();
                    const aria = (input.getAttribute('aria-label') || "").toLowerCase();
                    const label = input.labels?.[0]?.innerText.toLowerCase() || "";
                    const target = labelText.toLowerCase();

                    // 1. Aria or Managed Label (High Confidence)
                    if (aria.includes(target) || label.includes(target)) { confidence = 1.0; bestMatch = input; break; }
                    
                    // 2. Placeholder (High Confidence)
                    if (placeholder.includes(target)) { confidence = 0.98; bestMatch = input; break; }

                    // 3. ID/Name matches (Medium Confidence)
                    if (id.includes(target.replace(" ", "")) || name.includes(target.replace(" ", ""))) { 
                        confidence = 0.96; bestMatch = input; 
                    }
                }

                // 4. Structural Fallback (Only if no attributes found)
                if (!bestMatch) {
                    const labelEls = Array.from(document.querySelectorAll('label, div, span, b, bdi')).filter(el => {
                        const t = getBestText(el);
                        return t === labelText.toLowerCase() || t === (labelText.toLowerCase() + ":");
                    });

                    if (labelEls.length > 0) {
                        let container = labelEls[0].parentElement;
                        for (let i = 0; i < 3; i++) {
                            if (!container) break;
                            const found = container.querySelector('input:not([type="hidden"]), textarea, [role="textbox"]');
                            if (found) { bestMatch = found; confidence = 0.95; break; }
                            container = container.parentElement;
                        }
                    }
                }

                if (bestMatch && confidence >= 0.95) {
                    // Wrong Field Prevention (Section 10)
                    const iType = bestMatch.type || "text";
                    if (type === 'number' && iType !== 'number' && iType !== 'text') return { status: 'TYPE_MISMATCH' };

                    bestMatch.focus();
                    bestMatch.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    bestMatch.style.border = "3px solid #2ecc71"; // Success Green
                    return { status: 'OK', method: 'Precision' };
                }

                return { status: 'LOW_CONFIDENCE', confidence };
            }""", [label_text, expected_type])

            if result['status'] == 'OK':
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(clean_val, delay=10)
                await page.keyboard.press("Tab")
                logger.info(f"✅ Filled '{label_text}'")
                return True
            elif result['status'] == 'LOW_CONFIDENCE':
                logger.warning(f"⚠️ Low confidence for '{label_text}'. Skipping to ensure accuracy.")
                return False
            elif result['status'] == 'TYPE_MISMATCH':
                logger.error(f"❌ Type mismatch for '{label_text}'. Operation stopped.")
                return False

        except Exception as e:
            logger.warning(f"⚠️ Error filling '{label_text}': {e}")
            return False
        return False

async def run_single_fill(invoice_data, url, use_existing=True):
    return await SAPAutomation().fill_single_invoice(invoice_data, url, use_existing)
