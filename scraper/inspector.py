"""
Inspector tool to analyze fantasygems.run page structure and extract selectors
Run this locally to understand how to scrape the page properly
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def inspect_page():
    """Inspect and analyze the fantasygems.run page structure"""
    
    url = "https://www.fantasygems.run/#/saasLottery/WinGo?gameCode=WinGo_30S&lottery=WinGo"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Run with UI
        page = await browser.new_page()
        
        print(f"🔍 Navigating to {url}")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)  # Wait for JS to render
        
        # Get page source
        print("\n📄 Page loaded. Analyzing structure...\n")
        
        # List all visible elements that might contain game results
        elements_info = await page.evaluate("""
        () => {
            const info = {
                title: document.title,
                url: window.location.href,
                body_text_sample: document.body.innerText.substring(0, 500),
                divs_with_numbers: [],
                spans_with_numbers: [],
                buttons_with_numbers: [],
                all_text_nodes: []
            };
            
            // Find all divs that might contain numbers
            document.querySelectorAll('div').forEach(div => {
                const text = div.innerText?.trim();
                if (text && /[0-9]/.test(text) && text.length < 50) {
                    info.divs_with_numbers.push({
                        text: text,
                        class: div.className,
                        id: div.id,
                        data_attrs: Array.from(div.attributes)
                            .filter(a => a.name.startsWith('data-'))
                            .map(a => `${a.name}="${a.value}"`)
                            .join(' ')
                    });
                }
            });
            
            // Find all spans
            document.querySelectorAll('span').forEach(span => {
                const text = span.innerText?.trim();
                if (text && /[0-9]/.test(text) && text.length < 50) {
                    info.spans_with_numbers.push({
                        text: text,
                        class: span.className,
                        id: span.id,
                    });
                }
            });
            
            // List buttons
            document.querySelectorAll('button').forEach(btn => {
                const text = btn.innerText?.trim();
                if (text && /[0-9]/.test(text) && text.length < 50) {
                    info.buttons_with_numbers.push({
                        text: text,
                        class: btn.className,
                    });
                }
            });
            
            return info;
        }
        """)
        
        print("=" * 80)
        print("PAGE ANALYSIS RESULTS")
        print("=" * 80)
        
        print(f"\n📌 Title: {elements_info['title']}")
        print(f"📌 URL: {elements_info['url']}")
        
        if elements_info['divs_with_numbers']:
            print(f"\n📦 Found {len(elements_info['divs_with_numbers'])} DIVs with numbers:")
            for i, div in enumerate(elements_info['divs_with_numbers'][:10]):  # Show first 10
                print(f"  [{i}] Text: '{div['text']}'")
                if div['class']:
                    print(f"      Class: {div['class']}")
                if div['id']:
                    print(f"      ID: {div['id']}")
                if div['data_attrs']:
                    print(f"      Data: {div['data_attrs']}")
                print()
        
        if elements_info['spans_with_numbers']:
            print(f"\n🏷️  Found {len(elements_info['spans_with_numbers'])} SPANs with numbers:")
            for i, span in enumerate(elements_info['spans_with_numbers'][:5]):
                print(f"  [{i}] Text: '{span['text']}', Class: {span['class']}")
        
        if elements_info['buttons_with_numbers']:
            print(f"\n🔘 Found {len(elements_info['buttons_with_numbers'])} BUTTONs with numbers:")
            for i, btn in enumerate(elements_info['buttons_with_numbers'][:5]):
                print(f"  [{i}] Text: '{btn['text']}', Class: {btn['class']}")
        
        # Try common game result selectors
        print("\n" + "=" * 80)
        print("TESTING COMMON SELECTORS")
        print("=" * 80)
        
        selectors_to_test = [
            ("Result number (div.number)", "div.number"),
            ("Result container", ".result"),
            ("Game result", ".game-result"),
            ("Number display", "[class*='number']"),
            ("Result text", "[class*='result']"),
            ("Lottery result", "[class*='lottery']"),
            ("Current number", "[class*='current']"),
            ("Display text (common in Vue/React)", ".text-display"),
            ("Any large text", "h1, h2, h3, .title"),
        ]
        
        for name, selector in selectors_to_test:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    texts = []
                    for elem in elements[:3]:  # Get first 3
                        text = await elem.text_content()
                        if text:
                            texts.append(text.strip())
                    if texts:
                        print(f"\n✅ {name}")
                        print(f"   Selector: {selector}")
                        print(f"   Found {len(elements)} elements")
                        print(f"   Sample texts: {texts}")
            except Exception as e:
                pass
        
        # Get all network requests to find API endpoints
        print("\n" + "=" * 80)
        print("NETWORK REQUESTS (during page load)")
        print("=" * 80)
        
        network_logs = await page.evaluate("""
        () => {
            // This is a basic attempt - Playwright logs might be better
            return "Check browser DevTools Network tab for API calls"
        }
        """)
        
        print(network_logs)
        print("\n💡 Tip: Open browser DevTools (F12) and check:")
        print("   - Network tab for API calls returning game results")
        print("   - Look for JSON responses with number/result data")
        print("   - Check WebSocket connections for real-time updates")
        
        # Keep browser open for manual inspection
        print("\n🔍 Browser is open for inspection. Press Enter to close...")
        input()
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_page())
