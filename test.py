import asyncio
import time

async def async_func():
    print('new start')
    await asyncio.sleep(3)
    print('new end')
    return 'a'

def old_school_func():
    print('old start')
    time.sleep(5)
    print('old end')
    return 'b'

loop = asyncio.get_event_loop()
#result = loop.run_in_executor(None, old_school_func)

group = asyncio.gather(loop.run_in_executor(None, old_school_func), async_func())

results = loop.run_until_complete(group)
print('Result -> ' + str(results))
