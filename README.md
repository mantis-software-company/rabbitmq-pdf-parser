
# mq2mq-pdfparser

mq2mq-pdfparser is asynchronous job library that consume RabbitMQ for PDF urls and publish pdf text back to RabbitMQ. It stops when queue is empty.

## Installation

You can install this library easily with pip.
`pip install mq2mq-pdfparser` 

## Usage

Data must send to source queue should this format: 

`{"id": "foo", "url": "http://example.com/foo/bar.pdf"}`


### As a library
```py
import os
import asyncio
from mq2mq_pdfparser import consume

if __name__ == '__main__':
    logger = logging.getLogger("mq2mq_pdfparser")
    logger.setLevel(os.environ.get('LOG_LEVEL', "DEBUG"))
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            os.environ.get('LOG_FORMAT', "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    )
    logger.addHandler(handler)

    config = {
      "mq_host": os.environ.get('MQ_HOST'),
	  "mq_port": int(os.environ.get('MQ_PORT')), 
	  "mq_vhost": os.environ.get('MQ_VHOST'),
	  "mq_user": os.environ.get('MQ_USER'),
	  "mq_pass": os.environ.get('MQ_PASS'),
	  "mq_source_queue": os.environ.get('MQ_SOURCE_QUEUE'),
          "mq_target_queue": os.environ.get('MQ_TARGET_QUEUE')
    }
  
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        consume(
          loop=loop,
          consumer_pool_size=10,
          config=config
        )
    )

loop.close()
```

### Standalone
You can also call this library as standalone PDF parser job.  Just set required environment variables and run `mq2mq-pdfparser`. This usecase perfectly fits when you need run it on cronjobs or kubernetes jobs. 

**Required environment variables:**
- MQ_HOST
- MQ_PORT (optional)
- MQ_VHOST
- MQ_USER
- MQ_PASS
- MQ_SOURCE_QUEUE (Queue that job consume urls)
- MQ_TARGET_QUEUE (Queue that job publish texts)
- MQ_QUEUE_DURABLE (optional, default value: True)
- SQL_TEMPLATE (DB Insert query template. Ex: `insert into logs (body) values (%s);`)
-  CONSUMER_POOL_SIZE (optional, default value: 10)
-  LOG_LEVEL (Logging level. See: [Python logging module docs](https://docs.python.org/3/library/logging.html#logging-levels))

**Example Kubernetes job:** 
 ```yaml
# TO DO: Add Kubernetes job here.
 ```

