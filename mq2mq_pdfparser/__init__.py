import aiohttp
import aio_pika
import asyncio
import io
import json
import os
import PyPDF2
from aio_pika.pool import Pool
from distutils.util import strtobool
from functools import partial

async def run(loop, logger=None, config=None, consumer_pool_size=10):
    async def _get_connection():
        return await aio_pika.connect(
            host=config.get("mq_host"),
            port=config.get("mq_port"),
            login=config.get("mq_user"),
            password=config.get("mq_pass"),
            virtualhost=config.get("mq_vhost"),
            loop=loop
        )

    async def _get_channel():
        async with connection_pool.acquire() as connection:
            return await connection.channel()

    def _parse_file(pdf_content):
        pdf_reader = PyPDF2.PdfFileReader(io.BytesIO(pdf_content))
        pages = []
        for page in range(pdf_reader.numPages):
            page_obj = pdf_reader.getPage(page)
            pages.append(page_obj.extractText())
        return "".join(pages)

    async def _publish(content, channel):
        exchange = await channel.get_exchange(config.get("mq_target_exchange"))
        await exchange.publish(
            aio_pika.Message(content.encode("utf-8")),
            config.get("mq_target_routing_key"),
        )

    async def _consume(consumer_id):
        async with channel_pool.acquire() as channel:
            queue = await channel.declare_queue(
                config.get("mq_source_queue"), durable=config.get("mq_queue_durable"), auto_delete=False
            )
            while True:
                try:
                    m = await queue.get(timeout=300 * consumer_pool_size)
                    message = m.body.decode('utf-8')
                    if logger:
                        logger.debug(message)
                    try:
                        j = json.loads(message)
                        async with aiohttp.ClientSession() as session:
                            async with session.get(j["url"]) as response:
                                if response.status == 200:
                                    buffer = await response.read()
                                    pdf_text = await loop.run_in_executor(None, partial(_parse_file, buffer))
                                    await _publish(json.dumps({"id": j["id"], "pdf_text": pdf_text}), channel=channel)
                                    logger.debug("Consumer %s: pdf %s sent" % (consumer_id, j["id"]))
                                else:
                                    logger.error("Http Error: %s returns %s" % (j["url"], response.status))
                    except Exception as e:
                        if logger:
                            logger.error("PDF Parsing Error: %s" % (e,))
                        raise e
                    else:
                        m.ack()
                except aio_pika.exceptions.QueueEmpty:
                    if logger:
                        logger.info("Consumer %s: Queue empty. Stopping." % consumer_id)
                    break

    if config is None:
        config = {
            "mq_host": os.environ.get('MQ_HOST'),
            "mq_port": int(os.environ.get('MQ_PORT', '5672')),
            "mq_vhost": os.environ.get('MQ_VHOST'),
            "mq_user": os.environ.get('MQ_USER'),
            "mq_pass": os.environ.get('MQ_PASS'),
            "mq_source_queue": os.environ.get('MQ_SOURCE_QUEUE'),
            "mq_target_exchange": os.environ.get('MQ_TARGET_EXCHANGE'),
            "mq_target_routing_key": os.environ.get("MQ_TARGET_ROUTING_KEY"),
            "mq_queue_durable": bool(strtobool(os.environ.get('MQ_QUEUE_DURABLE', 'True'))),
            "consumer_pool_size": os.environ.get("CONSUMER_POOL_SIZE"),
        }

    if "consumer_pool_size" in config:
        if config.get("consumer_pool_size"):
            try:
                consumer_pool_size = int(config.get("consumer_pool_size"))
            except TypeError as e:
                if logger:
                    logger.error("Invalid pool size: %s" % (consumer_pool_size,))
                raise e

    connection_pool = Pool(_get_connection, max_size=consumer_pool_size, loop=loop)
    channel_pool = Pool(_get_channel, max_size=consumer_pool_size, loop=loop)

    async with connection_pool, channel_pool:
        consumer_pool = []
        if logger:
            logger.info("Consumers started")
        for i in range(consumer_pool_size):
            consumer_pool.append(_consume(consumer_id=i))

        await asyncio.gather(*consumer_pool)

