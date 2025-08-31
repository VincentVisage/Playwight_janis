from parsers.ebay.ebay import Ebay

import asyncio

new_account = {
    "login": "9micro3",
    }

async def add_new_account_ebey(new_account):
    ebay_acc = Ebay(account=new_account)
    await ebay_acc.connect()


if __name__ == "__main__":
    asyncio.run(add_new_account_ebey(new_account))