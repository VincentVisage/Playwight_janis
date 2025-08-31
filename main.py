from parsers.ebay.ebay import Ebay
from parsers.amazon.amazon import Amazon
import asyncio
import time

from accounts import get_accounts

async def main():

    accounts = get_accounts()

    while True:
        for acc in accounts:
            if acc["marketplace"] == "amazon":
                amazon = Amazon(acc)
                await amazon.run()
            elif acc["marketplace"] == "ebay":
                ebay = Ebay(acc)
                await ebay.run()

if __name__ == "__main__":
    asyncio.run(main())
    