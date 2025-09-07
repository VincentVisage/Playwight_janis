from parsers.amazon.amazon import Amazon

import asyncio


new_account = {
    "login": "",
    }

async def add_new_account_amazon(new_account):
    amazon_acc = Amazon(account=new_account)
    await amazon_acc.connect()

if __name__ == "__main__":
    asyncio.run(add_new_account_amazon(new_account))