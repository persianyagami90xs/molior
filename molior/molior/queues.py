import asyncio
from datetime import datetime

from ..tools import get_local_tz

# worker queues
task_queue = asyncio.Queue()
aptly_queue = asyncio.Queue()
notification_queue = asyncio.Queue()
backend_queue = asyncio.Queue()

# build log queues
buildlogs = {}


async def enqueue(queue, item):
    return await queue.put(item)


async def dequeue(queue):
    ret = await queue.get()
    queue.task_done()
    return ret


def enqueue_task(task):
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(enqueue(task_queue, task), loop)


async def dequeue_task():
    return await dequeue(task_queue)


def enqueue_aptly(task):
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(enqueue(aptly_queue, task), loop)


async def dequeue_aptly():
    return await dequeue(aptly_queue)


def enqueue_notification(msg):
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(enqueue(notification_queue, msg), loop)


async def dequeue_notification():
    return await dequeue(notification_queue)


def enqueue_backend(msg):
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(enqueue(backend_queue, msg), loop)


async def dequeue_backend():
    return await dequeue(backend_queue)


async def enqueue_buildlog(build_id, msg):
    if build_id not in buildlogs:
        buildlogs[build_id] = asyncio.Queue()
    await buildlogs[build_id].put(msg)


def buildlog(build_id, msg):
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(enqueue_buildlog(build_id, msg), loop)


def buildlogtitle(build_id, title, no_footer_newline=False, no_header_newline=True, error=False):
    now = get_local_tz().localize(datetime.now(), is_dst=None)
    date = datetime.strftime(now, "%a, %d %b %Y %H:%M:%S %z")

    header_newline = "\n"
    if no_header_newline:
        header_newline = ""

    footer_newline = "\n"
    if no_footer_newline:
        footer_newline = ""

    color = 36
    if error:
        color = 31

    BORDER = 80 * "+"

    msg = "{}\x1b[{}m\x1b[1m{}\x1b[0m\n".format(header_newline, color, BORDER) + \
          "\x1b[{}m\x1b[1m| molior: {:36} {} |\x1b[0m\n".format(color, title, date) + \
          "\x1b[{}m\x1b[1m{}\x1b[0m\n{}".format(color, BORDER, footer_newline)

    buildlog(build_id, msg)
