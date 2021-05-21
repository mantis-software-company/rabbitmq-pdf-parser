import aio_pika
import asyncio
import io
import json
import os
import PyPDF2
import requests
from aio_pika.pool import Pool
from distutils.util import strtobool

async def consume(loop, logger=None, config=None, consumer_pool_size=10):
    if config is None:
        config = {
            "mq_host": os.environ.get('MQ_HOST'),
            "mq_port": int(os.environ.get('MQ_PORT')),
            "mq_vhost": os.environ.get('MQ_VHOST'),
            "mq_user": os.environ.get('MQ_USER'),
            "mq_pass": os.environ.get('MQ_PASS'),
            "mq_source_queue": os.environ.get('MQ_SOURCE_QUEUE'),
            "mq_target_queue": os.environ.get('MQ_TARGET_QUEUE'),
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

    async def get_connection():
        return await aio_pika.connect(
            host=config.get("mq_host"),
            port=config.get("mq_port"),
            login=config.get("mq_user"),
            password=config.get("mq_pass"),
            virtualhost=config.get("mq_vhost"),
            loop=loop
        )

    connection_pool = Pool(get_connection, max_size=consumer_pool_size, loop=loop)

    async def get_channel():
        async with connection_pool.acquire() as connection:
            return await connection.channel()

    channel_pool = Pool(get_channel, max_size=consumer_pool_size, loop=loop)

    async def _consume():
        async with channel_pool.acquire() as channel:
            queue = await channel.declare_queue(
                config.get("mq_source_queue"), durable=config.get("mq_queue_durable"), auto_delete=False
            )
            while True:
                try:
                    m = await queue.get(timeout=5 * consumer_pool_size)
                    message = m.body.decode('utf-8')
                    if logger:
                        logger.debug(message)
                    try:
                        j = json.loads(message)
                        response = requests.get(j["url"])
                        if response.status_code == 200:
                            pdf_reader = PyPDF2.PdfFileReader(io.BytesIO(response.content))
                            pages = []
                            for i in range(pdf_reader.numPages):
                                page_obj = pdf_reader.getPage(i)
                                pages.append(page_obj.extractText())
                            await _publish(x=json.dumps({"id": j["id"], "pdfText": "".join(pages)}), ch=channel)
                    except Exception as e:
                        if logger:
                            logger.error("PDF Parsing Error: %s" % (e,))
                        raise e
                    else:
                        m.ack()
                except aio_pika.exceptions.QueueEmpty:
                    if logger:
                        logger.info("Queue empty. Stopping.")
                    break

    async def _publish(x, ch):
        await ch.default_exchange.publish(
            aio_pika.Message(x.encode("utf-8")),
            config.get("mq_source_queue"),
        )

    async with connection_pool, channel_pool:
        consumer_pool = []
        if logger:
            logger.info("Consumers started")
        for _ in range(consumer_pool_size):
            consumer_pool.append(_consume())

        await asyncio.gather(*consumer_pool)

