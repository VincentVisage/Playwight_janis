from playwright.async_api import async_playwright, Browser, Page, Locator, ElementHandle

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any

from pathlib import Path
import aiohttp
import time
import json
from pprint import pprint

from settings import API_URL


class Ebay():
    auth_url = "https://signin.ebay.com/signin/"

    def __init__(self, account: dict, headless=False, timeout=15000):
        self.login = account.get("login")
        password = account.get("password")
        if password:
            self.password = password
        self.timeout = timeout
        self.headless = headless
        self.user_dir = Path()
        self.max_pages_to_handle = 5


    @asynccontextmanager
    async def browser_context(self) -> AsyncGenerator[Browser, Any]:
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=f"profiles/{self.login}_ebay",
                headless=self.headless,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            try:
                yield context
            finally: 
                await context.close()


    @asynccontextmanager
    async def page_context(self, browser: Browser) -> AsyncGenerator[Page, Any]:
        page = await browser.new_page()

        try:
            await page.set_viewport_size({"width": 1920, "height": 1080})
            page.set_default_timeout(self.timeout)

            yield page
        finally:
            await page.close()


    async def sign_in(self, page: Page):

        """
            Sign in without context
        """
        
        """Login handling"""
        input()
        if count :=  await page.locator("#userid").count():
            await page.locator("#userid").fill(self.login, timeout=10000)
            await page.locator("#signin-continue-btn").click()

        time.sleep(3)

        """Password handling"""
        if count := await page.locator("#pass").count():
            await page.locator("#pass").fill(self.password, timeout=10000)
            await page.locator("#sgnBt").click()

        time.sleep(4)

        await page.goto("https://www.ebay.com/mye/myebay/purchase", timeout=15000)


    async def _check_login(self, page: Page):
        """Checking saved profiles"""
        await page.goto("https://www.ebay.com/mye/myebay/purchase", timeout=15000)
        if "signin" in page.url:
            return False
        else:
            return True


    async def _get_structured_purchase_order_data(self, order: Locator):
        keys = ["order_state", "order_date", "order_total", "order_number", "order_link"]
        order_data = []
        elements = await order.locator(".primary__item--item-text").all()
        for el in elements:
                text = await el.text_content()
                order_data.append(text)
        del order_data[5]
        del order_data[3]
        del order_data[1]
        order_link = await order.get_by_role("link").filter(has_text="View order details").get_attribute("href")
        order_data.append(order_link)

        
        order_data = dict(zip(keys, order_data))
        return order_data
    

    async def _collect_data_from_purchase_page(self, page: Page):
        orders = await page.locator(".m-order-card").all() 
        data= []
        for order in orders:
            order_state_tag = order.locator(".primary__item--item-text").first
            order_state = await order_state_tag.text_content()
            if order_state in ["Delivered"]:
                continue
              # список локаторов
            order_data = await self._get_structured_purchase_order_data(order=order)
            data.append(order_data)
        
        # if data:
            # print(data)

        return data
            
    
    async def _order_page(self, page: Page, links: list[str]):
        data = []
        for link in links:
            await page.goto(link)
            order_data = await self._collect_order_page(page=page)
            data.append(order_data)
        self.data = data
        # await page.goto(links[0])
        # await self._collect_order_page(page=page)
        # input()

    async def _collect_order_page(self, page: Page):
        time.sleep(1)
        try:
            order = {
                "order_number": None,
                "po_date": None,
                "order_summary": {
                    "items_price": None,
                    "shipping": None,
                    "tax": None,
                    "order_total": None,
                },
                "account": self.login,
                "marketplace": "ebay",
                "dev_state": None,
                "vendor": None,
                "track_number": None,
                "product": {
                    "title": None,
                    "price": None,
                    "item_qty": 1,
                    "product_id": None,
                }
            }



            order_box = page.locator(".order-box")

            order_info = await order_box.locator(".order-info").locator(".section").locator(".vodlabelsValues").all()
            order_info_list = [await info.locator("dd").text_content() for info in order_info]
            order["order_number"] = order_info_list[1]
            order["po_date"] = order_info_list[0]
            order["vendor"] = order_info_list[3]

            shipment_box = order_box.locator(".shipment-info")

            if count:= await shipment_box.locator(".shipment-card-sub-title").count():
                order_dev_sate = await shipment_box.locator(".shipment-card-sub-title").all()
                if len(order_dev_sate) == 1:
                    order["dev_state"] = await shipment_box.locator(".shipment-card-sub-title").text_content()
                else:
                    order["dev_state"] = "Returned or Canceled"
            else:
                order["dev_state"] = "Returned or Canceled"

            if count:= await shipment_box.locator(".tracking-box").locator(".tracking-info").locator(".tracking-info-details").filter(has_text="Number").count():
                order["track_number"] = await shipment_box.locator(".tracking-box").locator(".tracking-info").locator("dd").text_content()
            else:
                order["track_number"] = "Awaiting shipment"

            item = shipment_box.locator(".item-card")
            order["product"]["title"] = await (await item.locator(".item-title").all())[0].text_content()
            item_details = await item.locator(".item-details-info").locator(".item-aspect-value").all()
            order["product"]["product_id"] = (await item_details[0].text_content()).split(":")[1].strip()
            if len(item_details) == 3:
                try:
                    order["product"]["item_qty"] = int((await item_details[1].text_content()).split(" ")[2])
                except:
                    pass
            order["product"]["price"] = float(( await (await item.locator(".item-price").all())[0].text_content()).split(" ")[-1].replace("$", "").replace(",", "").replace("C", "")) / order["product"]["item_qty"]
            
            order_summary = page.locator("#payment-info").locator(".order-summary")
            payment_items = await order_summary.locator(".payment-line-items").locator(".vodlabelsValues").all()
            if payment_items and len(payment_items) == 3:
                order["order_summary"]["items_price"] = float((await payment_items[0].locator("dd").text_content()).replace(",", "").replace("$", "").replace("C", ""))
                shipping = (await payment_items[1].locator("dd").text_content()).strip()
                if shipping == "Free":
                    order["order_summary"]["shipping"] = 0.0
                else:
                    order["order_summary"]["shipping"] = float(shipping.replace(",", "").replace("$", "").replace("C", ""))
                order["order_summary"]["tax"] = float((await payment_items[2].locator("dd").text_content()).replace(",", "").replace("$", "").replace("C", ""))
            elif payment_items and len(payment_items) == 4:
                order["order_summary"]["items_price"] = float((await payment_items[0].locator("dd").text_content()).replace(",", "").replace("$", "").replace("C", ""))
                order["order_summary"]["discount"] = float((await payment_items[1].locator("dd").text_content()).replace(",", "").replace("$", "").replace("C", ""))
                shipping = (await payment_items[2].locator("dd").text_content()).strip()
                if shipping == "Free":
                    order["order_summary"]["shipping"] = 0.0
                else:
                    order["order_summary"]["shipping"] = float(shipping.replace(",", "").replace("$", "").replace("C", ""))
                order["order_summary"]["tax"] = float((await payment_items[3].locator("dd").text_content()).replace(",", "").replace("$", "").replace("C", ""))
            order_total = await order_summary.locator(".order-summary-total").locator(".vodlabelsValues").all()
            if order_total:
                order["order_summary"]["order_total"] = float((await order_total[0].locator("dd").text_content()).replace(",", "").replace("$", "").replace("C", ""))
                
            # pprint(order)
            return order
        except Exception as e:
            print(e)
            print(page.url)
            input()

    async def _сollect_data(self, page: Page):
        is_next_page = True
        links = []
        page_n = 1
        while is_next_page and self.max_pages_to_handle >= page_n:
            data = await self._collect_data_from_purchase_page(page=page)
            if data:
                for order in data:
                    links.append(order["order_link"])
            is_next_page = await self._next_page(page=page)
            if is_next_page:
                page_n += 1

            time.sleep(1)

        if links:
            await self._order_page(page=page, links=links)
                

    async def _next_page(self, page: Page):
        button_state = await page.locator(".pagination__next").get_attribute("aria-disabled")
        try:
            if button_state != "true":
                # await page.wait_for_selector(".m-throbber", state="detached", timeout=10000)
                await page.locator(".pagination__next").click()
                await page.wait_for_load_state("networkidle")
                return True
            
            else:
                return False
        except:
            return False
    

    async def run(self):
        async with self.browser_context() as browser:
            async with self.page_context(browser=browser) as page:
                if not await self._check_login(page=page): 
                    await self.sign_in(page=page)
                await self._сollect_data(page=page)
                await self._send_data()


    async def connect(self):
        async with self.browser_context() as browser:
            async with self.page_context(browser) as page:
                await self._connection(page)


    async def _send_data(self):
        async with aiohttp.ClientSession() as session:
            if self.data:
                async with session.post(API_URL, json=self.data) as response:
                    if response.status == 200:
                        pprint(json.dumps(self.data, ensure_ascii=False, indent=2))
                        print("Fine")
                
    
    async def _connection(self, page: Page):
        await page.goto(r'https://signin.ebay.com/signin/', timeout=20000)
        input()
        