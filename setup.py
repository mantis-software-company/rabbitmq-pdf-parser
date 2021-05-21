import setuptools

setuptools.setup(
    name="mq2mq-pdfparser",
    version="1.0.0",
    author="Furkan Kalkan",
    author_email="info@mantis.com.tr",
    description="Asynchronous job library that consume RabbitMQ for PDF urls and publish pdf text back.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    platforms="all",
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Internet",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
	"Topic :: Software Development :: Testing",
        "Intended Audience :: Developers",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Operating System :: Microsoft",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8"
    ],
    install_requires=['requests','PyPDF2', 'aio_pika'],
    python_requires=">3.6.*, <4",
    packages=['rabbitmq2psql_as_json'],
    scripts=['bin/mq2mq-pdfparser']
)
