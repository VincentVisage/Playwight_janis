from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, Page, Locator, ElementHandle, TimeoutError, expect
from pathlib import Path
from typing import AsyncGenerator, Any

import time
import json
import aiohttp
from pprint import pprint

from settings import API_URL


class Amazon():

    def __init__(self, account: dict, headless=False, timeout=30000):
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
                user_data_dir=f"profiles/{self.login}_amazon",
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


    async def _sign_in(self, page: Page):

        """
            Sign in without context
        """
        if "signin" in page.url:
            await page.goto(r'https://www.amazon.com/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com%2F%3Fref_%3Dnav_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=usflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0', timeout=20000)


        """Login handling"""    
        if count := await page.locator("#ap_email_login").count():
            await page.locator("#ap_email_login").fill(self.login)
            await page.locator("#continue").click()

        if count := await page.locator('[type="password]').count():
            await page.locator('[type="password]').fill(self.password, timeout=5000)
            await page.locator("#signInSubmit").click()
            """Password handling"""
            
        await page.goto("https://www.amazon.com/gp/css/order-history?ref_=abn_yadd_ad_your_orders")
        

    async def _check_login(self, page: Page):
        # print(self._check_login.__name__)
        try:
            await page.goto("https://www.amazon.com/gp/css/order-history?ref_=abn_yadd_ad_your_orders")
        except:
            print("It's log page")

        if (count := await page.locator("#ap_password").count()) or (count := await page.locator("#ap_email").count()):
            await self._sign_in(page=page)
        

    async def _old_parse(self, page: Page):

        order_box = []

        shipments = await page.locator(".a-box.shipment").all()
        for shipment in shipments:
            arriving_shipment_box = {
                "dev_state": None,
                "products": [],
            }
            dev_states_raw = await shipment.locator('.shipment-top-row').locator(".a-row").all()
            for i, dev_state_elem in enumerate(dev_states_raw):
                if i == 0:
                    dev_state_raw = await dev_state_elem.locator(".a-size-medium.a-text-bold").first.text_content()
                    arriving_shipment_box["dev_state"] = " ".join(dev_state_raw.split())

            

            shipment_boxes = await shipment.locator('.yohtmlc-item').all()
            
            for shipment_box in shipment_boxes:

                product = {
                    "title": None,
                    "price": None,
                    "vendor": None,
                    "item_qty": None,
                    "product_id": None,
                }

                
                order_ship = []
                is_there_item_qty = await shipment_box.locator("..").locator("..").locator(".item-view-qty").count()
                product["item_qty"] = 1
                if is_there_item_qty :
                    item_id_row = await shipment_box.locator("..").locator("..").locator(".item-view-qty").text_content()
                    product["item_qty"] = item_id_row.strip()

                if count := await shipment_box.locator('.a-row').count() :
                    rows = await shipment_box.locator('.a-row').all()
                    for row in rows:
                        if rows.index(row) == 0:
                            product_href = await row.locator('.a-link-normal').get_attribute("href")
                            product_id = product_href.split("/")[3]
                            product["product_id"] = product_id
                        text = await row.text_content()
                        order_ship.append(" ".join(text.split()))
                
            
                for value in order_ship:
                    if value == '':
                        continue
                    if order_ship.index(value) == 0:
                        product["title"] = value
                        
                    if "$" in value:
                        product["price"] = float(value.split("$")[-1].replace(",", ""))
                    if "Sold by" in value:
                        product["vendor"] = " ".join(value.split(":")[1].split())
                
                # print(order_ship_data)
                arriving_shipment_box["products"].append(product)
                # print((await shipment_box.inner_html()).split())
            order_box.append(arriving_shipment_box)

        return order_box
        

    async def _new_parse(self, page: Page):

        try:
            order_box = []

            shipments_boxes = await page.locator('[data-component="shipments"]').locator('.a-box').all()
            for shipment_box in shipments_boxes:

                arriving_shipment_box = {
                "dev_state": None,
                "products": [],
                }

                arriving_shipment_box["dev_state"] = (await shipment_box.locator('[data-component="shipmentStatus"]').locator(".a-color-base.od-status-message").text_content()).strip()


                product_pages = await shipment_box.locator('[data-component="purchasedItems"]').locator(".a-fixed-left-grid").all()
                for product_page in product_pages:

                    product = {
                    "title": None,
                    "price": None,
                    "vendor": None,
                    "item_qty": None,
                    "product_id": None,
                    }

                    if count := await product_page.locator(".od-item-view-qty").count():
                        product["item_qty"] = (await product_page.locator(".od-item-view-qty").text_content()).strip()
                    else:
                        product["item_qty"] = 1




                    try:
                        title_row = product_page.locator('[data-component="itemTitle"]')
                        product["title"] = (await title_row.text_content()).strip()
                    except:

                        title_row = product_page.locator('[data-component="itemTitle"]').first
                        product['title'] = (await title_row.text_content()).strip()

                        # title_rows = await product_page.locator('[data-component="itemTitle"]').all()
                        # for title in title_rows:
                        #     print((await title.text_content()).strip())
                        #     print(page.url)
                        # input()




                    product_href = await title_row.locator('.a-link-normal').get_attribute("href")
                    product_id = product_href.split("/")[2].split("?")[0]
                    product["product_id"] = product_id

                    vendor_row = await product_page.locator('[data-component="orderedMerchant"]').text_content()
                    product["vendor"] = vendor_row.split(":")[-1].strip()

                    price_row = await product_page.locator('[data-component="unitPrice"]').locator('[aria-hidden="true"]').text_content()
                    product["price"] = float(price_row.strip().replace("$", "").replace(",", ""))

                    arriving_shipment_box["products"].append(product)

                    order_box.append(arriving_shipment_box)
                
            return order_box    
        except Exception as e:
            print(e)
            input()

    async def _order_page(self, links, page: Page):
        BASE_URL = "https://www.amazon.com/"
        data = []
        for link in links:
            await page.goto(BASE_URL + link)
            data_from_page = await self._collect_order_page(page=page)
            data.append(data_from_page)

        if data:
            self.data = data
        # await page.goto(BASE_URL + links[1])
        # await page.goto("https://www.amazon.com/gp/your-account/order-details?ie=UTF8&orderID=113-4484373-2961815&ref=ab_ppx_yo_dt_b_fed_order_details")
        # await self._collect_order_page(page=page)
        # pprint(data)



    async def _collect_order_page(self ,page: Page):

        order = {
            "order_number": None,
            "po_date": None,
            "order_summary": {},
            "account": self.login,
            "marketplace": "amazon",
            "shipments": [

            ],
        }
        time.sleep(1)
        order["order_number"] = await page.locator('[data-component="orderId"] > span').text_content()
        order["po_date"] = await page.locator('[data-component="orderDate"] > span').text_content()

        summary_field = page.locator('[data-component="chargeSummary"]')
        # order_summary = (await summary_field.locator('.a-spacing-small').text_content()).strip().lower()
        summary_fields = await summary_field.locator(".od-line-item-row").all()
        for summary_fieled_row in summary_fields:
            string_list = (await summary_fieled_row.text_content()).split()
            low_string_list = [ s.lower().replace("$", "").replace(":", "") for s in string_list ]
            sum_name = "_".join(low_string_list[:-1])
            sum_value = float(low_string_list[-1].replace(",", ""))
            order["order_summary"][sum_name] = sum_value
            
            
        shipments = []
        
        if count:= await page.locator(".a-box.shipment").count():
            order["shipments"] = await self._old_parse(page)
        elif count:= await page.locator('[data-component="shipments"]').locator('.a-box').count():
            order["shipments"] = await self._new_parse(page)
        else:
            order["shipments"] = "Canceled"
            print("Order Canceled")
          
        # pprint(order)
        return order

    
    async def _collect_data(self, page: Page):

        links = []
        next_page = True
        page_num = 1
        while self.max_pages_to_handle >= page_num and next_page:
            try:
                await page.wait_for_selector("#orderCard")
                order_cards = await page.locator("id=orderCard").all()
                for order_card in order_cards:
                    order_delivery_boxes = await order_card.locator("id=orderCardDeliveryBox").all()
                    should_add_link = False
            
                    for order_delivery_box in order_delivery_boxes:
                        delivery_state = await order_delivery_box.locator('span.a-color-base.a-text-bold').text_content(timeout=3000)
                        delivery_state = delivery_state.strip()
                        if not any(delivers in delivery_state for delivers in ["Delivered", "Cancelled"]):
                            should_add_link = True
                            break  
            
                    if should_add_link:
                        link = await order_card.locator(".a-link-normal").filter(has_text="View order details").get_attribute("href", timeout=1500)
                        if link and link not in links: 
                            links.append(link)

            except TimeoutError:
                # print("страница завершена")
                pass
            except Exception as e:  
                print(e)

            
            page_num += 1
            # print(page_num)
            if count := await page.locator(".a-pagination").locator('a[href="#pagination/next/"]').filter(has_text="Next").count():
                await page.locator(".a-pagination").locator('a[href="#pagination/next/"]').filter(has_text="Next").click()
            else:
                next_page = False

        if links:
            await self._order_page(links=links, page=page)


    
    async def run(self):
        async with self.browser_context() as browser:
            async with self.page_context(browser) as page:
                await self._check_login(page=page)
                await self._collect_data(page=page)
                await self._send_data()

    
    async def connect(self):
        async with self.browser_context() as browser:
            async with self.page_context(browser) as page:
                await self._connection(page)


    async def _connection(self, page: Page):
        await page.goto(r'https://www.amazon.com/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com%2F%3Fref_%3Dnav_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=usflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0', timeout=20000)
        input()


    async def _send_data(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=self.data) as response:
                if response.status == 200:
                    print(json.dumps(self.data, ensure_ascii=False, indent=2))
                    print("Fine")